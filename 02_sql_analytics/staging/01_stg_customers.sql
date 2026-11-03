-- stg_customers — khách hàng (SRC-03). SCD1: 1 dòng / customer_id, giữ bản load mới nhất.
DROP TABLE IF EXISTS staging.stg_customers CASCADE;

CREATE TABLE staging.stg_customers AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(customer_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.customer_master r
)
SELECT
    staging.clean_text(customer_id)                                   AS customer_id,
    staging.clean_text(customer_name)                                 AS customer_name,
    staging.clean_text(customer_type)                                 AS customer_type,
    staging.clean_text(channel)                                       AS channel,
    staging.clean_text(province)                                      AS province,
    staging.clean_text(region)                                        AS region,
    staging.clean_text(address)                                       AS address,
    staging.clean_text(phone)                                         AS phone,
    staging.clean_text(tax_code)                                      AS tax_code,
    staging.cast_date(join_date, 'customer_master.join_date')           AS join_date,
    staging.cast_num(credit_limit, 'customer_master.credit_limit')      AS credit_limit,
    staging.clean_text(status)                                        AS status,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_customers ADD PRIMARY KEY (customer_id);
