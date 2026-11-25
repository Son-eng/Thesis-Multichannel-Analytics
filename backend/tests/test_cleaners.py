import unicodedata

import numpy as np
import pandas as pd
import pytest

from app.etl import cleaners


def test_tien_co_dau_phay_ngan_nghin():
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["1,415,000", "520,000"]))
    assert ket_qua.tolist() == [1415000, 520000]


def test_tien_ky_hieu_khoa_hoc():
    # int("2.28e+06") lỗi, regex bóc chữ số ra 228, phải ra 2.280.000.
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["2.28e+06", "1.438217e+06"]))
    assert ket_qua.tolist() == [2280000, 1438217]


def test_tien_nan_va_rong_giu_nguyen_nan():
    ket_qua = cleaners.doi_chuoi_tien_sang_so(pd.Series(["1,000", np.nan, "", "  "]))
    assert ket_qua.iloc[0] == 1000
    assert ket_qua.iloc[1:].isna().all()
    assert "nan" not in ket_qua.astype(object).tolist()


def test_tien_cot_lan_so_va_chuoi_khong_mat_so():
    cot_lan = pd.Series(["1,000", 2280000.0, np.nan], dtype=object)
    ket_qua = cleaners.doi_chuoi_tien_sang_so(cot_lan)
    assert ket_qua.iloc[0] == 1000
    assert ket_qua.iloc[1] == 2280000
    assert pd.isna(ket_qua.iloc[2])


def test_tien_chuoi_rac_bao_loi():
    with pytest.raises(ValueError):
        cleaners.doi_chuoi_tien_sang_so(pd.Series(["abc"]))


def test_ngay_shopee():
    ket_qua = cleaners.doc_ngay_shopee(pd.Series(["2026/07/01", "2026/08/23"]))
    assert ket_qua.tolist() == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-08-23")]


def test_thoi_gian_tiktok():
    ket_qua = cleaners.doc_thoi_gian_tiktok(pd.Series(["01/01/2026 10:39:24"]))
    assert ket_qua.iloc[0] == pd.Timestamp("2026-01-01 10:39:24")


def test_thoi_gian_tiktok_so_sanh_theo_ngay_khong_theo_chuoi():
    ket_qua = cleaners.doc_thoi_gian_tiktok(
        pd.Series(["31/07/2026 08:00:00", "23/08/2026 08:00:00"])
    )
    assert ket_qua.max() == pd.Timestamp("2026-08-23 08:00:00")


def test_timestamp_api_sang_gio_vn():
    ket_qua = cleaners.doi_timestamp_api_sang_gio_vn(pd.Series([1782864000]))
    assert ket_qua.iloc[0] == pd.Timestamp("2026-07-01 07:00:00")


@pytest.mark.parametrize(
    "timestamp, gio_vn_mong_doi",
    [
        # Đơn tạo 0h30 sáng 01/07 giờ VN là 17h30 ngày 30/06 theo UTC.
        (1782840600, "2026-07-01 00:30:00"),
        (1782863999, "2026-07-01 06:59:59"),
    ],
)
def test_timestamp_api_don_0h_7h_sang_khong_lui_ngay(timestamp, gio_vn_mong_doi):
    # Dùng UTC thì các đơn này bị tính sang ngày 30/06.
    ket_qua = cleaners.doi_timestamp_api_sang_gio_vn(pd.Series([timestamp]))
    assert ket_qua.iloc[0] == pd.Timestamp(gio_vn_mong_doi)
    assert ket_qua.dt.date.iloc[0] == pd.Timestamp("2026-07-01").date()


def test_khung_gio():
    thoi_gian = pd.Series(pd.to_datetime(["2026-07-01 00:30:00", "2026-07-01 23:59:59",
                                          "2026-07-01 07:00:00"]))
    ket_qua = cleaners.tinh_khung_gio(thoi_gian)
    assert ket_qua.tolist() == ["0H - 1H", "23H - 24H", "7H - 8H"]


