"""Ghi dữ liệu đã chuẩn hóa vào CSDL — chỗ hội tụ duy nhất của mọi đường (SPEC §4, §13).

Hiện file này mới có HỢP ĐỒNG ĐẦU RA: danh sách cột chuẩn của 2 bảng đơn hàng.
Hàm upsert sẽ thêm vào chính file này ở bước 7.

Vì sao khai báo danh sách cột ở đây: có 4 module chuẩn hóa (2 parser CSV, 2
transform API) và chúng chỉ chung nhau đúng một thứ — DataFrame đầu ra phải có
đủ và đúng các cột này. Khai báo một lần ở nơi nhận dữ liệu thì cả 4 module
cùng nhìn vào một chỗ, và test khứ hồi (§21.5) so được từng cột giữa 2 đường.
Không cần lớp cơ sở cho parser (§13 "Không còn base_parser.py", §0.3).

Cột của bảng (§3.1, §3.2) KHÔNG có trong danh sách, vì module chuẩn hóa không
tạo ra chúng:
- `id`, `uploaded_at`, `updated_at`: CSDL tự sinh / upsert tự đặt (§4).
- `source_file`: tên file chỉ nơi gọi biết (thư mục quét, nút tải file);
  đường API không có. Để ngoài danh sách thì 2 đường vẫn so được từng cột.
"""

# Thứ tự cột theo đúng thứ tự trong CREATE TABLE ở SPEC §3.1.
COT_CHUAN_SHOPEE = [
    "shop_name",
    "order_id",
    "sku",
    "product_code",
    "order_date",
    "order_created_at",
    "order_status_raw",
    "order_status",
    "is_returned",
    "product_name",
    "variation",
    "quantity",
    "returned_quantity",
    "unit_price",
    "nmv",
    "nmv_after_tax",
    "nmv_is_provisional",
    "is_affiliate",
    "province",
    "province_raw",
    "hour_bucket",
    "data_source",
]

# Theo thứ tự CREATE TABLE ở SPEC §3.2. Khác Shopee 3 chỗ: có
# `sku_subtotal_after_discount` và `order_amount` (MỨC ĐƠN — CẤM SUM theo
# dòng, §7.4); không có `nmv_is_provisional` vì TikTok không có NMV tạm tính.
COT_CHUAN_TIKTOK = [
    "shop_name",
    "order_id",
    "sku",
    "product_code",
    "order_date",
    "order_created_at",
    "order_status_raw",
    "order_status",
    "is_returned",
    "product_name",
    "variation",
    "quantity",
    "returned_quantity",
    "unit_price",
    "sku_subtotal_after_discount",
    "nmv",
    "nmv_after_tax",
    "order_amount",
    "is_affiliate",
    "province",
    "province_raw",
    "hour_bucket",
    "data_source",
]
