-- Bảng ghi nhận các phiên bản sales target đã đọc (Task 1.4.1).
-- Mỗi lần chạy loader thêm 1 dòng cho mỗi (sheet, phiên bản) — chỉ append, không bao giờ
-- update/delete, để giữ toàn bộ lịch sử phiên bản.
-- Dữ liệu target nằm ở raw.sales_targets_raw (bảng tạo động theo cột của file nguồn).
CREATE TABLE IF NOT EXISTS raw.sales_target_files (
    file_load_id     BIGSERIAL  PRIMARY KEY,
    version_label    TEXT       NOT NULL,   -- 'v1', 'v2', ...
    sheet_name       TEXT       NOT NULL,
    layout           TEXT       NOT NULL CHECK (layout IN ('long', 'wide')),
    rows_loaded      INTEGER    NOT NULL,
    _source_file     TEXT       NOT NULL,
    _source_sheet    TEXT,
    _source_platform TEXT       NOT NULL,
    _ingested_at     TIMESTAMP  NOT NULL,
    _batch_id        UUID       NOT NULL
);
