"""Bronze loader SRC-06: distributor_master"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-06',
    source_name='distributor_master',
    file_prefix='SRC06_',
)

if __name__ == '__main__':
    main(SOURCE)
