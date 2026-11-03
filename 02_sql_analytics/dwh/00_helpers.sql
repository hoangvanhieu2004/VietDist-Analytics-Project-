-- =====================================================================================
-- Helper cho Gold layer (schema dwh): mọi đối tượng trong dwh là VIEW (A-34).
-- dwh.drop_relation(name): drop dwh.<name> dù đang là bảng, view hay materialized view (CASCADE),
-- để mỗi file view có thể đổi cột thoải mái và tự chuyển đổi từ phiên bản bảng cũ.
-- =====================================================================================
CREATE OR REPLACE FUNCTION dwh.drop_relation(rel_name text) RETURNS void
LANGUAGE plpgsql AS
$$
DECLARE kind "char";
BEGIN
    SELECT c.relkind INTO kind
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'dwh' AND c.relname = rel_name;

    IF kind = 'r' THEN
        EXECUTE format('DROP TABLE dwh.%I CASCADE', rel_name);
    ELSIF kind = 'v' THEN
        EXECUTE format('DROP VIEW dwh.%I CASCADE', rel_name);
    ELSIF kind = 'm' THEN
        EXECUTE format('DROP MATERIALIZED VIEW dwh.%I CASCADE', rel_name);
    END IF;
END
$$;
