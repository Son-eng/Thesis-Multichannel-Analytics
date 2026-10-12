"""Test cho cleaners.py — tập trung vào các bẫy đã gặp ở SPEC §2.3, §5.2, §5.3, §17.7.

Phần tra bảng tỉnh ở đây dùng bảng nhỏ tự tạo để kiểm THUẬT TOÁN. Nội dung
bảng thật (province_map.json) được kiểm ở test_mappings.py.
"""

import unicodedata

import numpy as np
import pandas as pd
import pytest

from app.etl import cleaners


# ---------- Đổi chuỗi tiền sang số (SPEC §2.3, §17.7b-c) ----------

def test_tien_co_dau_phay_ngan_nghin():
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["1,415,000", "520,000"]))
    assert ket_qua.tolist() == [1415000, 520000]


def test_tien_ky_hieu_khoa_hoc():
    # int("2.28e+06") lỗi, regex bóc chữ số ra 228 — phải ra 2.280.000.
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["2.28e+06", "1.438217e+06"]))
    assert ket_qua.tolist() == [2280000, 1438217]


def test_tien_nan_va_rong_giu_nguyen_nan():
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["1,000", np.nan, "", "  "]))
    assert ket_qua.iloc[0] == 1000
    assert ket_qua.iloc[1:].isna().all()
    # Bẫy pandas 2.2: không được có chuỗi "nan" nào lọt ra (§17.7b).
    assert "nan" not in ket_qua.astype(object).tolist()


def test_tien_cot_lan_so_va_chuoi_khong_mat_so():
    # Cột object lẫn kiểu: .str.replace thuần sẽ biến 2.5 thành NaN.
    cot_lan = pd.Series(["1,000", 2280000.0, np.nan], dtype=object)
    ket_qua = cleaners.doi_chuoi_tien_sang_so(cot_lan)
    assert ket_qua.iloc[0] == 1000
    assert ket_qua.iloc[1] == 2280000
    assert pd.isna(ket_qua.iloc[2])


def test_tien_chuoi_rac_bao_loi():
    with pytest.raises(ValueError):
        cleaners.doi_chuoi_tien_sang_so(pd.Series(["abc"]))


# ---------- Đọc ngày (SPEC §2.1, §17.7a) ----------

def test_ngay_shopee():
    ket_qua = cleaners.doc_ngay_shopee(pd.Series(["2026/07/01", "2026/08/23"]))
    assert ket_qua.tolist() == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-08-23")]


def test_thoi_gian_tiktok():
    ket_qua = cleaners.doc_thoi_gian_tiktok(pd.Series(["01/01/2026 10:39:24"]))
    assert ket_qua.iloc[0] == pd.Timestamp("2026-01-01 10:39:24")


def test_thoi_gian_tiktok_so_sanh_theo_ngay_khong_theo_chuoi():
    # So chuỗi thì "31/07/2026" > "23/08/2026" vì '3' > '2' (§17.7a).
    ket_qua = cleaners.doc_thoi_gian_tiktok(
        pd.Series(["31/07/2026 08:00:00", "23/08/2026 08:00:00"])
    )
    assert ket_qua.max() == pd.Timestamp("2026-08-23 08:00:00")


def test_timestamp_api_sang_gio_vn():
    # 1782864000 = 2026-07-01 00:00:00 UTC → 07:00 giờ VN.
    ket_qua = cleaners.doi_timestamp_api_sang_gio_vn(pd.Series([1782864000]))
    assert ket_qua.iloc[0] == pd.Timestamp("2026-07-01 07:00:00")


@pytest.mark.parametrize(
    "timestamp, gio_vn_mong_doi",
    [
        # Đơn tạo 0h30 sáng 01/07 giờ VN = 17h30 ngày 30/06 theo UTC.
        (1782840600, "2026-07-01 00:30:00"),
        # Đơn tạo 6h59m59s sáng 01/07 giờ VN = 23h59m59s ngày 30/06 theo UTC.
        (1782863999, "2026-07-01 06:59:59"),
    ],
)
def test_timestamp_api_don_0h_7h_sang_khong_lui_ngay(timestamp, gio_vn_mong_doi):
    # Dùng UTC thì các đơn này bị tính sang ngày 30/06 — bẫy §18.3.
    ket_qua = cleaners.doi_timestamp_api_sang_gio_vn(pd.Series([timestamp]))
    assert ket_qua.iloc[0] == pd.Timestamp(gio_vn_mong_doi)
    assert ket_qua.dt.date.iloc[0] == pd.Timestamp("2026-07-01").date()


# ---------- Khung giờ (SPEC §2.2) ----------

def test_khung_gio():
    thoi_gian = pd.Series(pd.to_datetime(["2026-07-01 00:30:00", "2026-07-01 23:59:59",
                                          "2026-07-01 07:00:00"]))
    ket_qua = cleaners.tinh_khung_gio(thoi_gian)
    assert ket_qua.tolist() == ["0H - 1H", "23H - 24H", "7H - 8H"]


