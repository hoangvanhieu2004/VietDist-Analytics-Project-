"""Kiểm tra logic phiên bản sales target — Task 2.3.3.

Chạy SAU run_staging.py, từ thư mục gốc dự án:
    python 02_sql_analytics/tests/test_target_versioning.py

Phần 1 — dữ liệu thật: đúng bảng logic của đề bài (T1–T6 -> v1, T7–T12 -> v2), NV nghỉ việc không còn
         target từ T7 (A-28), truy vấn point-in-time.
Phần 2 — mô phỏng v3 (hiệu lực 2024-10-01, chỉ T10–T12) trong 1 transaction rồi ROLLBACK, không ghi gì:
         chứng minh logic chạy với số phiên bản bất kỳ.
"""
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / '01_ingestion'))
sys.stdout.reconfigure(encoding='utf-8')

from utils.db_utils import get_engine  # noqa: E402

MODEL_SQL = PROJECT_ROOT / '02_sql_analytics' / 'staging' / '13_stg_sales_targets_versioned.sql'
SAMPLE_EMPLOYEE = 'EMP1004'
V = 'staging.stg_sales_targets_versioned'
CAL = 'staging.stg_target_version_calendar'

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"[{'ĐẠT' if ok else 'KHÔNG ĐẠT'}] {name}" + (f'\n    {detail}' if detail else ''))


def calendar(conn):
    return dict(conn.execute(text(f'SELECT month, effective_version FROM {CAL} ORDER BY month')).all())


def scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def check_real_data(conn):
    print('=== Phần 1: dữ liệu thật')
    cal = calendar(conn)
    expected = {m: 'v1' if m <= 6 else 'v2' for m in range(1, 13)}
    check('Calendar: T1–T6 -> v1, T7–T12 -> v2 (bảng logic đề bài)', cal == expected, f'{cal}')

    rows = conn.execute(text(f"""
        SELECT version_code, (month <= 6) AS h1, is_latest, superseded_by, min(expiry_date), max(expiry_date), count(*)
        FROM {V} GROUP BY 1, 2, 3, 4 ORDER BY 1, 2 DESC""")).all()
    for r in rows:
        print(f'    {r[0]} {"T1–T6 " if r[1] else "T7–T12"} is_latest={r[2]!s:<5} superseded_by={r[3]!s:<4} '
              f'expiry {r[4]}→{r[5]}: {r[6]:,} dòng')
    summary = {(r[0], r[1], r[2]): r[6] for r in rows}
    n_v1_emp = scalar(conn, f"SELECT count(DISTINCT employee_id) FROM {V} WHERE version_code = 'v1'")
    n_v2_rows = scalar(conn, f"SELECT count(*) FROM {V} WHERE version_code = 'v2'")
    check('v1 T1–T6 đang áp dụng', summary.get(('v1', True, True)) == n_v1_emp * 6,
          f"{summary.get(('v1', True, True))} / {n_v1_emp * 6}")
    check('v1 T7–T12 bị v2 thay thế, hết hạn 2024-06-30',
          summary.get(('v1', False, False)) == n_v1_emp * 6
          and scalar(conn, f"SELECT count(*) FROM {V} WHERE version_code = 'v1' AND month >= 7 "
                           f"AND (expiry_date <> DATE '2024-06-30' OR superseded_by <> 'v2')") == 0,
          f"{summary.get(('v1', False, False))} dòng")
    check('v2 đang áp dụng toàn bộ', summary.get(('v2', False, True)) == n_v2_rows, f'{n_v2_rows} dòng')

    resigned = scalar(conn, f"""
        SELECT count(*) FROM {V} t
        WHERE t.is_latest AND t.month >= 7
          AND t.employee_id IN (SELECT employee_id FROM staging.stg_employee_changes WHERE change_type = 'Nghỉ việc')""")
    n_resigned_h1 = scalar(conn, f"""
        SELECT count(DISTINCT employee_id) FROM {V}
        WHERE is_latest AND month <= 6
          AND employee_id IN (SELECT employee_id FROM staging.stg_employee_changes WHERE change_type = 'Nghỉ việc')""")
    check('NV nghỉ việc: còn target T1–T6, không còn target đang áp dụng từ T7 (A-28)',
          resigned == 0 and n_resigned_h1 == 8, f'{n_resigned_h1} NV có target H1; {resigned} dòng latest từ T7')

    orig = scalar(conn, f"SELECT count(*) FROM {V} WHERE is_original AND version_code <> 'v1'")
    check('is_original = v1 (kế hoạch đầu năm) với mọi NV có trong v1', orig == 0, f'{orig} dòng is_original không phải v1')

    pit = conn.execute(text(f"""
        SELECT d::date, (SELECT version_code || ': ' || to_char(target_revenue, 'FM999,999,999')
                         FROM {V} WHERE employee_id = :e AND year = 2024 AND month = 8
                           AND d BETWEEN effective_date AND expiry_date)
        FROM unnest(ARRAY[DATE '2024-05-15', DATE '2024-08-15']) d"""), dict(e=SAMPLE_EMPLOYEE)).all()
    check(f'Point-in-time: target T8 của {SAMPLE_EMPLOYEE} theo kế hoạch ngày 15/5 là v1, ngày 15/8 là v2',
          pit[0][1].startswith('v1') and pit[1][1].startswith('v2'), f'{pit}')


