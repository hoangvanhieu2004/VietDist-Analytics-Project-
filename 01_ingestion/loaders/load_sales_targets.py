"""Bronze loader SRC-02: sales_target_plan nhiều phiên bản (Task 1.4).

Mỗi phiên bản (v1, v2, ...) có thể là 1 file riêng HOẶC 1 sheet riêng trong cùng file.
Với mỗi sheet:
1. Tự nhận layout + dòng header (trong 30 dòng đầu):
   - long: có cột month + target_*   (file thật hiện tại) -> giữ nguyên cột, thêm month_col 'T1'..'T12'
   - wide: có cột T1..T12            (theo mô tả đề bài) -> bỏ cột 'Tổng', melt sang month_col + target_value
   Sheet không thuộc 2 layout trên (Summary, hướng dẫn...) bị bỏ qua.
2. Bỏ dòng 'TỔNG' (giá trị đầu tiên của dòng là Tổng/Total).
3. Phiên bản lấy từ tên sheet -> tên file -> cột plan_version. Không xác định được, hoặc tên sheet
   và cột plan_version mâu thuẫn -> file FAILED, không tự đoán.
Kết quả (chỉ append): raw.sales_targets_raw (dữ liệu) + raw.sales_target_files (1 dòng/sheet-phiên bản).
"""
import re
import unicodedata

from base_loader import INGESTION_DIR, Frame, SourceConfig, main
from utils.file_parser import parse_file

TARGET_TABLE = 'sales_targets_raw'
FILES_TABLE = 'sales_target_files'
HEADER_SCAN_ROWS = 30
MIN_MONTH_COLS = 3

MONTH_HEADER_RE = re.compile(r'^(?:t|thang)_?0?(\d{1,2})$')   # T1, T01, Tháng 1 (đã chuẩn hoá)
VERSION_RE = re.compile(r'(?:^|_)(?:v|ver|version|phien_ban|pb)_?(\d+)(?:_|$)')
TOTAL_ROW_RE = re.compile(r'^(?:tong|total)(?:_|$)')
TOTAL_COLS = {'tong', 'tong_cong', 'total', 'ca_nam', 'tong_nam'}
MONTH_COLS = {'month', 'thang'}
VERSION_COLS = {'plan_version', 'version', 'phien_ban'}


def _norm(value):
    """'Tháng 7' -> 'thang_7', 'Plan V2 (Jul)' -> 'plan_v2_jul' — dùng để so khớp, không đổi dữ liệu."""
    s = str(value).replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^0-9a-z]+', '_', s.lower()).strip('_')


def month_label(name):
    """Tên cột tháng -> 'T1'..'T12'; không phải cột tháng -> None."""
    m = MONTH_HEADER_RE.match(_norm(name))
    return f'T{int(m.group(1))}' if m and 1 <= int(m.group(1)) <= 12 else None


