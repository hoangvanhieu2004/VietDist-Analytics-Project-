# Data Profile — Bronze (raw.*)

> File tự sinh bởi `02_sql_analytics/profiling/profile_raw.py` lúc 2026-11-02 09:26. Không sửa tay — chạy lại script để cập nhật.
> Phân tích và kế hoạch xử lý nằm ở `docs/data_issues.md`.

**Cách đọc:** "% thiếu" = NULL hoặc chuỗi rỗng. "Kiểu đoán" = kiểu mà ≥ 90% giá trị ép được; "Không ép được" = số giá trị còn lại. "mã (số 0 đầu)" = trông như số nhưng có số 0 đầu (SĐT, mã số thuế) nên cần giữ dạng text.

| Bảng | Số dòng | Số cột | Dòng trùng hoàn toàn |
|---|---:|---:|---:|
| raw.customer_master | 2,000 | 12 | 0 |
| raw.distributor_master | 138 | 14 | 0 |
| raw.distributor_orders | 35,945 | 21 | 0 |
| raw.employee_change_log | 13 | 8 | 0 |
| raw.employee_master | 228 | 15 | 0 |
| raw.product_master | 100 | 10 | 0 |
| raw.promotion_program | 40 | 14 | 0 |
| raw.return_transactions | 3,665 | 14 | 0 |
| raw.sales_targets_raw | 1,950 | 15 | 0 |
| raw.sales_transactions | 119,101 | 21 | 0 |
| raw.territory_mapping | 1,843 | 8 | 0 |

## raw.customer_master

- Số dòng: **2,000** — số cột dữ liệu: 12 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `customer_id` | text | 0.0% |  | 2,000 |  |  |  |  |  |
| `customer_name` | text | 0.0% |  | 1,942 |  |  |  |  |  |
| `customer_type` | text | 0.0% |  | 6 |  |  |  |  |  |
| `channel` | text | 0.0% |  | 3 |  |  |  |  |  |
| `province` | text | 0.0% |  | 23 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `address` | text | 0.0% |  | 1,976 |  |  |  |  |  |
| `phone` | mã (số 0 đầu) | 0.0% |  | 2,000 |  |  | 2.11e+09 | 2.999e+09 |  |
| `tax_code` | number | 51.7% |  | 965 |  |  | 1.005e+09 | 9.999e+09 |  |
| `join_date` | date | 0.0% |  | 1,291 |  |  | 2018-01-01 | 2024-03-29 |  |
| `credit_limit` | number | 0.0% |  | 4 |  |  | 5e+07 | 5e+08 |  |
| `status` | text | 0.0% |  | 2 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `customer_type`: Canteen (366), Online Seller (362), Tạp hóa (340), Cửa hàng tiện lợi (333), Siêu thị (313), Nhà hàng (286)
- `channel`: Traditional Trade (992), Modern Trade (646), E-commerce (362)
- `region`: Miền Bắc (704), Miền Trung (660), Miền Nam (636)
- `status`: Active (1,843), Inactive (157)

## raw.distributor_master

