"""Các hàm làm sạch dùng chung cho đường file và đường API, để hai đường cho cùng kết quả."""

import json
import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Tính theo vị trí file này vì thư mục làm việc lúc chạy không cố định.
THU_MUC_BANG_ANH_XA = Path(__file__).resolve().parent / "mappings"

# Việt Nam cố định UTC+7, không có giờ mùa hè nên cộng thẳng 7 giờ.
LECH_GIO_VIET_NAM = pd.Timedelta(7, unit="h")

# Quy ước VAT 8% của công ty.
HE_SO_VAT = 1.08

# Tiền tố cần bóc khi chuẩn hóa tỉnh; "Tinh ", "Thanh pho " không dấu có thật trong dữ liệu TikTok.
TIEN_TO_TINH = [
    "Tỉnh ",
    "Thành phố ",
    "Thành Phố ",
    "TP. ",
    "TP ",
    "Phố ",
    "Province de ",
    "Tinh ",
    "Thanh pho ",
]

HAU_TO_TINH = [" City", " city"]

TINH_KHONG_XAC_DINH = "Khác"

SKU_KHONG_XAC_DINH = "UNKNOWN"


def doc_file_anh_xa(ten_file):
    duong_dan = THU_MUC_BANG_ANH_XA / ten_file
    # Ghi rõ utf-8 vì trên Windows open() mặc định cp1252, đọc hỏng tên tỉnh có dấu.
    with open(duong_dan, encoding="utf-8") as file_json:
        return json.load(file_json)


def doi_chuoi_tien_sang_so(cot_tien):
    # Chỉ ép sang chuỗi ở ô có giá trị; ép cả cột thì NaN thành chuỗi "nan".
    co_gia_tri = cot_tien.notna()
    cot_dang_chuoi = cot_tien.astype(str).where(co_gia_tri)

    cot_bo_khoang_trang = cot_dang_chuoi.str.strip()
    cot_bo_dau_phay = cot_bo_khoang_trang.str.replace(",", "", regex=False)

    # Dùng pd.to_numeric để hiểu cả "2.28e+06"; errors="raise" để chuỗi rác dừng ngay thay vì làm hụt doanh thu.
    return pd.to_numeric(cot_bo_dau_phay, errors="raise")


def doc_ngay_shopee(cot_ngay):
    # Ghi rõ format để pandas không đoán nhầm ngày với tháng.
    return pd.to_datetime(cot_ngay, format="%Y/%m/%d", errors="raise")


def doc_thoi_gian_tiktok(cot_thoi_gian):
    return pd.to_datetime(cot_thoi_gian, format="%d/%m/%Y %H:%M:%S", errors="raise")


def doi_timestamp_api_sang_gio_vn(cot_timestamp):
    """Ngày đặt hàng phải tính theo giờ Việt Nam, dùng UTC thì đơn tạo lúc 0h–7h bị lùi sang hôm trước."""
    thoi_gian_utc = pd.to_datetime(cot_timestamp, unit="s")
    # Giữ dạng không múi giờ để cùng kiểu với đường file.
    return thoi_gian_utc + LECH_GIO_VIET_NAM


def tinh_khung_gio(cot_thoi_gian):
    co_thoi_gian = cot_thoi_gian.notna()
    # Có NaT thì .dt.hour ra số thực; điền tạm 0 rồi ép int, các ô này được trả về NaN ở cuối.
    gio_bat_dau = cot_thoi_gian.dt.hour.fillna(0).astype(int)
    gio_ket_thuc = gio_bat_dau + 1

    phan_dau = gio_bat_dau.astype(str) + "H"
    phan_cuoi = gio_ket_thuc.astype(str) + "H"
    khung_gio = phan_dau + " - " + phan_cuoi
    return khung_gio.where(co_thoi_gian)


def lam_sach_seller_sku_tiktok(cot_seller_sku):
    sku_bo_khoang_trang = cot_seller_sku.str.strip()
    # Chỉ bỏ nháy ở hai đầu; nháy ở giữa giữ lại để sku bám sát giá trị gốc.
    return sku_bo_khoang_trang.str.strip("'")


def bo_tien_to_tinh(ten_tinh):
    for tien_to in TIEN_TO_TINH:
        if ten_tinh.lower().startswith(tien_to.lower()):
            # Chỉ bỏ một tiền tố, bóc lặp lại dễ cắt nhầm.
            return ten_tinh[len(tien_to):]
    return ten_tinh