def test_khung_gio_nat_khong_thanh_chuoi_rac():
    thoi_gian = pd.Series(pd.to_datetime(["2026-07-01 07:15:00", None]))
    ket_qua = cleaners.tinh_khung_gio(thoi_gian)
    assert ket_qua.iloc[0] == "7H - 8H"
    assert pd.isna(ket_qua.iloc[1])


def test_sku_dau_nhay_hai_dau():
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["M15''", "BU01'", " 'M5' "]))
    assert ket_qua.tolist() == ["M15", "BU01", "M5"]


def test_sku_dau_nhay_o_giua_giu_nguyen():
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["BU01' + B3", "M15'_Live"]))
    assert ket_qua.tolist() == ["BU01' + B3", "M15'_Live"]


def test_sku_nan_giu_nguyen():
    ket_qua = cleaners.lam_sach_seller_sku_tiktok(pd.Series(["M5", np.nan]))
    assert pd.isna(ket_qua.iloc[1])


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
        ("Tinh An Giang", "An Giang"),
        ("Thanh pho Ha Noi", "Hà Nội"),
        ("Thành Phố Hà Nội", "Hà Nội"),
        ("Phố Hà Nội", "Hà Nội"),
        ("Ha Noi City", "Hà Nội"),
        ("TP. Hồ Chí Minh", "Hồ Chí Minh"),
        ("Ho Chi Minh City", "Hồ Chí Minh"),
        ("Ba Ria– Vung Tau", "Bà Rịa - Vũng Tàu"),
        ("Bà Rịa-Vũng Tàu", "Bà Rịa - Vũng Tàu"),
        ("Province de Dong Thap", "Đồng Tháp"),
        ("Ðắk Nông", "Đắk Nông"),
        ("Город Ханой", "Hà Nội"),
    ],
)
def test_tinh_thuat_toan(tinh_goc, tinh_chuan):
    assert cleaners.normalize_province(tinh_goc, BANG_TINH_MAU) == tinh_chuan


def test_tinh_dang_tach_dau_van_bo_duoc_tien_to():
    tinh_tach_dau = unicodedata.normalize("NFD", "Tỉnh An Giang")
    assert cleaners.normalize_province(tinh_tach_dau, BANG_TINH_MAU) == "An Giang"


def test_tinh_khong_khop_ve_khac_va_ghi_log(caplog):
    assert cleaners.normalize_province("Atlantis", BANG_TINH_MAU) == "Khác"
    assert "Atlantis" in caplog.text


def test_tinh_rong_ve_khac():
    assert cleaners.normalize_province(np.nan, BANG_TINH_MAU) == "Khác"


def test_ma_san_pham_tra_dung_va_sku_la_thanh_null_co_log(caplog):
    bang_mau = {"M3 pro": "M3 Plus", "M15": "M15"}
    ket_qua = cleaners.tra_ma_san_pham(pd.Series(["M3 pro", "M15", "X99", "X99"]), bang_mau)

    assert ket_qua.iloc[:2].tolist() == ["M3 Plus", "M15"]
    assert ket_qua.iloc[2:].isna().all()
    assert caplog.text.count("X99") == 1


def test_affiliate_o_rong_la_false():
    nguon = pd.Series(["AFF_Video", "ADS", np.nan, "", "  "])
    assert cleaners.xac_dinh_affiliate(nguon, "ADS").tolist() == [True, False, False, False, False]


def test_nmv_sau_thue_lam_tron_khong_cat():
    ket_qua = cleaners.tinh_nmv_sau_thue(pd.Series([1000, 2280000, 0]))
    assert ket_qua.tolist() == [926, 2111111, 0]


def test_nmv_sau_thue_nan_giu_nguyen():
    ket_qua = cleaners.tinh_nmv_sau_thue(pd.Series([1000, np.nan]))
    assert pd.isna(ket_qua.iloc[1])
