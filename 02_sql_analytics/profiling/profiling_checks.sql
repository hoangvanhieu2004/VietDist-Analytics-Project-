-- =====================================================================================
-- Task 2.1 — Kiểm tra chất lượng dữ liệu Bronze (raw.*) theo nghiệp vụ
-- Chạy cả file trong pgAdmin (Query Tool, kết nối vietdist_dw) hoặc:
--   psql -U postgres -h localhost -d vietdist_dw -f 02_sql_analytics/profiling/profiling_checks.sql
-- Chỉ đọc dữ liệu. Các hàm helper nằm trong pg_temp nên tự mất khi đóng session.
-- Kết quả 5 nhóm: 1) Duplicates & Missing keys  2) Incorrect values  3) Toàn vẹn tham chiếu
--                 4) Target & Employee  5) Phân bố change_type
-- Lưu ý: raw chỉ append — nếu đã load nhiều batch, số trùng sẽ gồm cả bản sao giữa các batch.
-- =====================================================================================

-- Ép kiểu an toàn: giá trị không hợp lệ -> NULL thay vì lỗi
CREATE OR REPLACE FUNCTION pg_temp.n(t text) RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN btrim(t) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN btrim(t)::numeric END $$;

CREATE OR REPLACE FUNCTION pg_temp.d(t text) RETURNS date LANGUAGE plpgsql IMMUTABLE AS
$$ BEGIN
     RETURN CASE WHEN btrim(t) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN left(btrim(t), 10)::date END;
   EXCEPTION WHEN others THEN RETURN NULL;
   END $$;

-- Dòng dữ liệu không gồm cột metadata (để so trùng hoàn toàn)
CREATE OR REPLACE FUNCTION pg_temp.data_row(j jsonb) RETURNS jsonb LANGUAGE sql IMMUTABLE AS
$$ SELECT j - '{_source_file,_source_sheet,_source_platform,_ingested_at,_batch_id}'::text[] $$;

-- Ngày ngoài khoảng hợp lệ 2022-01-01 .. 2026-12-31 (hoặc không ép được)
CREATE OR REPLACE FUNCTION pg_temp.bad_date(t text) RETURNS boolean LANGUAGE sql IMMUTABLE AS
$$ SELECT t IS NOT NULL AND (pg_temp.d(t) IS NULL OR pg_temp.d(t) NOT BETWEEN '2022-01-01' AND '2026-12-31') $$;


-- =====================================================================================
-- 1) DUPLICATES & MISSING KEYS
--    dong_trung_hoan_toan: dòng giống hệt nhau (không tính metadata)
--    nhom_khoa_trung / dong_thua_theo_khoa: trùng theo khoá chính dự kiến
--    khoa_null: dòng có ít nhất 1 cột khoá NULL hoặc rỗng
-- =====================================================================================
SELECT 'sales_transactions' AS bang, '(order_id, product_id)' AS khoa_chinh,
       (SELECT count(*) FROM raw.sales_transactions) AS tong_dong,
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.sales_transactions t) AS dong_trung_hoan_toan,
       (SELECT count(*) FROM (SELECT 1 FROM raw.sales_transactions GROUP BY order_id, product_id HAVING count(*) > 1) x) AS nhom_khoa_trung,
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.sales_transactions GROUP BY order_id, product_id HAVING count(*) > 1) x) AS dong_thua_theo_khoa,
       (SELECT count(*) FROM raw.sales_transactions WHERE coalesce(btrim(order_id), '') = '' OR coalesce(btrim(product_id), '') = '') AS khoa_null
UNION ALL
SELECT 'sales_transactions', '(order_id)',
       NULL, NULL,
       (SELECT count(*) FROM (SELECT 1 FROM raw.sales_transactions GROUP BY order_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.sales_transactions GROUP BY order_id HAVING count(*) > 1) x),
       NULL
UNION ALL
SELECT 'distributor_orders', '(order_id, product_id)',
       (SELECT count(*) FROM raw.distributor_orders),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.distributor_orders t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.distributor_orders GROUP BY order_id, product_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.distributor_orders GROUP BY order_id, product_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.distributor_orders WHERE coalesce(btrim(order_id), '') = '' OR coalesce(btrim(product_id), '') = '')
UNION ALL
SELECT 'customer_master', '(customer_id)',
       (SELECT count(*) FROM raw.customer_master),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.customer_master t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.customer_master GROUP BY customer_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.customer_master GROUP BY customer_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.customer_master WHERE coalesce(btrim(customer_id), '') = '')
