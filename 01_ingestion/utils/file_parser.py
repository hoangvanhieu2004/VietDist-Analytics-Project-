"""Đọc file nguồn (bytes) thành DataFrame — CSV, XLSX, XLSM, XLSB (Task 1.1.3).

Nguyên tắc cho Bronze: giữ nguyên tên cột và giá trị như trong file.
- Mọi giá trị đọc dạng chuỗi (dtype=str) để không mất số 0 đầu (vd SĐT '0928...')
- Ô trống -> None; dòng trống hoàn toàn bị bỏ
- XLSM: phần macro bị bỏ qua (đúng mong muốn)
- XLSB: pyxlsb trả ngày dưới dạng số serial Excel (vd '45672') — convert ở Silver
Dữ liệu thật hiện chỉ có CSV và XLSX; XLSM/XLSB được hỗ trợ theo yêu cầu đề bài.
"""
import io
from pathlib import PurePath

import pandas as pd

EXCEL_ENGINES = {'.xlsx': 'openpyxl', '.xlsm': 'openpyxl', '.xlsb': 'pyxlsb'}
CSV_ENCODINGS = ('utf-8-sig', 'cp1258')  # UTF-8 (có/không BOM), rồi Windows tiếng Việt
CSV_DELIMITERS = (',', ';', '\t', '|')


def get_extension(file_name):
    return PurePath(file_name).suffix.lower()


def _decode_csv(raw_bytes):
    if raw_bytes[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw_bytes.decode('utf-16')
    for encoding in CSV_ENCODINGS:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f'Không decode được CSV với các encoding {CSV_ENCODINGS}')


def _detect_delimiter(text):
    header_line = text.split('\n', 1)[0]
    return max(CSV_DELIMITERS, key=header_line.count)


def _clean(df):
    """Bỏ dòng trống hoàn toàn, NaN -> None."""
    df = df.dropna(how='all').reset_index(drop=True)
    return df.astype(object).where(df.notna(), None)


def list_sheets(raw_bytes, file_name):
    """Danh sách tên sheet của file Excel."""
    ext = get_extension(file_name)
    if ext not in EXCEL_ENGINES:
        raise ValueError(f'{file_name} không phải file Excel')
    with pd.ExcelFile(io.BytesIO(raw_bytes), engine=EXCEL_ENGINES[ext]) as xls:
        return xls.sheet_names


def parse_file(raw_bytes, file_name, sheet_name=0, header=0):
    """Đọc bytes của file thành DataFrame (mọi giá trị là str hoặc None).

    sheet_name: chỉ dùng cho Excel — index hoặc tên sheet; None = đọc tất cả sheet,
                khi đó trả về dict {tên sheet: DataFrame}.
    header:     index dòng header; None = không lấy header (cột đánh số 0, 1, 2...),
                dùng khi cần tự dò dòng header như file sales target.
    """
    ext = get_extension(file_name)

    if ext == '.csv':
        text = _decode_csv(raw_bytes)
        df = pd.read_csv(io.StringIO(text), sep=_detect_delimiter(text), header=header, dtype=str,
                         keep_default_na=False, na_values=[''])
        return _clean(df)

    if ext in EXCEL_ENGINES:
        result = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sheet_name, header=header, dtype=str,
                               engine=EXCEL_ENGINES[ext], keep_default_na=False, na_values=[''])
        if isinstance(result, dict):
            return {name: _clean(df) for name, df in result.items()}
        return _clean(result)

    raise ValueError(f'Định dạng không hỗ trợ: {file_name} (chỉ hỗ trợ .csv, .xlsx, .xlsm, .xlsb)')
