-- =====================================================================================
-- dim_distributors (VIEW) — nhà phân phối, SCD Type 2. Task 3.1. Khoá: distributor_sk (kiểm tra bằng test)
-- Lịch sử nằm ở bảng snapshots.distributors (merge tăng dần, A-32); view này chỉ đọc lại
-- và thêm dòng UNKNOWN (distributor_sk = -1, A-33).
-- Join với fact: fact.date BETWEEN effective_from AND effective_to.
-- =====================================================================================
SELECT dwh.drop_relation('dim_distributors');

CREATE VIEW dwh.dim_distributors AS
SELECT distributor_sk, distributor_id, distributor_name, tier, channel, region, province, contact_person,
       phone, email, tax_code, join_date, credit_limit, status, assigned_supervisor_id,
       effective_from, effective_to, is_current, change_reason
FROM snapshots.distributors
UNION ALL
SELECT -1, '-1', 'UNKNOWN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'UNKNOWN', NULL,
       DATE '1900-01-01', DATE '9999-12-31', true, 'Unknown member';
