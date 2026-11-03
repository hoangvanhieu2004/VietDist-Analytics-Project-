"""Bronze loader SRC-01: sales_transactions"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-01',
    source_name='sales_transactions',
    file_prefix='SRC01_',
)

if __name__ == '__main__':
    main(SOURCE)
