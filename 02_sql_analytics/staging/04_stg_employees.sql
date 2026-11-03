-- stg_employees — nhân viên (SRC-07, sheet Employee_v*). 1 dòng / (employee_id, version):
-- mỗi version là 1 snapshot đầy đủ; dim_employees (SCD2) dựng ở Phase 3.
-- dq_underage_at_join: cờ chất lượng — vào làm khi chưa đủ 18 tuổi (A-23), dữ liệu giữ nguyên.
DROP TABLE IF EXISTS staging.stg_employees CASCADE;

CREATE TABLE staging.stg_employees AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(employee_id), staging.clean_text(version)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.employee_master r
),
typed AS (
    SELECT
        staging.clean_text(employee_id)                               AS employee_id,
        staging.clean_text(version)                                   AS version,
        staging.cast_date(effective_date, 'employee_master.effective_date') AS effective_date,
        staging.clean_text(full_name)                                 AS full_name,
        staging.clean_text(gender)                                    AS gender,
        staging.cast_date(date_of_birth, 'employee_master.date_of_birth') AS date_of_birth,
        staging.cast_date(join_date, 'employee_master.join_date')       AS join_date,
        staging.clean_text(position)                                  AS position,
        staging.clean_text(region)                                    AS region,
        staging.clean_text(team)                                      AS team,
        staging.clean_text(email)                                     AS email,
        staging.clean_text(phone)                                     AS phone,
        staging.clean_text(status)                                    AS status,
        staging.cast_date(resign_date, 'employee_master.resign_date')   AS resign_date,
        staging.clean_text(transfer_note)                             AS transfer_note,
        _source_file, _source_sheet, _batch_id, _ingested_at
    FROM ranked
    WHERE rn = 1
)
SELECT t.*,
       (t.join_date < t.date_of_birth + interval '18 years')          AS dq_underage_at_join
FROM typed t;

ALTER TABLE staging.stg_employees ADD PRIMARY KEY (employee_id, version);
