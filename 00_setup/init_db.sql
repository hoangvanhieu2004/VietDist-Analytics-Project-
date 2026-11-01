-- Khởi tạo database vietdist_dw và 3 schema của Medallion architecture.
-- Chạy bằng psql (idempotent, chạy lại nhiều lần không lỗi):
--   psql -U postgres -h localhost -f 00_setup/init_db.sql
-- Nếu dùng pgAdmin: chạy CREATE DATABASE trước, kết nối vào vietdist_dw rồi chạy phần CREATE SCHEMA.

SELECT 'CREATE DATABASE vietdist_dw ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'vietdist_dw')
\gexec

\connect vietdist_dw

CREATE SCHEMA IF NOT EXISTS raw;      -- Bronze layer
CREATE SCHEMA IF NOT EXISTS staging;  -- Silver layer
CREATE SCHEMA IF NOT EXISTS dwh;      -- Gold layer

-- Kiểm tra: kết quả mong đợi 3 dòng
SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('raw', 'staging', 'dwh')
ORDER BY schema_name;
