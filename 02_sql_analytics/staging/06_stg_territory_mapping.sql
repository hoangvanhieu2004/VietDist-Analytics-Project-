-- stg_territory_mapping — phân công KH cho NV (SRC-08). expiry_date 9999-12-31 = đang hiệu lực.
-- Không dùng để suy ra vùng của giao dịch (A-20).
DROP TABLE IF EXISTS staging.stg_territory_mapping CASCADE;

CREATE TABLE staging.stg_territory_mapping AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(territory_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.territory_mapping r
)
SELECT
    staging.clean_text(territory_id)                                  AS territory_id,
    staging.clean_text(employee_id)                                   AS employee_id,
    staging.clean_text(customer_id)                                   AS customer_id,
    staging.clean_text(region)                                        AS region,
    staging.clean_text(team)                                          AS team,
    staging.cast_date(effective_date, 'territory_mapping.effective_date') AS effective_date,
    staging.cast_date(expiry_date, 'territory_mapping.expiry_date')     AS expiry_date,
    staging.clean_text(version)                                       AS version,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_territory_mapping ADD PRIMARY KEY (territory_id);