UNION ALL
SELECT 'product_master', '(product_id)',
       (SELECT count(*) FROM raw.product_master),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.product_master t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.product_master GROUP BY product_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.product_master GROUP BY product_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.product_master WHERE coalesce(btrim(product_id), '') = '')
UNION ALL
SELECT 'distributor_master', '(distributor_id)',
       (SELECT count(*) FROM raw.distributor_master),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.distributor_master t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.distributor_master GROUP BY distributor_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.distributor_master GROUP BY distributor_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.distributor_master WHERE coalesce(btrim(distributor_id), '') = '')
UNION ALL
SELECT 'employee_master', '(employee_id, version)',
       (SELECT count(*) FROM raw.employee_master),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.employee_master t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.employee_master GROUP BY employee_id, version HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.employee_master GROUP BY employee_id, version HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.employee_master WHERE coalesce(btrim(employee_id), '') = '' OR coalesce(btrim(version), '') = '')
UNION ALL
SELECT 'employee_change_log', '(employee_id, effective_date, change_type)',
       (SELECT count(*) FROM raw.employee_change_log),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.employee_change_log t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.employee_change_log GROUP BY employee_id, effective_date, change_type HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.employee_change_log GROUP BY employee_id, effective_date, change_type HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.employee_change_log WHERE coalesce(btrim(employee_id), '') = '' OR coalesce(btrim(effective_date), '') = '')
UNION ALL
SELECT 'territory_mapping', '(territory_id)',
       (SELECT count(*) FROM raw.territory_mapping),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.territory_mapping t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.territory_mapping GROUP BY territory_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.territory_mapping GROUP BY territory_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.territory_mapping WHERE coalesce(btrim(territory_id), '') = '')
UNION ALL
SELECT 'territory_mapping', '(employee_id, customer_id, effective_date)',
       NULL, NULL,
       (SELECT count(*) FROM (SELECT 1 FROM raw.territory_mapping GROUP BY employee_id, customer_id, effective_date HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.territory_mapping GROUP BY employee_id, customer_id, effective_date HAVING count(*) > 1) x),
       NULL
UNION ALL
SELECT 'return_transactions', '(return_id)',
       (SELECT count(*) FROM raw.return_transactions),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.return_transactions t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.return_transactions GROUP BY return_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.return_transactions GROUP BY return_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.return_transactions WHERE coalesce(btrim(return_id), '') = '')
UNION ALL
SELECT 'promotion_program', '(promotion_id)',
       (SELECT count(*) FROM raw.promotion_program),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.promotion_program t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.promotion_program GROUP BY promotion_id HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.promotion_program GROUP BY promotion_id HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.promotion_program WHERE coalesce(btrim(promotion_id), '') = '')
UNION ALL
SELECT 'sales_targets_raw', '(version_label, employee_id, year, month)',
       (SELECT count(*) FROM raw.sales_targets_raw),
       (SELECT count(*) - count(DISTINCT pg_temp.data_row(to_jsonb(t))) FROM raw.sales_targets_raw t),
       (SELECT count(*) FROM (SELECT 1 FROM raw.sales_targets_raw GROUP BY version_label, employee_id, year, month HAVING count(*) > 1) x),
       (SELECT coalesce(sum(c - 1), 0) FROM (SELECT count(*) c FROM raw.sales_targets_raw GROUP BY version_label, employee_id, year, month HAVING count(*) > 1) x),
       (SELECT count(*) FROM raw.sales_targets_raw WHERE coalesce(btrim(employee_id), '') = '' OR coalesce(btrim(month), '') = '');


