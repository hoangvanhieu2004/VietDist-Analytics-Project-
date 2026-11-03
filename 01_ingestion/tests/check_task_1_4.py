"""Kiểm tra CHECKPOINT Task 1.4 — Sales Target Plan nhiều phiên bản.

Chạy SAU khi đã load SRC-02 (run_bronze.py hoặc loaders/load_sales_targets.py), từ thư mục gốc:
    python 01_ingestion/tests/check_task_1_4.py

Phần A — dữ liệu thật trong vietdist_dw: số dòng khớp file (đếm độc lập bằng openpyxl), version,
         month_col, không có dòng TỔNG.
Phần B — DB tạm vietdist_dw_test (tạo rồi xoá): chạy file chỉ-v1 rồi file chỉ-v2 (tách từ file
         thật), file wide giả có dòng TỔNG + cột Tổng, và file có phiên bản mâu thuẫn.
"""
import io
import os
import sys
import uuid
from pathlib import Path

import openpyxl
from sqlalchemy import create_engine, text

INGESTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INGESTION_DIR / 'loaders'))
sys.stdout.reconfigure(encoding='utf-8')

import base_loader  # noqa: E402  (cũng thêm 01_ingestion/ vào sys.path)
import load_sales_targets  # noqa: E402
from connectors.gdrive_connector import download_file_as_bytes, list_files_in_folder  # noqa: E402
from utils import db_utils  # noqa: E402

CFG = load_sales_targets.SOURCE
TEST_DB = 'vietdist_dw_test'
VALID_MONTHS = {f'T{i}' for i in range(1, 13)}
TOTAL_ROW_SQL = ("SELECT count(*) FROM raw.sales_targets_raw t "
                 "WHERE to_jsonb(t)::text ~* '\"(tổng|tong|total)[^\"]*\"' AND {where}")

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"[{'ĐẠT' if ok else 'KHÔNG ĐẠT'}] {name}" + (f'\n    {detail}' if detail else ''))


def target_sheet_rows(raw_bytes):
    """Đếm độc lập: {tên sheet: số dòng dữ liệu} cho các sheet có header chứa cột 'month'."""
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True)
    counts = {}
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        header = [str(c).strip().lower() for c in next(rows, ()) if c is not None]
        if 'month' in header:
            counts[ws.title] = sum(1 for r in rows if any(c is not None and str(c).strip() for c in r))
    return counts


def scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


# ---------------------------------------------------------------- Phần A: dữ liệu thật
def check_real_data():
    print('=== Phần A: dữ liệu thật trong', os.getenv('DB_NAME'))
    files = base_loader.select_files(list_files_in_folder(base_loader.get_folder_id()), CFG)
    check(f'Tìm thấy file {CFG.file_prefix}* trên Drive', bool(files), ', '.join(f['name'] for f in files))

    with db_utils.get_engine().connect() as conn:
        for f in files:
            batch = scalar(conn, "SELECT batch_id FROM raw.ingest_log WHERE source_name=:s AND source_file=:f "
                                 "AND status='SUCCESS' ORDER BY logged_at DESC LIMIT 1",
                           s=CFG.source_name, f=f['name'])
            if batch is None:
                check(f"{f['name']} đã load", False, 'không có log SUCCESS — hãy chạy loader trước')
                continue
            for sheet, expected in target_sheet_rows(download_file_as_bytes(f['id'], f['mimeType'])).items():
                actual = scalar(conn, 'SELECT count(*) FROM raw.sales_targets_raw '
                                      'WHERE _batch_id=:b AND _source_file=:f AND _source_sheet=:s',
                                b=batch, f=f['name'], s=sheet)
                logged = conn.execute(text(
                    'SELECT version_label, rows_loaded FROM raw.sales_target_files '
                    'WHERE _batch_id=:b AND _source_file=:f AND sheet_name=:s'), dict(b=batch, f=f['name'], s=sheet)).all()
                check(f'raw.sales_targets_raw ← {f["name"]} / {sheet}', actual == expected,
                      f'DB {actual:,} / file {expected:,}')
                check(f'raw.sales_target_files có 1 dòng cho sheet {sheet}',
                      len(logged) == 1 and logged[0][1] == expected, f'{logged}')

        versions = [r[0] for r in conn.execute(text(
            'SELECT DISTINCT version_label FROM raw.sales_target_files ORDER BY 1'))]
        check('DISTINCT version_label có v1, v2', {'v1', 'v2'} <= set(versions), f'{versions}')
        months = {r[0] for r in conn.execute(text('SELECT DISTINCT month_col FROM raw.sales_targets_raw'))}
        check('month_col chỉ chứa T1..T12', months == VALID_MONTHS, f'{sorted(months, key=str)}')
        n_total = scalar(conn, TOTAL_ROW_SQL.format(where='true'))
        check("Không có dòng 'TỔNG' trong raw.sales_targets_raw", n_total == 0, f'{n_total} dòng')


