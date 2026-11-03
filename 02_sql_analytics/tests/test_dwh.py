"""Test Gold layer (dwh.*) — Task 3.1: dimension tables.

Chạy SAU run_dwh.py, từ thư mục gốc dự án:
    python 02_sql_analytics/tests/test_dwh.py

Phần 1 — test kiểu dbt (xem dq.py) gồm các CHECKPOINT của đề bài Task 3.1. Mọi đối tượng dwh là VIEW
         nên không có PRIMARY KEY — tính duy nhất của khoá được đảm bảo bằng các test unique ở đây.
Phần 2 — mô phỏng SCD2 cho nhà phân phối (đổi tier 1 NPP, chạy merge snapshots.distributors, kiểm tra
         qua view dwh.dim_distributors) rồi ROLLBACK.
"""
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text

from dq import accepted_values, custom, expression, get_engine, not_null, relationships, run_tests, unique

SNAPSHOT_SQL = Path(__file__).resolve().parents[1] / 'snapshots' / '01_distributors.sql'
TIERS = ['Platinum', 'Gold', 'Silver', 'Bronze', 'Chưa mua', 'UNKNOWN']
VIEWS = ['dim_date', 'dim_customers', 'dim_products', 'dim_employees', 'dim_distributors',
         'fact_sales', 'fact_returns', 'fact_targets', 'fact_distributor_orders',
         'mart_sales_vs_target', 'mart_distributor_performance',
         'dim_promotions', 'bridge_promotion_products']


def reconcile(name, dwh_sql, staging_sql):
    """Tổng ở dwh phải bằng tổng ở staging (sai số 1đ)."""
    return custom(name, f'SELECT CASE WHEN abs(({dwh_sql}) - ({staging_sql})) <= 1 THEN 0 ELSE 1 END')