-- =====================================================================================
-- 2) INCORRECT VALUES — mỗi bảng quét 1 lần, mỗi kiểm tra là 1 dòng kết quả
--    So sánh số tiền dùng sai số 1 VNĐ (làm tròn); fill_rate sai số 0.01
-- =====================================================================================
SELECT 'sales_transactions' AS bang, v.kiem_tra, v.so_dong_loi, s.tong AS tong_dong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.bad_date(order_date)) a1,
             count(*) FILTER (WHERE pg_temp.n(order_month) <> extract(month FROM pg_temp.d(order_date))) a2,
             count(*) FILTER (WHERE pg_temp.n(order_quarter) <> extract(quarter FROM pg_temp.d(order_date))) a3,
             count(*) FILTER (WHERE pg_temp.n(order_year) <> extract(year FROM pg_temp.d(order_date))) a4,
             count(*) FILTER (WHERE pg_temp.n(quantity) <= 0) a5,
             count(*) FILTER (WHERE pg_temp.n(unit_price) <= 0) a6,
             count(*) FILTER (WHERE pg_temp.n(discount_pct) NOT BETWEEN 0 AND 100) a7,
             count(*) FILTER (WHERE abs(pg_temp.n(gross_amount) - pg_temp.n(quantity) * pg_temp.n(unit_price)) > 1) a8,
             count(*) FILTER (WHERE abs(pg_temp.n(discount_amount) - pg_temp.n(gross_amount) * pg_temp.n(discount_pct) / 100) > 1) a9,
             count(*) FILTER (WHERE abs(pg_temp.n(net_amount) - (pg_temp.n(gross_amount) - pg_temp.n(discount_amount))) > 1) a10,
             count(*) FILTER (WHERE pg_temp.n(net_amount) < 0) a11
      FROM raw.sales_transactions) s,
     LATERAL (VALUES ('order_date không hợp lệ / ngoài 2022–2026', a1),
                     ('order_month ≠ tháng của order_date', a2),
                     ('order_quarter ≠ quý của order_date', a3),
                     ('order_year ≠ năm của order_date', a4),
                     ('quantity <= 0', a5),
                     ('unit_price <= 0', a6),
                     ('discount_pct ngoài 0–100', a7),
                     ('gross_amount ≠ quantity × unit_price', a8),
                     ('discount_amount ≠ gross_amount × discount_pct / 100', a9),
                     ('net_amount ≠ gross_amount − discount_amount', a10),
                     ('net_amount < 0', a11)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'distributor_orders', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.bad_date(order_date)) a1,
             count(*) FILTER (WHERE pg_temp.n(order_month) <> extract(month FROM pg_temp.d(order_date))) a2,
             count(*) FILTER (WHERE pg_temp.n(order_quarter) <> extract(quarter FROM pg_temp.d(order_date))) a3,
             count(*) FILTER (WHERE pg_temp.n(qty_ordered) <= 0) a4,
             count(*) FILTER (WHERE pg_temp.n(qty_delivered) < 0) a5,
             count(*) FILTER (WHERE pg_temp.n(qty_delivered) > pg_temp.n(qty_ordered)) a6,
             count(*) FILTER (WHERE pg_temp.n(fill_rate_pct) NOT BETWEEN 0 AND 100) a7,
             count(*) FILTER (WHERE abs(pg_temp.n(fill_rate_pct)
                                        - round(pg_temp.n(qty_delivered) / nullif(pg_temp.n(qty_ordered), 0) * 100, 2)) > 0.01) a8,
             count(*) FILTER (WHERE pg_temp.n(distributor_price) > pg_temp.n(unit_price_list)) a9,
             count(*) FILTER (WHERE abs(pg_temp.n(gross_amount) - pg_temp.n(qty_ordered) * pg_temp.n(distributor_price)) > 1) a10,
             count(*) FILTER (WHERE abs(pg_temp.n(delivered_amount) - pg_temp.n(qty_delivered) * pg_temp.n(distributor_price)) > 1) a11,
             count(*) FILTER (WHERE pg_temp.d(expected_delivery_date) < pg_temp.d(order_date)) a12,
             count(*) FILTER (WHERE pg_temp.d(actual_delivery_date) < pg_temp.d(order_date)) a13,
             count(*) FILTER (WHERE pg_temp.bad_date(actual_delivery_date)) a14
      FROM raw.distributor_orders) s,
     LATERAL (VALUES ('order_date không hợp lệ / ngoài 2022–2026', a1),
                     ('order_month ≠ tháng của order_date', a2),
                     ('order_quarter ≠ quý của order_date', a3),
                     ('qty_ordered <= 0', a4),
                     ('qty_delivered < 0', a5),
                     ('qty_delivered > qty_ordered', a6),
                     ('fill_rate_pct ngoài 0–100', a7),
                     ('fill_rate_pct ≠ qty_delivered / qty_ordered × 100', a8),
                     ('distributor_price > unit_price_list', a9),
                     ('gross_amount ≠ qty_ordered × distributor_price', a10),
                     ('delivered_amount ≠ qty_delivered × distributor_price', a11),
                     ('expected_delivery_date < order_date', a12),
                     ('actual_delivery_date < order_date', a13),
                     ('actual_delivery_date không hợp lệ / ngoài 2022–2026', a14)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'return_transactions', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.bad_date(return_date)) a1,
             count(*) FILTER (WHERE pg_temp.n(return_month) <> extract(month FROM pg_temp.d(return_date))) a2,
             count(*) FILTER (WHERE pg_temp.n(return_quantity) <= 0) a3,
             count(*) FILTER (WHERE abs(pg_temp.n(return_amount) - pg_temp.n(return_quantity) * pg_temp.n(unit_price)) > 1) a4
      FROM raw.return_transactions) s,
     LATERAL (VALUES ('return_date không hợp lệ / ngoài 2022–2026', a1),
                     ('return_month ≠ tháng của return_date', a2),
                     ('return_quantity <= 0', a3),
                     ('return_amount ≠ return_quantity × unit_price', a4)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'return_transactions', 'return_date < order_date của đơn gốc', count(*), NULL
FROM raw.return_transactions r
JOIN (SELECT order_id, min(pg_temp.d(order_date)) AS order_date FROM raw.sales_transactions GROUP BY order_id) o
  ON o.order_id = r.original_order_id
WHERE pg_temp.d(r.return_date) < o.order_date
UNION ALL
SELECT 'return_transactions', 'return_quantity > quantity của dòng bán gốc (cùng order_id, product_id)', count(*), NULL
FROM raw.return_transactions r
JOIN raw.sales_transactions s ON s.order_id = r.original_order_id AND s.product_id = r.product_id
WHERE pg_temp.n(r.return_quantity) > pg_temp.n(s.quantity)
UNION ALL
SELECT 'product_master', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.n(unit_price) <= 0) a1,
             count(*) FILTER (WHERE pg_temp.n(cost_price) <= 0) a2,
             count(*) FILTER (WHERE pg_temp.n(cost_price) > pg_temp.n(unit_price)) a3,
             count(*) FILTER (WHERE pg_temp.d(launch_date) > current_date) a4
      FROM raw.product_master) s,
     LATERAL (VALUES ('unit_price <= 0', a1), ('cost_price <= 0', a2),
                     ('cost_price > unit_price (bán lỗ)', a3), ('launch_date ở tương lai', a4)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'customer_master', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.n(credit_limit) < 0) a1,
             count(*) FILTER (WHERE pg_temp.d(join_date) > current_date) a2,
             count(*) FILTER (WHERE join_date IS NOT NULL AND pg_temp.d(join_date) IS NULL) a3
      FROM raw.customer_master) s,
     LATERAL (VALUES ('credit_limit < 0', a1), ('join_date ở tương lai', a2),
                     ('join_date không ép được sang date', a3)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'distributor_master', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.n(credit_limit) < 0) a1,
             count(*) FILTER (WHERE pg_temp.d(join_date) > current_date) a2,
             count(*) FILTER (WHERE email IS NOT NULL AND email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$') a3
      FROM raw.distributor_master) s,
     LATERAL (VALUES ('credit_limit < 0', a1), ('join_date ở tương lai', a2),
                     ('email sai định dạng', a3)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'employee_master', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.d(date_of_birth) >= pg_temp.d(join_date)) a1,
             count(*) FILTER (WHERE age(pg_temp.d(join_date), pg_temp.d(date_of_birth)) < interval '18 years') a2,
             count(*) FILTER (WHERE pg_temp.d(resign_date) < pg_temp.d(join_date)) a3,
             count(*) FILTER (WHERE pg_temp.d(effective_date) < pg_temp.d(join_date)) a4,
             count(*) FILTER (WHERE email IS NOT NULL AND email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$') a5
      FROM raw.employee_master) s,
     LATERAL (VALUES ('date_of_birth >= join_date', a1),
                     ('vào làm khi chưa đủ 18 tuổi', a2),
                     ('resign_date < join_date', a3),
                     ('effective_date < join_date (bản ghi hiệu lực trước khi vào làm)', a4),
                     ('email sai định dạng', a5)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'territory_mapping', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.d(expiry_date) < pg_temp.d(effective_date)) a1,
             count(*) FILTER (WHERE pg_temp.d(effective_date) IS NULL) a2,
             count(*) FILTER (WHERE pg_temp.d(expiry_date) IS NULL) a3
      FROM raw.territory_mapping) s,
     LATERAL (VALUES ('expiry_date < effective_date', a1),
                     ('effective_date thiếu / không hợp lệ', a2),
                     ('expiry_date thiếu / không hợp lệ', a3)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'territory_mapping', 'khách hàng có > 1 dòng hiệu lực chồng lấn thời gian', count(DISTINCT a.customer_id), NULL
FROM raw.territory_mapping a
JOIN raw.territory_mapping b
  ON a.customer_id = b.customer_id AND a.territory_id < b.territory_id
 AND daterange(pg_temp.d(a.effective_date), pg_temp.d(a.expiry_date), '[]')
  && daterange(pg_temp.d(b.effective_date), pg_temp.d(b.expiry_date), '[]')
UNION ALL
SELECT 'promotion_program', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.d(end_date) < pg_temp.d(start_date)) a1,
             count(*) FILTER (WHERE pg_temp.bad_date(start_date) OR pg_temp.bad_date(end_date)) a2,
             count(*) FILTER (WHERE pg_temp.n(discount_pct) NOT BETWEEN 0 AND 100) a3,
             count(*) FILTER (WHERE pg_temp.n(budget_vnd) < 0 OR pg_temp.n(actual_cost_vnd) < 0) a4,
             count(*) FILTER (WHERE pg_temp.n(actual_cost_vnd) > pg_temp.n(budget_vnd)) a5,
             count(*) FILTER (WHERE coalesce(btrim(applicable_products), '') = '') a6
      FROM raw.promotion_program) s,
     LATERAL (VALUES ('end_date < start_date', a1),
                     ('start/end_date không hợp lệ / ngoài 2022–2026', a2),
                     ('discount_pct ngoài 0–100', a3),
                     ('budget_vnd hoặc actual_cost_vnd < 0', a4),
                     ('actual_cost_vnd > budget_vnd (vượt ngân sách)', a5),
                     ('applicable_products rỗng', a6)) v(kiem_tra, so_dong_loi)
