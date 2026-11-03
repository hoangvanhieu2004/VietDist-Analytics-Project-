-- stg_distributors — nhà phân phối (SRC-06). 1 dòng / distributor_id (snapshot mới nhất;
-- lịch sử SCD2 dựng ở Gold từ các lần load).
DROP TABLE IF EXISTS staging.stg_distributors CASCADE;

CREATE TABLE staging.stg_distributors AS
WITH ranked AS (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY staging.clean_text(distributor_id)
                              ORDER BY _ingested_at DESC, _batch_id) AS rn
    FROM raw.distributor_master r
)
SELECT
    staging.clean_text(distributor_id)                                AS distributor_id,
    staging.clean_text(distributor_name)                              AS distributor_name,
    staging.clean_text(tier)                                          AS tier,
    staging.clean_text(channel)                                       AS channel,
    staging.clean_text(province)                                      AS province,
    staging.clean_text(region)                                        AS region,
    staging.clean_text(contact_person)                                AS contact_person,
    staging.clean_text(phone)                                         AS phone,
    staging.clean_text(email)                                         AS email,
    staging.clean_text(tax_code)                                      AS tax_code,
    staging.cast_date(join_date, 'distributor_master.join_date')        AS join_date,
    staging.cast_num(credit_limit, 'distributor_master.credit_limit')   AS credit_limit,
    staging.clean_text(status)                                        AS status,
    staging.clean_text(assigned_supervisor_id)                        AS assigned_supervisor_id,
    _source_file, _batch_id, _ingested_at
FROM ranked
WHERE rn = 1;

ALTER TABLE staging.stg_distributors ADD PRIMARY KEY (distributor_id);
