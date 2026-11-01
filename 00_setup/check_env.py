"""Kiểm tra CHECKPOINT Phase 0.

Chạy từ thư mục gốc dự án:  python 00_setup/check_env.py
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_MODULES = [
    'pandas', 'openpyxl', 'pyxlsb', 'sqlalchemy', 'psycopg2',
    'gspread', 'google.auth', 'googleapiclient', 'msal', 'requests', 'dotenv',
]

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f' — {detail}' if detail else ''))


# 1. Python version
v = sys.version_info
check('Python >= 3.11', v >= (3, 11), f'{v.major}.{v.minor}.{v.micro}')

# 2. Thư viện
missing = []
for m in REQUIRED_MODULES:
    try:
        importlib.import_module(m)
    except ImportError:
        missing.append(m)
check('Python packages', not missing, 'thiếu: ' + ', '.join(missing) if missing else 'đủ')

# 3. .env tồn tại và có password
env_path = ROOT / '.env'
check('.env tồn tại', env_path.exists())
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
pw = os.getenv('DB_PASSWORD')
check('DB_PASSWORD đã điền', bool(pw) and pw != 'your_password_here')

# 4. Kết nối DB + 3 schema
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    url = URL.create(
        'postgresql+psycopg2',
        username=os.getenv('DB_USER'), password=pw,
        host=os.getenv('DB_HOST'), port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME'),
    )
    with create_engine(url).connect() as conn:
        schemas = {r[0] for r in conn.execute(text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name IN ('raw', 'staging', 'dwh')"))}
    check(f"Kết nối DB {os.getenv('DB_NAME')}", True)
    check('Schema raw/staging/dwh', schemas == {'raw', 'staging', 'dwh'}, ', '.join(sorted(schemas)))
except Exception as e:
    check('Kết nối DB', False, str(e).splitlines()[0])

# 5. Git không track .env / credentials
try:
    out = subprocess.run(['git', 'status', '--porcelain', '--ignored'], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    exposed = [l for l in out.splitlines()
               if not l.startswith('!!') and ('.env' in l.split()[-1] and 'example' not in l
                                              or 'credentials/' in l)]
    check('git không thấy .env / credentials/', not exposed, '; '.join(exposed))
except Exception as e:
    check('git status', False, str(e))

print(f'\n{sum(results)}/{len(results)} checks passed')
sys.exit(0 if all(results) else 1)
