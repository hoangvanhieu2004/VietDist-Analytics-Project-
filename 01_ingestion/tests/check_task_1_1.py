"""Kiểm tra CHECKPOINT Task 1.1 — kết nối và đọc file từ Google Drive.

Chạy từ thư mục gốc dự án:  python 01_ingestion/tests/check_task_1_1.py
"""
import csv
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # -> 01_ingestion/
sys.stdout.reconfigure(encoding='utf-8')

from connectors.gdrive_connector import download_file_as_bytes, list_files_in_folder  # noqa: E402
from utils.file_parser import get_extension, parse_file  # noqa: E402

EXPECTED_FILE_COUNT = 10
MOJIBAKE_MARKERS = ('�', 'Ã', 'Â', 'á»')  # dấu hiệu tiếng Việt bị decode sai

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"[{'ĐẠT' if ok else 'KHÔNG ĐẠT'}] {name}" + (f'\n    {detail}' if detail else ''))


def download(f):
    return download_file_as_bytes(f['id'], f['mimeType'])


folder_id = os.getenv('GDRIVE_FOLDER_ID')
if not folder_id:
    sys.exit('Thiếu GDRIVE_FOLDER_ID trong .env')

# CP1: list_files_in_folder hiển thị danh sách file đúng
files = list_files_in_folder(folder_id)
for f in files:
    print(f"    {f['name']:<36} {int(f.get('size') or 0):>12,} bytes")
check(f'CP1 list_files_in_folder: {len(files)} file', len(files) == EXPECTED_FILE_COUNT,
      f'kỳ vọng {EXPECTED_FILE_COUNT} file')

csv_files = [f for f in files if get_extension(f['name']) == '.csv']

# CP2: download 1 CSV và đọc được thành DataFrame với đúng số cột
f = next(f for f in csv_files if 'customer_master' in f['name'])
raw = download(f)
df = parse_file(raw, f['name'])
header = next(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
check(f"CP2 đọc CSV {f['name']}", df.shape[1] == len(header),
      f'DataFrame {df.shape}, header trong file có {len(header)} cột')

# CP3: download file distributor_orders và đọc được thành DataFrame
f = next(f for f in files if 'distributor_orders' in f['name'])
sheets = parse_file(download(f), f['name'], sheet_name=None)
check(f"CP3 đọc {f['name']}", all(not d.empty for d in sheets.values()),
      ', '.join(f'sheet "{s}": {d.shape}' for s, d in sheets.items()))

# CP4: không có lỗi encoding khi đọc CSV tiếng Việt
for f in csv_files:
    df = parse_file(download(f), f['name'])
    text = ' '.join(str(v) for v in df.values.ravel() if v is not None)
    bad = sum(text.count(m) for m in MOJIBAKE_MARKERS)
    sample = next((v for v in df.iloc[0] if v and any(ord(c) > 127 for c in v)), '')
    check(f"CP4 encoding {f['name']}", bad == 0,
          f'{len(df):,} dòng, {bad} ký tự lỗi, ví dụ: "{sample}"')

print(f'\n{sum(results)}/{len(results)} checkpoint đạt')
sys.exit(0 if all(results) else 1)
