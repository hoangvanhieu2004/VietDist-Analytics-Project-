-- =====================================================================================
-- Hàm dùng chung cho Silver (schema staging) — Task 2.2
-- Ép kiểu FAIL-FAST: giá trị không hợp lệ -> RAISE EXCEPTION kèm cột + giá trị,
-- cả transaction của model bị rollback (bảng staging cũ giữ nguyên).
-- Tham số col: tên 'bảng.cột' để thông báo lỗi chỉ rõ chỗ sai.
-- =====================================================================================

-- Text: btrim; rỗng / 'nan' / 'null' / 'none' -> NULL
CREATE OR REPLACE FUNCTION staging.clean_text(t text) RETURNS text
LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN lower(btrim(t)) IN ('', 'nan', 'null', 'none') THEN NULL ELSE btrim(t) END $$;

CREATE OR REPLACE FUNCTION staging.cast_num(t text, col text) RETURNS numeric
LANGUAGE plpgsql IMMUTABLE AS
$$
DECLARE v text := staging.clean_text(t);
BEGIN
    IF v IS NULL THEN RETURN NULL; END IF;
    IF v !~ '^-?[0-9]+(\.[0-9]+)?$' THEN
        RAISE EXCEPTION 'Không ép được "%" sang số (cột %)', t, col;
    END IF;
    RETURN v::numeric;
END
$$;

-- Số nguyên: chấp nhận '226' và '226.0' (số từ Excel), từ chối '226.5'
CREATE OR REPLACE FUNCTION staging.cast_int(t text, col text) RETURNS integer
LANGUAGE plpgsql IMMUTABLE AS
$$
DECLARE n numeric := staging.cast_num(t, col);
BEGIN
    IF n IS NULL THEN RETURN NULL; END IF;
    IF n <> trunc(n) THEN
        RAISE EXCEPTION 'Không ép được "%" sang số nguyên (cột %)', t, col;
    END IF;
    RETURN n::integer;
END
$$;

-- Ngày: 'YYYY-MM-DD' hoặc 'YYYY-MM-DD 00:00:00' (Excel)
CREATE OR REPLACE FUNCTION staging.cast_date(t text, col text) RETURNS date
LANGUAGE plpgsql IMMUTABLE AS
$$
DECLARE v text := staging.clean_text(t);
BEGIN
    IF v IS NULL THEN RETURN NULL; END IF;
    IF v !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}( 00:00:00)?$' THEN
        RAISE EXCEPTION 'Không ép được "%" sang ngày (cột %)', t, col;
    END IF;
    BEGIN
        RETURN left(v, 10)::date;
    EXCEPTION WHEN others THEN
        RAISE EXCEPTION 'Ngày không tồn tại "%" (cột %)', t, col;
    END;
END
$$;

-- Boolean: Yes/No, True/False, 1/0, Có/Không
CREATE OR REPLACE FUNCTION staging.cast_bool(t text, col text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS
$$
DECLARE v text := lower(staging.clean_text(t));
BEGIN
    IF v IS NULL THEN RETURN NULL; END IF;
    IF v IN ('yes', 'true', '1', 'có', 'y') THEN RETURN true; END IF;
    IF v IN ('no', 'false', '0', 'không', 'n') THEN RETURN false; END IF;
    RAISE EXCEPTION 'Không ép được "%" sang boolean (cột %)', t, col;
END
$$;
