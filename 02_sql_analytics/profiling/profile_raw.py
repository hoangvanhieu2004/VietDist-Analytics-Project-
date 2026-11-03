"""Profile tự động mọi cột của các bảng raw.* (Task 2.1) -> docs/data_profile.md

Chạy từ thư mục gốc dự án:  python 02_sql_analytics/profiling/profile_raw.py

Với mỗi cột: % thiếu (NULL hoặc rỗng), khoảng trắng thừa, số giá trị khác nhau, kiểu đoán được
(date / number / mã / text), số giá trị không ép được sang kiểu đó + ví dụ, min/max, ngày ngoài
khoảng 2022–2026. Cột ít giá trị: liệt kê giá trị + tần suất, cảnh báo biến thể hoa/thường/khoảng trắng.
Chỉ đọc dữ liệu, không ghi vào DB.
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / '01_ingestion'))
sys.stdout.reconfigure(encoding='utf-8')

from utils.db_utils import get_engine  # noqa: E402

OUTPUT = PROJECT_ROOT / 'docs' / 'data_profile.md'
SKIP_TABLES = {'ingest_log', 'sales_target_files'}   # bảng hệ thống của pipeline
DATE_MIN, DATE_MAX = pd.Timestamp('2022-01-01'), pd.Timestamp('2026-12-31')
DATE_RANGE_EXEMPT = {'date_of_birth', 'join_date', 'launch_date', 'expiry_date'}
TYPE_THRESHOLD = 0.9        # >= 90% giá trị ép được -> coi là kiểu đó
CATEGORY_MAX_DISTINCT = 20  # cột text có <= 20 giá trị khác nhau -> liệt kê giá trị
EXAMPLES = 5

NUMERIC_RE = r'^-?\d+(?:\.\d+)?$'
DATE_RE = r'^\d{4}-\d{2}-\d{2}(?: 00:00:00)?$'


def md(value):
    """Escape giá trị để đặt trong ô bảng markdown."""
    return str(value).replace('|', '\\|').replace('\n', ' ')


def infer_type(values):
    """values: Series chuỗi đã strip, không rỗng. Trả về (kiểu, mask giá trị không ép được)."""
    is_date = values.str.match(DATE_RE) & pd.to_datetime(values.str[:10], format='%Y-%m-%d',
                                                          errors='coerce').notna()
    if is_date.mean() >= TYPE_THRESHOLD:
        return 'date', ~is_date
    is_num = values.str.match(NUMERIC_RE)
    if is_num.mean() >= TYPE_THRESHOLD:
        if values.str.match(r'^0\d').any():   # SĐT, mã số thuế... có số 0 đầu -> giữ dạng text
            return 'mã (số 0 đầu)', ~is_num
        return 'number', ~is_num
    return 'text', pd.Series(False, index=values.index)


def profile_column(series):
    total = len(series)
    non_null = series.dropna()
    stripped = non_null.str.strip()
    values = stripped[stripped != '']

    col = dict(
        missing=total - len(values),
        whitespace=int((non_null != stripped).sum()),
        distinct=values.nunique(),
        type='(trống)', fail=0, examples='', min='', max='', out_of_range='',
    )
    if values.empty:
        return col, values

    col['type'], fail_mask = infer_type(values)
    col['fail'] = int(fail_mask.sum())
    col['examples'] = ', '.join(f'`{v}`' for v in values[fail_mask].unique()[:EXAMPLES])
    ok = values[~fail_mask]
    if col['type'] == 'date' and not ok.empty:
        dates = pd.to_datetime(ok.str[:10], format='%Y-%m-%d')
        col['min'], col['max'] = dates.min().date(), dates.max().date()
        if series.name not in DATE_RANGE_EXEMPT:
            col['out_of_range'] = int(((dates < DATE_MIN) | (dates > DATE_MAX)).sum())
    elif col['type'] in ('number', 'mã (số 0 đầu)') and not ok.empty:
        nums = pd.to_numeric(ok)
        col['min'], col['max'] = f'{nums.min():,.4g}', f'{nums.max():,.4g}'
    return col, values


def category_section(name, values):
    """Liệt kê giá trị của cột ít giá trị; cảnh báo biến thể chỉ khác hoa/thường/khoảng trắng."""
    counts = values.value_counts()
    listing = ', '.join(f'{md(v)} ({n:,})' for v, n in counts.items())
    variants = values.str.lower().str.split().str.join(' ').nunique() < values.nunique()
    warn = ' ⚠️ **có biến thể chỉ khác hoa/thường/khoảng trắng**' if variants else ''
    return f'- `{name}`: {listing}{warn}'


def profile_table(conn, table):
    df = pd.read_sql(text(f'SELECT * FROM raw."{table}"'), conn)
    data_cols = [c for c in df.columns if not c.startswith('_')]
    exact_dups = int(df[data_cols].duplicated().sum())

    lines = [f'## raw.{table}', '',
             f'- Số dòng: **{len(df):,}** — số cột dữ liệu: {len(data_cols)} — '
             f'dòng trùng hoàn toàn (không tính metadata): **{exact_dups:,}**',
             f'- Batch: {", ".join(sorted(df["_batch_id"].astype(str).unique()))}', '',
             '| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |',
             '|---|---|---:|---:|---:|---:|---|---|---|---:|']
    categories = []
    for name in data_cols:
        col, values = profile_column(df[name].rename(name))
        pct = f'{col["missing"] / len(df):.1%}' if len(df) else '-'
        lines.append(f'| `{name}` | {col["type"]} | {pct} | {col["whitespace"] or ""} | {col["distinct"]:,} '
                     f'| {col["fail"] or ""} | {md(col["examples"])} | {col["min"]} | {col["max"]} '
                     f'| {col["out_of_range"] or ""} |')
        if col['type'] == 'text' and 0 < col['distinct'] <= CATEGORY_MAX_DISTINCT:
            categories.append(category_section(name, values))
    if categories:
        lines += ['', '**Giá trị của các cột phân loại:**', ''] + categories
    return lines + [''], dict(table=table, rows=len(df), cols=len(data_cols), exact_dups=exact_dups)


def main():
    engine = get_engine()
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw' ORDER BY 1"))
            if r[0] not in SKIP_TABLES]
        sections, summary = [], []
        for t in tables:
            print(f'profiling raw.{t} ...')
            lines, s = profile_table(conn, t)
            sections += lines
            summary.append(s)

    header = [
        '# Data Profile — Bronze (raw.*)', '',
        f'> File tự sinh bởi `02_sql_analytics/profiling/profile_raw.py` lúc '
        f'{datetime.now():%Y-%m-%d %H:%M}. Không sửa tay — chạy lại script để cập nhật.',
        '> Phân tích và kế hoạch xử lý nằm ở `docs/data_issues.md`.', '',
        '**Cách đọc:** "% thiếu" = NULL hoặc chuỗi rỗng. "Kiểu đoán" = kiểu mà ≥ 90% giá trị ép được; '
        '"Không ép được" = số giá trị còn lại. "mã (số 0 đầu)" = trông như số nhưng có số 0 đầu '
        '(SĐT, mã số thuế) nên cần giữ dạng text.', '',
        '| Bảng | Số dòng | Số cột | Dòng trùng hoàn toàn |', '|---|---:|---:|---:|',
    ] + [f'| raw.{s["table"]} | {s["rows"]:,} | {s["cols"]} | {s["exact_dups"]:,} |' for s in summary] + ['']

    OUTPUT.write_text('\n'.join(header + sections), encoding='utf-8')
    print(f'Đã ghi {OUTPUT}')


if __name__ == '__main__':
    main()
