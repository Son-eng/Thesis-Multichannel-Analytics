import json
from pathlib import Path

import pandas as pd
import pytest

from app.etl import cleaners, shopee_parser
from app.etl.status_mapper import gom_nhom_trang_thai_file

THU_MUC_GOC = Path(__file__).resolve().parents[2]
THU_MUC_MAU = THU_MUC_GOC / "data" / "samples"
DUONG_DAN_TEN_THAT = THU_MUC_GOC / "scripts" / "ten_that.local.json"

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

# Cột chữ được phép khác file gốc vì đã thay tên thương hiệu và tên gian hàng.
COT_DUOC_THAY_TEN = {
    "shopee": ["Tên sản phẩm", "Tên phân loại hàng"],
    "tiktok": ["Product Name", "Variation", "Shop"],
}

FILE_TUNG_SAN = {
    "shopee": ("Shopee Tracking_Order.csv", "shopee_orders_anonymized.csv", COT_PII_SHOPEE),
    "tiktok": ("TikTok Tracking_Order.csv", "tiktok_orders_anonymized.csv", COT_PII_TIKTOK),
}


def doc_nguyen_van(ten_file):
    return pd.read_csv(THU_MUC_MAU / ten_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def shopee():
    return pd.read_csv(THU_MUC_MAU / "shopee_orders_anonymized.csv",
                       dtype=str, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def tiktok():
    return pd.read_csv(THU_MUC_MAU / "tiktok_orders_anonymized.csv",
                       dtype=str, encoding="utf-8-sig")


@pytest.fixture(scope="module")
def bang_tinh():
    return cleaners.doc_file_anh_xa("province_map.json")


@pytest.fixture(scope="module")
def bang_san_pham():
    return cleaners.doc_file_anh_xa("product_map.json")


def test_so_dong_va_so_cot(shopee, tiktok):
    assert shopee.shape == (1774, 64)
    assert tiktok.shape == (7540, 53)


def test_khong_con_cot_pii(shopee, tiktok):
    assert [cot for cot in COT_PII_SHOPEE if cot in shopee.columns] == []
    assert [cot for cot in COT_PII_TIKTOK if cot in tiktok.columns] == []


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_khong_cot_nao_con_ten_that(san):
    if not DUONG_DAN_TEN_THAT.exists():
        pytest.skip(f"Không có {DUONG_DAN_TEN_THAT.name} (bình thường trên máy khác)")
    with open(DUONG_DAN_TEN_THAT, encoding="utf-8") as file_json:
        ten_that = json.load(file_json)
    danh_sach_ten_that = [ten_that["ten_thuong_hieu"]] + list(ten_that["ten_gia_gian_hang_tiktok"])

    _, ten_file_an_danh, _ = FILE_TUNG_SAN[san]
    bang = doc_nguyen_van(ten_file_an_danh)
    # Chỉ ghi tên cột, không ghi tên thật, vì thông báo lỗi của test có thể bị dán ra ngoài.
    cot_con_ten = []
    for ten_cot in bang.columns:
        for ten in danh_sach_ten_that:
            if bang[ten_cot].str.contains(ten, case=False, regex=False).any():
                cot_con_ten.append(ten_cot)
                break
    assert cot_con_ten == []


def test_ten_gian_hang_tiktok_da_thay(tiktok):
    assert tiktok["Shop"].value_counts().to_dict() == {"Shop A": 5377, "Shop B": 2163}


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_cot_khong_thay_ten_giong_het_file_goc(san):
    # Cần file gốc có dữ liệu thật, máy không có thì bỏ qua.
    ten_file_goc, ten_file_an_danh, danh_sach_pii = FILE_TUNG_SAN[san]
    if not (THU_MUC_MAU / ten_file_goc).exists():
        pytest.skip(f"Không có file gốc {ten_file_goc} (bình thường trên máy khác)")

    goc_bo_pii = doc_nguyen_van(ten_file_goc).drop(columns=danh_sach_pii)
    an_danh = doc_nguyen_van(ten_file_an_danh)
    assert list(an_danh.columns) == list(goc_bo_pii.columns)

    goc_khong_tinh_cot_thay = goc_bo_pii.drop(columns=COT_DUOC_THAY_TEN[san])
    an_danh_khong_tinh_cot_thay = an_danh.drop(columns=COT_DUOC_THAY_TEN[san])
    assert an_danh_khong_tinh_cot_thay.equals(goc_khong_tinh_cot_thay)


def test_du_lieu_ban_con_nguyen(shopee, tiktok):
    assert shopee["SKU sản phẩm"].isna().sum() == 6
    assert shopee["Trạng Thái Đơn Hàng"].isna().sum() == 19
    assert shopee["Giá gốc"].str.contains("e+", regex=False).all()
    assert tiktok["Province"].nunique() == 209
    assert (tiktok["Seller SKU"] == "M15''").any()


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


def test_tinh_khong_dong_nao_ve_khac_va_dung_so_tinh(shopee, tiktok, bang_tinh):
    tinh_shopee = shopee["Tỉnh/Thành phố"].apply(cleaners.normalize_province, args=(bang_tinh,))
    tinh_tiktok = tiktok["Province"].apply(cleaners.normalize_province, args=(bang_tinh,))

    assert (tinh_shopee == "Khác").sum() == 0
    assert (tinh_tiktok == "Khác").sum() == 0
    assert tinh_shopee.nunique() == 35
    assert tinh_tiktok.nunique() == 63

    tinh_chung = set(tinh_shopee) & set(tinh_tiktok)
    assert len(tinh_chung) == 35


def test_product_map_phu_du_sku_shopee(shopee, bang_san_pham):
    sku_san_pham = cleaners.lam_sach_o_sku(shopee["SKU sản phẩm"])
    sku_phan_loai = cleaners.lam_sach_o_sku(shopee["SKU phân loại hàng"])
    sku = cleaners.dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)

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
