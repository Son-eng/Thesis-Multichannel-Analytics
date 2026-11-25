import numpy as np
import pytest

from app.etl.status_mapper import gom_nhom_trang_thai_api, gom_nhom_trang_thai_file


@pytest.mark.parametrize(
    "trang_thai_goc, nhom",
    [
        ("Hoàn thành", "completed"),
        ("Đã nhận được hàng", "completed"),
        ("Đã giao", "delivered"),
        ("Đang giao", "shipping"),
        ("Chờ giao hàng", "pending"),
        ("Chờ xác nhận", "pending"),
        ("Đã hủy", "cancelled"),
    ],
)
def test_file_shopee_chuoi_co_dinh(trang_thai_goc, nhom):
    assert gom_nhom_trang_thai_file(trang_thai_goc, "shopee") == nhom


@pytest.mark.parametrize("ngay", ["2026-08-05", "2026-08-15", "2027-01-31"])
def test_file_shopee_nguoi_mua_xac_nhan_co_nhung_ngay(ngay):
    trang_thai = ("Người mua xác nhận đã nhận được hàng, tuy nhiên Người mua vẫn có thể "
                  f"gửi yêu cầu Trả hàng/Hoàn tiền tới ngày {ngay}.")
    assert gom_nhom_trang_thai_file(trang_thai, "shopee") == "completed"


@pytest.mark.parametrize("trang_thai_rong", [np.nan, None, "", "   "])
def test_file_shopee_rong_la_unknown(trang_thai_rong):
    assert gom_nhom_trang_thai_file(trang_thai_rong, "shopee") == "unknown"


def test_file_shopee_gia_tri_la_la_unknown_va_ghi_log(caplog):
    assert gom_nhom_trang_thai_file("Đang xử lý", "shopee") == "unknown"
    assert "Đang xử lý" in caplog.text


@pytest.mark.parametrize(
    "trang_thai_goc, nhom",
    [
        ("Đã hoàn tất", "completed"),
        ("Đã vận chuyển", "shipping"),
        ("Cần vận chuyển", "pending"),
        ("Đã hủy", "cancelled"),
    ],
)
def test_file_tiktok(trang_thai_goc, nhom):
    assert gom_nhom_trang_thai_file(trang_thai_goc, "tiktok") == nhom


def test_file_tiktok_khong_dung_quy_tac_tien_to_cua_shopee():
    trang_thai = "Người mua xác nhận đã nhận được hàng"
    assert gom_nhom_trang_thai_file(trang_thai, "tiktok") == "unknown"


def test_file_khoang_trang_hai_dau_van_khop():
    assert gom_nhom_trang_thai_file(" Đã hủy ", "tiktok") == "cancelled"


@pytest.mark.parametrize(
    "ma, nhom",
    [
        ("COMPLETED", "completed"),
        ("TO_RETURN", "completed"),
        ("TO_CONFIRM_RECEIVE", "delivered"),
        ("SHIPPED", "shipping"),
        ("UNPAID", "pending"),
        ("READY_TO_SHIP", "pending"),
        ("PROCESSED", "pending"),
        ("IN_CANCEL", "pending"),
        ("INVOICE_PENDING", "pending"),
        ("CANCELLED", "cancelled"),
    ],
)
def test_api_shopee(ma, nhom):
    assert gom_nhom_trang_thai_api(ma, "shopee") == nhom


@pytest.mark.parametrize(
    "ma, nhom",
    [
        ("COMPLETED", "completed"),
        ("DELIVERED", "delivered"),
        ("AWAITING_COLLECTION", "shipping"),
        ("IN_TRANSIT", "shipping"),
        ("PARTIALLY_SHIPPING", "shipping"),
        ("UNPAID", "pending"),
        ("ON_HOLD", "pending"),
        ("AWAITING_SHIPMENT", "pending"),
        ("CANCELLED", "cancelled"),
    ],
)
def test_api_tiktok(ma, nhom):
    assert gom_nhom_trang_thai_api(ma, "tiktok") == nhom


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_api_ma_la_la_unknown_va_ghi_log(san, caplog):
    assert gom_nhom_trang_thai_api("MA_MOI_CUA_SAN", san) == "unknown"
    assert "MA_MOI_CUA_SAN" in caplog.text


@pytest.mark.parametrize("ma_rong", [np.nan, None, ""])
def test_api_rong_la_unknown(ma_rong):
    assert gom_nhom_trang_thai_api(ma_rong, "shopee") == "unknown"


def test_api_ma_cua_san_nay_khong_lan_sang_san_kia():
    assert gom_nhom_trang_thai_api("DELIVERED", "shopee") == "unknown"
