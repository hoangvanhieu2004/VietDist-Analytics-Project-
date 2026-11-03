-- =====================================================================================
-- fact_distributor_orders (VIEW) — đơn hàng nhà phân phối. Task 3.2 (bổ sung cho BR-B-01/B-02)
-- Grain: 1 dòng / (order_id, product_id)
-- distributor_sk: bản ghi dim_distributors hiệu lực tại order_date (SCD2); không khớp -> -1.
-- qty_delivered_effective / delivered_amount_effective = 0 với dòng Cancelled (A-16);
-- Fill Rate = Σ qty_delivered_effective / Σ qty_ordered (A-17); is_ontime tính lại từ ngày (A-18).
-- =====================================================================================
SELECT dwh.drop_relation('fact_distributor_orders');

CREATE VIEW dwh.fact_distributor_orders AS
SELECT
    o.order_id,
    o.product_id,
    to_char(o.order_date, 'YYYYMMDD')::int                            AS date_key,
    o.order_date,
    o.distributor_id,
    coalesce(d.distributor_sk, -1)                                    AS distributor_sk,
    o.region,
    o.channel,
    o.product_category,
    o.qty_ordered,
    o.qty_delivered,
    o.qty_delivered_effective,
    o.fill_rate_pct,
    o.unit_price_list,
    o.distributor_price,
    o.gross_amount,
    o.delivered_amount,
    o.delivered_amount_effective,
    o.expected_delivery_date,
    o.actual_delivery_date,
    o.is_ontime,
    o.ontime_delivery,
    o.delivery_status,
    o.payment_terms
FROM staging.stg_distributor_orders o
LEFT JOIN dwh.dim_distributors d
       ON d.distributor_id = o.distributor_id
      AND o.order_date BETWEEN d.effective_from AND d.effective_to;
