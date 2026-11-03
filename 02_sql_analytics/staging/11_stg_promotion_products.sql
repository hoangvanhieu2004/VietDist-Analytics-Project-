-- stg_promotion_products — bảng cầu chương trình KM <-> sản phẩm (A-24).
-- Tách cột applicable_products ('PRD0017|PRD0040') của stg_promotions. Cần chạy sau 10_stg_promotions.
DROP TABLE IF EXISTS staging.stg_promotion_products CASCADE;

CREATE TABLE staging.stg_promotion_products AS
SELECT DISTINCT
    p.promotion_id,
    staging.clean_text(item)                                          AS product_id
FROM staging.stg_promotions p
CROSS JOIN LATERAL unnest(string_to_array(p.applicable_products, '|')) AS item
WHERE staging.clean_text(item) IS NOT NULL;

ALTER TABLE staging.stg_promotion_products ADD PRIMARY KEY (promotion_id, product_id);
