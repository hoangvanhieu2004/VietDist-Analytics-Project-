-- =====================================================================================
-- dim_customers (VIEW) — khách hàng, SCD Type 1. Task 3.1. Khoá: customer_id (kiểm tra bằng test)
-- Thêm: first_order_date / last_order_date (BR-A-03), net_revenue, loyalty_tier (A-30):
--   net_revenue = Σ net_amount dòng Delivered − Σ return_amount phiếu 'Đã xử lý' (A-21),
--                 trên toàn bộ dữ liệu hiện có
--   Xếp hạng KH có net_revenue > 0: top 10% Platinum, 20% kế Gold, 30% kế Silver, còn lại Bronze;
--   KH có giao dịch nhưng net_revenue <= 0 -> Bronze; KH chưa có giao dịch -> 'Chưa mua'.
-- Dòng customer_id = '-1' / UNKNOWN cho fact không khớp KH.
-- =====================================================================================
SELECT dwh.drop_relation('dim_customers');

CREATE VIEW dwh.dim_customers AS
WITH sales AS (
    SELECT customer_id,
           sum(net_amount) FILTER (WHERE is_delivered) AS delivered_net,
           min(order_date)                             AS first_order_date,
           max(order_date)                             AS last_order_date
    FROM staging.stg_sales_transactions
    GROUP BY customer_id
),
returns AS (
    SELECT customer_id, sum(return_amount) FILTER (WHERE is_processed) AS returned
    FROM staging.stg_returns
    GROUP BY customer_id
),
revenue AS (
    SELECT s.customer_id, s.first_order_date, s.last_order_date,
           coalesce(s.delivered_net, 0) - coalesce(r.returned, 0) AS net_revenue
    FROM sales s
    LEFT JOIN returns r USING (customer_id)
),
ranked AS (
    SELECT customer_id,
           percent_rank() OVER (ORDER BY net_revenue DESC) AS revenue_rank_pct
    FROM revenue
    WHERE net_revenue > 0
)
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_type,
    c.channel,
    c.province,
    c.region,
    c.address,
    c.phone,
    c.tax_code,
    c.join_date,
    c.credit_limit,
    c.status,
    rv.first_order_date,
    rv.last_order_date,
    coalesce(rv.net_revenue, 0)                                       AS net_revenue,
    CASE
        WHEN rv.customer_id IS NULL         THEN 'Chưa mua'
        WHEN rk.revenue_rank_pct IS NULL    THEN 'Bronze'
        WHEN rk.revenue_rank_pct < 0.10     THEN 'Platinum'
        WHEN rk.revenue_rank_pct < 0.30     THEN 'Gold'
        WHEN rk.revenue_rank_pct < 0.60     THEN 'Silver'
        ELSE 'Bronze'
    END                                                               AS loyalty_tier,
    c._batch_id                                                       AS _source_batch_id
FROM staging.stg_customers c
LEFT JOIN revenue rv USING (customer_id)
LEFT JOIN ranked rk USING (customer_id)
UNION ALL
SELECT '-1', 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, 0, 'UNKNOWN', NULL;
