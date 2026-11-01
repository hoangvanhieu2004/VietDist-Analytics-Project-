# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The repo currently holds only the two spec documents (both in Vietnamese). No code has been written yet:
- `02_VietDist_Project_Description_v2.0_Đề bài.docx`: the task brief, with phases, tasks, checkpoints and the target folder layout.
- `BRD_VietDist_Analytics_Project_v1.0.docx`: the business requirements, covering source systems, report requirements (BR-A-01..04, BR-B-01..04), RLS, and open questions OQ-01..10.

To read them from the shell: `unzip -p <file>.docx word/document.xml | sed -e 's/<\/w:p>/\n/g' -e 's/<[^>]*>//g'`.

Each phase in the brief ends with a "CHECKPOINT" list. Treat those lists as the acceptance criteria for that phase.

## What is being built

This is a local analytics pipeline for VietDist, an FMCG distributor. Excel and CSV files on Google Drive and OneDrive are loaded into PostgreSQL 16 (database `vietdist_dw`) using a Medallion architecture. Power BI Desktop then reports from the gold layer.

| Layer  | Schema    | Content | Tooling |
|--------|-----------|---------|---------|
| Bronze | `raw`     | Source rows unchanged: **every column TEXT**, plus metadata `_source_file`, `_source_platform` (`google_drive`/`onedrive`), `_ingested_at`, `_batch_id` (UUID per run) | Python + SQLAlchemy |
| Silver | `staging` | `stg_*` tables: typed, cleaned, deduplicated, with not_null and unique tests on PKs. The goal is 0 test failures | Python / SQL |
| Gold   | `dwh`     | Star schema plus mart tables read by Power BI | SQL |

Planned layout, from the brief:
```
00_setup/        requirements.txt, .env.example, init_db.sql (creates raw/staging/dwh)
01_ingestion/    connectors/gdrive_connector.py, loaders/load_<source>.py,
                 utils/file_parser.py (CSV/XLSX/XLSM/XLSB), utils/db_utils.py (add_metadata, load_to_bronze, get_engine)
02_sql_analytics/
03_power_bi/
docs/            data_dictionary.md, assumptions_log.md, data_issues.md (profiling results per raw table)
```

## Setup and commands

```bash
python -m venv venv && venv\Scripts\activate          # Windows
pip install pandas openpyxl pyxlsb sqlalchemy psycopg2-binary gspread google-auth msal requests python-dotenv
psql -U postgres -f 00_setup/init_db.sql               # once init_db.sql exists
cd 01_ingestion/loaders && python load_sales_transactions.py   # loaders use sys.path.append('..'), so run them from loaders/
```

`.env` holds `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` and `GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/...`. Both `.env` and `credentials/` must be listed in `.gitignore`.

## Sources (10 bronze tables, SRC-01..10)

| Source | Platform / format |
|---|---|
| sales_transactions, customer_master, distributor_master, return_transactions | Google Drive / CSV |
| distributor_orders | Google Drive / **XLSB** (needs `pyxlsb`) |
| sales_target_plan, employee_master, territory_mapping, promotion_program | OneDrive / XLSX (via `msal`) |
| product_master | OneDrive / **XLSM** (macros are ignored) |

Every loader must use the correct platform and parser, add the metadata columns, and write a row to `raw.ingest_log` (batch_id, source_name, source_file, source_platform, rows_loaded, status SUCCESS/FAILED, error_message, duration_sec). CSVs contain Vietnamese text, so watch the encoding.

Bronze loads use **append** mode. Running a loader twice doubles the row count, and that is expected. Deduplication happens in silver.

## Domain logic that is easy to get wrong

**Sales target versioning (SRC-02).** The brief calls this the hardest part of the project.
- A version (v1, v2, v3, and an unlimited number after that) can arrive as its own file **or** as its own sheet inside one file. Store every version and never overwrite an older one. Do not hardcode the number of versions.
- Bronze uses `raw.sales_target_files` (one row per file/sheet with a `version_label`) and `raw.sales_targets_raw` (long format). In the long table, `month_col` must hold only `T1`..`T12`. Drop the "Tổng" (total) column and the `TỔNG` row.
- Each version only revises the months from its issue date onward: v1 (Jan) covers T1–T12, v2 (Jul) revises T7–T12, and v3 (Oct) revises T10–T12. For any month, the effective version is the latest version issued that covers that month. So T1–6 use v1, T7–9 use v2, and T10–12 use v3.
- Silver `stg_sales_targets_versioned` and gold `fact_targets` are temporal facts, i.e. SCD2 applied to a fact table, with `version_code`, `effective_date`, `expiry_date` and `is_latest`. `mart_sales_vs_target` must support comparing actuals against every version (actual vs v1, v2 and v3), not only the latest.
- Distributors also have versioned targets (BR-B-02).

**SCD2 dimensions.** `dim_employees` (changes of region, team or level) and `dim_distributors` (changes of tier, region or channel) both use SCD2 with `effective_from`, `effective_to` and `is_current`. When a change happens, close the old row with `effective_to = change_date - 1` and insert a new row. Facts must join to these dimensions as of the transaction date (`fact.date BETWEEN effective_from AND effective_to`), never on the current state. `dim_customers` and `dim_products` are SCD1.

**Fiscal year.** The fiscal year runs from 01/09 to 31/08 and is labelled by its **start** year. For example, 2023-10-01 and 2024-01-01 both fall in FY2023. `dim_date` covers 2022–2026 and must support both fiscal and calendar year.

**YoY.** Year-over-year must work by month, quarter and YTD, for both fiscal and calendar years. If the current period includes Feb 29, the prior-year comparison runs to Feb 28 only.

**Metrics.** Net Revenue = gross revenue from delivered orders − returns (SRC-09). Achieve % = Actual / Target, guarding against Target = 0. The forecast is linear extrapolation done in Power BI.

**Gold tables.** The gold layer contains `dim_date`, `dim_employees`, `dim_customers`, `dim_products`, `dim_distributors`, `fact_sales` (grain: one line item), `fact_targets`, `fact_returns`, `mart_sales_vs_target` and `mart_distributor_performance`.

## Unresolved requirements

The BRD lists open questions OQ-03..10 that the business has not answered. They cover new/returning/churned customer definitions, the inventory source, reorder points, the distributor target format, the fill-rate grain, the target allocation grain, slow-moving stock and promotion cost. Before implementing anything that depends on one of these, record the assumption you made in `docs/assumptions_log.md`. The inventory data for BR-B-03 is not in SRC-01..10 at all.
