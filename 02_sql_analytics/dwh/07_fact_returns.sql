-- =====================================================================================
-- fact_returns (VIEW) — hàng trả về. Task 3.2. Grain: 1 dòng / return_id
-- Ghi nhận vào kỳ của return_date (A-36): date_key, employee_sk (SCD2) đều theo return_date.
-- return_amount_processed: chỉ phiếu 'Đã xử lý' — phần được trừ khỏi Net Revenue (A-21).
-- =====================================================================================
SELECT dwh.drop_relation('fact_returns');

CREATE VIEW dwh.fact_returns AS
SELECT
    r.return_id,
    r.original_order_id,
    r.product_id,
    to_char(r.return_date, 'YYYYMMDD')::int                           AS date_key,
    r.return_date,
    r.customer_id,
    r.employee_id,
    coalesce(e.employee_sk, -1)                                       AS employee_sk,
    r.region,
    r.province,
    r.return_quantity,
    r.unit_price,
    r.return_amount,
    CASE WHEN r.is_processed THEN r.return_amount ELSE 0 END          AS return_amount_processed,
    r.return_reason,
    r.status,
    r.is_processed
FROM staging.stg_returns r
LEFT JOIN dwh.dim_employees e
       ON e.employee_id = r.employee_id
      AND r.return_date BETWEEN e.effective_from AND e.effective_to;
