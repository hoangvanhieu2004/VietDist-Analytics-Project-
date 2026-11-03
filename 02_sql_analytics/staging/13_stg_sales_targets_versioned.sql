-- =====================================================================================
-- Task 2.3 — Sales target theo phiên bản (temporal fact, SCD2 áp cho fact)
--
-- stg_sales_targets_versioned: GIỮ MỌI phiên bản, 1 dòng / (version_code, employee_id, year, month).
--   Phạm vi của 1 phiên bản = các tháng từ tháng của effective_from đến effective_to.
--   Phiên bản mới thay thế TOÀN BỘ các tháng trong phạm vi của nó (A-28): dòng cũ của mọi NV
--   trong các tháng đó hết hạn, kể cả NV không có mặt trong phiên bản mới (vd NV đã nghỉ).
--   effective_date = effective_from của phiên bản (ngày hiệu lực, không phải ngày ban hành — A-29)
--   expiry_date    = effective_from của phiên bản kế tiếp phủ tháng đó − 1 ngày; 9999-12-31 nếu chưa bị thay
--   is_latest      = target đang áp dụng cho (NV, tháng)
--   is_original    = phiên bản đầu tiên có target cho (NV, tháng) — "kế hoạch đầu năm"
-- Point-in-time: WHERE <ngày> BETWEEN effective_date AND expiry_date
--
-- stg_target_version_calendar: 1 dòng / (year, month) — tháng đó đang áp dụng phiên bản nào.
-- Không giới hạn số phiên bản; thứ tự theo số trong version_code (v10 sau v9).
-- =====================================================================================

DROP TABLE IF EXISTS staging.stg_sales_targets_versioned CASCADE;

CREATE TABLE staging.stg_sales_targets_versioned AS
WITH targets AS (
    SELECT t.*,
           substring(t.version_label FROM '[0-9]+')::int AS version_number,
           make_date(t.year, t.month, 1)                 AS target_month
    FROM staging.stg_sales_targets t
),
versions AS (
    -- phạm vi hiệu lực của từng phiên bản (test kiểm tra mỗi phiên bản chỉ có 1 bộ ngày)
    SELECT version_label,
           version_number,
           min(version_date)                             AS version_date,
           min(effective_from)                           AS effective_from,
           date_trunc('month', min(effective_from))::date AS scope_from,
           max(effective_to)                             AS scope_to
    FROM targets
    GROUP BY version_label, version_number
)
SELECT
    t.version_label                                      AS version_code,
    t.version_number,
    t.version_date,
    t.employee_id,
    t.employee_name,
    t.region,
    t.team,
    t.year,
    t.month,
    t.target_month,
    t.target_revenue,
    t.target_quantity,
    t.target_new_customers,
    v.effective_from                                     AS effective_date,
    coalesce(nv.effective_from - 1, DATE '9999-12-31')   AS expiry_date,
    (nv.version_label IS NULL)                           AS is_latest,
    (t.version_number = min(t.version_number) OVER (PARTITION BY t.employee_id, t.year, t.month))
                                                         AS is_original,
    nv.version_label                                     AS superseded_by,
    t._source_file, t._source_sheet, t._batch_id, t._ingested_at
FROM targets t
JOIN versions v ON v.version_label = t.version_label
LEFT JOIN LATERAL (
    -- phiên bản kế tiếp (số nhỏ nhất lớn hơn) có phạm vi phủ tháng này
    SELECT nx.version_label, nx.effective_from
    FROM versions nx
    WHERE nx.version_number > t.version_number
      AND t.target_month BETWEEN nx.scope_from AND nx.scope_to
    ORDER BY nx.version_number
    LIMIT 1
) nv ON true;

ALTER TABLE staging.stg_sales_targets_versioned ADD PRIMARY KEY (version_code, employee_id, year, month);


DROP TABLE IF EXISTS staging.stg_target_version_calendar CASCADE;

CREATE TABLE staging.stg_target_version_calendar AS
WITH versions AS (
    -- cùng định nghĩa phạm vi như stg_sales_targets_versioned
    SELECT version_label                                  AS version_code,
           substring(version_label FROM '[0-9]+')::int    AS version_number,
           min(effective_from)                            AS effective_from,
           date_trunc('month', min(effective_from))::date AS scope_from,
           max(effective_to)                              AS scope_to
    FROM staging.stg_sales_targets
    GROUP BY version_label
),
months AS (
    SELECT DISTINCT year, month, make_date(year, month, 1) AS target_month
    FROM staging.stg_sales_targets
)
SELECT
    m.year,
    m.month,
    m.target_month,
    cur.version_code                                     AS effective_version,
    cur.version_number                                   AS effective_version_number,
    cur.effective_from                                   AS version_effective_date,
    (SELECT string_agg(v.version_code, ', ' ORDER BY v.version_number)
     FROM versions v
     WHERE m.target_month BETWEEN v.scope_from AND v.scope_to) AS versions_covering
FROM months m
CROSS JOIN LATERAL (
    -- phiên bản số lớn nhất có phạm vi phủ tháng này
    SELECT v.version_code, v.version_number, v.effective_from
    FROM versions v
    WHERE m.target_month BETWEEN v.scope_from AND v.scope_to
    ORDER BY v.version_number DESC
    LIMIT 1
) cur;

ALTER TABLE staging.stg_target_version_calendar ADD PRIMARY KEY (year, month);
