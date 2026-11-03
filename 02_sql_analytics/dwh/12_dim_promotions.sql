-- =====================================================================================
-- dim_promotions (VIEW) — chương trình khuyến mãi, SCD Type 1. Khoá: promotion_id (kiểm tra bằng test)
-- Phục vụ BR-B-04 (phân tích theo từng chương trình). Sản phẩm áp dụng nằm ở bridge_promotion_products.
-- is_counted_as_promo: chương trình được tính vào fact_sales.is_promo (không tính 'Planned', A-35).
-- duration_days: số ngày chạy KM (gồm cả ngày đầu và cuối) — dùng để so sánh trước kỳ / trong kỳ.
-- Dòng promotion_id = '-1' / UNKNOWN theo quy ước dim (A-33).
-- =====================================================================================
SELECT dwh.drop_relation('dim_promotions');

CREATE VIEW dwh.dim_promotions AS
SELECT
    p.promotion_id,
    p.promotion_name,
    p.promotion_type,
    p.target_channel,
    p.target_region,
    p.start_date,
    p.end_date,
    p.end_date - p.start_date + 1                                     AS duration_days,
    p.discount_pct,
    p.min_order_quantity,
    p.budget_vnd,
    p.actual_cost_vnd,
    p.status,
    p.status <> 'Planned'                                             AS is_counted_as_promo,
    p.created_by,
    p._batch_id                                                       AS _source_batch_id
FROM staging.stg_promotions p
UNION ALL
SELECT '-1', 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'UNKNOWN', FALSE, NULL, NULL;
