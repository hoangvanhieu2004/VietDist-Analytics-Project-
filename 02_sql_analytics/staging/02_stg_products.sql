-- stg_products — sản phẩm (SRC-04, sheet Products). SCD1: 1 dòng / product_id.
DROP TABLE IF EXISTS staging.stg_products CASCADE;

CREATE TABLE staging.stg_products AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(product_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.product_master r
)
SELECT
    staging.clean_text(product_id)                                    AS product_id,
    staging.clean_text(product_name)                                  AS product_name,
    staging.clean_text(category)                                      AS category,
    staging.clean_text(sub_category)                                  AS sub_category,
    staging.clean_text(unit)                                          AS unit,
    staging.cast_num(unit_price, 'product_master.unit_price')           AS unit_price,
    staging.cast_num(cost_price, 'product_master.cost_price')           AS cost_price,
    staging.cast_int(weight_gram, 'product_master.weight_gram')         AS weight_gram,
    staging.clean_text(status)                                        AS status,
    staging.cast_date(launch_date, 'product_master.launch_date')        AS launch_date,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_products ADD PRIMARY KEY (product_id);
