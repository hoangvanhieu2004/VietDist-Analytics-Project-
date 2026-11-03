-- stg_sales_targets — chỉ tiêu bán hàng theo phiên bản (SRC-02), chỉ cast + dedup.
-- 1 dòng / (version_label, employee_id, year, month). Logic hiệu lực (effective/expiry/is_latest)
-- làm ở Task 2.3 (stg_sales_targets_versioned).
-- Dựa trên layout long của file thật; nếu sau này có file layout wide (month_col/target_value),
-- year/month sẽ NULL và PRIMARY KEY báo lỗi -> cần bổ sung logic cho layout đó.
DROP TABLE IF EXISTS staging.stg_sales_targets CASCADE;

CREATE TABLE staging.stg_sales_targets AS
WITH typed AS (
    SELECT
        staging.clean_text(version_label)                             AS version_label,
        staging.clean_text(employee_id)                               AS employee_id,
        staging.cast_int(year, 'sales_targets_raw.year')                AS year,
        staging.cast_int(month, 'sales_targets_raw.month')              AS month,
        staging.clean_text(month_col)                                 AS month_col,
        staging.clean_text(plan_version)                              AS plan_version,
        staging.cast_date(version_date, 'sales_targets_raw.version_date') AS version_date,
        staging.cast_date(effective_from, 'sales_targets_raw.effective_from') AS effective_from,
        staging.cast_date(effective_to, 'sales_targets_raw.effective_to') AS effective_to,
        staging.clean_text(employee_name)                             AS employee_name,
        staging.clean_text(region)                                    AS region,
        staging.clean_text(team)                                      AS team,
        staging.cast_num(target_revenue, 'sales_targets_raw.target_revenue') AS target_revenue,
        staging.cast_int(target_quantity, 'sales_targets_raw.target_quantity') AS target_quantity,
        staging.cast_int(target_new_customers, 'sales_targets_raw.target_new_customers') AS target_new_customers,
        _source_file, _source_sheet, _batch_id, _ingested_at
    FROM raw.sales_targets_raw
),
ranked AS (
    SELECT t.*,
           ROW_NUMBER() OVER (PARTITION BY version_label, employee_id, year, month
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM typed t
)
SELECT version_label, employee_id, year, month, month_col, plan_version, version_date,
       effective_from, effective_to, employee_name, region, team,
       target_revenue, target_quantity, target_new_customers,
       _source_file, _source_sheet, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_sales_targets ADD PRIMARY KEY (version_label, employee_id, year, month);
