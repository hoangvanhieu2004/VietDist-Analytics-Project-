"""Chạy toàn bộ Bronze loader một lần, chung 1 batch_id.

    python 01_ingestion/run_bronze.py
    python 01_ingestion/run_bronze.py --only customer_master employee_master
"""
import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'loaders'))

from base_loader import run_loader  # noqa: E402
import load_customers  # noqa: E402
import load_distributor_orders  # noqa: E402
import load_distributors  # noqa: E402
import load_employees  # noqa: E402
import load_products  # noqa: E402
import load_promotion_program  # noqa: E402
import load_return_transactions  # noqa: E402
import load_sales_targets  # noqa: E402
import load_sales_transactions  # noqa: E402
import load_territory_mapping  # noqa: E402

# Thứ tự chạy theo mã nguồn
SOURCES = [
    load_sales_transactions.SOURCE,
    load_sales_targets.SOURCE,
    load_customers.SOURCE,
    load_products.SOURCE,
    load_distributor_orders.SOURCE,
    load_distributors.SOURCE,
    load_employees.SOURCE,
    load_territory_mapping.SOURCE,
    load_return_transactions.SOURCE,
    load_promotion_program.SOURCE,
]


def main():
    parser = argparse.ArgumentParser(description='Chạy toàn bộ Bronze loader')
    parser.add_argument('--only', nargs='+', choices=[s.source_name for s in SOURCES],
                        help='chỉ chạy các nguồn này')
    args = parser.parse_args()

    batch_id = str(uuid.uuid4())
    print(f'batch_id = {batch_id}\n')
    failed_sources = []
    for cfg in SOURCES:
        if args.only and cfg.source_name not in args.only:
            continue
        _, failed = run_loader(cfg, batch_id)
        if failed:
            failed_sources.append(cfg.source_name)
        print()

    print('Kết quả:', 'TẤT CẢ OK' if not failed_sources else f'lỗi ở {", ".join(failed_sources)}')
    sys.exit(1 if failed_sources else 0)


if __name__ == '__main__':
    main()
