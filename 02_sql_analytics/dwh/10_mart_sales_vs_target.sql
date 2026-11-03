-- =====================================================================================
-- mart_sales_vs_target (VIEW) — thực tế vs chỉ tiêu theo NV / tháng, MỌI phiên bản. Task 3.2.2
-- Grain: 1 dòng / (employee_id, year, month, version_code) — BR-A-01, BR-A-02.
--   - Có target: 1 dòng cho mỗi phiên bản có target (vd T8: v1 và v2).
--   - Có thực tế nhưng KHÔNG có target đang áp dụng: thêm 1 dòng version_code = NULL, để khi lọc
--     is_latest tổng thực tế vẫn đầy đủ.
--   is_latest = dòng của phiên bản đang áp dụng cho (NV, tháng) (hoặc dòng không-target ở trên).
-- !! Các cột thực tế LẶP LẠI trên mỗi dòng phiên bản: trong Power BI luôn lọc 1 phiên bản
--    (mặc định is_latest = TRUE) trước khi SUM, nếu không sẽ cộng trùng (A-37).
-- Thực tế (A-21, A-36):
--   actual_net_revenue = Σ net Delivered (theo order_date) − Σ trả 'Đã xử lý' (theo return_date)
--   active_customers   = số KH khác nhau có dòng Delivered trong tháng
--   new_customers      = số KH có đơn đầu tiên (dim_customers.first_order_date) trong tháng
-- region/team/employee_sk: cơ cấu tổ chức tại ngày đầu tháng (dim_employees SCD2).
-- achieve_pct = actual / target × 100 (NULL nếu target = 0 / không có target).
-- ly_* = cùng tháng năm trước; NULL khi chưa có dữ liệu năm trước (A-25).
-- =====================================================================================
SELECT dwh.drop_relation('mart_sales_vs_target');

CREATE VIEW dwh.mart_sales_vs_target AS
WITH sales AS (
    SELECT employee_id,
           date_trunc('month', order_date)::date                      AS month_start,
           sum(net_revenue)                                           AS delivered_net,
           sum(gross_amount) FILTER (WHERE is_delivered)              AS actual_gross,
           sum(quantity) FILTER (WHERE is_delivered)                  AS actual_quantity,
           count(DISTINCT customer_id) FILTER (WHERE is_delivered)    AS active_customers
    FROM dwh.fact_sales
    GROUP BY 1, 2
),
returns AS (
    SELECT employee_id,
           date_trunc('month', return_date)::date                     AS month_start,
           sum(return_amount_processed)                               AS returns_amount
    FROM dwh.fact_returns
    GROUP BY 1, 2
),
new_customers AS (
    SELECT s.employee_id,
           date_trunc('month', s.order_date)::date                    AS month_start,
           count(DISTINCT s.customer_id)                              AS new_customers
    FROM dwh.fact_sales s
    JOIN dwh.dim_customers c ON c.customer_id = s.customer_id AND s.order_date = c.first_order_date
    GROUP BY 1, 2
),
actual AS (
    SELECT employee_id, month_start,
           coalesce(s.delivered_net, 0) - coalesce(r.returns_amount, 0) AS actual_net_revenue,
           coalesce(s.delivered_net, 0)                               AS delivered_net,
           coalesce(r.returns_amount, 0)                              AS returns_amount,
           coalesce(s.actual_gross, 0)                                AS actual_gross,
           coalesce(s.actual_quantity, 0)                             AS actual_quantity,
           coalesce(s.active_customers, 0)                            AS active_customers,
           coalesce(n.new_customers, 0)                               AS new_customers
    FROM sales s
    FULL JOIN returns r USING (employee_id, month_start)
    LEFT JOIN new_customers n USING (employee_id, month_start)
),
grid AS (
    -- dòng có target: mọi phiên bản
    SELECT employee_id, target_month AS month_start, version_code, version_number,
           is_latest, is_original, target_revenue, target_quantity, target_new_customers
    FROM dwh.fact_targets
    UNION ALL
    -- dòng có thực tế nhưng không có target đang áp dụng
    SELECT a.employee_id, a.month_start, NULL, NULL, true, false, NULL, NULL, NULL
    FROM actual a
    WHERE NOT EXISTS (SELECT 1 FROM dwh.fact_targets t
                      WHERE t.employee_id = a.employee_id AND t.target_month = a.month_start AND t.is_latest)
)
SELECT
    extract(year FROM g.month_start)::int                             AS year,
    extract(month FROM g.month_start)::int                            AS month,
    to_char(g.month_start, 'YYYYMMDD')::int                           AS date_key,
    g.month_start,
    g.employee_id,
    coalesce(e.employee_sk, -1)                                       AS employee_sk,
    e.full_name                                                       AS employee_name,
    e.region,
    e.team,
    g.version_code,
    g.version_number,
    g.is_latest,
    g.is_original,
    g.target_revenue,
    g.target_quantity,
    g.target_new_customers,
    coalesce(a.actual_net_revenue, 0)                                 AS actual_net_revenue,
    coalesce(a.delivered_net, 0)                                      AS delivered_net,
    coalesce(a.returns_amount, 0)                                     AS returns_amount,
    coalesce(a.actual_gross, 0)                                       AS actual_gross,
    coalesce(a.actual_quantity, 0)                                    AS actual_quantity,
    coalesce(a.active_customers, 0)                                   AS active_customers,
    coalesce(a.new_customers, 0)                                      AS new_customers,
    round(coalesce(a.actual_net_revenue, 0) / nullif(g.target_revenue, 0) * 100, 2) AS achieve_pct,
    ly.actual_net_revenue                                             AS ly_net_revenue,
    round((coalesce(a.actual_net_revenue, 0) - ly.actual_net_revenue)
          / nullif(ly.actual_net_revenue, 0) * 100, 2)                AS yoy_growth_pct
FROM grid g
LEFT JOIN actual a
       ON a.employee_id = g.employee_id AND a.month_start = g.month_start
LEFT JOIN actual ly
       ON ly.employee_id = g.employee_id AND ly.month_start = (g.month_start - interval '1 year')::date
LEFT JOIN dwh.dim_employees e
       ON e.employee_id = g.employee_id
      AND g.month_start BETWEEN e.effective_from AND e.effective_to;