def bo_hau_to_tinh(ten_tinh):
    for hau_to in HAU_TO_TINH:
        if ten_tinh.endswith(hau_to):
            return ten_tinh[: -len(hau_to)]
    return ten_tinh


def tao_khoa_tra_tinh(ten_tinh):
    # NFD tách chữ có dấu thành chữ gốc và dấu, sau đó bỏ phần dấu.
    ten_tach_dau = unicodedata.normalize("NFD", ten_tinh)
    ky_tu_khong_dau = []
    for ky_tu in ten_tach_dau:
        if unicodedata.category(ky_tu) != "Mn":
            ky_tu_khong_dau.append(ky_tu)
    ten_khong_dau = "".join(ky_tu_khong_dau)

    # "đ" không tách được bằng NFD nên đổi tay; "Ð" (Eth) trong dữ liệu thật bị bỏ ở bước lọc a-z.
    ten_doi_d = ten_khong_dau.replace("đ", "d").replace("Đ", "d")
    ten_viet_thuong = ten_doi_d.lower()
    return re.sub(r"[^a-z]", "", ten_viet_thuong)


def normalize_province(tinh_goc, bang_tinh):
    """Chuẩn hóa tên tỉnh về tên chuẩn; không tra được thì trả "Khác" và ghi log."""
    if pd.isna(tinh_goc):
        logger.warning("Tỉnh rỗng, gán '%s'", TINH_KHONG_XAC_DINH)
        return TINH_KHONG_XAC_DINH

    # Đưa về NFC trước khi so tiền tố vì chuỗi chép từ web đôi khi ở dạng tách dấu.
    tinh_nfc = unicodedata.normalize("NFC", tinh_goc.strip())
    tinh_bo_tien_to = bo_tien_to_tinh(tinh_nfc)
    tinh_bo_hau_to = bo_hau_to_tinh(tinh_bo_tien_to)
    khoa_tra = tao_khoa_tra_tinh(tinh_bo_hau_to)

    # Tên không có chữ Latin ra khóa rỗng nên tra bằng chuỗi gốc.
    if khoa_tra == "":
        khoa_tra = tinh_nfc

    if khoa_tra in bang_tinh:
        return bang_tinh[khoa_tra]

    logger.warning("Không tra được tỉnh '%s' (khóa '%s'), gán '%s'",
                   tinh_goc, khoa_tra, TINH_KHONG_XAC_DINH)
    return TINH_KHONG_XAC_DINH


def lam_sach_o_sku(cot_sku):
    sku_da_strip = cot_sku.str.strip()
    return sku_da_strip.mask(sku_da_strip == "")


def dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai):
    """Dựng cột sku Shopee theo chuỗi dự phòng: SKU sản phẩm, SKU phân loại, rồi "UNKNOWN"."""
    # Chỗ duy nhất điền giá trị cho sku rỗng; trước đó NaN phải còn là NaN.
    sku_sau_du_phong = sku_san_pham.fillna(sku_phan_loai)
    return sku_sau_du_phong.fillna(SKU_KHONG_XAC_DINH)


def tra_ma_san_pham(cot_sku, bang_san_pham):
    """SKU không có trong bảng thì để NaN và ghi log, không làm hỏng cả lượt nạp."""
    ma_san_pham = cot_sku.map(bang_san_pham)

    # Log theo từng SKU lạ chứ không theo từng dòng.
    sku_khong_tra_duoc = cot_sku[ma_san_pham.isna()].unique()
    for sku in sku_khong_tra_duoc:
        logger.warning("SKU '%s' không có trong product_map.json, product_code = NULL", sku)
    return ma_san_pham


def xac_dinh_affiliate(cot_nguon_doanh_thu, nguon_tu_ban):
    """Tính cờ is_affiliate từ cột `Nguồn Doanh Thu` của file."""
    nguon_da_strip = cot_nguon_doanh_thu.str.strip()
    co_gia_tri = nguon_da_strip.notna() & (nguon_da_strip != "")
    khac_tu_ban = nguon_da_strip != nguon_tu_ban
    return co_gia_tri & khac_tu_ban


def tinh_nmv_sau_thue(cot_nmv):
    """NMV sau thuế = round(nmv / 1.08)."""
    nmv_chia_vat = cot_nmv / HE_SO_VAT
    # Làm tròn bằng round chứ không int(), vì int() cắt phần lẻ: 925,93 phải ra 926.
    return nmv_chia_vat.round(0)