def check_v3_simulation(conn):
    print('\n=== Phần 2: mô phỏng v3 (ban hành 2024-10-03, hiệu lực 2024-10-01, T10–T12) — sẽ ROLLBACK')
    trans = conn.begin()
    try:
        inserted = conn.execute(text("""
            INSERT INTO staging.stg_sales_targets
                (version_label, employee_id, year, month, month_col, plan_version, version_date,
                 effective_from, effective_to, employee_name, region, team, target_revenue,
                 target_quantity, target_new_customers, _source_file, _source_sheet, _batch_id, _ingested_at)
            SELECT 'v3', employee_id, year, month, month_col, 'v3', DATE '2024-10-03',
                   DATE '2024-10-01', DATE '2024-12-31', employee_name, region, team,
                   round(target_revenue * 1.1), target_quantity, target_new_customers,
                   'TEST_v3', 'TEST_v3', _batch_id, now()
            FROM staging.stg_sales_targets WHERE version_label = 'v2' AND month >= 10""")).rowcount
        with conn.connection.cursor() as cur:   # build lại model trong cùng transaction
            cur.execute(MODEL_SQL.read_text(encoding='utf-8'))

        cal = calendar(conn)
        expected = {m: 'v1' if m <= 6 else 'v2' if m <= 9 else 'v3' for m in range(1, 13)}
        check('Calendar: T1–T6 -> v1, T7–T9 -> v2, T10–T12 -> v3', cal == expected, f'{cal}')

        v2_q4 = conn.execute(text(f"""
            SELECT bool_and(NOT is_latest AND superseded_by = 'v3' AND expiry_date = DATE '2024-09-30'), count(*)
            FROM {V} WHERE version_code = 'v2' AND month >= 10""")).one()
        check('v2 T10–T12 bị v3 thay thế, hết hạn 2024-09-30', v2_q4[0] is True, f'{v2_q4[1]} dòng')
        v2_q3 = scalar(conn, f"SELECT bool_and(is_latest) FROM {V} WHERE version_code = 'v2' AND month BETWEEN 7 AND 9")
        check('v2 T7–T9 vẫn đang áp dụng', v2_q3 is True)
        v1_h2 = scalar(conn, f"SELECT bool_and(superseded_by = 'v2' AND expiry_date = DATE '2024-06-30') "
                             f"FROM {V} WHERE version_code = 'v1' AND month >= 7")
        check('v1 T7–T12 vẫn do v2 thay thế (phiên bản kế tiếp gần nhất)', v1_h2 is True)
        v3_latest = scalar(conn, f"SELECT count(*) FROM {V} WHERE version_code = 'v3' AND is_latest")
        check('v3 đang áp dụng toàn bộ', v3_latest == inserted, f'{v3_latest} / {inserted} dòng')
        multi = scalar(conn, f"""SELECT count(*) FROM (SELECT employee_id, month FROM {V} WHERE is_latest
                                 GROUP BY 1, 2 HAVING count(*) > 1) x""")
        check('Vẫn tối đa 1 dòng is_latest mỗi (NV, tháng)', multi == 0)
        pit = scalar(conn, f"""SELECT string_agg(version_code, ',' ORDER BY d) FROM {V}
                               JOIN unnest(ARRAY[DATE '2024-05-15', DATE '2024-08-15', DATE '2024-11-15']) d
                                 ON d BETWEEN effective_date AND expiry_date
                               WHERE employee_id = :e AND month = 11""", e=SAMPLE_EMPLOYEE)
        check(f'Point-in-time T11 của {SAMPLE_EMPLOYEE} theo ngày 15/5, 15/8, 15/11 = v1, v2, v3',
              pit == 'v1,v2,v3', f'{pit}')
    finally:
        trans.rollback()
    after = scalar(conn, "SELECT count(*) FROM staging.stg_sales_targets WHERE version_label = 'v3'")
    check('ROLLBACK: không còn dữ liệu v3 giả trong DB', after == 0)


if __name__ == '__main__':
    with get_engine().connect() as conn:
        check_real_data(conn)
        conn.commit()
        check_v3_simulation(conn)
    print(f'\n{sum(results)}/{len(results)} kiểm tra đạt')
    sys.exit(0 if all(results) else 1)
