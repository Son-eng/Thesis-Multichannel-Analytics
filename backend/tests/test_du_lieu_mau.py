"""Test trên 2 file mẫu ẩn danh — thay cho các phép đối chiếu dữ liệu thật ở bước 3.

Ở bước 3, các phép đối chiếu (phân bố trạng thái, bảng tỉnh phủ đủ, bảng sản
phẩm phủ đủ) phải chạy tay trên file gốc có PII, nên chỉ ghi được kết quả vào
TRACKLOG. Nay đã có bản ẩn danh trong repo (bước 4) → chuyển thành test, chạy
được trên máy hội đồng mà không cần file gốc.

File được đọc bằng dtype=str và để pandas tự đổi ô rỗng thành NaN — đúng kiểu
dữ liệu mà các hàm trong cleaners.py / status_mapper.py chờ nhận.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.etl import cleaners, shopee_parser
from app.etl.status_mapper import gom_nhom_trang_thai_file

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"

# Chép lại từ SPEC §5.1, §5.2 — CỐ Ý không import từ scripts/anonymize_samples.py:
# nếu danh sách trong script bị sửa sai thì test này vẫn bắt được.
COT_PII_SHOPEE = [
    "Người Mua", "Tên Người nhận", "Số điện thoại", "Địa chỉ nhận hàng", "Địa chỉ",
    "Email", "Họ & Tên", "Mã số thuế", "TP / Quận / Huyện", "Quận", "Ghi chú",
    "Nhận xét từ Người mua", "Mã vận đơn", "Mã Kiện Hàng",
]
COT_PII_TIKTOK = [
    "Buyer Username", "Recipient", "Phone #", "Detail Address",
    "Additional address information", "District", "Commune", "Buyer Message",
    "Seller Note", "Tracking ID", "Package ID", "Creator Handle",
    "Creator Username", "Checked Marked by",
]

# Các cột chữ được phép khác file gốc vì đã thay tên thương hiệu / tên gian hàng.
# Cũng chép tay, không import từ script — cùng lý do với danh sách PII.
COT_DUOC_THAY_TEN = {
    "shopee": ["Tên sản phẩm", "Tên phân loại hàng"],
    "tiktok": ["Product Name", "Variation", "Shop"],
}

# (file gốc có PII, file ẩn danh, danh sách PII) của từng sàn.
FILE_TUNG_SAN = {
    "shopee": ("Shopee Tracking_Order BOS (1).csv", "shopee_orders_anonymized.csv", COT_PII_SHOPEE),
    "tiktok": ("TikTok Tracking_Order.csv", "tiktok_orders_anonymized.csv", COT_PII_TIKTOK),
}


def doc_nguyen_van(ten_file):
    """Đọc CSV giữ đúng từng ô như trong file (ô rỗng là "", không phải NaN).

    Cần riêng cho phép so với file gốc: đọc mặc định thì "NA", "null" cũng
    thành NaN, so sánh sẽ bỏ sót khác biệt.
    """
    return pd.read_csv(THU_MUC_MAU / ten_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def shopee():
    """File Shopee ẩn danh, đọc một lần cho cả module."""
    return pd.read_csv(THU_MUC_MAU / "shopee_orders_anonymized.csv",
                       dtype=str, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def tiktok():
    """File TikTok ẩn danh, đọc một lần cho cả module."""
    return pd.read_csv(THU_MUC_MAU / "tiktok_orders_anonymized.csv",
                       dtype=str, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def bang_tinh():
    """Bảng tỉnh thật (province_map.json)."""
    return cleaners.doc_file_anh_xa("province_map.json")


@pytest.fixture(scope="module")
def bang_san_pham():
    """Bảng sản phẩm thật (product_map.json)."""
    return cleaners.doc_file_anh_xa("product_map.json")


# ---------- Cấu trúc file (SPEC §15.1) ----------

def test_so_dong_va_so_cot(shopee, tiktok):
    assert shopee.shape == (1774, 64)
    assert tiktok.shape == (7540, 53)


def test_khong_con_cot_pii(shopee, tiktok):
    assert [cot for cot in COT_PII_SHOPEE if cot in shopee.columns] == []
    assert [cot for cot in COT_PII_TIKTOK if cot in tiktok.columns] == []


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_khong_cot_nao_con_ten_thuong_hieu(san):
    # Khóa luận mục 1.3.2 cam kết không nêu tên doanh nghiệp; repo nộp cho khoa.
    # Kiểm MỌI cột, không chỉ 5 cột đã thay — tên lọt ở cột khác cũng phải bắt.
    _, ten_file_an_danh, _ = FILE_TUNG_SAN[san]
    bang = doc_nguyen_van(ten_file_an_danh)

    cot_con_ten = []
    for ten_cot in bang.columns:
        if bang[ten_cot].str.contains("Doanh nghiệp A", case=False, regex=False).any():
            cot_con_ten.append(ten_cot)
    assert cot_con_ten == []


def test_ten_gian_hang_tiktok_da_thay(tiktok):
    assert tiktok["Shop"].value_counts().to_dict() == {"Shop A": 5377, "Shop B": 2163}


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_cot_khong_thay_ten_giong_het_file_goc(san):
    # Cần file gốc có PII — chỉ có trên máy sinh viên. Máy hội đồng không có
    # file gốc thì bỏ qua (khác với file ẩn danh: thiếu thì báo lỗi).
    ten_file_goc, ten_file_an_danh, danh_sach_pii = FILE_TUNG_SAN[san]
    if not (THU_MUC_MAU / ten_file_goc).exists():
        pytest.skip(f"Không có file gốc {ten_file_goc} (bình thường trên máy khác)")

    goc_bo_pii = doc_nguyen_van(ten_file_goc).drop(columns=danh_sach_pii)
    an_danh = doc_nguyen_van(ten_file_an_danh)
    assert list(an_danh.columns) == list(goc_bo_pii.columns)

    # Thay tên chỉ được đụng vào đúng các cột trong danh sách.
    goc_khong_tinh_cot_thay = goc_bo_pii.drop(columns=COT_DUOC_THAY_TEN[san])
    an_danh_khong_tinh_cot_thay = an_danh.drop(columns=COT_DUOC_THAY_TEN[san])
    assert an_danh_khong_tinh_cot_thay.equals(goc_khong_tinh_cot_thay)


def test_du_lieu_ban_con_nguyen(shopee, tiktok):
    # Bản ẩn danh mà bị "làm sạch luôn" thì mọi test parser sau này pass giả.
    assert shopee["SKU sản phẩm"].isna().sum() == 6
    assert shopee["Trạng Thái Đơn Hàng"].isna().sum() == 19
    assert shopee["Giá gốc"].str.contains("e+", regex=False).all()
    assert tiktok["Province"].nunique() == 209
    assert (tiktok["Seller SKU"] == "M15''").any()


# ---------- Phân bố trạng thái (SPEC §17.6) ----------

def test_phan_bo_trang_thai_shopee(shopee):
    nhom = shopee["Trạng Thái Đơn Hàng"].apply(gom_nhom_trang_thai_file, args=("shopee",))
    assert nhom.value_counts().to_dict() == {
        "completed": 750,
        "cancelled": 544,
        "shipping": 172,
        "delivered": 154,
        "pending": 135,
        "unknown": 19,
    }


def test_phan_bo_trang_thai_tiktok(tiktok):
    nhom = tiktok["Order Status"].apply(gom_nhom_trang_thai_file, args=("tiktok",))
    assert nhom.value_counts().to_dict() == {
        "completed": 4689,
        "cancelled": 2178,
        "shipping": 616,
        "pending": 57,
    }


# ---------- Tỉnh (SPEC §5.3, §17.5) ----------

def test_tinh_khong_dong_nao_ve_khac_va_dung_so_tinh(shopee, tiktok, bang_tinh):
    tinh_shopee = shopee["Tỉnh/Thành phố"].apply(cleaners.normalize_province, args=(bang_tinh,))
    tinh_tiktok = tiktok["Province"].apply(cleaners.normalize_province, args=(bang_tinh,))

    assert (tinh_shopee == "Khác").sum() == 0
    assert (tinh_tiktok == "Khác").sum() == 0
    assert tinh_shopee.nunique() == 35
    assert tinh_tiktok.nunique() == 63

    tinh_chung = set(tinh_shopee) & set(tinh_tiktok)
    assert len(tinh_chung) == 35


# ---------- Mã sản phẩm (SPEC §5.4) ----------

def test_product_map_phu_du_sku_shopee(shopee, bang_san_pham):
    # Gọi đúng chuỗi dự phòng SKU của parser (§5.1), không dựng lại trong test.
    # Nội dung tập SKU (§17.7b: không "nan", có "M21 live") kiểm ở test_parsers.py.
    sku_san_pham = shopee_parser.lam_sach_o_sku(shopee["SKU sản phẩm"])
    sku_phan_loai = shopee_parser.lam_sach_o_sku(shopee["SKU phân loại hàng"])
    sku = shopee_parser.dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)

    tap_sku = set(sku)
    assert len(tap_sku) == 19
    assert tap_sku - set(bang_san_pham["shopee"]) == set()
    ma_san_pham = sku.map(bang_san_pham["shopee"])
    assert ma_san_pham.isna().sum() == 0
    assert ma_san_pham.nunique() == 10


def test_product_map_phu_du_sku_tiktok(tiktok, bang_san_pham):
    sku = cleaners.lam_sach_seller_sku_tiktok(tiktok["Seller SKU"])

    tap_sku = set(sku)
    assert len(tap_sku) == 33
    assert tap_sku - set(bang_san_pham["tiktok"]) == set()

    ma_san_pham = sku.map(bang_san_pham["tiktok"])
    assert ma_san_pham.isna().sum() == 0
    assert ma_san_pham.nunique() == 13
