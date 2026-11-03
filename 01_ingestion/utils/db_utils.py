"""Helper cho Bronze layer (Task 1.3.1): engine, metadata, load, truncate, ghi log."""
import csv
import io
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / '.env')

BRONZE_SCHEMA = 'raw'
INGEST_LOG_DDL = PROJECT_ROOT / '01_ingestion' / 'sql' / 'create_ingest_log.sql'

# Cột metadata và kiểu dữ liệu; mọi cột dữ liệu nguồn là TEXT
METADATA_COLUMNS = {
    '_source_file': 'TEXT',
    '_source_sheet': 'TEXT',      # chỉ có với file Excel
    '_source_platform': 'TEXT',
    '_ingested_at': 'TIMESTAMP',
    '_batch_id': 'UUID',
}

_engine = None


def get_engine():
    """SQLAlchemy engine tới PostgreSQL theo DB_* trong .env (tạo 1 lần, dùng lại)."""
    global _engine
    if _engine is None:
        url = URL.create(
            'postgresql+psycopg2',
            username=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME'),
        )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def run_sql_file(path):
    """Chạy 1 file SQL (DDL idempotent như CREATE TABLE IF NOT EXISTS)."""
    with get_engine().begin() as conn:
        conn.exec_driver_sql(Path(path).read_text(encoding='utf-8'))


def ensure_ingest_log():
    """Tạo bảng raw.ingest_log nếu chưa có."""
    run_sql_file(INGEST_LOG_DDL)


def add_metadata(df, source_file, source_platform, batch_id, source_sheet=None):
    """Thêm các cột metadata Bronze vào cuối DataFrame (trả về bản copy)."""
    df = df.copy()
    df['_source_file'] = source_file
    if source_sheet is not None:
        df['_source_sheet'] = source_sheet
    df['_source_platform'] = source_platform
    df['_ingested_at'] = datetime.now()
    df['_batch_id'] = batch_id
    return df


def _quote(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def _full_name(table_name, schema=BRONZE_SCHEMA):
    return f'{_quote(schema)}.{_quote(table_name)}'


def _ensure_table(conn, table_name, columns, schema):
    """Tạo bảng nếu chưa có; thêm cột mới nếu file nguồn có thêm cột (schema drift)."""
    insp = inspect(conn)
    if not insp.has_table(table_name, schema=schema):
        cols = ', '.join(f'{_quote(c)} {METADATA_COLUMNS.get(c, "TEXT")}' for c in columns)
        conn.execute(text(f'CREATE TABLE {_full_name(table_name, schema)} ({cols})'))
        return
    existing = {c['name'] for c in insp.get_columns(table_name, schema=schema)}
    for c in columns:
        if c not in existing:
            conn.execute(text(f'ALTER TABLE {_full_name(table_name, schema)} '
                              f'ADD COLUMN {_quote(c)} {METADATA_COLUMNS.get(c, "TEXT")}'))


def load_to_bronze(df, table_name, if_exists='append', conn=None, schema=BRONZE_SCHEMA):
    """Ghi DataFrame vào raw.<table_name> bằng COPY. Trả về số dòng đã ghi.

    if_exists: 'append' (mặc định cho Bronze) hoặc 'replace' (TRUNCATE trước khi ghi).
    conn:      connection đang mở để gộp vào cùng transaction; None = tự mở transaction.
    """
    if conn is None:
        with get_engine().begin() as own_conn:
            return load_to_bronze(df, table_name, if_exists, own_conn, schema)
    if if_exists not in ('append', 'replace'):
        raise ValueError(f"if_exists phải là 'append' hoặc 'replace', nhận: {if_exists}")
    if df.empty:
        return 0

    columns = list(df.columns)
    _ensure_table(conn, table_name, columns, schema)
    if if_exists == 'replace':
        conn.execute(text(f'TRUNCATE TABLE {_full_name(table_name, schema)}'))

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    buf.seek(0)
    col_list = ', '.join(_quote(c) for c in columns)
    with conn.connection.cursor() as cur:
        cur.copy_expert(f'COPY {_full_name(table_name, schema)} ({col_list}) FROM STDIN WITH (FORMAT csv)', buf)
    return len(df)


def truncate_table(table_name, schema=BRONZE_SCHEMA):
    with get_engine().begin() as conn:
        conn.execute(text(f'TRUNCATE TABLE {_full_name(table_name, schema)}'))


def log_ingest(batch_id, source_name, status, source_file=None, source_platform=None,
               rows_loaded=0, error_message=None, duration_sec=None, conn=None):
    """Ghi 1 dòng vào raw.ingest_log. status: 'SUCCESS' | 'FAILED'."""
    if conn is None:
        with get_engine().begin() as own_conn:
            return log_ingest(batch_id, source_name, status, source_file, source_platform,
                              rows_loaded, error_message, duration_sec, own_conn)
    conn.execute(text(
        'INSERT INTO raw.ingest_log (batch_id, source_name, source_file, source_platform,'
        ' rows_loaded, status, error_message, duration_sec)'
        ' VALUES (:bid, :sn, :sf, :sp, :rl, :st, :err, :dur)'
    ), dict(bid=batch_id, sn=source_name, sf=source_file, sp=source_platform,
            rl=rows_loaded, st=status, err=error_message, dur=duration_sec))
