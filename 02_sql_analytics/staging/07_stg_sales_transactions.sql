-- stg_sales_transactions — giao dịch bán hàng (SRC-01). Grain: 1 dòng / (order_id, product_id).
-- is_delivered:            dòng được tính doanh thu (A-21)
-- is_before_customer_join: cờ chất lượng — ngày bán trước ngày KH tham gia (A-23), dữ liệu giữ nguyên
-- discount_amount giữ nguyên nguồn (làm tròn 100đ, A-22). Cần chạy sau 01_stg_customers.
DROP TABLE IF EXISTS staging.stg_sales_transactions CASCADE;

CREATE TABLE staging.stg_sales_transactions AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(order_id), staging.clean_text(product_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.sales_transactions r
),
typed AS (
    SELECT
        staging.clean_text(order_id)                                  AS order_id,
        staging.clean_text(product_id)                                AS product_id,
        staging.cast_date(order_date, 'sales_transactions.order_date')  AS order_date,
        staging.cast_int(order_month, 'sales_transactions.order_month') AS order_month,
        staging.cast_int(order_quarter, 'sales_transactions.order_quarter') AS order_quarter,
        staging.cast_int(order_year, 'sales_transactions.order_year')   AS order_year,
        staging.clean_text(customer_id)                               AS customer_id,
        staging.clean_text(employee_id)                               AS employee_id,
        staging.clean_text(region)                                    AS region,
        staging.clean_text(province)                                  AS province,
        staging.clean_text(channel)                                   AS channel,
        staging.clean_text(product_category)                          AS product_category,
        staging.cast_int(quantity, 'sales_transactions.quantity')       AS quantity,
        staging.cast_num(unit_price, 'sales_transactions.unit_price')   AS unit_price,
        staging.cast_num(discount_pct, 'sales_transactions.discount_pct') AS discount_pct,
        staging.cast_num(discount_amount, 'sales_transactions.discount_amount') AS discount_amount,
        staging.cast_num(gross_amount, 'sales_transactions.gross_amount') AS gross_amount,
        staging.cast_num(net_amount, 'sales_transactions.net_amount')   AS net_amount,
        staging.clean_text(delivery_status)                           AS delivery_status,
        staging.clean_text(payment_method)                            AS payment_method,
        staging.clean_text(payment_status)                            AS payment_status,
        _source_file, _batch_id, _ingested_at
    FROM ranked
    WHERE rn = 1
)
SELECT t.*,
       (t.delivery_status = 'Delivered')                              AS is_delivered,
       coalesce(t.order_date < c.join_date, false)                    AS is_before_customer_join
FROM typed t
LEFT JOIN staging.stg_customers c ON c.customer_id = t.customer_id;

ALTER TABLE staging.stg_sales_transactions ADD PRIMARY KEY (order_id, product_id);
