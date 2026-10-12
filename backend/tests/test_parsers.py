"""Test 2 parser đường file trên 2 file mẫu ẩn danh — đối chiếu số liệu SPEC §17, §3.3.

Mọi con số ở đây chép NGUYÊN từ SPEC. Test fail thì sửa parser, KHÔNG sửa số
(§17.2, §17.7). Kết quả parser là "đáp án" cho test khứ hồi của đường API
(§21.5), nên đây là bộ test quan trọng nhất của đường file.

Một số test đọc thẳng CSV (cột 34, cột 50, cột công thức Lark) để kiểm chéo:
các cột đó parser không đọc, nên là nguồn độc lập với code đang được kiểm.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.etl import cleaners, shopee_parser, tiktok_parser
from app.etl.loader import COT_CHUAN_SHOPEE, COT_CHUAN_TIKTOK

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"


@pytest.fixture(scope="module")
def ket_qua_shopee():
    """(bảng chuẩn, bộ đếm) của file Shopee, chạy parser một lần cho cả module."""
    return shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, "Shop C")


@pytest.fixture(scope="module")
def ket_qua_tiktok():
    """(bảng chuẩn, bộ đếm) của file TikTok."""
    return tiktok_parser.chuan_hoa_file_tiktok(FILE_TIKTOK)


@pytest.fixture(scope="module")
def shopee(ket_qua_shopee):
    return ket_qua_shopee[0]


@pytest.fixture(scope="module")
def tiktok(ket_qua_tiktok):
    return ket_qua_tiktok[0]


def loc_dong_tinh_doanh_thu(bang):
    """Bộ lọc doanh thu §7.1: bỏ đơn hủy và dòng hoàn, GIỮ unknown."""
    khong_huy = bang["order_status"] != "cancelled"
    khong_hoan = ~bang["is_returned"]
    return bang[khong_huy & khong_hoan]


def doc_cot_tien_tu_csv(duong_dan, ten_cot):
    """Đọc thẳng 1 cột tiền từ CSV (đúng tên gốc, phân biệt hoa/thường), đổi sang số."""
    bang = pd.read_csv(duong_dan, usecols=[ten_cot], dtype=str, encoding="utf-8-sig")
    return cleaners.doi_chuoi_tien_sang_so(bang[ten_cot])


# ---------- Hợp đồng đầu ra (loader.py) ----------

def test_dung_va_du_cot_chuan(shopee, tiktok):
    assert list(shopee.columns) == COT_CHUAN_SHOPEE
    assert list(tiktok.columns) == COT_CHUAN_TIKTOK
    assert (shopee["data_source"] == "file").all()
    assert (tiktok["data_source"] == "file").all()


def test_gia_tri_rieng_cua_tung_san(shopee, tiktok):
    assert (shopee["shop_name"] == "Shop C").all()
    assert set(tiktok["shop_name"]) == {"Shop A", "Shop B"}
    # Đường file Shopee: NMV chính xác, không tạm tính; không có giờ tạo đơn.
    assert not shopee["nmv_is_provisional"].any()
    assert shopee["order_created_at"].isna().all()
    assert tiktok["order_created_at"].notna().all()


def test_giu_dung_thu_tu_dong_cua_file(shopee, tiktok):
    # Các test đọc thẳng CSV bên dưới ghép theo vị trí dòng — cần điều này đúng.
    assert shopee.index.equals(pd.RangeIndex(1774))
    assert tiktok.index.equals(pd.RangeIndex(7540))


def test_khong_doc_cot_pii(tmp_path):
    # File thật có cột PII (bản ẩn danh thì không) — parser phải bỏ qua.
    bang_mau = pd.read_csv(FILE_SHOPEE, dtype=str, encoding="utf-8-sig", nrows=3)
    bang_mau["Số điện thoại"] = "0900000000"
    duong_dan = tmp_path / "shopee_co_pii.csv"
    bang_mau.to_csv(duong_dan, index=False, encoding="utf-8-sig")

    bang_doc = shopee_parser.doc_csv_shopee(duong_dan)
    assert "Số điện thoại" not in bang_doc.columns
    assert set(bang_doc.columns) == set(shopee_parser.COT_CAN_DOC)


# ---------- Cấu trúc (SPEC §17.1, §4) ----------

@pytest.mark.parametrize("san, so_dong, so_don, so_don_nhieu_dong, so_sku, so_ma_sp", [
    ("shopee", 1774, 1761, 13, 19, 10),
    ("tiktok", 7540, 7526, 14, 33, 13),
])
def test_cau_truc(request, san, so_dong, so_don, so_don_nhieu_dong, so_sku, so_ma_sp):
    bang = request.getfixturevalue(san)
    assert len(bang) == so_dong
    assert bang["order_id"].nunique() == so_don
    assert (bang["order_id"].value_counts() > 1).sum() == so_don_nhieu_dong
    assert bang.duplicated(["order_id", "sku"]).sum() == 0
    assert bang["sku"].isna().sum() == 0
    assert bang["sku"].nunique() == so_sku
    assert bang["product_code"].isna().sum() == 0
    assert bang["product_code"].nunique() == so_ma_sp


def test_khoang_thoi_gian(shopee, tiktok):
    assert shopee["order_date"].min() == pd.Timestamp("2026-07-01")
    assert shopee["order_date"].max() == pd.Timestamp("2026-08-16")
    assert tiktok["order_date"].min() == pd.Timestamp("2026-01-01")
    assert tiktok["order_date"].max() == pd.Timestamp("2026-08-23")


def test_dong_huy_va_dong_hoan(shopee, tiktok):
    assert (shopee["order_status"] == "cancelled").sum() == 544
    assert (tiktok["order_status"] == "cancelled").sum() == 2178
    assert shopee["is_returned"].sum() == 56
    assert tiktok["is_returned"].sum() == 139
    # Shopee: returned_quantity khớp is_returned. TikTok: KHÔNG khớp (§3.2) —
    # vì vậy is_returned của TikTok lấy từ Cancelation/Return Type.
    assert (shopee["returned_quantity"] > 0).sum() == 56
    assert (tiktok["returned_quantity"] > 0).sum() == 2308


# ---------- Phân bố trạng thái (SPEC §17.6) ----------

def test_phan_bo_trang_thai(shopee, tiktok):
    assert shopee["order_status"].value_counts().to_dict() == {
        "completed": 750,
        "cancelled": 544,
        "shipping": 172,
        "delivered": 154,
        "pending": 135,
        "unknown": 19,
    }
    assert tiktok["order_status"].value_counts().to_dict() == {
        "completed": 4689,
        "cancelled": 2178,
        "shipping": 616,
        "pending": 57,
    }


# ---------- KPI theo §7.1 (SPEC §17.2) — assertion quan trọng nhất ----------

@pytest.mark.parametrize("san, doanh_thu, so_don, so_san_pham, aov", [
    ("shopee", 1_908_961_059, 1165, 1182, 1_638_593),
    ("tiktok", 7_538_502_584, 5211, 5292, 1_446_652),
])
def test_kpi_doanh_thu(request, san, doanh_thu, so_don, so_san_pham, aov):
    hop_le = loc_dong_tinh_doanh_thu(request.getfixturevalue(san))
    tong_doanh_thu = hop_le["nmv_after_tax"].sum()
    so_don_hop_le = hop_le["order_id"].nunique()

    assert tong_doanh_thu == doanh_thu
    assert so_don_hop_le == so_don
    assert hop_le["quantity"].sum() == so_san_pham
    assert round(tong_doanh_thu / so_don_hop_le) == aov


def test_doanh_thu_neu_khong_loc(shopee, tiktok):
    # Đối chiếu mức thổi phồng: +54,9% và +44,6% (§7.1).
    assert shopee["nmv_after_tax"].sum() == 2_956_837_916
    assert tiktok["nmv_after_tax"].sum() == 10_897_040_276
    nmv_don_huy_tiktok = tiktok.loc[tiktok["order_status"] == "cancelled", "nmv_after_tax"].sum()
    assert nmv_don_huy_tiktok == 3_156_537_517


def test_unknown_duoc_tinh_doanh_thu(shopee):
    # Loại nhầm unknown thì Shopee hụt đúng số này (§17.2 nguyên nhân 4).
    hop_le = loc_dong_tinh_doanh_thu(shopee)
    dong_unknown = hop_le[hop_le["order_status"] == "unknown"]
    assert len(dong_unknown) == 19
    assert dong_unknown["nmv_after_tax"].sum() == 29_814_813


# ---------- Doanh thu theo tháng (SPEC §17.3) ----------

def doanh_thu_theo_thang(bang):
    """{"YYYY-MM": doanh thu §7.1} của một bảng chuẩn."""
    hop_le = loc_dong_tinh_doanh_thu(bang)
    thang = hop_le["order_date"].dt.strftime("%Y-%m")
    tong_theo_thang = hop_le.groupby(thang)["nmv_after_tax"].sum()
    return tong_theo_thang.to_dict()


def test_doanh_thu_theo_thang_shopee(shopee):
    assert doanh_thu_theo_thang(shopee) == {
        "2026-07": 1_068_925_905,
        "2026-08": 840_035_154,
    }


def test_doanh_thu_theo_thang_tiktok(tiktok):
    assert doanh_thu_theo_thang(tiktok) == {
        "2026-01": 963_328_583,
        "2026-02": 1_056_998_596,
        "2026-03": 1_459_153_482,
        "2026-04": 1_014_538_449,
        "2026-05": 800_122_017,
        "2026-06": 566_274_001,
        "2026-07": 814_595_996,
        "2026-08": 863_491_460,
    }


# ---------- Bộ đếm chất lượng (SPEC §3.3) ----------

def test_bo_dem_shopee(ket_qua_shopee):
    assert ket_qua_shopee[1] == {
        "rows_sku_fallback": 6,
        "rows_sku_unknown": 0,
        "rows_status_unknown": 19,
        "rows_province_unmapped": 0,
        "rows_product_unmapped": 0,
    }


def test_bo_dem_tiktok(ket_qua_tiktok):
    assert ket_qua_tiktok[1] == {
        "rows_sku_fallback": 0,
        "rows_sku_unknown": 0,
        "rows_status_unknown": 0,
        "rows_province_unmapped": 0,
        "rows_product_unmapped": 0,
    }


# ---------- SKU Shopee: kiểm nội dung, không chỉ đếm (SPEC §17.7b) ----------

def test_sku_shopee_khong_co_chuoi_gia_va_co_du_phong(shopee):
    tap_sku = set(shopee["sku"])
    # 19 có 2 đường ra: đúng (có "M21 live") và sai (có chuỗi giả "nan").
    assert "nan" not in tap_sku
    assert "<NA>" not in tap_sku
    assert "UNKNOWN" not in tap_sku
    assert "M21 live" in tap_sku
    assert len(tap_sku) == 19


def test_chuoi_du_phong_sku_du_3_nhanh():
    sku_san_pham = shopee_parser.lam_sach_o_sku(pd.Series(["M15 ", np.nan, "  ", np.nan]))
    sku_phan_loai = shopee_parser.lam_sach_o_sku(pd.Series(["M5_2C", "M21 live", "M24", np.nan]))
    sku = shopee_parser.dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)
    # Ô chỉ có khoảng trắng cũng coi là rỗng → chuyển sang cột dự phòng.
    assert sku.tolist() == ["M15", "M21 live", "M24", "UNKNOWN"]


def test_sku_tiktok_rong_thanh_unknown():
    sku = tiktok_parser.tao_cot_sku(pd.Series(["'BU01'", np.nan, "''"]))
    assert sku.tolist() == ["BU01", "UNKNOWN", "UNKNOWN"]


# ---------- NMV tự tính (SPEC §7.5, §17.8) ----------

def test_22_dong_shopee_so_luong_lon_hon_1_nmv_bang_tien_nguoi_mua_tra(shopee):
    # Cột 34 — chữ N HOA, mức dòng. Đọc thẳng CSV vì parser không đọc cột này.
    tien_nguoi_mua_tra = doc_cot_tien_tu_csv(FILE_SHOPEE, "Tổng số tiền Người mua thanh toán")
    dong_nhieu_san_pham = shopee["quantity"] > 1

    assert dong_nhieu_san_pham.sum() == 22
    nmv_cac_dong = shopee.loc[dong_nhieu_san_pham, "nmv"]
    assert (nmv_cac_dong == tien_nguoi_mua_tra[dong_nhieu_san_pham]).all()


def test_nmv_sau_thue_khop_cot_lark_tru_dung_22_dong_loi(shopee, tiktok):
    # Shopee: Lark sai đúng ở 22 dòng số lượng > 1, khớp 1.752 dòng còn lại.
    lark_shopee = doc_cot_tien_tu_csv(FILE_SHOPEE, "NMV Sau Thuế")
    lech_shopee = shopee["nmv_after_tax"] != lark_shopee
    assert lech_shopee.sum() == 22
    assert lech_shopee.equals(shopee["quantity"] > 1)

    # TikTok: khớp 7.540/7.540.
    lark_tiktok = doc_cot_tien_tu_csv(FILE_TIKTOK, "NMV Sau Thuế")
    assert (tiktok["nmv_after_tax"] == lark_tiktok).all()


# ---------- Kiểm chéo độc lập bằng cột 50 (SPEC §3.1, §17.5) ----------

def test_cot_50_bang_0_o_591_dong(shopee):
    # Cột 50 — chữ n thường, mức đơn. Đã bỏ khỏi CSDL, chỉ đọc ở đây.
    tien_cot_50 = doc_cot_tien_tu_csv(FILE_SHOPEE, "Tổng số tiền người mua thanh toán")
    bang_0 = tien_cot_50 == 0
    assert bang_0.sum() == 591

    # 591 = toàn bộ 544 dòng hủy + 47 dòng hoàn (bộ lọc §7.1 loại 544 + 56).
    dong_huy = shopee["order_status"] == "cancelled"
    assert bang_0[dong_huy].all()
    bang_0_khong_huy = bang_0 & ~dong_huy
    assert bang_0_khong_huy.sum() == 47
    assert shopee.loc[bang_0_khong_huy, "is_returned"].all()


# ---------- Khung giờ và affiliate (SPEC §17.8, §21.4) ----------

def test_khung_gio_tiktok_tu_tinh_khop_cot_lark(tiktok):
    bang = pd.read_csv(FILE_TIKTOK, usecols=["Khung Giờ Ra Đơn"], dtype=str, encoding="utf-8-sig")
    assert (tiktok["hour_bucket"] == bang["Khung Giờ Ra Đơn"]).all()


def test_is_affiliate(shopee, tiktok):
    assert shopee["is_affiliate"].sum() == 771
    assert (~shopee["is_affiliate"]).sum() == 1003
    assert tiktok["is_affiliate"].sum() == 4297
    assert (~tiktok["is_affiliate"]).sum() == 3243
