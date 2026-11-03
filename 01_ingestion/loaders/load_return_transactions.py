"""Bronze loader SRC-09: return_transactions"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-09',
    source_name='return_transactions',
    file_prefix='SRC09_',
)

if __name__ == '__main__':
    main(SOURCE)
