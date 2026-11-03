# Data Issues — Bronze (raw.*) và kế hoạch xử lý ở Silver

> Task 2.1 — Data Profiling. Dữ liệu: batch load ngày 2026-11-02 (1 batch / bảng, chưa có bản sao giữa các batch).
> Số liệu chi tiết từng cột: [`data_profile.md`](data_profile.md) (tự sinh bởi `02_sql_analytics/profiling/profile_raw.py`).
> Kiểm tra nghiệp vụ: `02_sql_analytics/profiling/profiling_checks.sql` (chạy được trong pgAdmin).
> Định dạng mỗi bảng theo mẫu EDA: **Incorrect data types / Incorrect values / Missing data / Duplicates → Next step**.

## Tóm tắt

| Bảng | Số dòng | Khoá chính (đã kiểm tra) | Trùng | Khoá NULL | Vấn đề chính |
|---|---:|---|---:|---:|---|
| sales_transactions | 119,101 | (order_id, product_id) | 0 | 0 | discount làm tròn 100đ; đơn Cancelled nhưng Paid; 638 dòng trước ngày KH tham gia; chỉ có năm 2024 |
| sales_targets_raw | 1,950 | (version_label, employee_id, year, month) | 0 | 0 | Sạch |
| customer_master | 2,000 | customer_id | 0 | 0 | tax_code thiếu 51.7% |
| product_master | 100 | product_id | 0 | 0 | Sạch |
| distributor_orders | 35,945 | (order_id, product_id) | 0 | 0 | dòng Cancelled vẫn có qty_delivered; không dòng nào giao đủ; 177 dòng ontime sai |
| distributor_master | 138 | distributor_id | 0 | 0 | 13 NPP không có đơn |
| employee_master | 228 | (employee_id, version) | 0 | 0 | 8 NV vào làm < 18 tuổi; resign_date ≠ ngày hiệu lực Change_Log |
| employee_change_log | 13 | (employee_id, effective_date, change_type) | 0 | 0 | Sạch |
| territory_mapping | 1,843 | territory_id | 0 | 0 | Chưa cập nhật cho 5 NV chuyển vùng |
| return_transactions | 3,665 | return_id | 0 | 0 | Sạch |
| promotion_program | 40 | promotion_id | 0 | 0 | applicable_products dạng danh sách `\|`; giá trị "All" |

**Điểm tốt:** không có dòng trùng ở bảng nào, không có khoá NULL, không có khoảng trắng thừa hay biến thể hoa/thường,
toàn bộ 16 kiểm tra tham chiếu (mã KH/NV/SP/NPP/đơn gốc) đều khớp 100%, các công thức
`gross = qty × price`, `net = gross − discount`, `fill_rate = delivered / ordered`, `return_amount = qty × price` đều đúng.

**Chung cho mọi bảng — Incorrect data types:** Bronze lưu TEXT. Số từ Excel có dạng `'226.0'`, `'2024.0'`.
Cột trông như số nhưng là **mã** (có số 0 đầu hoặc không dùng để tính toán): `phone`, `tax_code` → giữ TEXT.
→ *Next step:* cast ở Silver: ngày → `DATE`, số lượng / tháng / năm → `INTEGER`, tiền / % → `NUMERIC`.

---

## raw.sales_transactions — 119,101 dòng (SRC-01)

- **Incorrect data types:** `order_date` → DATE; `order_month`, `order_quarter`, `order_year`, `quantity` → INTEGER;
  `unit_price`, `discount_pct`, `discount_amount`, `gross_amount`, `net_amount` → NUMERIC.
  -> *Next step:* cast ở Silver.
