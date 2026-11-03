-- stg_returns — phiếu trả hàng (SRC-09). 1 dòng / return_id.
-- is_processed: phiếu được trừ khỏi Net Revenue (status = 'Đã xử lý', A-21)
DROP TABLE IF EXISTS staging.stg_returns CASCADE;

CREATE TABLE staging.stg_returns AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(return_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.return_transactions r
)
SELECT
    staging.clean_text(return_id)                                     AS return_id,
    staging.clean_text(original_order_id)                             AS original_order_id,
    staging.clean_text(product_id)                                    AS product_id,
    staging.cast_date(return_date, 'return_transactions.return_date')   AS return_date,
    staging.cast_int(return_month, 'return_transactions.return_month')  AS return_month,
    staging.clean_text(customer_id)                                   AS customer_id,
    staging.clean_text(employee_id)                                   AS employee_id,
    staging.clean_text(region)                                        AS region,
    staging.clean_text(province)                                      AS province,
    staging.cast_int(return_quantity, 'return_transactions.return_quantity') AS return_quantity,
    staging.cast_num(unit_price, 'return_transactions.unit_price')      AS unit_price,
    staging.cast_num(return_amount, 'return_transactions.return_amount') AS return_amount,
    staging.clean_text(return_reason)                                 AS return_reason,
    staging.clean_text(status)                                        AS status,
    (staging.clean_text(status) = 'Đã xử lý')                         AS is_processed,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_returns ADD PRIMARY KEY (return_id);