# ---------------------------------------------------------------- Phần B: DB tạm
def build_test_files(real_bytes):
    """Tạo các file test trong bộ nhớ: chỉ-v1, chỉ-v2, wide giả, phiên bản mâu thuẫn."""
    def workbook_with(keep, rename=None):
        wb = openpyxl.load_workbook(io.BytesIO(real_bytes))
        for name in wb.sheetnames:
            if name not in keep:
                del wb[name]
        if rename:
            wb[rename[0]].title = rename[1]
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    names = openpyxl.load_workbook(io.BytesIO(real_bytes), read_only=True).sheetnames
    v1 = next(n for n in names if '_v1' in n.lower())
    v2 = next(n for n in names if '_v2' in n.lower())
    others = [n for n in names if n not in (v1, v2)]

    wide = openpyxl.Workbook()
    ws = wide.active
    ws.title = 'Plan v3'
    ws.append(['KẾ HOẠCH DOANH SỐ - ĐIỀU CHỈNH Q4'])
    ws.append([])
    ws.append(['Mã NV', 'Họ Tên'] + [f'T{i}' for i in range(1, 13)] + ['Tổng'])
    for k, (emp, name) in enumerate([('EMP9001', 'Nguyễn Văn A'), ('EMP9002', 'Trần Thị B')]):
        values = [(100 + k * 10 + m) * 1_000_000 for m in range(1, 13)]
        ws.append([emp, name] + values + [sum(values)])
    ws.append(['TỔNG', None] + [None] * 12 + [999])
    buf = io.BytesIO()
    wide.save(buf)

    return {
        'v1': ('SRC02_test_only_v1.xlsx', workbook_with([v1] + others), v1),
        'v2': ('SRC02_test_only_v2.xlsx', workbook_with([v2]), v2),
        'wide': ('SRC02_test_wide.xlsx', buf.getvalue(), 'Plan v3'),
        'mismatch': ('SRC02_test_mismatch.xlsx', workbook_with([v1], rename=(v1, 'Plan_v2_Check')), None),
    }


