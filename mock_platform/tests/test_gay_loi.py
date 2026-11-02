"""Test gây lỗi quá tải có chủ đích — MOCK_FAULT_RATE, MOCK_FAULT_SEED (SPEC §19.3 mục 5).

Lỗi quá tải được quyết định TRƯỚC mọi bước kiểm, nên với tỷ lệ 1 thì ngay cả
yêu cầu không ký cũng nhận lỗi quá tải — test dùng yêu cầu trơn cho gọn. Test
cần yêu cầu hợp lệ thì dùng lại client tự ký của test Shopee / TikTok.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import gay_loi
from test_shopee_routes import DUONG_DAN_REFRESH as REFRESH_SHOPEE, KhachShopee, than_lam_moi
from test_tiktok_routes import DUONG_DAN_SEARCH, KhachTikTok, lam_moi

T0 = int(datetime(2026, 9, 1, tzinfo=timezone(timedelta(hours=7))).timestamp())

# Mọi endpoint của 2 sàn: (phương thức, đường dẫn).
ENDPOINT_SHOPEE = [
    ("GET", "/api/v2/order/get_order_list"),
    ("GET", "/api/v2/order/get_order_detail"),
    ("POST", "/api/v2/payment/get_escrow_detail_batch"),
    ("POST", "/api/v2/auth/access_token/get"),
]
ENDPOINT_TIKTOK = [
    ("POST", "/order/202309/orders/search"),
    ("GET", "/finance/202501/orders/123/statement_transactions"),
    ("GET", "/api/v2/token/refresh"),
]


@pytest.fixture
def dong_ho():
    return {"bay_gio": T0}


def cau_hinh_loi(cau_hinh, ty_le, hat_giong=None):
    return cau_hinh.model_copy(update={"MOCK_FAULT_RATE": ty_le, "MOCK_FAULT_SEED": hat_giong})


def doi_ty_le(client, ty_le):
    """Đổi tỷ lệ lỗi của một app đang chạy (bảng token giữ nguyên)."""
    client.app.state.cau_hinh = cau_hinh_loi(client.app.state.cau_hinh, ty_le)


# ---------- Tỷ lệ 1: mọi yêu cầu đều lỗi, đúng khuôn từng sàn ----------

@pytest.mark.parametrize("phuong_thuc, duong_dan", ENDPOINT_SHOPEE)
def test_ty_le_1_shopee_moi_endpoint_tra_429(tao_client, cau_hinh, dong_ho, phuong_thuc, duong_dan):
    client = tao_client(cau_hinh_loi(cau_hinh, 1), dong_ho)
    phan_hoi = client.request(phuong_thuc, duong_dan)
    assert phan_hoi.status_code == 429
    assert phan_hoi.json()["error"] == "error_rate_limit"


@pytest.mark.parametrize("phuong_thuc, duong_dan", ENDPOINT_TIKTOK)
def test_ty_le_1_tiktok_moi_endpoint_tra_36009002(tao_client, cau_hinh, dong_ho, phuong_thuc, duong_dan):
    client = tao_client(cau_hinh_loi(cau_hinh, 1), dong_ho)
    phan_hoi = client.request(phuong_thuc, duong_dan)
    assert phan_hoi.status_code == 200
    assert phan_hoi.json()["code"] == 36009002


# ---------- Tỷ lệ 0: không yêu cầu hợp lệ nào lỗi ----------

def test_ty_le_0_khong_loi(tao_client, cau_hinh, dong_ho, du_lieu_tiktok):
    client = tao_client(cau_hinh_loi(cau_hinh, 0, hat_giong=1), dong_ho)
    khach_shopee = KhachShopee(client, cau_hinh, dong_ho)
    khach_tiktok = KhachTikTok(client, cau_hinh, dong_ho, du_lieu_tiktok["Shop A"]["shop_cipher"],
                               cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN)
    for _ in range(100):
        assert khach_shopee.get("/api/v2/order/get_order_detail", {"order_sn_list": "X"})["error"] == ""
        assert khach_tiktok.tim_don({})["code"] == 0


def test_ty_le_0_khong_rut_so_ngau_nhien(tao_client, cau_hinh, dong_ho):
    """Tắt gây lỗi thì bộ sinh số không bị đụng tới (§19.3 mục 5)."""
    client = tao_client(cau_hinh_loi(cau_hinh, 0, hat_giong=7), dong_ho)
    trang_thai_truoc = client.app.state.bo_sinh_ngau_nhien.getstate()
    for _ in range(20):
        client.get("/api/v2/order/get_order_detail")
    assert client.app.state.bo_sinh_ngau_nhien.getstate() == trang_thai_truoc


# ---------- Tỷ lệ 0,3 với seed cố định ----------

def chuoi_ket_qua(client, so_lan):
    return [client.get("/api/v2/order/get_order_detail").status_code == 429 for _ in range(so_lan)]


def test_ty_le_0_3_xap_xi_30_phan_tram_va_tai_lap_duoc(tao_client, cau_hinh, dong_ho):
    lan_1 = chuoi_ket_qua(tao_client(cau_hinh_loi(cau_hinh, 0.3, hat_giong=42), dong_ho), 1000)
    lan_2 = chuoi_ket_qua(tao_client(cau_hinh_loi(cau_hinh, 0.3, hat_giong=42), dong_ho), 1000)
    assert lan_1 == lan_2                         # cùng seed → cùng chuỗi lỗi
    assert 0.25 <= sum(lan_1) / 1000 <= 0.35      # xấp xỉ 30%
    lan_khac_seed = chuoi_ket_qua(tao_client(cau_hinh_loi(cau_hinh, 0.3, hat_giong=43), dong_ho), 1000)
    assert lan_khac_seed != lan_1


def test_ham_nen_gay_loi_ty_le_bien():
    trang_thai = SimpleNamespace(
        bo_sinh_ngau_nhien=gay_loi.tao_bo_sinh_ngau_nhien(0),
        cau_hinh=SimpleNamespace(MOCK_FAULT_RATE=1.0),
    )
    assert all(gay_loi.nen_gay_loi(trang_thai) for _ in range(1000))
    trang_thai.cau_hinh.MOCK_FAULT_RATE = 0.0
    assert not any(gay_loi.nen_gay_loi(trang_thai) for _ in range(1000))


# ---------- Lỗi không làm hỏng trạng thái ----------

def test_shopee_loi_qua_tai_khong_tieu_refresh_token(tao_client, cau_hinh, dong_ho):
    client = tao_client(cau_hinh_loi(cau_hinh, 1), dong_ho)
    khach = KhachShopee(client, cau_hinh, dong_ho)
    than = than_lam_moi(cau_hinh, cau_hinh.SHOPEE_REFRESH_TOKEN)

    # Gọi làm mới HỢP LỆ nhưng gặp lỗi quá tải 3 lần — như connector thử lại.
    for _ in range(3):
        phan_hoi = client.post(REFRESH_SHOPEE, params=khach.tham_so_chung(REFRESH_SHOPEE, la_shop_api=False), json=than)
        assert phan_hoi.status_code == 429
    doi_ty_le(client, 0)
    # refresh_token vẫn còn nguyên: lần làm mới này thành công.
    assert khach.post(REFRESH_SHOPEE, than, la_shop_api=False)["error"] == ""


def test_tiktok_loi_qua_tai_khong_cap_token(tao_client, cau_hinh, dong_ho, du_lieu_tiktok):
    client = tao_client(cau_hinh_loi(cau_hinh, 1), dong_ho)
    assert lam_moi(client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)["code"] == 36009002
    doi_ty_le(client, 0)
    # Token ban đầu vẫn dùng được, refresh vẫn dùng được.
    khach = KhachTikTok(client, cau_hinh, dong_ho, du_lieu_tiktok["Shop A"]["shop_cipher"],
                        cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN)
    assert khach.tim_don({})["code"] == 0
    assert lam_moi(client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)["code"] == 0


def test_loi_qua_tai_khong_doi_du_lieu(tao_client, cau_hinh, dong_ho, du_lieu_tiktok):
    client = tao_client(cau_hinh_loi(cau_hinh, 0.5, hat_giong=3), dong_ho)
    khach = KhachTikTok(client, cau_hinh, dong_ho, du_lieu_tiktok["Shop B"]["shop_cipher"],
                        cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN)
    khoang = {"create_time_ge": 0, "create_time_lt": T0}
    ket_qua = []
    for _ in range(40):
        phan_hoi = khach.goi("POST", DUONG_DAN_SEARCH, {"page_size": "5"}, khoang)
        if phan_hoi["code"] == 0:
            ket_qua.append([don["id"] for don in phan_hoi["data"]["orders"]])
    # Lần thành công nào cũng ra đúng một trang như nhau: lỗi xen giữa không làm đổi dữ liệu.
    assert ket_qua and all(trang == ket_qua[0] for trang in ket_qua)
    assert len(ket_qua) < 40                     # và thật sự có lỗi xen giữa
