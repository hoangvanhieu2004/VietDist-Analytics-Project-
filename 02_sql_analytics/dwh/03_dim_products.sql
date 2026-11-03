-- =====================================================================================
-- dim_products (VIEW) — sản phẩm, SCD Type 1. Task 3.1. Khoá: product_id (kiểm tra bằng test)
-- Thêm: gross_margin = unit_price − cost_price, gross_margin_pct = gross_margin / unit_price.
-- Dòng product_id = '-1' / UNKNOWN cho fact không khớp SP.
-- =====================================================================================
SELECT dwh.drop_relation('dim_products');

CREATE VIEW dwh.dim_products AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.unit,
    p.unit_price,
    p.cost_price,
    p.unit_price - p.cost_price                                       AS gross_margin,
    round((p.unit_price - p.cost_price) / nullif(p.unit_price, 0), 4) AS gross_margin_pct,
    p.weight_gram,
    p.status,
    p.launch_date,
    p._batch_id                                                       AS _source_batch_id
FROM staging.stg_products p
UNION ALL
SELECT '-1', 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'UNKNOWN', NULL, NULL;
