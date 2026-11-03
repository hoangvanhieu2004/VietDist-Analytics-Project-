-- =====================================================================================
-- fact_sales (VIEW) — giao dịch bán hàng. Task 3.2.1. Grain: 1 dòng / (order_id, product_id)
-- employee_sk: bản ghi dim_employees hiệu lực tại order_date (SCD2); không khớp -> -1 (UNKNOWN).
-- net_revenue: = net_amount nếu Delivered, ngược lại 0 (A-21). Trừ hàng trả nằm ở fact_returns.
-- is_promo: SP có chương trình KM (không tính 'Planned') đang chạy vào ngày bán, khớp kênh và vùng
--           của giao dịch hoặc KM áp dụng 'All' (A-24, A-35) — BR-A-03 doanh thu trong / ngoài KM.
-- =====================================================================================
SELECT dwh.drop_relation('fact_sales');

CREATE VIEW dwh.fact_sales AS
SELECT
    s.order_id,
    s.product_id,
    to_char(s.order_date, 'YYYYMMDD')::int                            AS date_key,
    s.order_date,
    s.customer_id,
    s.employee_id,
    coalesce(e.employee_sk, -1)                                       AS employee_sk,
    s.region,
    s.province,
    s.channel,
    s.quantity,
    s.unit_price,
    s.discount_pct,
    s.discount_amount,
    s.gross_amount,
    s.net_amount,
    CASE WHEN s.is_delivered THEN s.net_amount ELSE 0 END             AS net_revenue,
    s.delivery_status,
    s.payment_method,
    s.payment_status,
    s.is_delivered,
    EXISTS (
        SELECT 1
        FROM staging.stg_promotion_products pp
        JOIN staging.stg_promotions p USING (promotion_id)
        WHERE pp.product_id = s.product_id
          AND p.status <> 'Planned'
          AND s.order_date BETWEEN p.start_date AND p.end_date
          AND p.target_channel IN ('All', s.channel)
          AND p.target_region IN ('All', s.region)
    )                                                                 AS is_promo,
    s.is_before_customer_join
FROM staging.stg_sales_transactions s
LEFT JOIN dwh.dim_employees e
       ON e.employee_id = s.employee_id
      AND s.order_date BETWEEN e.effective_from AND e.effective_to;