- **Incorrect values:**
  - 13,971 dòng `discount_amount ≠ gross_amount × discount_pct / 100`, chênh lệch luôn trong ±50đ
    → hệ thống nguồn **làm tròn chiết khấu tới 100đ**, `net_amount` vẫn khớp `gross − discount`.
    -> *Next step:* No action — dùng `discount_amount`, `net_amount` như nguồn.
  - 4,800 dòng `delivery_status = Cancelled` nhưng 3,570 dòng trong đó `payment_status = Paid`.
    -> *Next step:* No action ở Silver; Net Revenue chỉ tính dòng `Delivered` (BRD 3.1). Hỏi business về hoàn tiền.
  - 638 dòng có `order_date` **trước** `customer_master.join_date` của khách.
    -> *Next step:* giữ dữ liệu, thêm cờ `is_before_customer_join`; báo Data Steward.
  - 10,904 đơn có nhiều `delivery_status` khác nhau giữa các dòng → trạng thái ở **cấp dòng**, không phải cấp đơn.
    -> *Next step:* No action — grain của `fact_sales` là 1 dòng (order_id, product_id).
  - Tất cả giao dịch nằm trong **2024-01-01 → 2024-12-31**.
    -> *Next step:* **không tính được YoY** (BR-A-01, BR-B-01) vì không có dữ liệu 2023 — cần hỏi Coach.
- **Missing data:** 0% ở mọi cột.
  -> *Next step:* No action.
- **Duplicates:** 0 dòng trùng hoàn toàn; 0 trùng theo (order_id, product_id). `order_id` **không** unique (50,000 đơn / 119,101 dòng).
  -> *Next step:* PK của `stg_sales_transactions` = (order_id, product_id); vẫn dedup theo PK, giữ bản ghi mới nhất
  (`_ingested_at`) để an toàn khi load lại.
- **Cột dư thừa:** `order_month/quarter/year`, `region`, `province`, `channel`, `product_category` khớp 100% với
  `order_date`, `customer_master`, `product_master`.
  -> *Next step:* giữ ở Silver; Gold lấy từ dim (dim_date, dim_customers, dim_products).

## raw.sales_targets_raw — 1,950 dòng (SRC-02)

- **Incorrect data types:** `version_date`, `effective_from`, `effective_to` → DATE; `year`, `month`, `target_quantity`,
  `target_new_customers` → INTEGER; `target_revenue` → NUMERIC.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có. v1: 111 NV × tháng 1–12, ban hành 2024-01-05, hiệu lực 2024-01-01 → 2024-12-31.
  v2: 103 NV × tháng 7–12, ban hành 2024-07-03, hiệu lực 2024-07-01 → 2024-12-31. Không có target = 0 hoặc âm.
  `plan_version` khớp `version_label` 100%. 8 NV có ở v1 nhưng không có ở v2 = đúng 8 NV nghỉ việc.
  -> *Next step:* No action. Task 2.3: tính `effective_date / expiry_date / is_latest` theo từng tháng
  (tháng 1–6 → v1; tháng 7–12 → v2; v1 tháng 7–12 bị v2 thay thế, `is_latest = false`).
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0 theo (version_label, employee_id, year, month).
  -> *Next step:* dedup theo khoá này + `_ingested_at` mới nhất khi load lại cùng file.

## raw.customer_master — 2,000 dòng (SRC-03)

- **Incorrect data types:** `join_date` → DATE; `credit_limit` → NUMERIC; `phone`, `tax_code` giữ TEXT.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có (credit_limit 50–500 triệu, join_date 2018–2024).
  -> *Next step:* No action.
- **Missing data:** `tax_code` thiếu 1,034 dòng (51.7%) — hợp lý với khách lẻ / hộ kinh doanh.
  -> *Next step:* No action (cột không dùng cho báo cáo); giữ NULL.
- **Duplicates:** 0.
  -> *Next step:* dedup theo `customer_id`, giữ `_ingested_at` mới nhất (SCD1).
- **Ghi chú:** 198 KH chưa có giao dịch; 157 KH không có trong territory_mapping (= số KH `Inactive`).

## raw.product_master — 100 dòng (SRC-04)