UNION ALL
SELECT 'sales_targets_raw', v.kiem_tra, v.so_dong_loi, s.tong
FROM (SELECT count(*) AS tong,
             count(*) FILTER (WHERE pg_temp.n(target_revenue) < 0 OR pg_temp.n(target_quantity) < 0
                                 OR pg_temp.n(target_new_customers) < 0) a1,
             count(*) FILTER (WHERE pg_temp.n(target_revenue) = 0) a2,
             count(*) FILTER (WHERE pg_temp.n(month) NOT BETWEEN 1 AND 12 OR pg_temp.n(month) IS NULL) a3,
             count(*) FILTER (WHERE pg_temp.d(effective_to) < pg_temp.d(effective_from)) a4
      FROM raw.sales_targets_raw) s,
     LATERAL (VALUES ('target âm', a1),
                     ('target_revenue = 0 (cần xử lý chia cho 0 khi tính % achieve)', a2),
                     ('month ngoài 1–12', a3),
                     ('effective_to < effective_from', a4)) v(kiem_tra, so_dong_loi);


-- =====================================================================================
-- 3) TOÀN VẸN THAM CHIẾU — mã trong bảng giao dịch không có trong bảng master
-- =====================================================================================
SELECT 'sales_transactions.customer_id → customer_master' AS kiem_tra, count(*) AS dong_loi, count(DISTINCT s.customer_id) AS ma_khong_ton_tai
FROM raw.sales_transactions s
WHERE s.customer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.customer_master m WHERE m.customer_id = s.customer_id)
UNION ALL
SELECT 'sales_transactions.employee_id → employee_master', count(*), count(DISTINCT s.employee_id)
FROM raw.sales_transactions s
WHERE s.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = s.employee_id)
UNION ALL
SELECT 'sales_transactions.product_id → product_master', count(*), count(DISTINCT s.product_id)
FROM raw.sales_transactions s
WHERE s.product_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.product_master m WHERE m.product_id = s.product_id)
UNION ALL
SELECT 'return_transactions.original_order_id → sales_transactions', count(*), count(DISTINCT r.original_order_id)
FROM raw.return_transactions r
WHERE r.original_order_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.sales_transactions s WHERE s.order_id = r.original_order_id)
UNION ALL
SELECT 'return_transactions (order_id, product_id) → dòng bán gốc', count(*), count(DISTINCT r.return_id)
FROM raw.return_transactions r
WHERE NOT EXISTS (SELECT 1 FROM raw.sales_transactions s WHERE s.order_id = r.original_order_id AND s.product_id = r.product_id)
UNION ALL
SELECT 'return_transactions.customer_id → customer_master', count(*), count(DISTINCT r.customer_id)
FROM raw.return_transactions r
WHERE r.customer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.customer_master m WHERE m.customer_id = r.customer_id)
UNION ALL
SELECT 'return_transactions.employee_id → employee_master', count(*), count(DISTINCT r.employee_id)
FROM raw.return_transactions r
WHERE r.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = r.employee_id)
UNION ALL
SELECT 'return_transactions.product_id → product_master', count(*), count(DISTINCT r.product_id)
FROM raw.return_transactions r
WHERE r.product_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.product_master m WHERE m.product_id = r.product_id)
UNION ALL
SELECT 'distributor_orders.distributor_id → distributor_master', count(*), count(DISTINCT o.distributor_id)
FROM raw.distributor_orders o
WHERE o.distributor_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.distributor_master m WHERE m.distributor_id = o.distributor_id)
UNION ALL
SELECT 'distributor_orders.product_id → product_master', count(*), count(DISTINCT o.product_id)
FROM raw.distributor_orders o
WHERE o.product_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.product_master m WHERE m.product_id = o.product_id)
UNION ALL
SELECT 'distributor_master.assigned_supervisor_id → employee_master', count(*), count(DISTINCT d.assigned_supervisor_id)
FROM raw.distributor_master d
WHERE d.assigned_supervisor_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = d.assigned_supervisor_id)
UNION ALL
SELECT 'territory_mapping.employee_id → employee_master', count(*), count(DISTINCT t.employee_id)
FROM raw.territory_mapping t
WHERE t.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = t.employee_id)
UNION ALL
SELECT 'territory_mapping.customer_id → customer_master', count(*), count(DISTINCT t.customer_id)
FROM raw.territory_mapping t
WHERE t.customer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.customer_master m WHERE m.customer_id = t.customer_id)
UNION ALL
SELECT 'sales_targets_raw.employee_id → employee_master', count(*), count(DISTINCT t.employee_id)
FROM raw.sales_targets_raw t
WHERE t.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = t.employee_id)
UNION ALL
SELECT 'employee_change_log.employee_id → employee_master', count(*), count(DISTINCT c.employee_id)
FROM raw.employee_change_log c
WHERE c.employee_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM raw.employee_master m WHERE m.employee_id = c.employee_id)
UNION ALL
SELECT 'promotion_program.applicable_products → product_master', count(*), count(DISTINCT p.product_id)
FROM (SELECT btrim(unnest(string_to_array(applicable_products, '|'))) AS product_id FROM raw.promotion_program) p
WHERE NOT EXISTS (SELECT 1 FROM raw.product_master m WHERE m.product_id = p.product_id);


