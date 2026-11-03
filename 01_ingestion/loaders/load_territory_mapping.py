"""Bronze loader SRC-08: territory_mapping"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-08',
    source_name='territory_mapping',
    file_prefix='SRC08_',
)

if __name__ == '__main__':
    main(SOURCE)
