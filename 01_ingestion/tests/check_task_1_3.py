"""Kiểm tra CHECKPOINT Task 1.3 — load dữ liệu thô vào Bronze (schema raw).

Chạy SAU khi đã chạy run_bronze.py, từ thư mục gốc dự án:
    python 01_ingestion/tests/check_task_1_3.py
    python 01_ingestion/tests/check_task_1_3.py --skip-double   # bỏ qua test chạy 2 lần

Số dòng nguồn được đếm ĐỘC LẬP (csv / openpyxl), không dùng file_parser của dự án.
Test "chạy 2 lần" dùng DB tạm vietdist_dw_test (tạo rồi xoá) để không nhân đôi dữ liệu thật.
"""
import argparse
import csv
import fnmatch
import io
import os
import subprocess
import sys
from pathlib import Path

import openpyxl
from sqlalchemy import create_engine, text

INGESTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INGESTION_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from connectors.gdrive_connector import download_file_as_bytes, list_files_in_folder  # noqa: E402
from run_bronze import SOURCES as ALL_SOURCES  # noqa: E402
from base_loader import get_folder_id, select_files  # noqa: E402

SOURCES = [s for s in ALL_SOURCES if s.parse_fn is None]  # SRC-02 kiểm tra ở check_task_1_4.py
from utils.db_utils import get_engine  # noqa: E402
from utils.file_parser import get_extension  # noqa: E402

TEST_DB = 'vietdist_dw_test'
DOUBLE_TEST_LOADER = 'load_sales_transactions.py'
METADATA = ['_source_file', '_source_platform', '_ingested_at', '_batch_id']

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"[{'ĐẠT' if ok else 'KHÔNG ĐẠT'}] {name}" + (f'\n    {detail}' if detail else ''))


def expected_rows(cfg, f):
    """Đếm số dòng dữ liệu của file nguồn -> dict {(bảng raw, sheet | None): số dòng}."""
    raw = download_file_as_bytes(f['id'], f['mimeType'])
    if get_extension(f['name']) == '.csv':
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
        return {(cfg.source_name, None): sum(1 for r in rows[1:] if any(c.strip() for c in r))}

    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True)
    sheet_map = cfg.sheets or {wb.sheetnames[0]: cfg.source_name}
    counts = {}
    for ws in wb.worksheets:
        table = next((t for p, t in sheet_map.items() if fnmatch.fnmatch(ws.title.lower(), p.lower())), None)
        if table:
            counts[(table, ws.title)] = sum(1 for r in ws.iter_rows(min_row=2, values_only=True)
                                            if any(c is not None and str(c).strip() for c in r))
    return counts


def table_exists(conn, table):
    return conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), dict(t=f'raw.{table}')).scalar()


def check_loaded_data():
    drive_files = list_files_in_folder(get_folder_id())
    engine = get_engine()
    with engine.connect() as conn:
        # CP: bảng tồn tại + đủ cột metadata
        tables = sorted({cfg.source_name for cfg in SOURCES} | {t for cfg in SOURCES for t in (cfg.sheets or {}).values()})
        missing = [t for t in tables if not table_exists(conn, t)]
        check(f'Đủ {len(tables)} bảng raw.*', not missing, f'thiếu: {missing}' if missing else ', '.join(tables))
        for t in set(tables) - set(missing):
            cols = {r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='raw' AND table_name=:t"),
                dict(t=t))}
            lacking = [m for m in METADATA if m not in cols]
            if lacking:
                check(f'raw.{t} có đủ cột metadata', False, f'thiếu {lacking}')

        # CP: ingest_log có dòng SUCCESS
        n_success = conn.execute(text("SELECT count(*) FROM raw.ingest_log WHERE status='SUCCESS'")).scalar() \
            if table_exists(conn, 'ingest_log') else 0
        check('raw.ingest_log có ít nhất 1 dòng SUCCESS', n_success >= 1, f'{n_success} dòng SUCCESS')

        # CP: số dòng khớp file nguồn + _source_file đúng tên file gốc (theo batch SUCCESS gần nhất)
        for cfg in SOURCES:
            for f in select_files(drive_files, cfg):
                batch = conn.execute(text(
                    "SELECT batch_id FROM raw.ingest_log WHERE source_name=:s AND source_file=:f "
                    "AND status='SUCCESS' ORDER BY logged_at DESC LIMIT 1"), dict(s=cfg.source_name, f=f['name'])).scalar()
                if batch is None:
                    check(f"{f['name']} đã load", False, 'không có log SUCCESS')
                    continue
                for (table, sheet), expected in expected_rows(cfg, f).items():
                    sql = (f'SELECT count(*) FROM raw."{table}" WHERE _batch_id = :b AND _source_file = :f'
                           + (' AND _source_sheet = :sh' if sheet else ''))
                    actual = conn.execute(text(sql), dict(b=batch, f=f['name'], sh=sheet)).scalar()
                    label = f"raw.{table} ← {f['name']}" + (f' / {sheet}' if sheet else '')
                    check(f'Số dòng {label}', actual == expected, f'DB {actual:,} / file {expected:,}')


def check_double_run():
    """Chạy loader 2 lần với cùng file trên DB tạm -> số dòng phải tăng gấp đôi."""
    admin_url = get_engine().url.set(database='postgres')
    admin = create_engine(admin_url, isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)'))
        conn.execute(text(f"CREATE DATABASE {TEST_DB} ENCODING 'UTF8'"))
    try:
        test_engine = create_engine(get_engine().url.set(database=TEST_DB))
        with test_engine.begin() as conn:
            conn.execute(text('CREATE SCHEMA raw'))
        env = {**os.environ, 'DB_NAME': TEST_DB, 'PYTHONIOENCODING': 'utf-8'}
        loader = INGESTION_DIR / 'loaders' / DOUBLE_TEST_LOADER
        counts = []
        for _ in range(2):
            subprocess.run([sys.executable, str(loader)], env=env, check=True, capture_output=True)
            with test_engine.connect() as conn:
                counts.append(conn.execute(text('SELECT count(*) FROM raw.sales_transactions')).scalar())
        test_engine.dispose()
        check(f'Chạy {DOUBLE_TEST_LOADER} 2 lần -> số dòng tăng gấp đôi',
              counts[0] > 0 and counts[1] == 2 * counts[0], f'lần 1: {counts[0]:,}, lần 2: {counts[1]:,}')
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)'))
        admin.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-double', action='store_true', help='bỏ qua test chạy loader 2 lần')
    args = parser.parse_args()

    check_loaded_data()
    if not args.skip_double:
        check_double_run()

    print(f'\n{sum(results)}/{len(results)} checkpoint đạt')
    sys.exit(0 if all(results) else 1)
