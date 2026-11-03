"""Bronze loader SRC-10: promotion_program"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-10',
    source_name='promotion_program',
    file_prefix='SRC10_',
)

if __name__ == '__main__':
    main(SOURCE)
