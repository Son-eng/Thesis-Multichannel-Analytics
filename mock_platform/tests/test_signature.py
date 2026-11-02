"""Test chữ ký và timestamp (SPEC §19.3 mục 1–2).

Số liệu mẫu chép NGUYÊN từ tài liệu:
- TikTok: test vector chính thức trong `Sign your API request.md` — bắt buộc pass (§19.3).
- Shopee: ví dụ chuỗi cơ sở trong `shopeeapideveloperguidetomtat (1).md` mục 5.
  Tài liệu không cho chữ ký kỳ vọng, nên chữ ký được so với một lần tính HMAC
  độc lập bằng thư viện chuẩn ngay trong test.
"""

import hashlib
import hmac

import signature

# ---------- TikTok: test vector chính thức ----------

def test_tiktok_test_vector_chinh_thuc():
    app_secret = "e59af819cc"
    tham_so = {"app_key": "29a39d", "timestamp": "1623812664"}
    duong_dan = "/authorization/202309/shops"

    chuoi_bao = app_secret + signature.chuoi_can_ky_tiktok(duong_dan, tham_so) + app_secret
    assert chuoi_bao == "e59af819cc/authorization/202309/shopsapp_key29a39dtimestamp1623812664e59af819cc"
    assert (signature.tinh_chu_ky_tiktok(app_secret, duong_dan, tham_so)
            == "b596b73e0cc6de07ac26f036364178ab16b0a907af13d43f0a0cd2345f582dc8")


def test_tiktok_vi_du_co_shop_cipher_va_body():
    """Ví dụ thứ 2 của tài liệu (Update Shop Webhook): chuỗi sau bước 4."""
    tham_so = {
        "timestamp": "1696909648",
        "shop_cipher": "ROW_xkMbgAAAeVAQra0eZWebFQq5aIK",
        "app_key": "68xu9ks5p4i8",
    }
    body = '{"address":"https://partner.tiktokshop.com","event_type":"PACKAGE_UPDATE"}'
    assert signature.chuoi_can_ky_tiktok("/event/202309/webhooks", tham_so, body) == (
        "/event/202309/webhooksapp_key68xu9ks5p4i8shop_cipherROW_xkMbgAAAeVAQra0eZWebFQq5aIK"
        'timestamp1696909648{"address":"https://partner.tiktokshop.com","event_type":"PACKAGE_UPDATE"}'
    )


def test_tiktok_bo_sign_va_access_token_khoi_chuoi_ky():
    co_ban = {"app_key": "29a39d", "timestamp": "1623812664"}
    them = {**co_ban, "sign": "bat_ky", "access_token": "bat_ky"}
    assert signature.chuoi_can_ky_tiktok("/p", them) == signature.chuoi_can_ky_tiktok("/p", co_ban)


def test_tiktok_body_khac_mot_khoang_trang_la_chu_ky_khac():
    """Bẫy §20.1: phải ký đúng chuỗi body đã gửi, serialize lại là lệch."""
    tham_so = {"app_key": "k", "timestamp": "1"}
    goc = signature.tinh_chu_ky_tiktok("s", "/p", tham_so, '{"a":1}')
    assert signature.tinh_chu_ky_tiktok("s", "/p", tham_so, '{"a": 1}') != goc


# ---------- Shopee ----------

def test_shopee_chuoi_co_so_dung_vi_du_tai_lieu():
    chuoi = signature.chuoi_co_so_shopee(
        2001887, "/api/v2/shop/get_shop_info", 1655714431,
        "59777174636562737266615546704c6d", 14701711,
    )
    assert chuoi == "2001887/api/v2/shop/get_shop_info165571443159777174636562737266615546704c6d14701711"


def test_shopee_public_api_khong_co_token_va_shop():
    assert signature.chuoi_co_so_shopee(2001887, "/api/v2/auth/access_token/get", 1655714431) == (
        "2001887/api/v2/auth/access_token/get1655714431"
    )


def test_shopee_chu_ky_la_hmac_khoa_partner_key():
    chuoi = "2001887/api/v2/shop/get_shop_info165571443159777174636562737266615546704c6d14701711"
    mong_doi = hmac.new(b"khoa_thu", chuoi.encode(), hashlib.sha256).hexdigest()
    assert signature.tinh_chu_ky_shopee(
        "khoa_thu", 2001887, "/api/v2/shop/get_shop_info", 1655714431,
        "59777174636562737266615546704c6d", 14701711,
    ) == mong_doi


def test_shopee_doi_bat_ky_thanh_phan_nao_la_chu_ky_khac():
    goc = signature.tinh_chu_ky_shopee("k", 1, "/a", 100, "tok", 9)
    assert signature.tinh_chu_ky_shopee("k2", 1, "/a", 100, "tok", 9) != goc
    assert signature.tinh_chu_ky_shopee("k", 1, "/b", 100, "tok", 9) != goc
    assert signature.tinh_chu_ky_shopee("k", 1, "/a", 101, "tok", 9) != goc
    assert signature.tinh_chu_ky_shopee("k", 1, "/a", 100, "tok2", 9) != goc
    assert signature.tinh_chu_ky_shopee("k", 1, "/a", 100, "tok", 8) != goc


# ---------- So chữ ký, timestamp ----------

def test_chu_ky_khop():
    assert signature.chu_ky_khop("abc", "abc")
    assert not signature.chu_ky_khop("abd", "abc")
    assert not signature.chu_ky_khop(None, "abc")


def test_timestamp_trong_va_ngoai_5_phut():
    bay_gio = 1_700_000_000
    assert signature.thoi_gian_hop_le(bay_gio, bay_gio)
    assert signature.thoi_gian_hop_le(str(bay_gio - 300), bay_gio)     # đúng 5 phút: còn hợp lệ
    assert not signature.thoi_gian_hop_le(bay_gio - 301, bay_gio)
    assert not signature.thoi_gian_hop_le(bay_gio + 301, bay_gio)      # timestamp ở tương lai cũng chặn
    assert not signature.thoi_gian_hop_le("abc", bay_gio)
    assert not signature.thoi_gian_hop_le(None, bay_gio)