- **Incorrect data types:** `unit_price`, `cost_price` → NUMERIC; `weight_gram` → INTEGER; `launch_date` → DATE.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có (giá vốn < giá bán ở mọi SP; giá bán khớp 100% với giá trong sales).
  -> *Next step:* No action.
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0.
  -> *Next step:* dedup theo `product_id` (SCD1).

## raw.distributor_orders — 35,945 dòng (SRC-05)

- **Incorrect data types:** `order_date`, `expected_delivery_date`, `actual_delivery_date` → DATE;
  `order_month`, `order_quarter`, `qty_ordered`, `qty_delivered` → INTEGER;
  `fill_rate_pct`, `unit_price_list`, `distributor_price`, `gross_amount`, `delivered_amount` → NUMERIC;
  `ontime_delivery` (Yes/No) → BOOLEAN.
  -> *Next step:* cast ở Silver.
- **Incorrect values:**
  - 1,740 dòng `delivery_status = Cancelled` nhưng vẫn có `qty_delivered` 14–499 và `delivered_amount` > 0.
    -> *Next step:* **cần business xác nhận**. Đề xuất: ở Silver giữ nguyên, thêm cột `qty_delivered_effective`
    = 0 nếu Cancelled; Fill Rate (BR-B-01) tính trên cột này.
  - Không có dòng nào `qty_delivered = qty_ordered`, kể cả `Delivered` → "giao đúng số lượng" theo định nghĩa
    Fill Rate của BRD sẽ luôn = 0%.
    -> *Next step:* dùng `fill_rate_pct` (= delivered / ordered) làm Fill Rate; ghi vào OQ-07.
  - 177 dòng `ontime_delivery = No` nhưng `actual_delivery_date <= expected_delivery_date`.
    -> *Next step:* Silver tính lại `is_ontime = actual_delivery_date <= expected_delivery_date`, giữ cột gốc để đối chiếu.
  - 4,142 đơn có nhiều `delivery_status` khác nhau giữa các dòng → trạng thái ở cấp dòng.
    -> *Next step:* No action — grain (order_id, product_id).
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0 theo (order_id, product_id). `order_id` không unique (8,000 đơn).
  -> *Next step:* PK = (order_id, product_id); dedup theo PK + `_ingested_at`.

## raw.distributor_master — 138 dòng (SRC-06)

- **Incorrect data types:** `join_date` → DATE; `credit_limit` → NUMERIC; `phone`, `tax_code` giữ TEXT.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có; email đúng định dạng; `assigned_supervisor_id` (9 người) đều có trong employee_master.
  -> *Next step:* No action.
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0.
  -> *Next step:* dedup theo `distributor_id`.
- **Ghi chú:** 13 NPP không có đơn trong 2024 (= số NPP `Inactive`). Nguồn chỉ có **1 snapshot** → chưa có lịch sử
  đổi tier/region để làm SCD2 (BR-B-02); SCD2 sẽ bắt đầu tích luỹ từ các lần load sau.

## raw.employee_master — 228 dòng (SRC-07, 2 sheet × 114 NV)

- **Incorrect data types:** `date_of_birth`, `join_date`, `effective_date`, `resign_date` → DATE; `phone` giữ TEXT.
  -> *Next step:* cast ở Silver.
- **Incorrect values:**
  - 8 NV (16 dòng, cả v1 và v2) **vào làm khi 15–17 tuổi**: EMP1006, EMP1019, EMP1035, EMP1045, EMP1046, EMP1059,
    EMP1069, EMP1104 (vd EMP1045 sinh 2002-07-31, vào làm 2018-02-09).
    -> *Next step:* giữ dữ liệu, thêm cờ `dq_underage_at_join`; báo HR. Không ảnh hưởng chỉ số bán hàng.
  - `resign_date` của 8 NV nghỉ việc là 2024-05-24 → 2024-06-18, nhưng `Change_Log.effective_date` = 2024-07-01
    và các NV này **vẫn có 547 dòng bán hàng** sau `resign_date` (đến 2024-06-30).
    -> *Next step:* **cần business xác nhận**. Đề xuất: SCD2 dùng `Change_Log.effective_date` (2024-07-01) làm mốc
    đổi trạng thái; `resign_date` giữ như thuộc tính (ngày nộp đơn); giao dịch đến 30/6 là hợp lệ.