TESTS = {
    'schema': [
        custom('mọi đối tượng dữ liệu trong dwh là VIEW (không có bảng / materialized view)',
               "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
               "WHERE n.nspname = 'dwh' AND c.relkind IN ('r', 'm', 'p')"),
        custom(f'đủ {len(VIEWS)} view: {", ".join(VIEWS)}',
               f"SELECT {len(VIEWS)} - count(*) FROM information_schema.views WHERE table_schema = 'dwh' "
               f"AND table_name IN ({', '.join(repr(v) for v in VIEWS)})"),
    ],
    'dim_date': [
        unique('dwh.dim_date', 'date_key'),
        unique('dwh.dim_date', 'date'),
        *not_null('dwh.dim_date', 'date', 'year', 'month', 'fiscal_year', 'fiscal_month', 'fiscal_quarter',
                  'date_last_year'),
        custom('CHECKPOINT: đủ ngày 2022-01-01 → 2026-12-31, không thiếu ngày',
               "SELECT abs(count(*) - (DATE '2026-12-31' - DATE '2022-01-01' + 1)) "
               "  + count(*) FILTER (WHERE date NOT BETWEEN DATE '2022-01-01' AND DATE '2026-12-31') "
               "FROM dwh.dim_date"),
        custom('CHECKPOINT: fiscal_year = 2023 cho 2023-10-01 và 2024-01-01',
               "SELECT count(*) FROM dwh.dim_date "
               "WHERE date IN (DATE '2023-10-01', DATE '2024-01-01') AND fiscal_year <> 2023"),
        custom('fiscal_year biên: 2023-08-31 -> 2022, 2023-09-01 -> 2023, 2024-08-31 -> 2023',
               "SELECT count(*) FROM dwh.dim_date WHERE "
               "(date = DATE '2023-08-31' AND fiscal_year <> 2022) OR (date = DATE '2023-09-01' AND fiscal_year <> 2023) "
               "OR (date = DATE '2024-08-31' AND fiscal_year <> 2023)"),
        expression('dwh.dim_date', "fiscal_month = CASE WHEN month >= 9 THEN month - 8 ELSE month + 4 END",
                   'fiscal_month: tháng 9 = 1 … tháng 8 = 12'),
        expression('dwh.dim_date', 'fiscal_quarter = (fiscal_month - 1) / 3 + 1'),
        expression('dwh.dim_date', 'fiscal_day_of_year = date - make_date(fiscal_year, 9, 1) + 1'),
        custom('date_last_year của 2024-02-29 = 2023-02-28 (quy tắc YoY BRD 3.1)',
               "SELECT count(*) FROM dwh.dim_date WHERE date = DATE '2024-02-29' "
               "AND date_last_year <> DATE '2023-02-28'"),
    ],
    'dim_customers': [
        unique('dwh.dim_customers', 'customer_id'),
        *not_null('dwh.dim_customers', 'customer_id', 'customer_name', 'loyalty_tier', 'net_revenue'),
        accepted_values('dwh.dim_customers', 'loyalty_tier', TIERS),
        relationships('stg_customers', 'customer_id', 'dwh.dim_customers'),
        custom('có dòng UNKNOWN (-1)', "SELECT 1 - count(*) FROM dwh.dim_customers WHERE customer_id = '-1'"),
        expression('dwh.dim_customers', "customer_id = '-1' OR (loyalty_tier = 'Chưa mua') = (first_order_date IS NULL)",
                   "'Chưa mua' ⇔ không có giao dịch"),
        custom('tier xếp đúng thứ tự doanh thu (min Platinum >= max Gold >= max Silver)',
               "SELECT count(*) FROM (SELECT min(net_revenue) FILTER (WHERE loyalty_tier = 'Platinum') p, "
               "max(net_revenue) FILTER (WHERE loyalty_tier = 'Gold') g, "
               "min(net_revenue) FILTER (WHERE loyalty_tier = 'Gold') g2, "
               "max(net_revenue) FILTER (WHERE loyalty_tier = 'Silver') s FROM dwh.dim_customers) x "
               "WHERE p < g OR g2 < s"),
    ],
    'dim_products': [
        unique('dwh.dim_products', 'product_id'),
        *not_null('dwh.dim_products', 'product_id', 'product_name'),
        relationships('stg_products', 'product_id', 'dwh.dim_products'),
        custom('có dòng UNKNOWN (-1)', "SELECT 1 - count(*) FROM dwh.dim_products WHERE product_id = '-1'"),
        expression('dwh.dim_products', "product_id = '-1' OR gross_margin = unit_price - cost_price"),
    ],
    'dim_employees': [
        unique('dwh.dim_employees', 'employee_sk'),
        unique('dwh.dim_employees', 'employee_id', 'effective_from'),
        *not_null('dwh.dim_employees', 'employee_sk', 'employee_id', 'effective_from', 'effective_to',
                  'is_current', 'change_reason'),
        expression('dwh.dim_employees', 'effective_to >= effective_from'),
        custom('CHECKPOINT: is_current = TRUE đúng 1 bản ghi / NV, và là bản ghi mới nhất',
               "SELECT count(*) FROM (SELECT employee_id, count(*) FILTER (WHERE is_current) n_cur, "
               "  max(effective_from) last_from, max(effective_from) FILTER (WHERE is_current) cur_from "
               "  FROM dwh.dim_employees GROUP BY employee_id) x WHERE n_cur <> 1 OR cur_from <> last_from"),
        custom('CHECKPOINT: NV chuyển vùng (Change_Log) có >= 2 bản ghi',
               "SELECT count(*) FROM staging.stg_employee_changes c WHERE c.change_type = 'Chuyển vùng' "
               "AND (SELECT count(*) FROM dwh.dim_employees d WHERE d.employee_id = c.employee_id) < 2"),
        custom('mỗi dòng Change_Log có bản ghi SCD2 bắt đầu đúng ngày, region/team mới đúng',
               "SELECT count(*) FROM staging.stg_employee_changes c WHERE NOT EXISTS ("
               "  SELECT 1 FROM dwh.dim_employees d WHERE d.employee_id = c.employee_id "
               "  AND d.effective_from = c.effective_date AND d.change_reason LIKE '%' || c.change_type || '%' "
               "  AND (c.change_type <> 'Chuyển vùng' OR (d.region = c.new_region AND d.team = c.new_team)))"),
        custom('bản ghi SCD2 (không phải đầu tiên) đều có trong Change_Log',
               "SELECT count(*) FROM dwh.dim_employees d WHERE d.change_reason NOT IN ('Khởi tạo', 'Unknown member') "
               "AND NOT EXISTS (SELECT 1 FROM staging.stg_employee_changes c "
               "  WHERE c.employee_id = d.employee_id AND c.effective_date = d.effective_from)"),
        custom('khoảng hiệu lực liên tục: effective_to + 1 = effective_from bản ghi kế',
               "SELECT count(*) FROM (SELECT effective_to, lead(effective_from) OVER "
               "  (PARTITION BY employee_id ORDER BY effective_from) nxt FROM dwh.dim_employees) x "
               "WHERE nxt IS NOT NULL AND effective_to + 1 <> nxt"),
        custom('mọi NV ở staging có trong dim', "SELECT count(*) FROM (SELECT DISTINCT employee_id FROM "
               "staging.stg_employees EXCEPT SELECT employee_id FROM dwh.dim_employees) x"),
        custom('bản ghi current khớp snapshot mới nhất ở staging (region, team, position, status)',
               "SELECT count(*) FROM dwh.dim_employees d JOIN (SELECT DISTINCT ON (employee_id) * "
               "  FROM staging.stg_employees ORDER BY employee_id, effective_date DESC) s USING (employee_id) "
               "WHERE d.is_current AND (d.region, d.team, d.position, d.status) "
               "  IS DISTINCT FROM (s.region, s.team, s.position, s.status)"),
        custom('mỗi dòng bán hàng khớp đúng 1 bản ghi NV theo ngày giao dịch',
               "SELECT count(*) FROM staging.stg_sales_transactions s WHERE (SELECT count(*) FROM dwh.dim_employees d "
               "  WHERE d.employee_id = s.employee_id AND s.order_date BETWEEN d.effective_from AND d.effective_to) <> 1"),
        custom('có dòng UNKNOWN (-1)', "SELECT 1 - count(*) FROM dwh.dim_employees WHERE employee_sk = -1"),
    ],
    'dim_distributors': [
        unique('dwh.dim_distributors', 'distributor_sk'),
        unique('dwh.dim_distributors', 'distributor_id', 'effective_from'),
        *not_null('dwh.dim_distributors', 'distributor_sk', 'distributor_id', 'effective_from', 'effective_to',
                  'is_current'),
        expression('dwh.dim_distributors', 'effective_to >= effective_from'),
        custom('đúng 1 bản ghi current / NPP', "SELECT count(*) FROM (SELECT distributor_id FROM dwh.dim_distributors "
               "GROUP BY distributor_id HAVING count(*) FILTER (WHERE is_current) <> 1) x"),
        custom('mọi NPP ở staging có bản ghi current khớp tier/region/channel',
               "SELECT count(*) FROM staging.stg_distributors s WHERE NOT EXISTS (SELECT 1 FROM dwh.dim_distributors d "
               "  WHERE d.distributor_id = s.distributor_id AND d.is_current "
               "  AND (d.tier, d.region, d.channel) IS NOT DISTINCT FROM (s.tier, s.region, s.channel))"),
        custom('mỗi đơn NPP khớp đúng 1 bản ghi NPP theo ngày đặt',
               "SELECT count(*) FROM staging.stg_distributor_orders o WHERE (SELECT count(*) FROM dwh.dim_distributors d "
               "  WHERE d.distributor_id = o.distributor_id AND o.order_date BETWEEN d.effective_from AND d.effective_to) <> 1"),
        custom('có dòng UNKNOWN (-1)', "SELECT 1 - count(*) FROM dwh.dim_distributors WHERE distributor_sk = -1"),
    ],
    'fact_sales': [
        unique('dwh.fact_sales', 'order_id', 'product_id'),
        *not_null('dwh.fact_sales', 'date_key', 'customer_id', 'product_id', 'employee_sk', 'net_revenue', 'is_promo'),
        reconcile('số dòng = stg_sales_transactions', 'SELECT count(*) FROM dwh.fact_sales',
                  'SELECT count(*) FROM staging.stg_sales_transactions'),
        reconcile('Σ net_amount = staging', 'SELECT sum(net_amount) FROM dwh.fact_sales',
                  'SELECT sum(net_amount) FROM staging.stg_sales_transactions'),
        expression('dwh.fact_sales', 'employee_sk <> -1', 'mọi dòng khớp được NV (SCD2 theo order_date)'),
        expression('dwh.fact_sales', 'net_revenue = CASE WHEN is_delivered THEN net_amount ELSE 0 END'),
        relationships('dwh.fact_sales', 'date_key', 'dwh.dim_date'),
        relationships('dwh.fact_sales', 'customer_id', 'dwh.dim_customers'),
        relationships('dwh.fact_sales', 'product_id', 'dwh.dim_products'),
        relationships('dwh.fact_sales', 'employee_sk', 'dwh.dim_employees'),
    ],
    'fact_returns': [
        unique('dwh.fact_returns', 'return_id'),
        *not_null('dwh.fact_returns', 'date_key', 'employee_sk', 'return_amount', 'return_amount_processed'),
        reconcile('số dòng = stg_returns', 'SELECT count(*) FROM dwh.fact_returns',
                  'SELECT count(*) FROM staging.stg_returns'),
        reconcile('Σ return_amount_processed = Σ phiếu Đã xử lý ở staging',
                  'SELECT sum(return_amount_processed) FROM dwh.fact_returns',
                  'SELECT sum(return_amount) FROM staging.stg_returns WHERE is_processed'),
        expression('dwh.fact_returns', 'employee_sk <> -1', 'mọi dòng khớp được NV (SCD2 theo return_date)'),
        relationships('dwh.fact_returns', 'date_key', 'dwh.dim_date'),
        relationships('dwh.fact_returns', ['original_order_id', 'product_id'], 'dwh.fact_sales',
                      ['order_id', 'product_id']),
    ],
    'fact_targets': [
        unique('dwh.fact_targets', 'version_code', 'employee_id', 'year', 'month'),
        *not_null('dwh.fact_targets', 'date_key', 'employee_sk', 'target_revenue', 'is_latest'),
        reconcile('số dòng = stg_sales_targets_versioned', 'SELECT count(*) FROM dwh.fact_targets',
                  'SELECT count(*) FROM staging.stg_sales_targets_versioned'),
        reconcile('Σ target_revenue = staging', 'SELECT sum(target_revenue) FROM dwh.fact_targets',
                  'SELECT sum(target_revenue) FROM staging.stg_sales_targets'),
        expression('dwh.fact_targets', 'employee_sk <> -1', 'mọi dòng khớp được NV (SCD2 theo tháng target)'),
        custom('target T7+ của NV chuyển vùng gắn với bản ghi vùng MỚI',
               "SELECT count(*) FROM dwh.fact_targets t JOIN dwh.dim_employees e USING (employee_sk) "
               "JOIN staging.stg_employee_changes c ON c.employee_id = t.employee_id AND c.change_type = 'Chuyển vùng' "
               "WHERE t.target_month >= c.effective_date AND e.region <> c.new_region"),
    ],
    'fact_distributor_orders': [
        unique('dwh.fact_distributor_orders', 'order_id', 'product_id'),
        *not_null('dwh.fact_distributor_orders', 'date_key', 'distributor_sk', 'qty_ordered', 'qty_delivered_effective'),
        reconcile('số dòng = stg_distributor_orders', 'SELECT count(*) FROM dwh.fact_distributor_orders',
                  'SELECT count(*) FROM staging.stg_distributor_orders'),
        reconcile('Σ gross_amount = staging', 'SELECT sum(gross_amount) FROM dwh.fact_distributor_orders',
                  'SELECT sum(gross_amount) FROM staging.stg_distributor_orders'),
        expression('dwh.fact_distributor_orders', 'distributor_sk <> -1', 'mọi dòng khớp được NPP (SCD2 theo order_date)'),
        relationships('dwh.fact_distributor_orders', 'date_key', 'dwh.dim_date'),
        relationships('dwh.fact_distributor_orders', 'product_id', 'dwh.dim_products'),
    ],
    'mart_sales_vs_target': [
        unique('dwh.mart_sales_vs_target', 'employee_id', 'year', 'month', 'version_code'),
        custom('mỗi (NV, tháng) có tối đa 1 dòng is_latest',
               'SELECT count(*) FROM (SELECT employee_id, year, month FROM dwh.mart_sales_vs_target '
               'GROUP BY 1, 2, 3 HAVING count(*) FILTER (WHERE is_latest) > 1) x'),
        # NV nghỉ việc không còn target đang áp dụng từ T7 (A-28) -> được phép 0 dòng is_latest nếu không có thực tế
        custom('(NV, tháng) có thực tế ≠ 0 hoặc có target đang áp dụng -> đúng 1 dòng is_latest',
               'SELECT count(*) FROM (SELECT employee_id, year, month FROM dwh.mart_sales_vs_target '
               'GROUP BY 1, 2, 3 HAVING (bool_or(actual_net_revenue <> 0 OR delivered_net <> 0 OR returns_amount <> 0) '
               '  OR bool_or(is_latest AND version_code IS NOT NULL)) '
               'AND count(*) FILTER (WHERE is_latest) <> 1) x'),
        reconcile('Σ actual_net_revenue (is_latest) = Σ net Delivered − Σ trả Đã xử lý ở staging',
                  'SELECT sum(actual_net_revenue) FROM dwh.mart_sales_vs_target WHERE is_latest',
                  'SELECT (SELECT sum(net_amount) FROM staging.stg_sales_transactions WHERE is_delivered) '
                  '     - (SELECT sum(return_amount) FROM staging.stg_returns WHERE is_processed)'),
        reconcile('số dòng có target = fact_targets',
                  'SELECT count(*) FROM dwh.mart_sales_vs_target WHERE version_code IS NOT NULL',
                  'SELECT count(*) FROM dwh.fact_targets'),
        reconcile('Σ new_customers (is_latest) = số KH có giao dịch',
                  'SELECT sum(new_customers) FROM dwh.mart_sales_vs_target WHERE is_latest',
                  'SELECT count(DISTINCT customer_id) FROM staging.stg_sales_transactions'),
        custom('CHECKPOINT: T1–T6 chỉ có v1; T7–T12 có cả v1 và v2, v2 là is_latest (NV còn làm)',
               "SELECT count(*) FROM (SELECT employee_id, month, "
               "  string_agg(version_code, ',' ORDER BY version_code) AS versions, "
               "  max(version_code) FILTER (WHERE is_latest) AS latest "
               "  FROM dwh.mart_sales_vs_target WHERE version_code IS NOT NULL "
               "  AND employee_id IN (SELECT employee_id FROM dwh.fact_targets WHERE version_code = 'v2') "
               "  GROUP BY 1, 2) x "
               "WHERE (month <= 6 AND (versions <> 'v1' OR latest <> 'v1')) "
               "   OR (month >= 7 AND (versions <> 'v1,v2' OR latest <> 'v2'))"),
        expression('dwh.mart_sales_vs_target',
                   'achieve_pct IS NOT DISTINCT FROM round(actual_net_revenue / nullif(target_revenue, 0) * 100, 2)',
                   'achieve_pct = actual / target × 100'),
        expression('dwh.mart_sales_vs_target', 'employee_sk <> -1', 'mọi dòng có cơ cấu tổ chức tại tháng'),
    ],
    'mart_distributor_performance': [
        unique('dwh.mart_distributor_performance', 'distributor_id', 'year', 'month'),
        custom('lưới đủ NPP × tháng',
               'SELECT abs((SELECT count(*) FROM dwh.mart_distributor_performance) - '
               '(SELECT count(DISTINCT distributor_id) FROM dwh.dim_distributors WHERE distributor_sk <> -1) * '
               '(SELECT count(DISTINCT date_trunc(\'month\', order_date)) FROM dwh.fact_distributor_orders))'),
        reconcile('Σ total_order_value = fact', 'SELECT sum(total_order_value) FROM dwh.mart_distributor_performance',
                  'SELECT sum(gross_amount) FROM dwh.fact_distributor_orders'),
        reconcile('Σ total_orders = số đơn khác nhau theo (NPP, tháng)',
                  'SELECT sum(total_orders) FROM dwh.mart_distributor_performance',
                  "SELECT count(DISTINCT (order_id, distributor_id, date_trunc('month', order_date))) "
                  'FROM dwh.fact_distributor_orders'),
        expression('dwh.mart_distributor_performance', 'fill_rate IS NULL OR fill_rate BETWEEN 0 AND 1'),
        expression('dwh.mart_distributor_performance',
                   'inactive_alert = (last_order_date IS NULL OR days_since_last_order > 30)'),
        expression('dwh.mart_distributor_performance', "total_orders = 0 OR last_order_date >= month_start",
                   'tháng có đơn -> last_order_date nằm trong tháng'),
        expression('dwh.mart_distributor_performance', 'distributor_sk <> -1', 'mọi dòng có bản ghi NPP tại cuối tháng'),
    ],
    'dim_promotions': [
        unique('dwh.dim_promotions', 'promotion_id'),
        *not_null('dwh.dim_promotions', 'promotion_id', 'promotion_name'),
        relationships('stg_promotions', 'promotion_id', 'dwh.dim_promotions'),
        custom('có dòng UNKNOWN (-1)', "SELECT 1 - count(*) FROM dwh.dim_promotions WHERE promotion_id = '-1'"),
        expression('dwh.dim_promotions', "promotion_id = '-1' OR duration_days >= 1", 'end_date >= start_date'),
    ],
    'bridge_promotion_products': [
        unique('dwh.bridge_promotion_products', 'promotion_id', 'product_id'),
        relationships('dwh.bridge_promotion_products', 'promotion_id', 'dwh.dim_promotions'),
        relationships('dwh.bridge_promotion_products', 'product_id', 'dwh.dim_products'),
        custom('số dòng = stg_promotion_products',
               'SELECT abs((SELECT count(*) FROM dwh.bridge_promotion_products) - '
               '(SELECT count(*) FROM staging.stg_promotion_products))'),
    ],
}


