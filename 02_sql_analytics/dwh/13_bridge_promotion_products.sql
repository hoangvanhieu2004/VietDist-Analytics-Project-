-- =====================================================================================
-- bridge_promotion_products (VIEW) — cầu nhiều-nhiều chương trình KM <-> sản phẩm (BR-B-04:
-- một sản phẩm có thể thuộc nhiều chương trình cùng lúc). Khoá: (promotion_id, product_id).
-- =====================================================================================
SELECT dwh.drop_relation('bridge_promotion_products');

CREATE VIEW dwh.bridge_promotion_products AS
SELECT
    pp.promotion_id,
    pp.product_id
FROM staging.stg_promotion_products pp;
