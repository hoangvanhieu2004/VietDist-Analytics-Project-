"""Chạy các file model SQL (NN_<tên>.sql) theo thứ tự — dùng chung cho staging, snapshots và dwh.

Mỗi file chạy trong 1 transaction: lỗi -> rollback file đó (đối tượng cũ giữ nguyên), dừng và báo lỗi.
File tên 'NN_helpers.sql' luôn được chạy (kể cả khi lọc only) và không đếm dòng.
"""
import sys
import time
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / '01_ingestion'))
sys.stdout.reconfigure(encoding='utf-8')

from utils.db_utils import get_engine  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent
STAGING_DIR = SQL_DIR / 'staging'
SNAPSHOTS_DIR = SQL_DIR / 'snapshots'
DWH_DIR = SQL_DIR / 'dwh'
HELPERS = 'helpers'


def model_name(path):
    """'07_stg_sales_transactions.sql' -> 'stg_sales_transactions'"""
    return path.stem.split('_', 1)[1]


def model_files(models_dir):
    return sorted(Path(models_dir).glob('[0-9][0-9]_*.sql'))


def model_names(models_dir):
    return [model_name(f) for f in model_files(models_dir) if model_name(f) != HELPERS]


def build(models_dir, schema, only=None):
    """Chạy các model của 1 thư mục vào schema; only = danh sách tên model (None = tất cả)."""
    print(f'== {schema}')
    engine = get_engine()
    for f in model_files(models_dir):
        name = model_name(f)
        if only and name != HELPERS and name not in only:
            continue
        start = time.time()
        try:
            with engine.begin() as conn:
                # cursor thô, không truyền params: để psycopg2 không hiểu '%' trong RAISE là placeholder
                with conn.connection.cursor() as cur:
                    cur.execute(f.read_text(encoding='utf-8'))
                rows = None if name == HELPERS else conn.execute(text(f'SELECT count(*) FROM {schema}.{name}')).scalar()
        except Exception as e:
            print(f'  LỖI: {f.name}\n    {str(e).splitlines()[0]}')
            print('Dừng. Đối tượng của file lỗi giữ nguyên phiên bản trước.')
            sys.exit(1)
        detail = 'hàm helper' if rows is None else f'{rows:,} dòng'
        print(f'  OK: {f.name:<36} {detail:>14}  ({time.time() - start:.1f}s)')


def build_gold(only=None):
    """Gold = snapshots (bảng lịch sử, merge) rồi dwh (view). View cần snapshot tồn tại trước."""
    build(SNAPSHOTS_DIR, 'snapshots')
    build(DWH_DIR, 'dwh', only)
