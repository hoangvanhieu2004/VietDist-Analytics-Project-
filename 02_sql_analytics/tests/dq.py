"""Helper data quality test kiểu dbt — dùng chung cho test_staging.py và test_dwh.py.

Mỗi helper trả về (tên test, SQL đếm số dòng VI PHẠM); test đạt khi = 0.
Tên bảng không có schema -> mặc định 'staging.'; viết 'dwh.dim_x' để test schema khác.
"""
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / '01_ingestion'))
sys.stdout.reconfigure(encoding='utf-8')

from utils.db_utils import get_engine  # noqa: E402

DEFAULT_SCHEMA = 'staging'


def q(table):
    return table if '.' in table else f'{DEFAULT_SCHEMA}.{table}'


def unique(table, *cols):
    c = ', '.join(cols)
    return (f'unique({c})',
            f'SELECT count(*) FROM (SELECT {c} FROM {q(table)} GROUP BY {c} HAVING count(*) > 1) x')


def not_null(table, *cols):
    return [(f'not_null({c})', f'SELECT count(*) FROM {q(table)} WHERE {c} IS NULL') for c in cols]


def accepted_values(table, col, values):
    vals = ', '.join("'" + v.replace("'", "''") + "'" for v in values)
    return (f'accepted_values({col})',
            f'SELECT count(*) FROM {q(table)} WHERE {col} IS NOT NULL AND {col} NOT IN ({vals})')


def relationships(table, cols, ref_table, ref_cols=None):
    """Mọi giá trị (khác NULL) của cols phải tồn tại trong ref_table.ref_cols."""
    cols = [cols] if isinstance(cols, str) else cols
    ref_cols = ref_cols or cols
    ref_cols = [ref_cols] if isinstance(ref_cols, str) else ref_cols
    cond = ' AND '.join(f'r.{rc} = t.{c}' for c, rc in zip(cols, ref_cols))
    not_null_cond = ' AND '.join(f't.{c} IS NOT NULL' for c in cols)
    return (f'relationships({", ".join(cols)} → {ref_table})',
            f'SELECT count(*) FROM {q(table)} t WHERE {not_null_cond} '
            f'AND NOT EXISTS (SELECT 1 FROM {q(ref_table)} r WHERE {cond})')


def expression(table, condition, name=None):
    """condition phải TRUE với mọi dòng (NULL tính là vi phạm)."""
    return (f'expression: {name or condition}',
            f'SELECT count(*) FROM {q(table)} WHERE ({condition}) IS NOT TRUE')


def custom(name, sql):
    """Test viết tay: sql trả về số dòng vi phạm."""
    return name, sql


def row_count(table, raw_table, raw_key):
    """Số dòng staging = số khoá khác nhau trong raw (dedup không làm mất / thừa bản ghi)."""
    return (f'row_count = số khoá distinct trong raw.{raw_table}',
            f'SELECT abs((SELECT count(*) FROM {q(table)}) - '
            f'(SELECT count(DISTINCT ({raw_key})) FROM raw.{raw_table}))')


def run_tests(tests, schema=DEFAULT_SCHEMA):
    """Chạy dict {bảng: [(tên, sql), ...]}, in PASS/FAIL. Trả về danh sách test FAIL."""
    total, failed = 0, []
    with get_engine().connect() as conn:
        for table, table_tests in tests.items():
            print(f'\n== {schema}.{table}')
            for name, sql in table_tests:
                total += 1
                try:
                    bad = conn.execute(text(sql)).scalar()
                except Exception as e:
                    conn.rollback()
                    bad, name = -1, f'{name} — LỖI SQL: {str(e).splitlines()[0]}'
                ok = bad == 0
                print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + ('' if ok else f'  -> {bad:,} dòng vi phạm'))
                if not ok:
                    failed.append(f'{table}: {name}')

    print(f'\n{total - len(failed)}/{total} test PASS, {len(failed)} FAIL')
    for f in failed:
        print(f'  - {f}')
    return failed