-- =====================================================================================
-- 4) TARGET & EMPLOYEE — logic phiên bản và lịch sử nhân viên
-- =====================================================================================
WITH emp AS (
    SELECT employee_id, version, region, team, status, position,
           pg_temp.d(resign_date) AS resign_date
    FROM raw.employee_master
),
v1 AS (SELECT * FROM emp WHERE version = 'v1'),
v2 AS (SELECT * FROM emp WHERE version = 'v2'),
chg AS (SELECT DISTINCT employee_id, change_type FROM raw.employee_change_log)
SELECT 'Target: plan_version ≠ version_label' AS kiem_tra,
       (SELECT count(*) FROM raw.sales_targets_raw WHERE plan_version IS DISTINCT FROM version_label)::text AS ket_qua
UNION ALL
SELECT 'Target: số NV / số tháng theo phiên bản',
       (SELECT string_agg(format('%s: %s NV, tháng %s–%s, %s dòng', version_label, nv, tmin, tmax, n), '; ' ORDER BY version_label)
        FROM (SELECT version_label, count(DISTINCT employee_id) nv, min(pg_temp.n(month)) tmin,
                     max(pg_temp.n(month)) tmax, count(*) n
              FROM raw.sales_targets_raw GROUP BY version_label) x)
UNION ALL
SELECT 'Target: tháng nằm trước effective_from của phiên bản',
       (SELECT count(*) FROM raw.sales_targets_raw
        WHERE make_date(pg_temp.n(year)::int, pg_temp.n(month)::int, 1)
              < date_trunc('month', pg_temp.d(effective_from)))::text
