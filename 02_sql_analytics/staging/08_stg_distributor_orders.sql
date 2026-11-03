-- stg_distributor_orders — đơn hàng nhà phân phối (SRC-05). Grain: 1 dòng / (order_id, product_id).
-- ontime_delivery:            giá trị gốc của nguồn (Yes/No -> boolean), giữ để đối chiếu
-- is_ontime:                  tính lại = actual_delivery_date <= expected_delivery_date (A-18)
-- qty_delivered_effective,
-- delivered_amount_effective: = 0 với dòng Cancelled, còn lại = giá trị nguồn (A-16); dùng cho Fill Rate (A-17)
DROP TABLE IF EXISTS staging.stg_distributor_orders CASCADE;

CREATE TABLE staging.stg_distributor_orders AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(order_id), staging.clean_text(product_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.distributor_orders r
),
typed AS (
    SELECT
        staging.clean_text(order_id)                                  AS order_id,
        staging.clean_text(product_id)                                AS product_id,
        staging.cast_date(order_date, 'distributor_orders.order_date')  AS order_date,
        staging.cast_int(order_month, 'distributor_orders.order_month') AS order_month,
        staging.cast_int(order_quarter, 'distributor_orders.order_quarter') AS order_quarter,
        staging.clean_text(distributor_id)                            AS distributor_id,
        staging.clean_text(region)                                    AS region,
        staging.clean_text(channel)                                   AS channel,
        staging.clean_text(product_category)                          AS product_category,
        staging.cast_int(qty_ordered, 'distributor_orders.qty_ordered') AS qty_ordered,
        staging.cast_int(qty_delivered, 'distributor_orders.qty_delivered') AS qty_delivered,
        staging.cast_num(fill_rate_pct, 'distributor_orders.fill_rate_pct') AS fill_rate_pct,
        staging.cast_num(unit_price_list, 'distributor_orders.unit_price_list') AS unit_price_list,
        staging.cast_num(distributor_price, 'distributor_orders.distributor_price') AS distributor_price,
        staging.cast_num(gross_amount, 'distributor_orders.gross_amount') AS gross_amount,
        staging.cast_num(delivered_amount, 'distributor_orders.delivered_amount') AS delivered_amount,
        staging.cast_date(expected_delivery_date, 'distributor_orders.expected_delivery_date') AS expected_delivery_date,
        staging.cast_date(actual_delivery_date, 'distributor_orders.actual_delivery_date') AS actual_delivery_date,
        staging.cast_bool(ontime_delivery, 'distributor_orders.ontime_delivery') AS ontime_delivery,
        staging.clean_text(delivery_status)                           AS delivery_status,
        staging.clean_text(payment_terms)                             AS payment_terms,
        _source_file, _source_sheet, _batch_id, _ingested_at
    FROM ranked
    WHERE rn = 1
)
SELECT t.*,
       (t.actual_delivery_date <= t.expected_delivery_date)           AS is_ontime,
       CASE WHEN t.delivery_status = 'Cancelled' THEN 0 ELSE t.qty_delivered END    AS qty_delivered_effective,
       CASE WHEN t.delivery_status = 'Cancelled' THEN 0 ELSE t.delivered_amount END AS delivered_amount_effective
FROM typed t;

ALTER TABLE staging.stg_distributor_orders ADD PRIMARY KEY (order_id, product_id);
