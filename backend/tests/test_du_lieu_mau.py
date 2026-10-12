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

from app.etl import cleaners
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
    # Dựng tạm chuỗi dự phòng SKU của §5.1 (SKU sản phẩm → SKU phân loại hàng).
    # Bước 5 sẽ có shopee_parser làm việc này; khi đó đổi sang gọi parser.
    sku_chinh = shopee["SKU sản phẩm"].str.strip()
    sku_du_phong = shopee["SKU phân loại hàng"].str.strip()
    sku = sku_chinh.fillna(sku_du_phong)

    tap_sku = set(sku)
    # Kiểm nội dung, không chỉ đếm — con số 19 có 2 đường ra, một đúng một sai (§17.7b).
    assert "nan" not in tap_sku
    assert "M21 live" in tap_sku
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
