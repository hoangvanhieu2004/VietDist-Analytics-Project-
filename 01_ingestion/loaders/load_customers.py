"""Bronze loader SRC-03: customer_master"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-03',
    source_name='customer_master',
    file_prefix='SRC03_',
)

if __name__ == '__main__':
    main(SOURCE)