- **Missing data:** `resign_date` thiếu 96.5%, `transfer_note` thiếu 97.8% — đúng nghiệp vụ (chỉ NV nghỉ / chuyển mới có).
  -> *Next step:* No action.
- **Duplicates:** 0 theo (employee_id, version). Sheet v2 là **snapshot đầy đủ** (114 NV, gồm cả 8 NV `Resigned`),
  chỉ 13 NV thay đổi so với v1 (5 chuyển vùng + 8 nghỉ).
  -> *Next step:* Phase 3 `dim_employees` (SCD2): chỉ tạo bản ghi mới cho NV có thay đổi; NV không đổi giữ 1 bản ghi
  `2024-01-01 → 9999-12-31`.
- **Ghi chú:** 3 `Area Manager` không có target và không có giao dịch.

## raw.employee_change_log — 13 dòng (SRC-07, sheet Change_Log)

- **Incorrect data types:** `effective_date` → DATE.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có. 5 `Chuyển vùng` + 8 `Nghỉ việc`, tất cả hiệu lực 2024-07-01; khớp 100% với khác biệt
  giữa sheet v1 và v2 (không có NV đổi vùng mà thiếu trong log).
  -> *Next step:* No action.
- **Missing data:** `new_region`, `new_team` thiếu 61.5% = 8 dòng `Nghỉ việc` — đúng nghiệp vụ.
  -> *Next step:* No action.
- **Duplicates:** 0.
  -> *Next step:* No action.

## raw.territory_mapping — 1,843 dòng (SRC-08)

- **Incorrect data types:** `effective_date`, `expiry_date` → DATE (`9999-12-31` = đang hiệu lực).
  -> *Next step:* cast ở Silver.
- **Incorrect values:**
  - Chỉ có `version = v1`, mọi dòng `2024-01-01 → 9999-12-31` → **chưa cập nhật** cho 5 NV chuyển vùng 2024-07-01:
    khách hàng vẫn gán cho NV cũ với region cũ (vd EMP1018: 22 KH Miền Bắc, nhưng từ 7/2024 thuộc Miền Nam).
    -> *Next step:* **cần business xác nhận** KH của NV chuyển vùng được giao cho ai. Tạm thời giữ nguyên; không dùng
    territory_mapping để suy ra region của giao dịch (dùng region của KH / NV tại thời điểm giao dịch).
  - 4,192 dòng bán hàng do NV **khác** NV phụ trách KH thực hiện → territory không độc quyền.
    -> *Next step:* No action; báo cáo theo `sales_transactions.employee_id`, không theo territory.
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0 theo `territory_id` và theo (employee_id, customer_id, effective_date); mỗi KH chỉ có 1 dòng.
  -> *Next step:* dedup theo `territory_id`.

## raw.return_transactions — 3,665 dòng (SRC-09)

- **Incorrect data types:** `return_date` → DATE; `return_month`, `return_quantity` → INTEGER;
  `unit_price`, `return_amount` → NUMERIC.
  -> *Next step:* cast ở Silver.
- **Incorrect values:** không có. Mọi phiếu trả khớp được dòng bán gốc (order_id, product_id), cùng KH/NV/đơn giá,
  ngày trả sau ngày bán, số lượng trả ≤ số lượng mua; đơn gốc đều `Delivered`.
  -> *Next step:* No action. Net Revenue = Delivered − Returns; cần quyết định có trừ phiếu `Từ chối` (169) và
  `Đang xử lý` (506) không — đề xuất chỉ trừ `Đã xử lý`.
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0.
  -> *Next step:* dedup theo `return_id`.

## raw.promotion_program — 40 dòng (SRC-10)

