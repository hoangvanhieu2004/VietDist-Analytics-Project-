-- =====================================================================================
-- fact_targets (VIEW) — chỉ tiêu theo NV / tháng / phiên bản (temporal fact). Task 3.2
-- Grain: 1 dòng / (version_code, employee_id, year, month) — giữ mọi phiên bản (Task 2.3).
-- employee_sk: bản ghi dim_employees hiệu lực tại ngày đầu tháng của target (NV chuyển vùng 01/07
-- -> target từ T7 tính cho vùng mới). date_key = ngày đầu tháng.
-- Lọc chỉ tiêu đang áp dụng: is_latest; kế hoạch đầu năm: is_original;
-- point-in-time: <ngày> BETWEEN effective_date AND expiry_date.
-- =====================================================================================
SELECT dwh.drop_relation('fact_targets');

CREATE VIEW dwh.fact_targets AS
SELECT
    t.version_code,
    t.version_number,
    t.version_date,
    t.employee_id,
    coalesce(e.employee_sk, -1)                                       AS employee_sk,
    t.year,
    t.month,
    to_char(t.target_month, 'YYYYMMDD')::int                          AS date_key,
    t.target_month,
    t.target_revenue,
    t.target_quantity,
    t.target_new_customers,
    t.effective_date,
    t.expiry_date,
    t.is_latest,
    t.is_original,
    t.superseded_by
FROM staging.stg_sales_targets_versioned t
LEFT JOIN dwh.dim_employees e
       ON e.employee_id = t.employee_id
      AND t.target_month BETWEEN e.effective_from AND e.effective_to;
