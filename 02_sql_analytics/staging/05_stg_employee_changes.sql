-- stg_employee_changes — lịch sử chuyển vùng / nghỉ việc (SRC-07, sheet Change_Log).
-- effective_date là mốc thay đổi chính thức dùng cho SCD2 (A-19).
DROP TABLE IF EXISTS staging.stg_employee_changes CASCADE;

CREATE TABLE staging.stg_employee_changes AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(employee_id), staging.clean_text(effective_date),
                                           staging.clean_text(change_type)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.employee_change_log r
)
SELECT
    staging.clean_text(employee_id)                                   AS employee_id,
    staging.cast_date(effective_date, 'employee_change_log.effective_date') AS effective_date,
    staging.clean_text(change_type)                                   AS change_type,
    staging.clean_text(employee_name)                                 AS employee_name,
    staging.clean_text(old_region)                                    AS old_region,
    staging.clean_text(new_region)                                    AS new_region,
    staging.clean_text(old_team)                                      AS old_team,
    staging.clean_text(new_team)                                      AS new_team,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_employee_changes ADD PRIMARY KEY (employee_id, effective_date, change_type);
