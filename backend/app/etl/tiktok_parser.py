"""Đọc file CSV TikTok → DataFrame cột chuẩn — đường nạp file dự phòng."""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_TIKTOK
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_file

# Chỉ đọc các cột cần, để thông tin cá nhân không vào bộ nhớ; không đọc các cột công thức của Lark.
COT_CAN_DOC = [
    "Shop",
    "Order ID",
    "Seller SKU",
    "Created Time",
    "Order Status",
    "Cancelation/Return Type",
    "Product Name",
    "Variation",
    "Quantity",
    "Sku Quantity of return",
    "SKU Unit Original Price",
    "SKU Subtotal Before Discount",
    "SKU Seller Discount",
    "SKU Subtotal After Discount",
    "Order Amount",
    "Nguồn Doanh Thu",
    "Province",
]

# Seller SKU rỗng thì gán cùng giá trị với Shopee để sku luôn NOT NULL.
SKU_KHONG_XAC_DINH = "UNKNOWN"

LOAI_HOAN_HANG = "Return/Refund"

# Ô rỗng không phải affiliate.
NGUON_TU_BAN_TIKTOK = "Inhouse"


def doc_csv_tiktok(duong_dan):
    # dtype=str để Order ID 18 chữ số không bị đổi thành số thực và mất chữ số cuối.
    return pd.read_csv(duong_dan, usecols=COT_CAN_DOC, dtype=str, encoding="utf-8-sig")


def tao_cot_sku(cot_seller_sku):
    sku_da_lam_sach = cleaners.lam_sach_seller_sku_tiktok(cot_seller_sku)
    sku_rong = sku_da_lam_sach.isna() | (sku_da_lam_sach == "")
    return sku_da_lam_sach.mask(sku_rong, SKU_KHONG_XAC_DINH)


def tinh_nmv_tiktok(tong_truoc_giam_gia, nguoi_ban_giam_gia):
    """Chỉ trừ phần người bán tự giảm; phần sàn giảm thì sàn bù lại nên không trừ."""
    return tong_truoc_giam_gia - nguoi_ban_giam_gia


def tao_bang_chuan(bang_goc, sku):
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["tiktok"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    thoi_gian_tao_don = cleaners.doc_thoi_gian_tiktok(bang_goc["Created Time"])
    tong_truoc_giam_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Subtotal Before Discount"])
    nguoi_ban_giam_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Seller Discount"])
    nmv = tinh_nmv_tiktok(tong_truoc_giam_gia, nguoi_ban_giam_gia)

    bang_chuan = pd.DataFrame(index=bang_goc.index)
    bang_chuan["shop_name"] = bang_goc["Shop"]
    bang_chuan["order_id"] = bang_goc["Order ID"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    # Giữ kiểu ngày-giờ lúc 0h cho cùng kiểu với order_date của Shopee.
    bang_chuan["order_date"] = thoi_gian_tao_don.dt.normalize()
    bang_chuan["order_created_at"] = thoi_gian_tao_don
    bang_chuan["order_status_raw"] = bang_goc["Order Status"]
    # Order Status quyết định trạng thái, Cancelation/Return Type không ghi đè.
    bang_chuan["order_status"] = bang_goc["Order Status"].apply(
        gom_nhom_trang_thai_file, args=("tiktok",)
    )
    # Không dùng Sku Quantity of return > 0 vì TikTok điền cột đó cả cho đơn hủy.
    bang_chuan["is_returned"] = bang_goc["Cancelation/Return Type"] == LOAI_HOAN_HANG
    bang_chuan["product_name"] = bang_goc["Product Name"]
    bang_chuan["variation"] = bang_goc["Variation"].str.strip()
    bang_chuan["quantity"] = pd.to_numeric(bang_goc["Quantity"], errors="raise")
    # Không dùng tính tỷ lệ hoàn, lý do như is_returned ở trên.
    bang_chuan["returned_quantity"] = pd.to_numeric(bang_goc["Sku Quantity of return"], errors="raise")
    bang_chuan["unit_price"] = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Unit Original Price"])
    bang_chuan["sku_subtotal_after_discount"] = cleaners.doi_chuoi_tien_sang_so(
        bang_goc["SKU Subtotal After Discount"]
    )
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # Mức đơn, lặp lại trên mọi dòng của đơn, không được SUM theo dòng.
    bang_chuan["order_amount"] = cleaners.doi_chuoi_tien_sang_so(bang_goc["Order Amount"])
    bang_chuan["is_affiliate"] = cleaners.xac_dinh_affiliate(bang_goc["Nguồn Doanh Thu"], NGUON_TU_BAN_TIKTOK)
    bang_chuan["province"] = bang_goc["Province"].apply(
        cleaners.normalize_province, args=(bang_tinh,)
    )
    bang_chuan["province_raw"] = bang_goc["Province"]
    # Tự tính từ giờ tạo đơn để đường API tính cùng một cách.
    bang_chuan["hour_bucket"] = cleaners.tinh_khung_gio(thoi_gian_tao_don)
    bang_chuan["data_source"] = "file"

    return bang_chuan[COT_CHUAN_TIKTOK]


def chuan_hoa_file_tiktok(duong_dan):
    bang_goc = doc_csv_tiktok(duong_dan)
    sku = tao_cot_sku(bang_goc["Seller SKU"])
    bang_chuan = tao_bang_chuan(bang_goc, sku)

    # TikTok không có chuỗi dự phòng sku nên rows_sku_fallback luôn bằng 0.
    bo_dem = {
        "rows_sku_fallback": 0,
        "rows_sku_unknown": int((sku == SKU_KHONG_XAC_DINH).sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan, bo_dem
