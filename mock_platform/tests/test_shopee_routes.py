"""Test 4 endpoint Shopee qua tầng HTTP bằng TestClient (SPEC §19.2, §19.3).

Mỗi test tự ký yêu cầu đúng thuật toán Shopee — như một client thật — rồi sửa
từng thành phần (chữ ký, timestamp, token, tham số) để xem máy chủ từ chối
đúng mã lỗi tài liệu.

Đồng hồ của máy chủ là đồng hồ giả (dict `dong_ho`), nên "4 giờ sau" hay
"30 ngày sau" chỉ là đổi một con số.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

import signature

GIO_VN = timezone(timedelta(hours=7))
# Mốc "bây giờ" của máy chủ trong test: sau toàn bộ dữ liệu mẫu Shopee (01/07–16/08/2026).
T0 = int(datetime(2026, 9, 1, tzinfo=GIO_VN).timestamp())
MUOI_LAM_NGAY = 15 * 24 * 3600

DUONG_DAN_LIST = "/api/v2/order/get_order_list"
DUONG_DAN_DETAIL = "/api/v2/order/get_order_detail"
DUONG_DAN_ESCROW = "/api/v2/payment/get_escrow_detail_batch"
DUONG_DAN_REFRESH = "/api/v2/auth/access_token/get"


@pytest.fixture
def dong_ho():
    return {"bay_gio": T0}


@pytest.fixture
def client(tao_client, cau_hinh, dong_ho):
    """App mới cho mỗi test: bảng token sạch, không bị test trước làm mới mất."""
    return tao_client(cau_hinh, dong_ho)


class KhachShopee:
    """Client Shopee tối giản dùng trong test: tự ký mọi yêu cầu Shop API / Public API."""

    def __init__(self, client, cau_hinh, dong_ho):
        self.client = client
        self.cau_hinh = cau_hinh
        self.dong_ho = dong_ho
        self.access_token = cau_hinh.SHOPEE_ACCESS_TOKEN

    def tham_so_chung(self, duong_dan, la_shop_api=True, **sua):
        """Tham số chung đã ký. `sua` ghi đè từng thành phần SAU khi tính chữ ký
        (trừ khi chính nó là thành phần được ký: timestamp, access_token, shop_id
        được ký theo giá trị đã sửa — để chỉ một điều kiện sai mỗi lần)."""
        timestamp = sua.pop("timestamp", self.dong_ho["bay_gio"])
        access_token = sua.pop("access_token", self.access_token) if la_shop_api else ""
        shop_id = sua.pop("shop_id", self.cau_hinh.SHOPEE_SHOP_ID) if la_shop_api else ""
        partner_id = self.cau_hinh.SHOPEE_PARTNER_ID
        tham_so = {
            "partner_id": partner_id,
            "timestamp": timestamp,
            "sign": signature.tinh_chu_ky_shopee(
                self.cau_hinh.SHOPEE_PARTNER_KEY, partner_id, duong_dan, timestamp, access_token, shop_id
            ),
        }
        if la_shop_api:
            tham_so.update(access_token=access_token, shop_id=shop_id)
        tham_so.update(sua)
        return {khoa: gia_tri for khoa, gia_tri in tham_so.items() if gia_tri is not None}

    def get(self, duong_dan, tham_so_rieng, **sua):
        phan_hoi = self.client.get(duong_dan, params={**self.tham_so_chung(duong_dan, **sua), **tham_so_rieng})
        assert phan_hoi.status_code == 200
        return phan_hoi.json()

    def post(self, duong_dan, than, la_shop_api=True, **sua):
        phan_hoi = self.client.post(
            duong_dan, params=self.tham_so_chung(duong_dan, la_shop_api, **sua),
            content=than if isinstance(than, str) else json.dumps(than),
            headers={"content-type": "application/json"},
        )
        assert phan_hoi.status_code == 200
        return phan_hoi.json()

    def danh_sach_don(self, tu_luc, den_luc, **them):
        tham_so = {"time_range_field": "create_time", "time_from": tu_luc, "time_to": den_luc, "page_size": 100, **them}
        return self.get(DUONG_DAN_LIST, tham_so)


@pytest.fixture
def khach(client, cau_hinh, dong_ho):
    return KhachShopee(client, cau_hinh, dong_ho)


def ma_loi(phan_hoi):
    return phan_hoi["error"]


# ---------- Kéo đủ dữ liệu ----------

def test_keo_du_moi_don_theo_cua_so_15_ngay(khach, du_lieu_shopee):
    """Như connector sẽ làm: chia cửa sổ ≤ 15 ngày, mỗi cửa sổ đi hết cursor, rồi lấy chi tiết lô 50."""
    tu_luc = int(datetime(2026, 7, 1, tzinfo=GIO_VN).timestamp())
    het_luc = int(datetime(2026, 9, 1, tzinfo=GIO_VN).timestamp())
    cac_ma = []
    while tu_luc < het_luc:
        # Hai đầu đều được tính (§16 mục 8) → cửa sổ sau bắt đầu từ den_luc + 1.
        den_luc = min(tu_luc + MUOI_LAM_NGAY, het_luc)
        cursor = ""
        while True:
            phan_hoi = khach.danh_sach_don(tu_luc, den_luc, cursor=cursor)
            assert ma_loi(phan_hoi) == ""
            cac_ma += [don["order_sn"] for don in phan_hoi["response"]["order_list"]]
            if not phan_hoi["response"]["more"]:
                assert phan_hoi["response"]["next_cursor"] == ""
                break
            cursor = phan_hoi["response"]["next_cursor"]
        tu_luc = den_luc + 1

    assert len(cac_ma) == len(set(cac_ma)) == 1761           # không trùng, không thiếu (§17.1)
    so_mat_hang = 0
    for dau in range(0, len(cac_ma), 50):
        lo = cac_ma[dau:dau + 50]
        phan_hoi = khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ",".join(lo), "response_optional_fields": "item_list"})
        assert [don["order_sn"] for don in phan_hoi["response"]["order_list"]] == lo
        so_mat_hang += sum(len(don["item_list"]) for don in phan_hoi["response"]["order_list"])
    assert so_mat_hang == 1774


def test_phan_trang_khong_trung_khong_sot(khach):
    tu_luc = int(datetime(2026, 7, 1, tzinfo=GIO_VN).timestamp())
    tat_ca = khach.danh_sach_don(tu_luc, tu_luc + MUOI_LAM_NGAY)["response"]
    assert tat_ca["more"]   # > 100 đơn trong 15 ngày đầu tháng 7 → phải có trang sau
    gop = []
    cursor = ""
    while True:
        trang = khach.danh_sach_don(tu_luc, tu_luc + MUOI_LAM_NGAY, page_size=7, cursor=cursor)["response"]
        gop += [don["order_sn"] for don in trang["order_list"]]
        if not trang["more"]:
            break
        cursor = trang["next_cursor"]
    assert len(gop) == len(set(gop))
    assert gop[:100] == [don["order_sn"] for don in tat_ca["order_list"]]


def test_loc_theo_update_time_va_order_status(khach, du_lieu_shopee):
    tu_luc = int(datetime(2026, 7, 1, tzinfo=GIO_VN).timestamp())
    phan_hoi = khach.get(DUONG_DAN_LIST, {
        "time_range_field": "update_time", "time_from": tu_luc, "time_to": tu_luc + MUOI_LAM_NGAY,
        "page_size": 100, "order_status": "CANCELLED", "response_optional_fields": "order_status",
    })
    cac_don = phan_hoi["response"]["order_list"]
    assert cac_don and {don["order_status"] for don in cac_don} == {"CANCELLED"}
    for don in cac_don:
        assert tu_luc <= du_lieu_shopee["don_hang"][don["order_sn"]]["update_time"] <= tu_luc + MUOI_LAM_NGAY


def test_order_detail_chi_tra_truong_tuy_chon_khi_xin(khach, du_lieu_shopee):
    ma = next(iter(du_lieu_shopee["don_hang"]))
    co_ban = khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ma})["response"]["order_list"][0]
    assert set(co_ban) == {"order_sn", "order_status", "create_time", "update_time"}
    day_du = khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ma, "response_optional_fields": "item_list,recipient_address"})
    don = day_du["response"]["order_list"][0]
    assert don["item_list"] == du_lieu_shopee["don_hang"][ma]["item_list"]
    assert don["recipient_address"] == du_lieu_shopee["don_hang"][ma]["recipient_address"]


# ---------- Giới hạn tham số → error_param ----------

@pytest.mark.parametrize("sua", [
    {"page_size": 101},
    {"page_size": 0},
    {"time_to": T0 - 10 * 86400 + MUOI_LAM_NGAY + 1},   # 15 ngày + 1 giây
    {"time_from": T0, "time_to": T0 - 1},               # time_from > time_to
    {"time_range_field": "pay_time"},
    {"cursor": "abc"},
    {"page_size": "muoi"},
])
def test_get_order_list_sai_tham_so(khach, sua):
    tham_so = {"time_range_field": "create_time", "time_from": T0 - 10 * 86400, "time_to": T0, "page_size": 100, **sua}
    assert ma_loi(khach.get(DUONG_DAN_LIST, tham_so)) == "error_param"


def test_dung_15_ngay_va_page_size_100_van_hop_le(khach):
    tham_so = {"time_range_field": "create_time", "time_from": T0 - MUOI_LAM_NGAY, "time_to": T0, "page_size": 100}
    assert ma_loi(khach.get(DUONG_DAN_LIST, tham_so)) == ""


def test_order_detail_qua_50_ma(khach, du_lieu_shopee):
    cac_ma = list(du_lieu_shopee["don_hang"])
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ",".join(cac_ma[:50])})) == ""
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ",".join(cac_ma[:51])})) == "error_param"
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": ""})) == "error_param"


# ---------- Chữ ký, timestamp, token ----------

def test_sai_chu_ky(khach):
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, sign="0" * 64)) == "error_sign"


def test_ky_bang_partner_key_khac(client, cau_hinh, dong_ho):
    khach_gia = KhachShopee(client, cau_hinh.model_copy(update={"SHOPEE_PARTNER_KEY": "khoa_khac"}), dong_ho)
    assert ma_loi(khach_gia.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"})) == "error_sign"


def test_timestamp_lech_qua_5_phut(khach):
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, timestamp=T0 - 301)) == "error_param"
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, timestamp=T0 - 300)) == ""


def test_thieu_tham_so_chung(khach):
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, access_token=None)) == "error_param"
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, sign=None)) == "error_param"


def test_partner_id_sai(khach):
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, partner_id=999)) == "error_auth"


def test_token_sai_hoac_cua_shop_khac(khach):
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, access_token="token_bia")) == "error_auth"
    # Chữ ký đúng với shop_id khác, nhưng token không thuộc shop đó.
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, shop_id=999999)) == "error_auth"


def test_token_het_han_sau_4_gio(khach, dong_ho):
    dong_ho["bay_gio"] = T0 + 4 * 3600 - 1
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"})) == ""
    dong_ho["bay_gio"] = T0 + 4 * 3600
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"})) == "error_auth"


def test_han_token_rut_ngan_qua_cau_hinh(tao_client, cau_hinh, dong_ho):
    cau_hinh_ngan = cau_hinh.model_copy(update={"MOCK_SHOPEE_ACCESS_TTL_SECONDS": 5})
    khach = KhachShopee(tao_client(cau_hinh_ngan, dong_ho), cau_hinh_ngan, dong_ho)
    dong_ho["bay_gio"] = T0 + 5
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"})) == "error_auth"


def test_phan_hoi_loi_dung_khuon(khach):
    phan_hoi = khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"}, sign="sai")
    assert set(phan_hoi) == {"request_id", "error", "message"}
    assert phan_hoi["request_id"] and phan_hoi["message"]


# ---------- Escrow ----------

def test_escrow_che_do_all_tra_moi_don(khach, du_lieu_shopee):
    cac_ma = list(du_lieu_shopee["don_hang"])[:50]
    phan_hoi = khach.post(DUONG_DAN_ESCROW, {"order_sn_list": cac_ma})
    assert ma_loi(phan_hoi) == "" and "warning" not in phan_hoi
    ket_qua = phan_hoi["response"]
    assert [phan["escrow_detail"]["order_sn"] for phan in ket_qua] == cac_ma
    mat_hang = ket_qua[0]["escrow_detail"]["order_income"]["items"][0]
    assert set(mat_hang) == {"item_id", "model_id", "seller_discount"}


def test_escrow_completed_only_bao_loi_don_chua_hoan_tat(tao_client, cau_hinh, dong_ho, du_lieu_shopee):
    cau_hinh_xau = cau_hinh.model_copy(update={"MOCK_ESCROW_MODE": "completed_only"})
    khach = KhachShopee(tao_client(cau_hinh_xau, dong_ho), cau_hinh_xau, dong_ho)
    don = du_lieu_shopee["don_hang"]
    hoan_tat = next(ma for ma in don if don[ma]["order_status"] == "COMPLETED")
    da_huy = next(ma for ma in don if don[ma]["order_status"] == "CANCELLED")

    phan_hoi = khach.post(DUONG_DAN_ESCROW, {"order_sn_list": [hoan_tat, da_huy]})
    assert ma_loi(phan_hoi) == ""
    assert da_huy in phan_hoi["warning"]
    assert phan_hoi["response"][0]["escrow_detail"]["order_sn"] == hoan_tat
    assert phan_hoi["response"][1]["order_sn"] == da_huy
    assert phan_hoi["response"][1]["fail_error"] == "mock_escrow_not_available"
    assert "escrow_detail" not in phan_hoi["response"][1]


@pytest.mark.parametrize("than", [
    {"order_sn_list": [f"MA{i}" for i in range(51)]},
    {"order_sn_list": []},
    {"order_sn_list": "MA1,MA2"},
    {},
    "khong phai json",
])
def test_escrow_sai_body(khach, than):
    assert ma_loi(khach.post(DUONG_DAN_ESCROW, than)) == "error_param"


def test_escrow_van_kiem_chu_ky(khach):
    assert ma_loi(khach.post(DUONG_DAN_ESCROW, {"order_sn_list": ["X"]}, sign="sai")) == "error_sign"


# ---------- Làm mới token ----------

def than_lam_moi(cau_hinh, refresh_token):
    return {"refresh_token": refresh_token, "partner_id": cau_hinh.SHOPEE_PARTNER_ID, "shop_id": cau_hinh.SHOPEE_SHOP_ID}


def test_lam_moi_cap_token_moi_dung_duoc(khach, cau_hinh):
    phan_hoi = khach.post(DUONG_DAN_REFRESH, than_lam_moi(cau_hinh, cau_hinh.SHOPEE_REFRESH_TOKEN), la_shop_api=False)
    assert ma_loi(phan_hoi) == ""
    token_moi = phan_hoi["response"]
    assert token_moi["expire_in"] == 4 * 3600
    assert token_moi["access_token"] != cau_hinh.SHOPEE_ACCESS_TOKEN
    khach.access_token = token_moi["access_token"]
    assert ma_loi(khach.get(DUONG_DAN_DETAIL, {"order_sn_list": "X"})) == ""


def test_lam_moi_2_lan_bang_cung_refresh_cu_lan_2_bi_tu_choi(khach, cau_hinh):
    than = than_lam_moi(cau_hinh, cau_hinh.SHOPEE_REFRESH_TOKEN)
    assert ma_loi(khach.post(DUONG_DAN_REFRESH, than, la_shop_api=False)) == ""
    assert ma_loi(khach.post(DUONG_DAN_REFRESH, than, la_shop_api=False)) == "error_auth"   # giả định §16 mục 7


def test_refresh_token_qua_30_ngay(khach, cau_hinh, dong_ho):
    dong_ho["bay_gio"] = T0 + 30 * 86400
    phan_hoi = khach.post(DUONG_DAN_REFRESH, than_lam_moi(cau_hinh, cau_hinh.SHOPEE_REFRESH_TOKEN), la_shop_api=False)
    assert ma_loi(phan_hoi) == "refresh_token_expired"


def test_lam_moi_la_public_api_ky_khong_co_token(khach, cau_hinh):
    """Ký kiểu Shop API (có access_token, shop_id) cho endpoint Public → sai chữ ký."""
    tham_so = khach.tham_so_chung(DUONG_DAN_REFRESH, la_shop_api=True)
    phan_hoi = khach.client.post(DUONG_DAN_REFRESH, params=tham_so, json=than_lam_moi(cau_hinh, cau_hinh.SHOPEE_REFRESH_TOKEN))
    assert ma_loi(phan_hoi.json()) == "error_sign"


def test_lam_moi_thieu_shop_id(khach, cau_hinh):
    than = {"refresh_token": cau_hinh.SHOPEE_REFRESH_TOKEN, "partner_id": cau_hinh.SHOPEE_PARTNER_ID}
    assert ma_loi(khach.post(DUONG_DAN_REFRESH, than, la_shop_api=False)) == "error_param"