- **Incorrect data types:** `start_date`, `end_date` → DATE; `discount_pct`, `budget_vnd`, `actual_cost_vnd` → NUMERIC;
  `min_order_quantity` → INTEGER.
  -> *Next step:* cast ở Silver.
- **Incorrect values:**
  - 6 chương trình `actual_cost_vnd > budget_vnd` (vượt ngân sách) — thông tin nghiệp vụ hợp lệ, không phải lỗi.
    -> *Next step:* No action; dùng cho ROI (BR-B-04).
  - `target_channel` / `target_region` có giá trị `All` (9 / 8 chương trình).
    -> *Next step:* khi join, `All` khớp mọi kênh / vùng.
  - `applicable_products` là danh sách `PRD0017|PRD0040` (1 chương trình nhiều SP; 1 SP có thể thuộc nhiều chương trình).
    -> *Next step:* Silver tách thành bảng cầu `stg_promotion_products (promotion_id, product_id)`.
- **Missing data:** 0%.
  -> *Next step:* No action.
- **Duplicates:** 0.
  -> *Next step:* dedup theo `promotion_id`.

---

## Vấn đề chéo bảng / thiếu dữ liệu so với BRD

| # | Vấn đề | Ảnh hưởng | Đề xuất |
|---|---|---|---|
| X-1 | Sales và distributor orders chỉ có năm **2024** | Không tính được YoY (BR-A-01, BR-B-01); FY2023 (09/2023–08/2024) chỉ có 8 tháng | Hỏi Coach có dữ liệu 2023 không; nếu không, measure YoY trả BLANK |
| X-2 | 2,019 dòng bán H2/2024 có `region` (theo KH) ≠ region mới của NV đã chuyển vùng | Báo cáo theo vùng của NV khác báo cáo theo vùng của KH | Báo cáo theo NV dùng `dim_employees` SCD2 tại ngày giao dịch; theo khu vực bán dùng region của KH — ghi rõ trong semantic model |
| X-3 | Không có file **target của NPP** | BR-B-02 (% đạt chỉ tiêu NPP) chưa làm được | Hỏi Coach (OQ-06) |
| X-4 | Không có dữ liệu **tồn kho** | BR-B-03 chưa làm được | Đã biết (OQ-04) |
| X-5 | distributor_master chỉ 1 snapshot | Chưa có lịch sử đổi tier/region cho SCD2 (BR-B-02) | SCD2 tích luỹ từ các lần load sau |

## Kế hoạch cho Silver (Task 2.2)

1. **Cast kiểu** theo từng bảng như trên; cột mã (`phone`, `tax_code`, mọi `*_id`) giữ TEXT; `btrim` mọi cột text.
2. **Dedup** theo PK đã xác định, giữ bản ghi có `_ingested_at` mới nhất (an toàn khi Bronze bị load lại).
3. **Cột tính thêm / cờ chất lượng:** `is_ontime` (distributor_orders), `qty_delivered_effective` (chờ xác nhận),
   `is_before_customer_join` (sales), `dq_underage_at_join` (employee).
4. **Bảng cầu** `stg_promotion_products` từ `applicable_products`.
5. **Test** cho mỗi bảng: `not_null` + `unique` trên PK, cộng các kiểm tra công thức đang = 0 lỗi ở trên
   (để phát hiện nếu dữ liệu mới vi phạm).

## Câu hỏi cần Coach / Business xác nhận

1. Dòng distributor order `Cancelled` nhưng có `qty_delivered` > 0: có tính vào Fill Rate / doanh số không?
2. Ngày nghỉ việc dùng `resign_date` (24/5–18/6) hay `Change_Log.effective_date` (1/7)?
3. Khách hàng của 5 NV chuyển vùng được giao lại cho ai từ 7/2024?
4. Net Revenue trừ phiếu trả ở trạng thái nào (`Đã xử lý` / `Đang xử lý` / `Từ chối`)?
5. Có dữ liệu 2023 để tính YoY không? Có file target cho NPP không?
