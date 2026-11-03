"""Bronze loader SRC-07: employee_master"""
from base_loader import SourceConfig, main

SOURCE = SourceConfig(
    src_id='SRC-07',
    source_name='employee_master',
    file_prefix='SRC07_',
    sheets={'Employee_v*': 'employee_master', 'Change_Log': 'employee_change_log'},
)

if __name__ == '__main__':
    main(SOURCE)