def month_from_value(value):
    """Giá trị cột month ('7', '7.0') -> 'T7'; không hợp lệ -> None."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return f'T{int(n)}' if n.is_integer() and 1 <= n <= 12 else None


def detect_version(text):
    m = VERSION_RE.search(_norm(text)) if text else None
    return f'v{int(m.group(1))}' if m else None


def detect_layout(raw_df):
    """Trả về ('wide' | 'long', index dòng header) hoặc (None, None)."""
    for i in range(min(HEADER_SCAN_ROWS, len(raw_df))):
        names = [_norm(v) for v in raw_df.iloc[i] if v is not None]
        if sum(month_label(n) is not None for n in names) >= MIN_MONTH_COLS:
            return 'wide', i
        if set(names) & MONTH_COLS and any(n.startswith('target') for n in names):
            return 'long', i
    return None, None


def _header_names(row):
    names, seen = [], {}
    for i, v in enumerate(row):
        name = str(v).strip() if v is not None else f'col_{i}'
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f'{name}_{seen[name]}')
    return names


def _is_total_row(row):
    first = next((v for v in row if v is not None), None)
    return first is not None and bool(TOTAL_ROW_RE.match(_norm(first)))


def sheet_to_frame(raw_df, layout, header_row):
    """Sheet thô (không header) -> DataFrame Bronze có cột month_col."""
    body = raw_df.iloc[header_row + 1:].copy()
    body.columns = _header_names(raw_df.iloc[header_row])
    body = body.loc[:, body.notna().any()]            # bỏ cột trống hoàn toàn
    body = body[~body.apply(_is_total_row, axis=1)]   # bỏ dòng TỔNG

    if layout == 'wide':
        month_cols = {c: month_label(c) for c in body.columns if month_label(c)}
        id_cols = [c for c in body.columns if c not in month_cols and _norm(c) not in TOTAL_COLS]
        body = body.melt(id_vars=id_cols, value_vars=list(month_cols),
                         var_name='month_col', value_name='target_value')
        body['month_col'] = body['month_col'].map(month_cols)
        body = body[body['target_value'].notna()]
    else:
        month_col = next(c for c in body.columns if _norm(c) in MONTH_COLS)
        body['month_col'] = body[month_col].map(month_from_value)
        invalid = body['month_col'].isna()
        if invalid.any():
            raise ValueError(f'{invalid.sum()} dòng có cột "{month_col}" không phải tháng 1..12')

    return body.astype(object).where(body.notna(), None).reset_index(drop=True)


def assign_version(df, sheet_name, file_name):
    """Thêm cột version_label ở đầu DataFrame."""
    expected = detect_version(sheet_name) or detect_version(file_name)
    col = next((c for c in df.columns if _norm(c) in VERSION_COLS), None)
    row_versions = df[col].map(detect_version) if col else None

    if expected is None:
        if row_versions is None or row_versions.isna().any():
            raise ValueError(f'Không xác định được phiên bản của sheet "{sheet_name}" từ tên sheet, '
                             f'tên file hay cột {sorted(VERSION_COLS)} — đặt tên chứa v1/v2/...')
        labels = row_versions
    else:
        if row_versions is not None:
            mismatch = row_versions.notna() & (row_versions != expected)
            if mismatch.any():
                found = sorted(row_versions[mismatch].unique())
                raise ValueError(f'Sheet "{sheet_name}" là {expected} nhưng {mismatch.sum()} dòng có '
                                 f'{col} = {found}')
        labels = expected
    df.insert(0, 'version_label', labels)
    return df


def parse_target_file(cfg, raw_bytes, file_name):
    """parse_fn cho base_loader: mỗi sheet target -> 2 Frame (dữ liệu + dòng ghi nhận phiên bản)."""
    parsed = parse_file(raw_bytes, file_name, sheet_name=None, header=None)
    sheets = parsed if isinstance(parsed, dict) else {'csv': parsed}

    frames, skipped = [], []
    for sheet, raw_df in sheets.items():
        layout, header_row = detect_layout(raw_df)
        if layout is None:
            skipped.append(sheet)
            continue
        df = assign_version(sheet_to_frame(raw_df, layout, header_row), sheet, file_name)
        frames.append(Frame(TARGET_TABLE, sheet, df))

        summary = df.groupby('version_label').size().reset_index(name='rows_loaded')
        summary.insert(1, 'sheet_name', sheet)
        summary.insert(2, 'layout', layout)
        frames.append(Frame(FILES_TABLE, sheet, summary, count_rows=False))
        print(f'    - sheet "{sheet}": layout {layout}, header ở dòng {header_row}, '
              f'phiên bản {", ".join(summary["version_label"])}')

    if not frames:
        raise ValueError(f'Không có sheet target nào (cần cột T1..T12 hoặc month + target_*); '
                         f'file có: {list(sheets)}')
    return frames, skipped


SOURCE = SourceConfig(
    src_id='SRC-02',
    source_name='sales_target_plan',
    file_prefix='SRC02_',
    parse_fn=parse_target_file,
    setup_sql=INGESTION_DIR / 'sql' / 'create_sales_target_tables.sql',
)

if __name__ == '__main__':
    main(SOURCE)
