-- =====================================================================================
-- mart_distributor_performance (VIEW) — hiệu suất nhà phân phối theo tháng. Task 3.2 — BR-B-01, B-02
-- Grain: 1 dòng / (distributor_id, year, month), lưới ĐỦ các tháng có dữ liệu đơn NPP
-- (kể cả tháng NPP không đặt hàng — cần cho cảnh báo không hoạt động).
-- tier/region/channel/distributor_sk: bản ghi SCD2 hiệu lực tại cuối tháng.
--   total_orders        = số đơn khác nhau; total_order_value = Σ gross (giá trị đặt)
--   delivered_value     = Σ delivered_amount_effective (Cancelled = 0, A-16)
--   fill_rate           = Σ qty_delivered_effective / Σ qty_ordered, tỷ lệ 0–1 (A-17)
--   ontime_rate         = tỷ lệ dòng giao đúng hạn trong các dòng không Cancelled (A-18)
--   last_order_date     = ngày đặt gần nhất tính đến cuối tháng; days_since_last_order tính tới cuối tháng
--   inactive_alert      = chưa từng đặt hoặc > 30 ngày không đặt hàng tính tới cuối tháng (BR-B-01)
-- Chưa có chỉ tiêu NPP (thiếu nguồn, A-27). ly_* NULL khi chưa có dữ liệu năm trước (A-25).
-- =====================================================================================
SELECT dwh.drop_relation('mart_distributor_performance');

CREATE VIEW dwh.mart_distributor_performance AS
WITH months AS (
    SELECT DISTINCT date_trunc('month', d.date)::date                 AS month_start,
           (date_trunc('month', d.date) + interval '1 month - 1 day')::date AS month_end
    FROM dwh.dim_date d
    WHERE d.date BETWEEN (SELECT date_trunc('month', min(order_date)) FROM dwh.fact_distributor_orders)
                     AND (SELECT max(order_date) FROM dwh.fact_distributor_orders)
),
distributors AS (
    SELECT DISTINCT distributor_id FROM dwh.dim_distributors WHERE distributor_sk <> -1
),
monthly AS (
    SELECT distributor_id,
           date_trunc('month', order_date)::date                      AS month_start,
           count(DISTINCT order_id)                                   AS total_orders,
           count(*)                                                   AS order_lines,
           sum(qty_ordered)                                           AS qty_ordered,
           sum(qty_delivered_effective)                               AS qty_delivered,
           sum(gross_amount)                                          AS total_order_value,
           sum(delivered_amount_effective)                            AS delivered_value,
           count(*) FILTER (WHERE delivery_status = 'Cancelled')      AS cancelled_lines,
           max(order_date)                                            AS max_order_date,
           avg(CASE WHEN is_ontime THEN 1.0 ELSE 0.0 END)
               FILTER (WHERE delivery_status <> 'Cancelled')          AS ontime_rate
    FROM dwh.fact_distributor_orders
    GROUP BY 1, 2
),
grid AS (
    -- ngày đặt gần nhất tính tới cuối tháng = max luỹ kế của max_order_date theo tháng
    SELECT m.month_start, m.month_end, g.distributor_id,
           max(x.max_order_date) OVER (PARTITION BY g.distributor_id ORDER BY m.month_start) AS last_order_date
    FROM months m
    CROSS JOIN distributors g
    LEFT JOIN monthly x ON x.distributor_id = g.distributor_id AND x.month_start = m.month_start
)
SELECT
    extract(year FROM g.month_start)::int                             AS year,
    extract(month FROM g.month_start)::int                            AS month,
    to_char(g.month_start, 'YYYYMMDD')::int                           AS date_key,
    g.month_start,
    g.distributor_id,
    coalesce(d.distributor_sk, -1)                                    AS distributor_sk,
    d.distributor_name,
    d.tier,
    d.region,
    d.channel,
    d.status,
    coalesce(x.total_orders, 0)                                       AS total_orders,
    coalesce(x.order_lines, 0)                                        AS order_lines,
    coalesce(x.qty_ordered, 0)                                        AS qty_ordered,
    coalesce(x.qty_delivered, 0)                                      AS qty_delivered,
    coalesce(x.total_order_value, 0)                                  AS total_order_value,
    coalesce(x.delivered_value, 0)                                    AS delivered_value,
    coalesce(x.cancelled_lines, 0)                                    AS cancelled_lines,
    round(x.qty_delivered::numeric / nullif(x.qty_ordered, 0), 4)     AS fill_rate,
    round(x.ontime_rate, 4)                                           AS ontime_rate,
    g.last_order_date,
    g.month_end - g.last_order_date                                   AS days_since_last_order,
    (g.last_order_date IS NULL OR g.month_end - g.last_order_date > 30) AS inactive_alert,
    ly.total_order_value                                              AS ly_total_order_value,
    round((coalesce(x.total_order_value, 0) - ly.total_order_value)
          / nullif(ly.total_order_value, 0) * 100, 2)                 AS yoy_growth_pct
FROM grid g
LEFT JOIN monthly x
       ON x.distributor_id = g.distributor_id AND x.month_start = g.month_start
LEFT JOIN monthly ly
       ON ly.distributor_id = g.distributor_id AND ly.month_start = (g.month_start - interval '1 year')::date
LEFT JOIN dwh.dim_distributors d
       ON d.distributor_id = g.distributor_id
      AND g.month_end BETWEEN d.effective_from AND d.effective_to;