UNION ALL
SELECT 'Target: phiên bản có > 1 bộ (version_date, effective_from, effective_to)',
       (SELECT count(*) FROM (SELECT version_label FROM raw.sales_targets_raw GROUP BY version_label
                              HAVING count(DISTINCT (version_date, effective_from, effective_to)) > 1) x)::text
UNION ALL
SELECT 'Target: bộ ngày hiệu lực theo phiên bản',
       (SELECT string_agg(DISTINCT format('%s: ban hành %s, hiệu lực %s → %s', version_label,
                                          left(version_date, 10), left(effective_from, 10), left(effective_to, 10)), '; ')
        FROM raw.sales_targets_raw)
UNION ALL
SELECT 'Target v1 có nhưng v2 không có (số NV)',
       (SELECT count(*) FROM (SELECT DISTINCT employee_id FROM raw.sales_targets_raw WHERE version_label = 'v1'
                              EXCEPT SELECT DISTINCT employee_id FROM raw.sales_targets_raw WHERE version_label = 'v2') x)::text
UNION ALL
SELECT 'Employee: NV có trong v1 nhưng không có trong v2', (SELECT count(*) FROM v1 WHERE employee_id NOT IN (SELECT employee_id FROM v2))::text
UNION ALL
SELECT 'Employee: NV đổi region/team giữa v1 và v2',
       (SELECT count(*) FROM v1 JOIN v2 USING (employee_id)
        WHERE v1.region IS DISTINCT FROM v2.region OR v1.team IS DISTINCT FROM v2.team)::text
