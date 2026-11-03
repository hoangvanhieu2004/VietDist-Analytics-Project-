"""Logic Bronze dùng chung cho mọi loader (Task 1.3.3).

Mỗi loader chỉ khai báo 1 SourceConfig rồi gọi main(SOURCE). Với mỗi file khớp file_prefix:
download -> parse -> add_metadata -> load vào raw.<bảng> + ghi ingest_log SUCCESS trong
CÙNG 1 transaction. File lỗi: rollback, ghi log FAILED, chạy tiếp file khác.
"""
import fnmatch
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

INGESTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INGESTION_DIR))  # -> 01_ingestion/

from connectors.gdrive_connector import download_file_as_bytes, list_files_in_folder  # noqa: E402
from utils.db_utils import (add_metadata, ensure_ingest_log, get_engine, load_to_bronze,  # noqa: E402
                            log_ingest, run_sql_file)
from utils.file_parser import EXCEL_ENGINES, get_extension, parse_file  # noqa: E402

PLATFORM = 'google_drive'
SUPPORTED_EXTENSIONS = {'.csv', *EXCEL_ENGINES}


@dataclass(frozen=True)
class SourceConfig:
    src_id: str          # mã nguồn theo BRD, vd 'SRC-01'
    source_name: str     # tên nguồn trong ingest_log; cũng là bảng raw mặc định
    file_prefix: str     # tiền tố tên file trên Drive, vd 'SRC01_'
    sheets: dict = None  # chỉ cho Excel: {glob tên sheet: bảng raw}. None = sheet đầu -> raw.<source_name>
    parse_fn: Callable = None  # (cfg, raw_bytes, file_name) -> (list[Frame], sheet bỏ qua); None = mặc định
    setup_sql: Path = None     # file DDL chạy trước khi load (bảng cần kiểu cố định)


@dataclass
class Frame:
    table: str               # bảng raw đích
    sheet: str               # sheet nguồn; None với CSV
    df: object               # pandas DataFrame
    count_rows: bool = True  # False = bảng phụ (vd raw.sales_target_files), không tính vào rows_loaded


def get_folder_id():
    folder_id = os.getenv('GDRIVE_FOLDER_ID')
    if not folder_id:
        raise RuntimeError('Thiếu GDRIVE_FOLDER_ID trong .env')
    return folder_id


def select_files(files, cfg):
    return [f for f in files
            if f['name'].lower().startswith(cfg.file_prefix.lower())
            and get_extension(f['name']) in SUPPORTED_EXTENSIONS]


def frames_from_file(cfg, raw_bytes, file_name):
    """Tách file thành list[Frame] và list sheet bị bỏ qua."""
    if cfg.parse_fn:
        return cfg.parse_fn(cfg, raw_bytes, file_name)
    if get_extension(file_name) == '.csv':
        return [Frame(cfg.source_name, None, parse_file(raw_bytes, file_name))], []

    sheets = parse_file(raw_bytes, file_name, sheet_name=None)
    sheet_map = cfg.sheets or {next(iter(sheets)): cfg.source_name}
    frames, skipped = [], []
    for sheet, df in sheets.items():
        table = next((t for pattern, t in sheet_map.items()
                      if fnmatch.fnmatch(sheet.lower(), pattern.lower())), None)
        if table:
            frames.append(Frame(table, sheet, df))
        else:
            skipped.append(sheet)
    if not frames:
        raise ValueError(f'Không sheet nào khớp {list(sheet_map)}; file có: {list(sheets)}')
    return frames, skipped


def prepare(cfg):
    """Tạo các bảng hệ thống cần cho nguồn (ingest_log + DDL riêng nếu có)."""
    ensure_ingest_log()
    if cfg.setup_sql:
        run_sql_file(cfg.setup_sql)


def load_one_file(cfg, file_name, raw_bytes, batch_id, started_at=None):
    """Load 1 file (đã download) trong 1 transaction: data + log SUCCESS. Trả về số dòng."""
    started_at = started_at or time.time()
    frames, skipped = frames_from_file(cfg, raw_bytes, file_name)
    total = 0
    with get_engine().begin() as conn:
        for fr in frames:
            df = add_metadata(fr.df, file_name, PLATFORM, batch_id, source_sheet=fr.sheet)
            rows = load_to_bronze(df, fr.table, if_exists='append', conn=conn)
            if fr.count_rows:
                total += rows
            if fr.sheet is not None:
                print(f'    - sheet "{fr.sheet}" -> raw.{fr.table}: {rows} dòng')
        log_ingest(batch_id, cfg.source_name, 'SUCCESS', source_file=file_name, source_platform=PLATFORM,
                   rows_loaded=total, duration_sec=round(time.time() - started_at, 2), conn=conn)
    for sheet in skipped:
        print(f'    - sheet "{sheet}": bỏ qua')
    return total


def run_loader(cfg, batch_id=None):
    """Load mọi file của 1 nguồn vào Bronze. Trả về (tổng số dòng, số lỗi)."""
    batch_id = batch_id or str(uuid.uuid4())
    prepare(cfg)

    try:
        files = select_files(list_files_in_folder(get_folder_id()), cfg)
        if not files:
            raise FileNotFoundError(f'Không có file nào bắt đầu bằng "{cfg.file_prefix}"')
    except Exception as e:
        print(f'[{cfg.src_id}] {cfg.source_name}: LỖI — {e}')
        log_ingest(batch_id, cfg.source_name, 'FAILED', source_platform=PLATFORM, error_message=str(e))
        return 0, 1

    print(f'[{cfg.src_id}] {cfg.source_name}: tìm thấy {len(files)} file')
    total_loaded, failed = 0, 0
    for f in files:
        start = time.time()
        try:
            raw_bytes = download_file_as_bytes(f['id'], f['mimeType'])
            rows = load_one_file(cfg, f['name'], raw_bytes, batch_id, started_at=start)
            total_loaded += rows
            print(f'  OK: {f["name"]} — {rows} dòng')
        except Exception as e:
            failed += 1
            print(f'  LỖI: {f["name"]} — {e}')
            log_ingest(batch_id, cfg.source_name, 'FAILED', source_file=f['name'], source_platform=PLATFORM,
                       error_message=str(e), duration_sec=round(time.time() - start, 2))

    print(f'  Tổng cộng: {total_loaded} dòng đã load, {failed} file lỗi')
    return total_loaded, failed


def main(cfg):
    _, failed = run_loader(cfg)
    sys.exit(1 if failed else 0)
