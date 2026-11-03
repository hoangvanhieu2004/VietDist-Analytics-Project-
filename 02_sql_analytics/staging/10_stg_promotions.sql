-- stg_promotions — chương trình khuyến mãi (SRC-10). 1 dòng / promotion_id.
-- target_channel / target_region = 'All' nghĩa là áp dụng cho mọi kênh / vùng (A-24).
-- Danh sách sản phẩm tách sang stg_promotion_products.
DROP TABLE IF EXISTS staging.stg_promotions CASCADE;

CREATE TABLE staging.stg_promotions AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(promotion_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.promotion_program r
)
SELECT
    staging.clean_text(promotion_id)                                  AS promotion_id,
    staging.clean_text(promotion_name)                                AS promotion_name,
    staging.clean_text(promotion_type)                                AS promotion_type,
    staging.clean_text(target_channel)                                AS target_channel,
    staging.clean_text(target_region)                                 AS target_region,
    staging.cast_date(start_date, 'promotion_program.start_date')       AS start_date,
    staging.cast_date(end_date, 'promotion_program.end_date')           AS end_date,
    staging.clean_text(applicable_products)                           AS applicable_products,
    staging.cast_num(discount_pct, 'promotion_program.discount_pct')    AS discount_pct,
    staging.cast_int(min_order_quantity, 'promotion_program.min_order_quantity') AS min_order_quantity,
    staging.cast_num(budget_vnd, 'promotion_program.budget_vnd')        AS budget_vnd,
    staging.cast_num(actual_cost_vnd, 'promotion_program.actual_cost_vnd') AS actual_cost_vnd,
    staging.clean_text(status)                                        AS status,
    staging.clean_text(created_by)                                    AS created_by,
    _source_file, _source_sheet, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_promotions ADD PRIMARY KEY (promotion_id);