def check_versioning_on_test_db():
    print('\n=== Phần B: chạy lần lượt các phiên bản trên DB tạm', TEST_DB)
    real = base_loader.select_files(list_files_in_folder(base_loader.get_folder_id()), CFG)[0]
    real_bytes = download_file_as_bytes(real['id'], real['mimeType'])
    expected = target_sheet_rows(real_bytes)
    test_files = build_test_files(real_bytes)

    admin = create_engine(db_utils.get_engine().url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)'))
        conn.execute(text(f"CREATE DATABASE {TEST_DB} ENCODING 'UTF8'"))
    original_db = os.environ.get('DB_NAME')
    try:
        os.environ['DB_NAME'] = TEST_DB
        db_utils._engine = None  # engine mới trỏ tới DB tạm
        with db_utils.get_engine().begin() as conn:
            conn.execute(text('CREATE SCHEMA raw'))
        base_loader.prepare(CFG)

        def load(key):
            name, data, _ = test_files[key]
            print(f'  -> load {name}')
            return base_loader.load_one_file(CFG, name, data, str(uuid.uuid4()))

        def count(conn, version):
            return scalar(conn, 'SELECT count(*) FROM raw.sales_targets_raw WHERE version_label=:v', v=version)

        # Chạy với file v1
        load('v1')
        v1_sheet = test_files['v1'][2]
        with db_utils.get_engine().connect() as conn:
            rows = conn.execute(text('SELECT version_label, sheet_name FROM raw.sales_target_files')).all()
            check('File v1: raw.sales_target_files có 1 dòng/sheet target (Summary bị bỏ qua)',
                  rows == [('v1', v1_sheet)], f'{rows}')
            check('File v1: raw.sales_targets_raw có dữ liệu v1', count(conn, 'v1') == expected[v1_sheet],
                  f'{count(conn, "v1"):,} / {expected[v1_sheet]:,}')

        # Chạy tiếp với file v2 — v1 phải còn nguyên
        load('v2')
        v2_sheet = test_files['v2'][2]
        with db_utils.get_engine().connect() as conn:
            versions = [r[0] for r in conn.execute(text(
                'SELECT DISTINCT version_label FROM raw.sales_target_files ORDER BY 1'))]
            check('File v2: thêm dòng mới, KHÔNG xoá dòng v1', versions == ['v1', 'v2'], f'{versions}')
            check('File v2: dữ liệu v1 còn nguyên, v2 đủ dòng',
                  count(conn, 'v1') == expected[v1_sheet] and count(conn, 'v2') == expected[v2_sheet],
                  f'v1 {count(conn, "v1"):,}, v2 {count(conn, "v2"):,}')

        # File wide có dòng TỔNG + cột Tổng
        load('wide')
        with db_utils.get_engine().connect() as conn:
            check('File wide: 2 NV × 12 tháng = 24 dòng v3', count(conn, 'v3') == 24, f'{count(conn, "v3")}')
            n_total = scalar(conn, TOTAL_ROW_SQL.format(where="version_label='v3'"))
            check("File wide: dòng 'TỔNG' không xuất hiện", n_total == 0, f'{n_total} dòng')
            months = {r[0] for r in conn.execute(text(
                "SELECT DISTINCT month_col FROM raw.sales_targets_raw WHERE version_label='v3'"))}
            check('File wide: month_col đúng T1..T12', months == VALID_MONTHS, f'{sorted(months)}')
            cols = [r[0] for r in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='raw' AND table_name='sales_targets_raw'"))]
            check('File wide: không có cột Tổng', not any(c.lower() in ('tổng', 'tong', 'total') for c in cols))

        # Tên sheet nói v2 nhưng cột plan_version là v1 -> phải lỗi, không ghi gì
        with db_utils.get_engine().connect() as conn:
            before = scalar(conn, 'SELECT count(*) FROM raw.sales_targets_raw')
        try:
            load('mismatch')
            failed, msg = False, 'không báo lỗi'
        except ValueError as e:
            failed, msg = True, str(e)
        with db_utils.get_engine().connect() as conn:
            after = scalar(conn, 'SELECT count(*) FROM raw.sales_targets_raw')
        check('Phiên bản mâu thuẫn -> báo lỗi và không ghi dòng nào', failed and before == after, msg)
    finally:
        db_utils.get_engine().dispose()
        db_utils._engine = None
        if original_db is None:
            os.environ.pop('DB_NAME', None)
        else:
            os.environ['DB_NAME'] = original_db
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)'))
        admin.dispose()


if __name__ == '__main__':
    check_real_data()
    check_versioning_on_test_db()
    print(f'\n{sum(results)}/{len(results)} checkpoint đạt')
    sys.exit(0 if all(results) else 1)
