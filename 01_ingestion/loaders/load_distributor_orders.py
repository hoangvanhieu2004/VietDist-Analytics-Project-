"""Bronze loader SRC-05: distributor_orders"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-05',
    source_name='distributor_orders',
    file_prefix='SRC05_',
)

if __name__ == '__main__':
    main(SOURCE)