def scd2_distributor_simulation():
    """Đổi tier của 1 NPP ở staging (trong transaction), chạy merge 2 lần, kiểm tra, rồi ROLLBACK."""
    print('\n=== Mô phỏng SCD2 nhà phân phối: merge snapshots.distributors, đọc qua view (sẽ ROLLBACK)')
    merge_sql = SNAPSHOT_SQL.read_text(encoding='utf-8')
    failures = []

    def check(name, ok, detail=''):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f'  ({detail})' if detail else ''))
        if not ok:
            failures.append(f'scd2 simulation: {name}')

    with get_engine().connect() as conn:
        trans = conn.begin()
        try:
            dist_id, old_tier, load_date = conn.execute(text(
                "SELECT distributor_id, tier, _ingested_at::date FROM staging.stg_distributors "
                "WHERE tier <> 'Nhà phân phối cấp 1' ORDER BY distributor_id LIMIT 1")).one()
            before = conn.execute(text('SELECT count(*) FROM dwh.dim_distributors')).scalar()
            conn.execute(text("UPDATE staging.stg_distributors SET tier = 'Nhà phân phối cấp 1', "
                              "_ingested_at = _ingested_at + interval '30 days' WHERE distributor_id = :d"),
                         dict(d=dist_id))
            for _ in range(2):   # chạy 2 lần: lần 2 phải không đổi gì (idempotent)
                with conn.connection.cursor() as cur:
                    cur.execute(merge_sql)
            rows = conn.execute(text(
                'SELECT tier, effective_from, effective_to, is_current, change_reason FROM dwh.dim_distributors '
                'WHERE distributor_id = :d ORDER BY effective_from'), dict(d=dist_id)).all()
            after = conn.execute(text('SELECT count(*) FROM dwh.dim_distributors')).scalar()
            new_date = conn.execute(text('SELECT _ingested_at::date FROM staging.stg_distributors '
                                         'WHERE distributor_id = :d'), dict(d=dist_id)).scalar()
            print(f'    {dist_id}: {old_tier} -> Nhà phân phối cấp 1, load_date {new_date}')
            for r in rows:
                print(f'    {r}')
            check('NPP có 2 bản ghi: cũ đã đóng, mới là current',
                  len(rows) == 2 and rows[0][0] == old_tier and not rows[0][3]
                  and rows[1][0] == 'Nhà phân phối cấp 1' and rows[1][3])
            check('bản ghi cũ hết hạn = load_date − 1, bản ghi mới bắt đầu = load_date',
                  rows[0][2] == rows[1][1] - timedelta(days=1) and rows[1][1] == new_date)
            check('chỉ thêm đúng 1 dòng (chạy merge 2 lần vẫn idempotent)', after == before + 1, f'{before} -> {after}')
        finally:
            trans.rollback()
        restored = conn.execute(text('SELECT count(*) FROM dwh.dim_distributors WHERE distributor_id = :d'),
                                dict(d=dist_id)).scalar()
        check('ROLLBACK: dim_distributors trở về 1 bản ghi', restored == 1)
    return failures


if __name__ == '__main__':
    failed = run_tests(TESTS, 'dwh')
    failed += scd2_distributor_simulation()
    print(f'\nTổng: {len(failed)} FAIL')
    sys.exit(1 if failed else 0)
