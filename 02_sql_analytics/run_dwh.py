"""Build Gold layer — Phase 3: snapshots (bảng lịch sử SCD2, merge tăng dần) rồi dwh (toàn VIEW).

Chạy SAU run_staging.py (run_staging.py đã tự gọi bước này), từ thư mục gốc dự án:
    python 02_sql_analytics/run_dwh.py
    python 02_sql_analytics/run_dwh.py --only dim_date dim_employees

Snapshot luôn chạy (merge idempotent: không có thay đổi thì không làm gì).
"""
import argparse

from model_runner import DWH_DIR, build_gold, model_names

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build Gold layer (snapshots.* + view dwh.*)')
    parser.add_argument('--only', nargs='+', choices=model_names(DWH_DIR), help='chỉ tạo lại các view này')
    args = parser.parse_args()

    build_gold(args.only)
    print('Xong.')
