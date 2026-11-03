"""Build Silver layer (schema staging) từ Bronze — Task 2.2 / 2.3, rồi tạo lại Gold.

Chạy từ thư mục gốc dự án:
    python 02_sql_analytics/run_staging.py
    python 02_sql_analytics/run_staging.py --only stg_customers stg_sales_transactions
    python 02_sql_analytics/run_staging.py --no-dwh

Model staging dùng DROP TABLE ... CASCADE nên xoá luôn các view dwh phụ thuộc; vì vậy sau khi build
staging, script tự chạy lại snapshots + view dwh (giống run_dwh.py) trừ khi có --no-dwh.
"""
import argparse

from model_runner import STAGING_DIR, build, build_gold, model_names

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build Silver layer (staging.*) rồi tạo lại Gold (dwh.*)')
    parser.add_argument('--only', nargs='+', choices=model_names(STAGING_DIR), help='chỉ build các model này')
    parser.add_argument('--no-dwh', action='store_true', help='không tạo lại snapshots + view dwh')
    args = parser.parse_args()

    build(STAGING_DIR, 'staging', args.only)
    if not args.no_dwh:
        build_gold()
    print('Xong.')
