"""Test luồng ỦY QUYỀN gian hàng của máy chủ giả lập (chỉ dẫn 026, giai đoạn 2).

Hai sàn, mỗi sàn đi hết một vòng như người thật:
    mở trang ủy quyền → bấm Đồng ý / Từ chối → sàn chuyển về `redirect` kèm mã ủy quyền → đổi mã lấy token.

Khuôn đường dẫn, tham số, chữ ký theo tài liệu đã xác minh ở giai đoạn 0 (báo cáo 026 mục a):
- Shopee: `GET /api/v2/shop/auth_partner` (ký như Public API), redirect trả `code` + `shop_id`,
  đổi mã bằng `POST /api/v2/auth/token/get`.
- TikTok: `GET /open/authorize?service_id=…`, redirect (đã đăng ký) trả `code`,
  đổi mã bằng `GET /api/v2/token/get` (`grant_type=authorized_code`), `GET /authorization/202309/shops` lấy cipher.
Phần không có trong tài liệu (trả `state`, tham số khi từ chối, thu hồi token cũ) là GIẢ ĐỊNH, ghi ở SPEC §16.

Đồng hồ máy chủ là đồng hồ giả (dict `dong_ho`) nên "10 phút sau" chỉ là đổi một con số.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

import signature

GIO_VN = timezone(timedelta(hours=7))
T0 = int(datetime(2026, 9, 1, tzinfo=GIO_VN).timestamp())

AUTH_PARTNER = "/api/v2/shop/auth_partner"
TOKEN_GET_SHOPEE = "/api/v2/auth/token/get"
LIST_SHOPEE = "/api/v2/order/get_order_list"
OPEN_AUTHORIZE = "/open/authorize"
TOKEN_GET_TIKTOK = "/api/v2/token/get"
SHOPS_TIKTOK = "/authorization/202309/shops"
SEARCH_TIKTOK = "/order/202309/orders/search"

REDIRECT_SHOPEE = "http://localhost:8000/api/connections/shopee/callback?state=ABC123"
SHOP_D_ID = "200004"
CIPHER_E = "MOCK_CIPHER_SHOP_E"


@pytest.fixture
def dong_ho():
    return {"bay_gio": T0}


@pytest.fixture
def client(tao_client, cau_hinh, dong_ho):
    return tao_client(cau_hinh, dong_ho)


# =====================================================================
# Shopee
# =====================================================================

def tham_so_auth_shopee(cau_hinh, dong_ho, **sua):
    """Tham số trang ủy quyền Shopee, ký như Public API: partner_id + path + timestamp."""
    timestamp = sua.pop("timestamp", dong_ho["bay_gio"])
    partner_id = sua.pop("partner_id", cau_hinh.SHOPEE_PARTNER_ID)
    tham_so = {
        "partner_id": partner_id, "timestamp": timestamp,
        "sign": signature.tinh_chu_ky_shopee(cau_hinh.SHOPEE_PARTNER_KEY, partner_id, AUTH_PARTNER, timestamp),
        "redirect": REDIRECT_SHOPEE,
    }
    tham_so.update(sua)
    return {k: v for k, v in tham_so.items() if v is not None}


def mo_trang_shopee(client, cau_hinh, dong_ho, **sua):
    return client.get(AUTH_PARTNER, params=tham_so_auth_shopee(cau_hinh, dong_ho, **sua))


def lay_phien(html):
    """Mã phiên ủy quyền nằm trong ô ẩn của biểu mẫu."""
    khop = re.search(r'name="phien" value="([^"]+)"', html)
    assert khop, "trang ủy quyền thiếu ô ẩn 'phien'"
    return khop.group(1)


def quyet_dinh_shopee(client, phien, quyet_dinh, shop_id=None):
    du_lieu = {"phien": phien, "quyet_dinh": quyet_dinh}
    if shop_id is not None:
        du_lieu["shop_id"] = shop_id
    return client.post("/mock/shopee/quyet-dinh", data=du_lieu, follow_redirects=False)


def doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id=None, **sua):
    """POST /api/v2/auth/token/get — Public API: chữ ký chỉ có partner_id + path + timestamp."""
    timestamp = dong_ho["bay_gio"]
    partner_id = sua.pop("partner_id", cau_hinh.SHOPEE_PARTNER_ID)
    tham_so = {
        "partner_id": partner_id, "timestamp": timestamp,
        "sign": signature.tinh_chu_ky_shopee(cau_hinh.SHOPEE_PARTNER_KEY, partner_id, TOKEN_GET_SHOPEE, timestamp),
    }
    tham_so.update(sua.pop("tham_so", {}))
    than = {"code": code, "partner_id": partner_id}
    if shop_id is not None:
        than["shop_id"] = int(shop_id)
    return client.post(TOKEN_GET_SHOPEE, params=tham_so, content=json.dumps(than),
                       headers={"content-type": "application/json"}).json()


def ky_shop_api_shopee(cau_hinh, duong_dan, timestamp, access_token, shop_id):
    return signature.tinh_chu_ky_shopee(cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.SHOPEE_PARTNER_ID, duong_dan,
                                        timestamp, access_token, shop_id)


def dem_don_shopee(client, cau_hinh, dong_ho, access_token, shop_id):
    """Số đơn Shopee của shop (qua get_order_list, cửa sổ 15 ngày quanh tháng có dữ liệu mẫu)."""
    tu_luc = int(datetime(2026, 8, 1, tzinfo=GIO_VN).timestamp())
    tham_so = {
        "partner_id": cau_hinh.SHOPEE_PARTNER_ID, "timestamp": dong_ho["bay_gio"],
        "sign": ky_shop_api_shopee(cau_hinh, LIST_SHOPEE, dong_ho["bay_gio"], access_token, str(shop_id)),
        "access_token": access_token, "shop_id": str(shop_id),
        "time_range_field": "create_time", "time_from": tu_luc, "time_to": tu_luc + 15 * 24 * 3600, "page_size": 100,
    }
    phan_hoi = client.get(LIST_SHOPEE, params=tham_so).json()
    assert phan_hoi["error"] == "", phan_hoi
    return len(phan_hoi["response"]["order_list"])


def uy_quyen_shopee(client, cau_hinh, dong_ho, shop_id):
    """Cả vòng: mở trang → Đồng ý chọn shop → lấy `code` ở redirect. Trả (code, shop_id ở redirect)."""
    trang = mo_trang_shopee(client, cau_hinh, dong_ho)
    assert trang.status_code == 200
    phan_hoi = quyet_dinh_shopee(client, lay_phien(trang.text), "dong_y", shop_id)
    truy_van = parse_qs(urlparse(phan_hoi.headers["location"]).query)
    return truy_van["code"][0], truy_van["shop_id"][0]


def test_shopee_trang_uy_quyen_hien_cac_shop_va_hai_nut(client, cau_hinh, dong_ho):
    trang = mo_trang_shopee(client, cau_hinh, dong_ho)
    assert trang.status_code == 200 and "text/html" in trang.headers["content-type"]
    cac_chu = trang.text
    assert "xin quyền đọc đơn hàng" in cac_chu
    assert "Shop C" in cac_chu and "Shop D" in cac_chu          # shop hiện có + một shop MỚI chưa có đơn
    assert "Đồng ý" in cac_chu and "Từ chối" in cac_chu


@pytest.mark.parametrize("sua, ma_loi_mong_doi", [
    ({"sign": "sai"}, "error_sign"),
    ({"partner_id": 999}, "error_auth"),
    ({"redirect": None}, "error_param"),
    ({"timestamp": T0 - 3600}, "error_param"),
])
def test_shopee_trang_uy_quyen_tu_choi_yeu_cau_sai(client, cau_hinh, dong_ho, sua, ma_loi_mong_doi):
    # `timestamp` và `partner_id` được KÝ theo giá trị đã sửa, `sign`/`redirect` ghi đè sau khi ký.
    phan_hoi = mo_trang_shopee(client, cau_hinh, dong_ho, **sua)
    assert phan_hoi.json()["error"] == ma_loi_mong_doi


def test_shopee_dong_y_shop_moi_ve_redirect_kem_code_va_shop_id_giu_nguyen_state(client, cau_hinh, dong_ho):
    trang = mo_trang_shopee(client, cau_hinh, dong_ho)
    phan_hoi = quyet_dinh_shopee(client, lay_phien(trang.text), "dong_y", SHOP_D_ID)
    assert phan_hoi.status_code in (302, 303)
    dich = urlparse(phan_hoi.headers["location"])
    assert f"{dich.scheme}://{dich.netloc}{dich.path}" == "http://localhost:8000/api/connections/shopee/callback"
    truy_van = parse_qs(dich.query)
    assert truy_van["state"] == ["ABC123"]                     # query có sẵn của redirect được giữ, code nối thêm
    assert truy_van["shop_id"] == [SHOP_D_ID] and len(truy_van["code"][0]) >= 16
    assert "error" not in truy_van


def test_shopee_tu_choi_ve_redirect_kem_loi_khong_co_code(client, cau_hinh, dong_ho):
    trang = mo_trang_shopee(client, cau_hinh, dong_ho)
    phan_hoi = quyet_dinh_shopee(client, lay_phien(trang.text), "tu_choi")
    truy_van = parse_qs(urlparse(phan_hoi.headers["location"]).query)
    assert truy_van["error"] == ["access_denied"] and "code" not in truy_van and truy_van["state"] == ["ABC123"]


def test_shopee_phien_chi_dung_mot_lan(client, cau_hinh, dong_ho):
    phien = lay_phien(mo_trang_shopee(client, cau_hinh, dong_ho).text)
    assert quyet_dinh_shopee(client, phien, "dong_y", SHOP_D_ID).status_code in (302, 303)
    lan_hai = quyet_dinh_shopee(client, phien, "dong_y", SHOP_D_ID)
    assert lan_hai.status_code == 400                            # phiên đã dùng: không cấp thêm code


def test_shopee_phien_het_han_sau_muoi_phut(client, cau_hinh, dong_ho):
    phien = lay_phien(mo_trang_shopee(client, cau_hinh, dong_ho).text)
    dong_ho["bay_gio"] += 10 * 60 + 1
    assert quyet_dinh_shopee(client, phien, "dong_y", SHOP_D_ID).status_code == 400


def test_shopee_shop_khong_co_trong_danh_sach_bi_tu_choi(client, cau_hinh, dong_ho):
    phien = lay_phien(mo_trang_shopee(client, cau_hinh, dong_ho).text)
    assert quyet_dinh_shopee(client, phien, "dong_y", "12345").status_code == 400


def test_shopee_doi_ma_lay_token_va_shop_moi_dong_bo_ra_khong_don(client, cau_hinh, dong_ho):
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    ket_qua = doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)
    assert ket_qua["error"] == "", ket_qua
    phan_hoi = ket_qua["response"]
    assert phan_hoi["access_token"] and phan_hoi["refresh_token"] and phan_hoi["expire_in"] == 4 * 3600
    assert phan_hoi["shop_id_list"] == [int(SHOP_D_ID)]
    # Token mới dùng được cho ĐÚNG shop D, và shop D chưa có đơn nào.
    assert dem_don_shopee(client, cau_hinh, dong_ho, phan_hoi["access_token"], SHOP_D_ID) == 0
    # Token của shop D không đọc được shop C.
    tham_so = {
        "partner_id": cau_hinh.SHOPEE_PARTNER_ID, "timestamp": dong_ho["bay_gio"],
        "sign": ky_shop_api_shopee(cau_hinh, LIST_SHOPEE, dong_ho["bay_gio"], phan_hoi["access_token"], str(cau_hinh.SHOPEE_SHOP_ID)),
        "access_token": phan_hoi["access_token"], "shop_id": str(cau_hinh.SHOPEE_SHOP_ID),
        "time_range_field": "create_time", "time_from": 0, "time_to": 10, "page_size": 100,
    }
    assert client.get(LIST_SHOPEE, params=tham_so).json()["error"] == "error_auth"


def test_shopee_ma_chi_dung_mot_lan(client, cau_hinh, dong_ho):
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)["error"] == ""
    lan_hai = doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)
    assert lan_hai["error"] == "invalid_code"


def test_shopee_ma_het_han_sau_muoi_phut_bi_tu_choi(client, cau_hinh, dong_ho):
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    dong_ho["bay_gio"] += 10 * 60 + 1
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)["error"] == "invalid_code"


def test_shopee_ma_con_han_den_giay_cuoi(client, cau_hinh, dong_ho):
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    dong_ho["bay_gio"] += 10 * 60 - 1
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)["error"] == ""


def test_shopee_doi_ma_sai_chu_ky_hoac_partner_bi_tu_choi_va_khong_tieu_ma(client, cau_hinh, dong_ho):
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id, tham_so={"sign": "sai"})["error"] == "error_sign"
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id, partner_id=999)["error"] == "error_auth"
    assert doi_ma_shopee(client, cau_hinh, dong_ho, "ma-khong-ton-tai", shop_id)["error"] == "invalid_code"
    # Các lần hỏng ở trên KHÔNG được làm mất mã: vẫn đổi được.
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)["error"] == ""


def test_shopee_shop_id_gui_kem_phai_khop_voi_ma(client, cau_hinh, dong_ho):
    code, _ = uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    assert doi_ma_shopee(client, cau_hinh, dong_ho, code, cau_hinh.SHOPEE_SHOP_ID)["error"] == "invalid_code"


def test_shopee_uy_quyen_lai_shop_c_cap_token_moi_token_cu_van_dung_toi_han_du_lieu_khong_doi(client, cau_hinh, dong_ho):
    truoc = dem_don_shopee(client, cau_hinh, dong_ho, cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_SHOP_ID)
    assert truoc > 0
    code, shop_id = uy_quyen_shopee(client, cau_hinh, dong_ho, str(cau_hinh.SHOPEE_SHOP_ID))
    moi = doi_ma_shopee(client, cau_hinh, dong_ho, code, shop_id)["response"]
    assert moi["access_token"] != cau_hinh.SHOPEE_ACCESS_TOKEN
    assert dem_don_shopee(client, cau_hinh, dong_ho, moi["access_token"], cau_hinh.SHOPEE_SHOP_ID) == truoc
    # GIẢ ĐỊNH (chưa xác minh, §16): token cũ vẫn dùng được tới hạn.
    assert dem_don_shopee(client, cau_hinh, dong_ho, cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_SHOP_ID) == truoc


# =====================================================================
# TikTok
# =====================================================================

STATE_TIKTOK = "st_xyz789"


def mo_trang_tiktok(client, cau_hinh, **sua):
    tham_so = {"service_id": cau_hinh.TIKTOK_SERVICE_ID, "state": STATE_TIKTOK}
    tham_so.update(sua)
    return client.get(OPEN_AUTHORIZE, params={k: v for k, v in tham_so.items() if v is not None})


def quyet_dinh_tiktok(client, phien, quyet_dinh, shop=None):
    du_lieu = {"phien": phien, "quyet_dinh": quyet_dinh}
    if shop is not None:
        du_lieu["shop"] = shop
    return client.post("/mock/tiktok/quyet-dinh", data=du_lieu, follow_redirects=False)


def uy_quyen_tiktok(client, cau_hinh, shop):
    trang = mo_trang_tiktok(client, cau_hinh)
    phan_hoi = quyet_dinh_tiktok(client, lay_phien(trang.text), "dong_y", shop)
    return parse_qs(urlparse(phan_hoi.headers["location"]).query)["code"][0]


def doi_ma_tiktok(client, cau_hinh, auth_code, **sua):
    tham_so = {"app_key": cau_hinh.TIKTOK_APP_KEY, "app_secret": cau_hinh.TIKTOK_APP_SECRET,
               "auth_code": auth_code, "grant_type": "authorized_code"}
    tham_so.update(sua)
    return client.get(TOKEN_GET_TIKTOK, params=tham_so).json()


def goi_open_api_tiktok(client, cau_hinh, dong_ho, duong_dan, access_token, shop_cipher=None, phuong_thuc="GET", than=""):
    tham_so = {"app_key": cau_hinh.TIKTOK_APP_KEY, "timestamp": str(dong_ho["bay_gio"])}
    if shop_cipher is not None:
        tham_so["shop_cipher"] = shop_cipher
    if duong_dan == SEARCH_TIKTOK:
        tham_so["page_size"] = "100"
    tham_so["sign"] = signature.tinh_chu_ky_tiktok(cau_hinh.TIKTOK_APP_SECRET, duong_dan, tham_so, than)
    phan_hoi = client.request(phuong_thuc, duong_dan, params=tham_so, content=than,
                              headers={"content-type": "application/json", "x-tts-access-token": access_token})
    assert phan_hoi.status_code == 200
    return phan_hoi.json()


def test_tiktok_trang_uy_quyen_can_dung_service_id(client, cau_hinh):
    trang = mo_trang_tiktok(client, cau_hinh)
    assert trang.status_code == 200 and "text/html" in trang.headers["content-type"]
    assert "xin quyền đọc đơn hàng" in trang.text
    assert all(ten in trang.text for ten in ("Shop A", "Shop B", "Shop E"))      # 2 shop hiện có + 1 shop MỚI
    assert "Đồng ý" in trang.text and "Từ chối" in trang.text
    assert mo_trang_tiktok(client, cau_hinh, service_id="sai").status_code == 400
    assert mo_trang_tiktok(client, cau_hinh, service_id=None).status_code == 400


def test_tiktok_dong_y_ve_redirect_da_dang_ky_kem_code_va_state(client, cau_hinh):
    phien = lay_phien(mo_trang_tiktok(client, cau_hinh).text)
    phan_hoi = quyet_dinh_tiktok(client, phien, "dong_y", "Shop E")
    dich = urlparse(phan_hoi.headers["location"])
    # TikTok không nhận `redirect` ở URL: chuyển về Redirect URL ĐÃ ĐĂNG KÝ (cấu hình của app).
    assert f"{dich.scheme}://{dich.netloc}{dich.path}" == cau_hinh.TIKTOK_REDIRECT_URL
    truy_van = parse_qs(dich.query)
    assert truy_van["state"] == [STATE_TIKTOK] and len(truy_van["code"][0]) >= 16 and "error" not in truy_van


def test_tiktok_tu_choi_ve_redirect_kem_loi(client, cau_hinh):
    phien = lay_phien(mo_trang_tiktok(client, cau_hinh).text)
    truy_van = parse_qs(urlparse(quyet_dinh_tiktok(client, phien, "tu_choi").headers["location"]).query)
    assert truy_van["error"] == ["access_denied"] and "code" not in truy_van and truy_van["state"] == [STATE_TIKTOK]
    assert quyet_dinh_tiktok(client, phien, "dong_y", "Shop E").status_code == 400      # phiên đã dùng


def test_tiktok_doi_ma_lay_token_va_danh_sach_shop_co_cipher_va_ten(client, cau_hinh, dong_ho):
    code = uy_quyen_tiktok(client, cau_hinh, "Shop E")
    ket_qua = doi_ma_tiktok(client, cau_hinh, code)
    assert ket_qua["code"] == 0, ket_qua
    access_token = ket_qua["data"]["access_token"]
    assert access_token and ket_qua["data"]["refresh_token"]
    # Danh sách shop đã ủy quyền: header token + query ký (không có shop_cipher).
    cac_shop = goi_open_api_tiktok(client, cau_hinh, dong_ho, SHOPS_TIKTOK, access_token)
    assert cac_shop["code"] == 0, cac_shop
    (shop,) = cac_shop["data"]["shops"]
    assert shop["name"] == "Shop E" and shop["cipher"] == CIPHER_E and shop["id"] and shop["region"] == "VN"
    # Shop mới chưa có đơn: đồng bộ ra 0 đơn và không báo lỗi.
    don = goi_open_api_tiktok(client, cau_hinh, dong_ho, SEARCH_TIKTOK, access_token, CIPHER_E, "POST", "{}")
    assert don["code"] == 0 and don["data"]["orders"] == [] and don["data"]["total_count"] == 0


def test_tiktok_danh_sach_shop_sai_chu_ky_hoac_token_bi_tu_choi(client, cau_hinh, dong_ho):
    access_token = doi_ma_tiktok(client, cau_hinh, uy_quyen_tiktok(client, cau_hinh, "Shop E"))["data"]["access_token"]
    assert goi_open_api_tiktok(client, cau_hinh, dong_ho, SHOPS_TIKTOK, "token-sai")["code"] != 0
    tham_so = {"app_key": cau_hinh.TIKTOK_APP_KEY, "timestamp": str(dong_ho["bay_gio"]), "sign": "sai"}
    phan_hoi = client.get(SHOPS_TIKTOK, params=tham_so, headers={"x-tts-access-token": access_token}).json()
    assert phan_hoi["code"] != 0


def test_tiktok_ma_chi_dung_mot_lan_va_het_han_sau_30_phut(client, cau_hinh, dong_ho):
    code = uy_quyen_tiktok(client, cau_hinh, "Shop E")
    assert doi_ma_tiktok(client, cau_hinh, code)["code"] == 0
    assert doi_ma_tiktok(client, cau_hinh, code)["code"] != 0                        # lần hai: bị từ chối
    code2 = uy_quyen_tiktok(client, cau_hinh, "Shop E")
    dong_ho["bay_gio"] += 30 * 60 + 1
    assert doi_ma_tiktok(client, cau_hinh, code2)["code"] != 0                       # hết hạn
    code3 = uy_quyen_tiktok(client, cau_hinh, "Shop E")
    dong_ho["bay_gio"] += 30 * 60 - 1
    assert doi_ma_tiktok(client, cau_hinh, code3)["code"] == 0                       # còn hạn đến giây cuối


def test_tiktok_doi_ma_sai_khoa_ung_dung_hoac_grant_type_bi_tu_choi_va_khong_tieu_ma(client, cau_hinh):
    code = uy_quyen_tiktok(client, cau_hinh, "Shop E")
    assert doi_ma_tiktok(client, cau_hinh, code, app_secret="sai")["code"] != 0
    assert doi_ma_tiktok(client, cau_hinh, code, app_key="sai")["code"] != 0
    assert doi_ma_tiktok(client, cau_hinh, code, grant_type="authorization_code")["code"] != 0   # KHÔNG phải OAuth chuẩn
    assert doi_ma_tiktok(client, cau_hinh, "khong-ton-tai")["code"] != 0
    assert doi_ma_tiktok(client, cau_hinh, code)["code"] == 0                         # mã vẫn còn nguyên


def test_tiktok_uy_quyen_lai_shop_a_cap_token_moi_du_lieu_khong_doi(client, cau_hinh, dong_ho, du_lieu_tiktok):
    cipher_a = du_lieu_tiktok["Shop A"]["shop_cipher"]
    truoc = goi_open_api_tiktok(client, cau_hinh, dong_ho, SEARCH_TIKTOK, cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cipher_a, "POST", "{}")
    assert truoc["code"] == 0 and truoc["data"]["total_count"] > 0
    moi = doi_ma_tiktok(client, cau_hinh, uy_quyen_tiktok(client, cau_hinh, "Shop A"))["data"]["access_token"]
    sau = goi_open_api_tiktok(client, cau_hinh, dong_ho, SEARCH_TIKTOK, moi, cipher_a, "POST", "{}")
    assert sau["data"]["total_count"] == truoc["data"]["total_count"]
    cu = goi_open_api_tiktok(client, cau_hinh, dong_ho, SEARCH_TIKTOK, cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cipher_a, "POST", "{}")
    assert cu["data"]["total_count"] == truoc["data"]["total_count"]        # GIẢ ĐỊNH: token cũ vẫn dùng tới hạn


def test_du_lieu_shop_moi_khong_lam_thay_doi_du_lieu_shop_co_san(client, cau_hinh, dong_ho, du_lieu_shopee, du_lieu_tiktok):
    """Bất biến: số đơn ở máy chủ giả lập (và vì thế số liệu đồng bộ) của Shop A/B/C không đổi dù có thêm shop mới."""
    assert len(du_lieu_shopee["don_hang"]) == 1761                            # đơn Shopee dựng từ CSV mẫu
    assert {ten: len(shop["don_hang"]) for ten, shop in du_lieu_tiktok.items()} == {"Shop A": 5364, "Shop B": 2162}   # 7.526 (§17.1)
    # Dữ liệu dựng sẵn không bị đụng khi thêm shop mới, và shop mới nằm NGOÀI nó.
    uy_quyen_shopee(client, cau_hinh, dong_ho, SHOP_D_ID)
    uy_quyen_tiktok(client, cau_hinh, "Shop E")
    assert len(du_lieu_shopee["don_hang"]) == 1761 and set(du_lieu_tiktok) == {"Shop A", "Shop B"}
