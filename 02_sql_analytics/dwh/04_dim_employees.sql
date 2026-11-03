-- =====================================================================================
-- dim_employees (VIEW) — nhân viên, SCD Type 2, tính hoàn toàn từ staging. Task 3.1.2
-- Khoá: employee_sk (kiểm tra bằng test)
-- Nguồn: stg_employees (mỗi version là 1 snapshot đầy đủ; v1 hiệu lực 2024-01-01, v2 2024-07-01
-- = ngày trong Change_Log, A-19).
-- Thuộc tính theo dõi lịch sử: region, team, position, status. Chỉ tạo bản ghi mới khi 1 trong
-- các thuộc tính này đổi so với snapshot trước; snapshot không đổi được gộp (A-26).
--   effective_from: bản ghi đầu = join_date (A-31); bản ghi sau = effective_date của snapshot
--   effective_to:   effective_from của bản ghi kế tiếp − 1 ngày; bản ghi cuối 9999-12-31
--   is_current:     bản ghi cuối của mỗi NV
-- Join với fact: fact.date BETWEEN effective_from AND effective_to.
-- employee_sk = -1: UNKNOWN. employee_sk = row_number theo (employee_id, effective_from): cùng dữ liệu
-- staging -> cùng khoá; fact (view) tính lại cùng lúc nên luôn khớp.
-- =====================================================================================
SELECT dwh.drop_relation('dim_employees');

CREATE VIEW dwh.dim_employees AS
WITH snapshots AS (
    SELECT e.*,
           row_number() OVER w                                        AS snapshot_no,
           lag(region)   OVER w                                       AS prev_region,
           lag(team)     OVER w                                       AS prev_team,
           lag(position) OVER w                                       AS prev_position,
           lag(status)   OVER w                                       AS prev_status
    FROM staging.stg_employees e
    WINDOW w AS (PARTITION BY employee_id
                 ORDER BY effective_date, substring(version FROM '[0-9]+')::int)
),
changes AS (
    -- snapshot đầu tiên + snapshot có thuộc tính theo dõi thay đổi
    SELECT s.*,
           concat_ws(', ',
               CASE WHEN region   IS DISTINCT FROM prev_region   THEN 'region'   END,
               CASE WHEN team     IS DISTINCT FROM prev_team     THEN 'team'     END,
               CASE WHEN position IS DISTINCT FROM prev_position THEN 'position' END,
               CASE WHEN status   IS DISTINCT FROM prev_status   THEN 'status'   END) AS changed_attrs
    FROM snapshots s
    WHERE snapshot_no = 1
       OR region   IS DISTINCT FROM prev_region
       OR team     IS DISTINCT FROM prev_team
       OR position IS DISTINCT FROM prev_position
       OR status   IS DISTINCT FROM prev_status
),
versioned AS (
    SELECT c.*,
           CASE WHEN c.snapshot_no = 1 THEN least(c.join_date, c.effective_date)
                ELSE c.effective_date END                             AS effective_from,
           CASE WHEN c.snapshot_no = 1 THEN 'Khởi tạo'
                ELSE coalesce(
                    (SELECT string_agg(ch.change_type, ', ')
                     FROM staging.stg_employee_changes ch
                     WHERE ch.employee_id = c.employee_id AND ch.effective_date = c.effective_date),
                    'Thay đổi ' || c.changed_attrs) END               AS change_reason
    FROM changes c
)
SELECT
    (row_number() OVER (ORDER BY employee_id, effective_from))::int   AS employee_sk,
    employee_id,
    full_name,
    gender,
    date_of_birth,
    join_date,
    position,
    region,
    team,
    email,
    phone,
    status,
    resign_date,
    transfer_note,
    dq_underage_at_join,
    effective_from,
    coalesce(lead(effective_from) OVER (PARTITION BY employee_id ORDER BY effective_from) - 1,
             DATE '9999-12-31')                                       AS effective_to,
    (lead(effective_from) OVER (PARTITION BY employee_id ORDER BY effective_from) IS NULL) AS is_current,
    change_reason,
    version                                                           AS source_version
FROM versioned
UNION ALL
SELECT -1, '-1', 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'UNKNOWN', NULL, NULL, NULL,
       DATE '1900-01-01', DATE '9999-12-31', true, 'Unknown member', NULL;