- Số dòng: **138** — số cột dữ liệu: 14 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `distributor_id` | text | 0.0% |  | 138 |  |  |  |  |  |
| `distributor_name` | text | 0.0% |  | 138 |  |  |  |  |  |
| `tier` | text | 0.0% |  | 3 |  |  |  |  |  |
| `channel` | text | 0.0% |  | 3 |  |  |  |  |  |
| `province` | text | 0.0% |  | 23 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `contact_person` | text | 0.0% |  | 136 |  |  |  |  |  |
| `phone` | mã (số 0 đầu) | 0.0% |  | 138 |  |  | 2.117e+09 | 2.997e+09 |  |
| `email` | text | 0.0% |  | 138 |  |  |  |  |  |
| `tax_code` | number | 0.0% |  | 138 |  |  | 1.06e+09 | 9.898e+09 |  |
| `join_date` | date | 0.0% |  | 130 |  |  | 2015-01-08 | 2023-06-04 |  |
| `credit_limit` | number | 0.0% |  | 4 |  |  | 2e+08 | 2e+09 |  |
| `status` | text | 0.0% |  | 2 |  |  |  |  |  |
| `assigned_supervisor_id` | text | 0.0% |  | 9 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `tier`: Đại lý cấp 2 (59), Điểm bán lẻ (50), Nhà phân phối cấp 1 (29)
- `channel`: Traditional Trade (58), E-commerce (44), Modern Trade (36)
- `region`: Miền Bắc (50), Miền Nam (46), Miền Trung (42)
- `status`: Active (125), Inactive (13)
- `assigned_supervisor_id`: EMP1034 (22), EMP1023 (19), EMP1043 (17), EMP1001 (17), EMP1097 (15), EMP1067 (15), EMP1012 (14), EMP1082 (11), EMP1052 (8)

## raw.distributor_orders

- Số dòng: **35,945** — số cột dữ liệu: 21 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `order_id` | text | 0.0% |  | 8,000 |  |  |  |  |  |
| `order_date` | date | 0.0% |  | 366 |  |  | 2024-01-01 | 2024-12-31 |  |
| `order_month` | number | 0.0% |  | 12 |  |  | 1 | 12 |  |
| `order_quarter` | number | 0.0% |  | 4 |  |  | 1 | 4 |  |
| `distributor_id` | text | 0.0% |  | 125 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `channel` | text | 0.0% |  | 3 |  |  |  |  |  |
| `product_id` | text | 0.0% |  | 92 |  |  |  |  |  |
| `product_category` | text | 0.0% |  | 4 |  |  |  |  |  |
| `qty_ordered` | number | 0.0% |  | 481 |  |  | 20 | 500 |  |
| `qty_delivered` | number | 0.0% |  | 485 |  |  | 14 | 499 |  |
| `fill_rate_pct` | number | 0.0% |  | 2,998 |  |  | 66.67 | 99.8 |  |
| `unit_price_list` | number | 0.0% |  | 12 |  |  | 8,500 | 5e+04 |  |
| `distributor_price` | number | 0.0% |  | 2,642 |  |  | 6,800 | 4.5e+04 |  |
| `gross_amount` | number | 0.0% |  | 33,085 |  |  | 1.398e+05 | 2.23e+07 |  |
| `delivered_amount` | number | 0.0% |  | 32,749 |  |  | 1.044e+05 | 2.127e+07 |  |
| `expected_delivery_date` | date | 0.0% |  | 366 |  |  | 2024-01-03 | 2025-01-02 |  |
| `actual_delivery_date` | date | 0.0% |  | 365 |  |  | 2024-01-02 | 2024-12-31 |  |
| `ontime_delivery` | text | 0.0% |  | 2 |  |  |  |  |  |
| `delivery_status` | text | 0.0% |  | 3 |  |  |  |  |  |
| `payment_terms` | text | 0.0% |  | 4 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `region`: Miền Bắc (13,006), Miền Nam (11,791), Miền Trung (11,148)
- `channel`: Traditional Trade (15,158), E-commerce (11,185), Modern Trade (9,602)
- `product_category`: Thực phẩm (12,019), Thức uống (11,363), Chăm sóc cá nhân (6,675), Gia dụng (5,888)
- `ontime_delivery`: No (21,494), Yes (14,451)
- `delivery_status`: Delivered (29,585), Partial (4,620), Cancelled (1,740)
- `payment_terms`: NET45 (9,086), NET15 (9,037), COD (8,924), NET30 (8,898)

## raw.employee_change_log

