"""Data quality test cho Silver layer (staging.*) — Task 2.2.2.

Chạy SAU run_staging.py, từ thư mục gốc dự án:
    python 02_sql_analytics/tests/test_staging.py

Mỗi test là 1 query đếm số dòng VI PHẠM; test đạt khi = 0. Các loại test (giống dbt, xem dq.py):
unique, not_null, accepted_values, relationships, expression (điều kiện phải đúng), row_count (khớp raw), custom.
"""
import sys

from dq import (accepted_values, custom, expression, not_null, relationships,  # noqa: F401
                row_count, run_tests, unique)

REGIONS = ['Miền Bắc', 'Miền Trung', 'Miền Nam']
CHANNELS = ['Modern Trade', 'Traditional Trade', 'E-commerce']


# ---------------------------------------------------------------- test cho từng bảng
TESTS = {
    'stg_customers': [
        unique('stg_customers', 'customer_id'),
        *not_null('stg_customers', 'customer_id', 'customer_name', 'channel', 'region', 'join_date', 'status'),
        accepted_values('stg_customers', 'region', REGIONS),
        accepted_values('stg_customers', 'channel', CHANNELS),
        accepted_values('stg_customers', 'status', ['Active', 'Inactive']),
        expression('stg_customers', 'credit_limit >= 0'),
        row_count('stg_customers', 'customer_master', 'btrim(customer_id)'),
    ],
    'stg_products': [
        unique('stg_products', 'product_id'),
        *not_null('stg_products', 'product_id', 'product_name', 'category', 'unit_price', 'cost_price', 'status'),
        accepted_values('stg_products', 'status', ['Active', 'Discontinued']),
        expression('stg_products', 'unit_price > 0'),
        expression('stg_products', 'cost_price > 0 AND cost_price <= unit_price', 'cost_price trong (0, unit_price]'),
        row_count('stg_products', 'product_master', 'btrim(product_id)'),
    ],
    'stg_distributors': [
        unique('stg_distributors', 'distributor_id'),
        *not_null('stg_distributors', 'distributor_id', 'distributor_name', 'tier', 'channel', 'region', 'status'),
        accepted_values('stg_distributors', 'region', REGIONS),
        accepted_values('stg_distributors', 'channel', CHANNELS),
        accepted_values('stg_distributors', 'tier', ['Nhà phân phối cấp 1', 'Đại lý cấp 2', 'Điểm bán lẻ']),
        accepted_values('stg_distributors', 'status', ['Active', 'Inactive']),
        relationships('stg_distributors', 'assigned_supervisor_id', 'stg_employees', 'employee_id'),
        row_count('stg_distributors', 'distributor_master', 'btrim(distributor_id)'),
    ],
    'stg_employees': [
        unique('stg_employees', 'employee_id', 'version'),
        *not_null('stg_employees', 'employee_id', 'version', 'effective_date', 'full_name', 'join_date',
                  'position', 'region', 'team', 'status'),
        accepted_values('stg_employees', 'region', REGIONS),
        accepted_values('stg_employees', 'status', ['Active', 'Resigned']),
        expression('stg_employees', 'date_of_birth < join_date'),
        expression('stg_employees', "status <> 'Resigned' OR resign_date IS NOT NULL",
                   'NV Resigned phải có resign_date'),
        row_count('stg_employees', 'employee_master', 'btrim(employee_id), btrim(version)'),
    ],
    'stg_employee_changes': [
        unique('stg_employee_changes', 'employee_id', 'effective_date', 'change_type'),
        *not_null('stg_employee_changes', 'employee_id', 'effective_date', 'change_type', 'old_region', 'old_team'),
        accepted_values('stg_employee_changes', 'change_type', ['Chuyển vùng', 'Nghỉ việc']),
        expression('stg_employee_changes', "change_type <> 'Chuyển vùng' OR (new_region IS NOT NULL AND new_team IS NOT NULL)",
                   'Chuyển vùng phải có new_region, new_team'),
        relationships('stg_employee_changes', 'employee_id', 'stg_employees'),
        row_count('stg_employee_changes', 'employee_change_log',
                  'btrim(employee_id), btrim(effective_date), btrim(change_type)'),
    ],
    'stg_territory_mapping': [
        unique('stg_territory_mapping', 'territory_id'),
        *not_null('stg_territory_mapping', 'territory_id', 'employee_id', 'customer_id', 'effective_date', 'expiry_date'),
        accepted_values('stg_territory_mapping', 'region', REGIONS),
        expression('stg_territory_mapping', 'expiry_date >= effective_date'),
        relationships('stg_territory_mapping', 'employee_id', 'stg_employees'),
        relationships('stg_territory_mapping', 'customer_id', 'stg_customers'),
        row_count('stg_territory_mapping', 'territory_mapping', 'btrim(territory_id)'),
    ],
    'stg_sales_transactions': [
        unique('stg_sales_transactions', 'order_id', 'product_id'),
        *not_null('stg_sales_transactions', 'order_id', 'product_id', 'order_date', 'customer_id', 'employee_id',
                  'quantity', 'unit_price', 'gross_amount', 'discount_amount', 'net_amount', 'delivery_status',
                  'is_delivered', 'is_before_customer_join'),
        accepted_values('stg_sales_transactions', 'region', REGIONS),
        accepted_values('stg_sales_transactions', 'channel', CHANNELS),
        accepted_values('stg_sales_transactions', 'delivery_status', ['Delivered', 'Delivering', 'Cancelled']),
        accepted_values('stg_sales_transactions', 'payment_status', ['Paid', 'Partial', 'Unpaid']),
        expression('stg_sales_transactions', 'quantity > 0'),
        expression('stg_sales_transactions', 'unit_price > 0'),
        expression('stg_sales_transactions', 'discount_pct BETWEEN 0 AND 100'),
        expression('stg_sales_transactions', 'gross_amount = quantity * unit_price'),
        expression('stg_sales_transactions', 'net_amount = gross_amount - discount_amount'),
        expression('stg_sales_transactions', 'abs(discount_amount - gross_amount * discount_pct / 100) <= 50',
                   'discount_amount ≈ gross × pct (làm tròn 100đ, A-22)'),
        expression('stg_sales_transactions', "order_month = extract(month FROM order_date) "
                                             "AND order_quarter = extract(quarter FROM order_date) "
                                             "AND order_year = extract(year FROM order_date)",
                   'order_month/quarter/year khớp order_date'),
        relationships('stg_sales_transactions', 'customer_id', 'stg_customers'),
        relationships('stg_sales_transactions', 'product_id', 'stg_products'),
        relationships('stg_sales_transactions', 'employee_id', 'stg_employees'),
        row_count('stg_sales_transactions', 'sales_transactions', 'btrim(order_id), btrim(product_id)'),
    ],
    'stg_distributor_orders': [
        unique('stg_distributor_orders', 'order_id', 'product_id'),
        *not_null('stg_distributor_orders', 'order_id', 'product_id', 'order_date', 'distributor_id', 'qty_ordered',
                  'qty_delivered', 'distributor_price', 'gross_amount', 'expected_delivery_date',
                  'actual_delivery_date', 'delivery_status', 'is_ontime', 'qty_delivered_effective',
                  'delivered_amount_effective'),
        accepted_values('stg_distributor_orders', 'region', REGIONS),
        accepted_values('stg_distributor_orders', 'channel', CHANNELS),
        accepted_values('stg_distributor_orders', 'delivery_status', ['Delivered', 'Partial', 'Cancelled']),
        expression('stg_distributor_orders', 'qty_ordered > 0'),
        expression('stg_distributor_orders', 'qty_delivered BETWEEN 0 AND qty_ordered'),
        expression('stg_distributor_orders', 'fill_rate_pct BETWEEN 0 AND 100'),
        expression('stg_distributor_orders', 'gross_amount = qty_ordered * distributor_price'),
        expression('stg_distributor_orders', 'actual_delivery_date >= order_date'),
        expression('stg_distributor_orders', "delivery_status <> 'Cancelled' OR qty_delivered_effective = 0",
                   'Cancelled -> qty_delivered_effective = 0 (A-16)'),
        relationships('stg_distributor_orders', 'distributor_id', 'stg_distributors'),
        relationships('stg_distributor_orders', 'product_id', 'stg_products'),
        row_count('stg_distributor_orders', 'distributor_orders', 'btrim(order_id), btrim(product_id)'),
    ],
    'stg_returns': [
        unique('stg_returns', 'return_id'),
        *not_null('stg_returns', 'return_id', 'original_order_id', 'product_id', 'return_date', 'return_quantity',
                  'return_amount', 'status', 'is_processed'),
        accepted_values('stg_returns', 'status', ['Đã xử lý', 'Đang xử lý', 'Từ chối']),
        expression('stg_returns', 'return_quantity > 0'),
        expression('stg_returns', 'return_amount = return_quantity * unit_price'),
        relationships('stg_returns', ['original_order_id', 'product_id'], 'stg_sales_transactions',
                      ['order_id', 'product_id']),
        relationships('stg_returns', 'customer_id', 'stg_customers'),
        relationships('stg_returns', 'employee_id', 'stg_employees'),
        row_count('stg_returns', 'return_transactions', 'btrim(return_id)'),
    ],
    'stg_promotions': [
        unique('stg_promotions', 'promotion_id'),
        *not_null('stg_promotions', 'promotion_id', 'promotion_name', 'start_date', 'end_date', 'applicable_products'),
        accepted_values('stg_promotions', 'target_channel', CHANNELS + ['All']),
        accepted_values('stg_promotions', 'target_region', REGIONS + ['All']),
        expression('stg_promotions', 'end_date >= start_date'),
        expression('stg_promotions', 'discount_pct BETWEEN 0 AND 100'),
        row_count('stg_promotions', 'promotion_program', 'btrim(promotion_id)'),
    ],
    'stg_promotion_products': [
        unique('stg_promotion_products', 'promotion_id', 'product_id'),
        *not_null('stg_promotion_products', 'promotion_id', 'product_id'),
        relationships('stg_promotion_products', 'promotion_id', 'stg_promotions'),
        relationships('stg_promotion_products', 'product_id', 'stg_products'),
    ],
    'stg_sales_targets': [
        unique('stg_sales_targets', 'version_label', 'employee_id', 'year', 'month'),
        *not_null('stg_sales_targets', 'version_label', 'employee_id', 'year', 'month', 'effective_from',
                  'effective_to', 'target_revenue'),
        accepted_values('stg_sales_targets', 'region', REGIONS),
        expression('stg_sales_targets', 'month BETWEEN 1 AND 12'),
        expression('stg_sales_targets', 'target_revenue > 0', 'target_revenue > 0 (tránh chia cho 0)'),
        expression('stg_sales_targets', 'effective_to >= effective_from'),
        expression('stg_sales_targets', 'plan_version = version_label'),
        relationships('stg_sales_targets', 'employee_id', 'stg_employees'),
        row_count('stg_sales_targets', 'sales_targets_raw',
                  'btrim(version_label), btrim(employee_id), btrim(year), btrim(month)'),
    ],
    'stg_sales_targets_versioned': [
        unique('stg_sales_targets_versioned', 'version_code', 'employee_id', 'year', 'month'),
        *not_null('stg_sales_targets_versioned', 'version_code', 'version_number', 'employee_id', 'target_month',
                  'target_revenue', 'effective_date', 'expiry_date', 'is_latest', 'is_original'),
        expression('stg_sales_targets_versioned', 'expiry_date >= effective_date'),
        expression('stg_sales_targets_versioned', "is_latest = (expiry_date = DATE '9999-12-31')",
                   'is_latest ⇔ expiry_date = 9999-12-31'),
        expression('stg_sales_targets_versioned', 'is_latest = (superseded_by IS NULL)',
                   'is_latest ⇔ không bị phiên bản nào thay thế'),
        custom('mỗi phiên bản có đúng 1 bộ (version_date, effective_from, effective_to)',
               'SELECT count(*) FROM (SELECT version_label FROM staging.stg_sales_targets GROUP BY version_label '
               '  HAVING count(DISTINCT (version_date, effective_from, effective_to)) > 1) x'),
        custom('phiên bản số lớn hơn không có hiệu lực sớm hơn',
               'SELECT count(*) FROM (SELECT DISTINCT version_number, effective_date '
               '  FROM staging.stg_sales_targets_versioned) a '
               'JOIN (SELECT DISTINCT version_number, effective_date FROM staging.stg_sales_targets_versioned) b '
               '  ON b.version_number > a.version_number AND b.effective_date < a.effective_date'),
        custom('mỗi (NV, tháng) có tối đa 1 dòng is_latest',
               'SELECT count(*) FROM (SELECT employee_id, year, month FROM staging.stg_sales_targets_versioned '
               '  WHERE is_latest GROUP BY 1, 2, 3 HAVING count(*) > 1) x'),
        custom('khoảng hiệu lực các phiên bản của cùng (NV, tháng) không chồng lấn',
               'SELECT count(*) FROM staging.stg_sales_targets_versioned a '
               'JOIN staging.stg_sales_targets_versioned b ON a.employee_id = b.employee_id '
               '  AND a.year = b.year AND a.month = b.month AND a.version_number < b.version_number '
               "  AND daterange(a.effective_date, a.expiry_date, '[]') && daterange(b.effective_date, b.expiry_date, '[]')"),
        custom('dòng bị thay thế hết hạn đúng 1 ngày trước khi phiên bản sau có hiệu lực',
               'SELECT count(*) FROM staging.stg_sales_targets_versioned t '
               'WHERE t.superseded_by IS NOT NULL AND t.expiry_date <> '
               '  (SELECT min(n.effective_date) FROM staging.stg_sales_targets_versioned n '
               '   WHERE n.version_code = t.superseded_by) - 1'),
        custom('dòng is_latest thuộc đúng phiên bản đang áp dụng của tháng (calendar)',
               'SELECT count(*) FROM staging.stg_sales_targets_versioned t '
               'JOIN staging.stg_target_version_calendar c USING (year, month) '
               'WHERE t.is_latest AND t.version_code <> c.effective_version'),
        custom('row_count = staging.stg_sales_targets',
               'SELECT abs((SELECT count(*) FROM staging.stg_sales_targets_versioned) - '
               '(SELECT count(*) FROM staging.stg_sales_targets))'),
    ],
    'stg_target_version_calendar': [
        unique('stg_target_version_calendar', 'year', 'month'),
        *not_null('stg_target_version_calendar', 'year', 'month', 'effective_version', 'versions_covering'),
        relationships('stg_target_version_calendar', 'effective_version', 'stg_sales_targets_versioned',
                      'version_code'),
        custom('calendar có đủ mọi tháng có target',
               'SELECT count(*) FROM (SELECT DISTINCT year, month FROM staging.stg_sales_targets) m '
               'WHERE NOT EXISTS (SELECT 1 FROM staging.stg_target_version_calendar c '
               '  WHERE c.year = m.year AND c.month = m.month)'),
    ],
}


if __name__ == '__main__':
    sys.exit(1 if run_tests(TESTS, 'staging') else 0)
