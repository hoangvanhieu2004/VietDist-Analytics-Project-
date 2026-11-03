-- =====================================================================================
-- dim_date (VIEW) — calendar 2022-01-01 .. 2026-12-31. Task 3.1.1. Khoá: date_key (kiểm tra bằng test)
-- Năm tài chính: 01/09 -> 31/08, đặt tên theo NĂM BẮT ĐẦU (2024-01-01 thuộc FY2023).
--   fiscal_month: tháng 9 = 1 ... tháng 8 = 12; fiscal_quarter: Q1 = tháng 9–11
-- date_last_year = date − 1 năm (PostgreSQL tự đưa 29/02 về 28/02) — quy tắc YoY của BRD 3.1.
-- Không có dòng UNKNOWN: Power BI yêu cầu bảng ngày liên tục, không có ngày rỗng.
-- =====================================================================================
SELECT dwh.drop_relation('dim_date');

CREATE VIEW dwh.dim_date AS
WITH days AS (
    SELECT d::date AS date
    FROM generate_series(DATE '2022-01-01', DATE '2026-12-31', interval '1 day') AS d
),
base AS (
    SELECT date,
           extract(year FROM date)::int     AS year,
           extract(month FROM date)::int    AS month,
           extract(isodow FROM date)::int   AS day_of_week,
           (date_trunc('month', date) + interval '1 month - 1 day')::date AS month_end,
           CASE WHEN extract(month FROM date) >= 9 THEN extract(year FROM date)::int
                ELSE extract(year FROM date)::int - 1 END AS fiscal_year
    FROM days
)
SELECT
    to_char(date, 'YYYYMMDD')::int                                    AS date_key,
    date,
    -- năm dương lịch
    year,
    extract(quarter FROM date)::int                                   AS quarter,
    'Q' || extract(quarter FROM date)::int || '-' || year             AS year_quarter,
    month,
    'Tháng ' || month                                                 AS month_name,
    to_char(date, 'YYYY-MM')                                          AS year_month,
    extract(week FROM date)::int                                      AS week_of_year,
    extract(isoyear FROM date)::int                                   AS iso_year,
    extract(day FROM date)::int                                       AS day_of_month,
    extract(doy FROM date)::int                                       AS day_of_year,
    day_of_week,
    (ARRAY['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật'])[day_of_week] AS day_name,
    (day_of_week IN (6, 7))                                           AS is_weekend,
    (date = month_end)                                                AS is_month_end,
    extract(day FROM month_end)::int                                  AS days_in_month,
    -- năm tài chính
    fiscal_year,
    'FY' || fiscal_year                                               AS fiscal_year_label,
    ((month + 3) % 12) + 1                                            AS fiscal_month,
    ((((month + 3) % 12)) / 3) + 1                                    AS fiscal_quarter,
    (date - make_date(fiscal_year, 9, 1)) + 1                         AS fiscal_day_of_year,
    -- hỗ trợ YoY
    (date - interval '1 year')::date                                  AS date_last_year,
    (month = 2 AND extract(day FROM date) = 29)                       AS is_leap_day
FROM base;
