"""Đọc file CSV Shopee → DataFrame cột chuẩn — đường nạp file dự phòng."""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_SHOPEE
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_file

# Chỉ đọc các cột cần, để thông tin cá nhân của người mua không vào bộ nhớ.
# Không .lower() tên cột vì file có hai cột chỉ khác chữ hoa thường.
COT_CAN_DOC = [
    "Mã đơn hàng",
    "Ngày đặt hàng",
    "Trạng Thái Đơn Hàng",
    "SKU sản phẩm",
    "SKU phân loại hàng",
    "Tên sản phẩm",
    "Tên phân loại hàng",
    "Số lượng",
    "Số lượng sản phẩm được hoàn trả",
    "Giá gốc",
    "Người bán trợ giá",
    "Nguồn Doanh Thu",
    "Tỉnh/Thành phố",
    "Khung Giờ Ra Đơn",
]

# Ô rỗng không phải affiliate.
NGUON_TU_BAN_SHOPEE = "ADS"


def doc_csv_shopee(duong_dan):
    # dtype=str để pandas không tự đoán kiểu; cleaners đổi số và kiểm lỗi.
    return pd.read_csv(duong_dan, usecols=COT_CAN_DOC, dtype=str, encoding="utf-8-sig")


def tinh_nmv_shopee(gia_goc, so_luong, nguoi_ban_tro_gia):
    """Không dùng cột NMV của file vì Lark trừ trợ giá cả dòng vào giá một sản phẩm, sai ở dòng số lượng > 1."""
    gia_tri_theo_gia_goc = gia_goc * so_luong
    return gia_tri_theo_gia_goc - nguoi_ban_tro_gia


def tao_bang_chuan(bang_goc, sku, ten_shop):
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["shopee"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    so_luong = pd.to_numeric(bang_goc["Số lượng"], errors="raise")
    so_luong_hoan = pd.to_numeric(bang_goc["Số lượng sản phẩm được hoàn trả"], errors="raise")
    # Giá gốc ghi bằng ký hiệu khoa học ("2.28e+06").
    gia_goc = cleaners.doi_chuoi_tien_sang_so(bang_goc["Giá gốc"])
    nguoi_ban_tro_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["Người bán trợ giá"])
    nmv = tinh_nmv_shopee(gia_goc, so_luong, nguoi_ban_tro_gia)

    bang_chuan = pd.DataFrame(index=bang_goc.index)
    bang_chuan["shop_name"] = ten_shop
    bang_chuan["order_id"] = bang_goc["Mã đơn hàng"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    bang_chuan["order_date"] = cleaners.doc_ngay_shopee(bang_goc["Ngày đặt hàng"])
    # File Shopee chỉ có ngày, không có giờ tạo đơn.
    bang_chuan["order_created_at"] = pd.Series(pd.NaT, index=bang_goc.index, dtype="datetime64[ns]")
    bang_chuan["order_status_raw"] = bang_goc["Trạng Thái Đơn Hàng"]
    bang_chuan["order_status"] = bang_goc["Trạng Thái Đơn Hàng"].apply(
        gom_nhom_trang_thai_file, args=("shopee",)
    )
    # Số lượng hoàn > 0 khớp đúng các dòng hoàn của Shopee nên dùng được.
    bang_chuan["is_returned"] = so_luong_hoan > 0
    bang_chuan["product_name"] = bang_goc["Tên sản phẩm"]
    # File ghi một dấu cách cho ô không có phân loại, API ghi chuỗi rỗng; strip để hai đường như nhau.
    bang_chuan["variation"] = bang_goc["Tên phân loại hàng"].str.strip()
    bang_chuan["quantity"] = so_luong
    bang_chuan["returned_quantity"] = so_luong_hoan
    bang_chuan["unit_price"] = gia_goc
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # Đường file có đủ trợ giá nên NMV chính xác, không tạm tính.
    bang_chuan["nmv_is_provisional"] = False
    bang_chuan["is_affiliate"] = cleaners.xac_dinh_affiliate(bang_goc["Nguồn Doanh Thu"], NGUON_TU_BAN_SHOPEE)
    bang_chuan["province"] = bang_goc["Tỉnh/Thành phố"].apply(
        cleaners.normalize_province, args=(bang_tinh,)
    )
    bang_chuan["province_raw"] = bang_goc["Tỉnh/Thành phố"]
    bang_chuan["hour_bucket"] = bang_goc["Khung Giờ Ra Đơn"]
    bang_chuan["data_source"] = "file"

    return bang_chuan[COT_CHUAN_SHOPEE]


def chuan_hoa_file_shopee(duong_dan, ten_shop):
    """Chuẩn hóa một file CSV Shopee thành dữ liệu sẵn sàng nạp CSDL."""
    bang_goc = doc_csv_shopee(duong_dan)

    sku_san_pham = cleaners.lam_sach_o_sku(bang_goc["SKU sản phẩm"])
    sku_phan_loai = cleaners.lam_sach_o_sku(bang_goc["SKU phân loại hàng"])
    sku = cleaners.dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)

    bang_chuan = tao_bang_chuan(bang_goc, sku, ten_shop)

    # Đếm lại các chỗ đã sửa dữ liệu bẩn để lỗi dữ liệu không bị che mất.
    dung_sku_du_phong = sku_san_pham.isna() & sku_phan_loai.notna()
    khong_co_sku = sku_san_pham.isna() & sku_phan_loai.isna()
    bo_dem = {
        "rows_sku_fallback": int(dung_sku_du_phong.sum()),
        "rows_sku_unknown": int(khong_co_sku.sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan, bo_dem