UNION ALL
SELECT 'Employee: đổi region/team nhưng KHÔNG có trong Change_Log',
       (SELECT count(*) FROM v1 JOIN v2 USING (employee_id)
        WHERE (v1.region IS DISTINCT FROM v2.region OR v1.team IS DISTINCT FROM v2.team)
          AND employee_id NOT IN (SELECT employee_id FROM chg))::text
UNION ALL
SELECT 'Employee: status v2 theo giá trị',
       (SELECT string_agg(format('%s: %s', coalesce(status, '(null)'), n), '; ') FROM (SELECT status, count(*) n FROM v2 GROUP BY status) x)
UNION ALL
SELECT 'Employee: Change_Log "Nghỉ việc" nhưng v2 không có resign_date',
       (SELECT count(*) FROM chg JOIN v2 USING (employee_id)
        WHERE chg.change_type = 'Nghỉ việc' AND v2.resign_date IS NULL)::text
UNION ALL
SELECT 'Employee: có resign_date nhưng vẫn có target sau ngày nghỉ (dòng target)',
       (SELECT count(*) FROM raw.sales_targets_raw t
        JOIN (SELECT employee_id, max(resign_date) AS resign_date FROM emp GROUP BY employee_id) e USING (employee_id)
        WHERE make_date(pg_temp.n(t.year)::int, pg_temp.n(t.month)::int, 1) > e.resign_date)::text
UNION ALL
SELECT 'Sales: giao dịch sau ngày nghỉ việc của NV (dòng)',
       (SELECT count(*) FROM raw.sales_transactions s
        JOIN (SELECT employee_id, max(resign_date) AS resign_date FROM emp GROUP BY employee_id) e USING (employee_id)
        WHERE pg_temp.d(s.order_date) > e.resign_date)::text
UNION ALL
SELECT 'Sales: số NV có giao dịch nhưng không có target (v1)',
       (SELECT count(*) FROM (SELECT DISTINCT employee_id FROM raw.sales_transactions
                              EXCEPT SELECT DISTINCT employee_id FROM raw.sales_targets_raw WHERE version_label = 'v1') x)::text
UNION ALL
SELECT 'Sales: khoảng thời gian giao dịch',
       (SELECT format('%s → %s', min(pg_temp.d(order_date)), max(pg_temp.d(order_date))) FROM raw.sales_transactions)
UNION ALL
SELECT 'Distributor orders: khoảng thời gian',
       (SELECT format('%s → %s', min(pg_temp.d(order_date)), max(pg_temp.d(order_date))) FROM raw.distributor_orders);


-- =====================================================================================
-- 5) PHÂN BỐ change_type trong Change_Log
-- =====================================================================================
SELECT change_type, count(*) AS so_dong, string_agg(DISTINCT left(effective_date, 10), ', ') AS ngay_hieu_luc
FROM raw.employee_change_log
GROUP BY change_type
ORDER BY change_type;
