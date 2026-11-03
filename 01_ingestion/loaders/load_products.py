"""Bronze loader SRC-04: product_master"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-04',
    source_name='product_master',
    file_prefix='SRC04_',
    sheets={'Products': 'product_master'},  # Category_Summary là số tổng hợp, bỏ qua
)

if __name__ == '__main__':
    main(SOURCE)