def test_khung_gio_nat_khong_thanh_chuoi_rac():
    thoi_gian = pd.Series(pd.to_datetime(["2026-07-01 07:15:00", None]))
    ket_qua = cleaners.tinh_khung_gio(thoi_gian)
    assert ket_qua.iloc[0] == "7H - 8H"   # không phải "7.0H - 8.0H"
    assert pd.isna(ket_qua.iloc[1])


# ---------- Seller SKU TikTok (SPEC §5.2) ----------

def test_sku_dau_nhay_hai_dau():
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["M15''", "BU01'", " 'M5' "]))
    assert ket_qua.tolist() == ["M15", "BU01", "M5"]


def test_sku_dau_nhay_o_giua_giu_nguyen():
    # Chủ ý KHÔNG dùng replace (§5.2): nháy ở giữa được giữ để truy vết.
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["BU01' + B3", "M15'_Live"]))
    assert ket_qua.tolist() == ["BU01' + B3", "M15'_Live"]


def test_sku_nan_giu_nguyen():
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["M5", np.nan]))
    assert pd.isna(ket_qua.iloc[1])


# ---------- Thuật toán chuẩn hóa tỉnh (SPEC §5.3), dùng bảng nhỏ ----------

BANG_TINH_MAU = {
    "angiang": "An Giang",
    "hanoi": "Hà Nội",
    "hochiminh": "Hồ Chí Minh",
    "bariavungtau": "Bà Rịa - Vũng Tàu",
    "dongthap": "Đồng Tháp",
    "aknong": "Đắk Nông",
    "Город Ханой": "Hà Nội",
}


@pytest.mark.parametrize(
    "tinh_goc, tinh_chuan",
    [
        ("An Giang", "An Giang"),
        ("Tỉnh An Giang", "An Giang"),
        ("Tinh An Giang", "An Giang"),            # tiền tố không dấu (chốt 12/10)
        ("Thanh pho Ha Noi", "Hà Nội"),           # tiền tố không dấu (chốt 12/10)
        ("Thành Phố Hà Nội", "Hà Nội"),
        ("Phố Hà Nội", "Hà Nội"),
        ("Ha Noi City", "Hà Nội"),
        ("TP. Hồ Chí Minh", "Hồ Chí Minh"),
        ("Ho Chi Minh City", "Hồ Chí Minh"),
        ("Ba Ria– Vung Tau", "Bà Rịa - Vũng Tàu"),  # dấu gạch en-dash
        ("Bà Rịa-Vũng Tàu", "Bà Rịa - Vũng Tàu"),
        ("Province de Dong Thap", "Đồng Tháp"),
        ("Ðắk Nông", "Đắk Nông"),                  # "Ð" Iceland, không phải "Đ"
        ("Город Ханой", "Hà Nội"),                 # khóa rỗng → tra chuỗi gốc
    ],
)
def test_tinh_thuat_toan(tinh_goc, tinh_chuan):
    assert cleaners.normalize_province(tinh_goc, BANG_TINH_MAU) == tinh_chuan


def test_tinh_dang_tach_dau_van_bo_duoc_tien_to():
    # Giả lập chuỗi chép từ web/Excel ở dạng tách dấu (NFD).
    tinh_tach_dau = unicodedata.normalize("NFD", "Tỉnh An Giang")
    assert cleaners.normalize_province(tinh_tach_dau, BANG_TINH_MAU) == "An Giang"


def test_tinh_khong_khop_ve_khac_va_ghi_log(caplog):
    assert cleaners.normalize_province("Atlantis", BANG_TINH_MAU) == "Khác"
    assert "Atlantis" in caplog.text


def test_tinh_rong_ve_khac():
    assert cleaners.normalize_province(np.nan, BANG_TINH_MAU) == "Khác"


# ---------- Mã sản phẩm (SPEC §5.4) ----------

def test_ma_san_pham_tra_dung_va_sku_la_thanh_null_co_log(caplog):
    bang_mau = {"M3 pro": "M3 Plus", "M15": "M15"}
    ket_qua = cleaners.tra_ma_san_pham(pd.Series(["M3 pro", "M15", "X99", "X99"]), bang_mau)

    assert ket_qua.iloc[:2].tolist() == ["M3 Plus", "M15"]
    assert ket_qua.iloc[2:].isna().all()
    # SKU lạ lặp 2 dòng nhưng chỉ log 1 lần.
    assert caplog.text.count("X99") == 1


# ---------- NMV sau thuế (SPEC §7.5, §17.8) ----------

def test_nmv_sau_thue_lam_tron_khong_cat():
    # 1000 / 1.08 = 925,93: int() ra 925 (sai), làm tròn ra 926 (đúng).
    ket_qua = cleaners.tinh_nmv_sau_thue(pd.Series([1000, 2280000, 0]))
    assert ket_qua.tolist() == [926, 2111111, 0]


def test_nmv_sau_thue_nan_giu_nguyen():
    ket_qua = cleaners.tinh_nmv_sau_thue(pd.Series([1000, np.nan]))
    assert pd.isna(ket_qua.iloc[1])