- Số dòng: **13** — số cột dữ liệu: 8 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `employee_id` | text | 0.0% |  | 13 |  |  |  |  |  |
| `employee_name` | text | 0.0% |  | 13 |  |  |  |  |  |
| `change_type` | text | 0.0% |  | 2 |  |  |  |  |  |
| `effective_date` | date | 0.0% |  | 1 |  |  | 2024-07-01 | 2024-07-01 |  |
| `old_region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `new_region` | text | 61.5% |  | 3 |  |  |  |  |  |
| `old_team` | text | 0.0% |  | 9 |  |  |  |  |  |
| `new_team` | text | 61.5% |  | 5 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `employee_id`: EMP1035 (1), EMP1054 (1), EMP1075 (1), EMP1051 (1), EMP1070 (1), EMP1046 (1), EMP1100 (1), EMP1048 (1), EMP1018 (1), EMP1004 (1), EMP1092 (1), EMP1026 (1), EMP1078 (1)
- `employee_name`: Đỗ Hữu Long (1), Hoàng Văn Hùng (1), Bùi Văn Lộc (1), Lý Thanh Phúc (1), Phạm Xuân Linh (1), Ngô Đức Cường (1), Lý Thị Lộc (1), Trần Quốc Nhân (1), Trần Thành Tuấn (1), Đỗ Minh An (1), Phạm Xuân Quân (1), Bùi Thanh Thắng (1), Ngô Bá Dũng (1)
- `change_type`: Nghỉ việc (8), Chuyển vùng (5)
- `old_region`: Miền Nam (6), Miền Trung (4), Miền Bắc (3)
- `new_region`: Miền Nam (2), Miền Bắc (2), Miền Trung (1)
- `old_team`: Team Nam 2 (3), Team Trung 2 (3), Team Trung 1 (1), Team Nam 1 (1), Team Nam 4 (1), Team Bắc 2 (1), Team Bắc 1 (1), Team Nam 3 (1), Team Bắc 3 (1)
- `new_team`: Team Nam 3 (1), Team Trung 2 (1), Team Bắc 3 (1), Team Nam 4 (1), Team Bắc 1 (1)

## raw.employee_master

- Số dòng: **228** — số cột dữ liệu: 15 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `employee_id` | text | 0.0% |  | 114 |  |  |  |  |  |
| `full_name` | text | 0.0% |  | 112 |  |  |  |  |  |
| `gender` | text | 0.0% |  | 2 |  |  |  |  |  |
| `date_of_birth` | date | 0.0% |  | 114 |  |  | 1976-01-08 | 2003-09-28 |  |
| `join_date` | date | 0.0% |  | 112 |  |  | 2010-12-27 | 2023-11-19 |  |
| `position` | text | 0.0% |  | 4 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `team` | text | 0.0% |  | 10 |  |  |  |  |  |
| `email` | text | 0.0% |  | 114 |  |  |  |  |  |
| `phone` | mã (số 0 đầu) | 0.0% |  | 114 |  |  | 9.102e+08 | 9.999e+08 |  |
| `status` | text | 0.0% |  | 2 |  |  |  |  |  |
| `version` | text | 0.0% |  | 2 |  |  |  |  |  |
| `effective_date` | date | 0.0% |  | 2 |  |  | 2024-01-01 | 2024-07-01 |  |
| `resign_date` | date | 96.5% |  | 7 |  |  | 2024-05-24 | 2024-06-18 |  |
| `transfer_note` | text | 97.8% |  | 3 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `gender`: Nữ (122), Nam (106)
- `position`: Senior Sales Representative (116), Sales Representative (88), Sales Supervisor (18), Area Manager (6)
- `region`: Miền Nam (122), Miền Bắc (67), Miền Trung (39)
- `team`: Team Nam 4 (31), Team Nam 1 (30), Team Nam 3 (30), Team Nam 2 (29), Team Bắc 1 (22), Team Bắc 3 (22), Team Bắc 2 (21), Team Trung 2 (19), Team Trung 1 (18), Management (6)
- `status`: Active (220), Resigned (8)
- `version`: v1 (114), v2 (114)
- `transfer_note`: Chuyển từ Miền Bắc sang Miền Nam (2), Chuyển từ Miền Nam sang Miền Bắc (2), Chuyển từ Miền Bắc sang Miền Trung (1)

## raw.product_master

- Số dòng: **100** — số cột dữ liệu: 10 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `product_id` | text | 0.0% |  | 100 |  |  |  |  |  |
| `product_name` | text | 0.0% |  | 100 |  |  |  |  |  |
| `category` | text | 0.0% |  | 4 |  |  |  |  |  |
| `sub_category` | text | 0.0% |  | 17 |  |  |  |  |  |
| `unit` | text | 0.0% |  | 6 |  |  |  |  |  |
| `unit_price` | number | 0.0% |  | 12 |  |  | 8,500 | 5e+04 |  |
| `cost_price` | number | 0.0% |  | 77 |  |  | 5,000 | 3.53e+04 |  |
| `weight_gram` | number | 0.0% |  | 7 |  |  | 150 | 1,000 |  |
| `status` | text | 0.0% |  | 2 |  |  |  |  |  |
| `launch_date` | date | 0.0% |  | 100 |  |  | 2018-03-06 | 2023-12-26 |  |

**Giá trị của các cột phân loại:**

- `category`: Thực phẩm (35), Thức uống (31), Chăm sóc cá nhân (19), Gia dụng (15)
- `sub_category`: Nước uống đóng chai (8), Sữa (8), Mì ăn liền (8), Bánh kẹo (8), Nước tăng lực (7), Cháo ăn liền (7), Dầu ăn (7), Sữa tắm (7), Bột giặt (6), Gia vị (5), Nước lau sàn (5), Nước giải khát (4), Trà đóng chai (4), Dầu gội (4), Kem đánh răng (4), Xà phòng (4), Nước rửa chén (4)
- `unit`: Hộp (21), Túi (21), Lon (19), Chai (15), Gói (12), Thùng (12)
- `status`: Active (92), Discontinued (8)

## raw.promotion_program

- Số dòng: **40** — số cột dữ liệu: 14 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `promotion_id` | text | 0.0% |  | 40 |  |  |  |  |  |
| `promotion_name` | text | 0.0% |  | 40 |  |  |  |  |  |
| `promotion_type` | text | 0.0% |  | 5 |  |  |  |  |  |
| `target_channel` | text | 0.0% |  | 4 |  |  |  |  |  |
| `target_region` | text | 0.0% |  | 4 |  |  |  |  |  |
| `start_date` | date | 0.0% |  | 38 |  |  | 2024-01-02 | 2024-10-28 |  |
| `end_date` | date | 0.0% |  | 39 |  |  | 2024-01-24 | 2024-12-16 |  |
| `applicable_products` | text | 0.0% |  | 40 |  |  |  |  |  |
| `discount_pct` | number | 0.0% |  | 6 |  |  | 5 | 20 |  |
| `min_order_quantity` | number | 0.0% |  | 4 |  |  | 0 | 50 |  |
| `budget_vnd` | number | 0.0% |  | 40 |  |  | 5.3e+07 | 4.85e+08 |  |
| `actual_cost_vnd` | number | 0.0% |  | 39 |  |  | 4e+07 | 4.66e+08 |  |
| `status` | text | 0.0% |  | 3 |  |  |  |  |  |
| `created_by` | text | 0.0% |  | 40 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `promotion_type`: Giảm giá trực tiếp (11), Tích điểm đổi quà (10), Tặng hàng kèm (7), Chiết khấu theo sản lượng (6), Combo khuyến mãi (6)
- `target_channel`: E-commerce (11), Modern Trade (10), Traditional Trade (10), All (9)
- `target_region`: Miền Nam (14), Miền Trung (11), All (8), Miền Bắc (7)
- `status`: Completed (34), Planned (3), Active (3)

## raw.return_transactions

- Số dòng: **3,665** — số cột dữ liệu: 14 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `return_id` | text | 0.0% |  | 3,665 |  |  |  |  |  |
| `original_order_id` | text | 0.0% |  | 3,564 |  |  |  |  |  |
| `return_date` | date | 0.0% |  | 362 |  |  | 2024-01-05 | 2024-12-31 |  |
| `return_month` | number | 0.0% |  | 12 |  |  | 1 | 12 |  |
| `customer_id` | text | 0.0% |  | 967 |  |  |  |  |  |
| `employee_id` | text | 0.0% |  | 106 |  |  |  |  |  |
| `product_id` | text | 0.0% |  | 92 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `province` | text | 0.0% |  | 23 |  |  |  |  |  |
| `return_quantity` | number | 0.0% |  | 59 |  |  | 1 | 60 |  |
| `unit_price` | number | 0.0% |  | 12 |  |  | 8,500 | 5e+04 |  |
| `return_amount` | number | 0.0% |  | 346 |  |  | 8,500 | 2.85e+06 |  |
| `return_reason` | text | 0.0% |  | 6 |  |  |  |  |  |
| `status` | text | 0.0% |  | 3 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `region`: Miền Trung (1,324), Miền Nam (1,202), Miền Bắc (1,139)
- `return_reason`: Khách từ chối nhận (643), Hàng vỡ vận chuyển (625), Hàng hết hạn (619), Hàng lỗi (608), Không đúng đơn hàng (605), Sai sản phẩm (565)
- `status`: Đã xử lý (2,990), Đang xử lý (506), Từ chối (169)

## raw.sales_targets_raw

- Số dòng: **1,950** — số cột dữ liệu: 15 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: e929f943-2e18-4cee-862d-496ec4763000

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `version_label` | text | 0.0% |  | 2 |  |  |  |  |  |
| `plan_version` | text | 0.0% |  | 2 |  |  |  |  |  |
| `version_date` | date | 0.0% |  | 2 |  |  | 2024-01-05 | 2024-07-03 |  |
| `effective_from` | date | 0.0% |  | 2 |  |  | 2024-01-01 | 2024-07-01 |  |
| `effective_to` | date | 0.0% |  | 1 |  |  | 2024-12-31 | 2024-12-31 |  |
| `employee_id` | text | 0.0% |  | 111 |  |  |  |  |  |
| `employee_name` | text | 0.0% |  | 109 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `team` | text | 0.0% |  | 9 |  |  |  |  |  |
| `year` | number | 0.0% |  | 1 |  |  | 2,024 | 2,024 |  |
| `month` | number | 0.0% |  | 12 |  |  | 1 | 12 |  |
| `target_revenue` | number | 0.0% |  | 857 |  |  | 1.12e+08 | 4.272e+08 |  |
| `target_quantity` | number | 0.0% |  | 857 |  |  | 6,222 | 2.373e+04 |  |
| `target_new_customers` | number | 0.0% |  | 13 |  |  | 3 | 15 |  |
| `month_col` | text | 0.0% |  | 12 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `version_label`: v1 (1,332), v2 (618)
- `plan_version`: v1 (1,332), v2 (618)
- `region`: Miền Nam (1,056), Miền Bắc (588), Miền Trung (306)
- `team`: Team Nam 3 (270), Team Nam 4 (270), Team Nam 1 (264), Team Nam 2 (252), Team Bắc 1 (198), Team Bắc 3 (198), Team Bắc 2 (192), Team Trung 1 (156), Team Trung 2 (150)
- `month_col`: T7 (214), T8 (214), T9 (214), T10 (214), T11 (214), T12 (214), T1 (111), T2 (111), T3 (111), T4 (111), T5 (111), T6 (111)

## raw.sales_transactions

- Số dòng: **119,101** — số cột dữ liệu: 21 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `order_id` | text | 0.0% |  | 50,000 |  |  |  |  |  |
| `order_date` | date | 0.0% |  | 366 |  |  | 2024-01-01 | 2024-12-31 |  |
| `order_month` | number | 0.0% |  | 12 |  |  | 1 | 12 |  |
| `order_quarter` | number | 0.0% |  | 4 |  |  | 1 | 4 |  |
| `order_year` | number | 0.0% |  | 1 |  |  | 2,024 | 2,024 |  |
| `customer_id` | text | 0.0% |  | 1,802 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `province` | text | 0.0% |  | 23 |  |  |  |  |  |
| `channel` | text | 0.0% |  | 3 |  |  |  |  |  |
| `employee_id` | text | 0.0% |  | 108 |  |  |  |  |  |
| `product_id` | text | 0.0% |  | 92 |  |  |  |  |  |
| `product_category` | text | 0.0% |  | 4 |  |  |  |  |  |
| `quantity` | number | 0.0% |  | 116 |  |  | 5 | 120 |  |
| `unit_price` | number | 0.0% |  | 12 |  |  | 8,500 | 5e+04 |  |
| `discount_pct` | number | 0.0% |  | 6 |  |  | 0 | 15 |  |
| `discount_amount` | number | 0.0% |  | 1,742 |  |  | 0 | 9e+05 |  |
| `gross_amount` | number | 0.0% |  | 812 |  |  | 4.25e+04 | 6e+06 |  |
| `net_amount` | number | 0.0% |  | 4,034 |  |  | 3.61e+04 | 6e+06 |  |
| `delivery_status` | text | 0.0% |  | 3 |  |  |  |  |  |
| `payment_method` | text | 0.0% |  | 3 |  |  |  |  |  |
| `payment_status` | text | 0.0% |  | 3 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `region`: Miền Trung (43,393), Miền Nam (38,266), Miền Bắc (37,442)
- `channel`: Traditional Trade (55,110), Modern Trade (46,080), E-commerce (17,911)
- `product_category`: Thực phẩm (40,001), Thức uống (37,691), Chăm sóc cá nhân (21,984), Gia dụng (19,425)
- `delivery_status`: Delivered (104,720), Delivering (9,581), Cancelled (4,800)
- `payment_method`: Công nợ (39,775), Chuyển khoản (39,734), Tiền mặt (39,592)
- `payment_status`: Paid (89,524), Partial (17,791), Unpaid (11,786)

## raw.territory_mapping

- Số dòng: **1,843** — số cột dữ liệu: 8 — dòng trùng hoàn toàn (không tính metadata): **0**
- Batch: dae108c2-af7c-4bbf-b4b9-8832d096240b

| Cột | Kiểu đoán | % thiếu | Khoảng trắng thừa | Khác nhau | Không ép được | Ví dụ lỗi | Min | Max | Ngày ngoài 2022–2026 |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| `territory_id` | text | 0.0% |  | 1,843 |  |  |  |  |  |
| `employee_id` | text | 0.0% |  | 102 |  |  |  |  |  |
| `customer_id` | text | 0.0% |  | 1,843 |  |  |  |  |  |
| `region` | text | 0.0% |  | 3 |  |  |  |  |  |
| `team` | text | 0.0% |  | 9 |  |  |  |  |  |
| `effective_date` | date | 0.0% |  | 1 |  |  | 2024-01-01 | 2024-01-01 |  |
| `expiry_date` | date | 0.0% |  | 1 |  |  | 9999-12-31 | 9999-12-31 |  |
| `version` | text | 0.0% |  | 1 |  |  |  |  |  |

**Giá trị của các cột phân loại:**

- `region`: Miền Bắc (647), Miền Trung (614), Miền Nam (582)
- `team`: Team Trung 1 (310), Team Trung 2 (304), Team Bắc 1 (220), Team Bắc 2 (217), Team Bắc 3 (210), Team Nam 1 (154), Team Nam 2 (148), Team Nam 3 (140), Team Nam 4 (140)
- `version`: v1 (1,843)
