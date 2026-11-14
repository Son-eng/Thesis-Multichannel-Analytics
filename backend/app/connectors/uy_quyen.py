"""Connector cho luồng ỦY QUYỀN gian hàng của hai sàn (chỉ dẫn 026, SPEC §22).

CHỈ nói chuyện HTTP, không biết CSDL (cùng nguyên tắc với hai client đồng bộ, §20.1): dựng địa chỉ trang ủy quyền,
đổi mã ủy quyền lấy token, lấy danh sách shop TikTok. Việc ghi `platform_tokens` là của `services/ket_noi_gian_hang.py`.

Khuôn đã xác minh ở giai đoạn 0 (báo cáo 026 mục a, nguồn trong `Pipeline/`):
- Shopee: trang `GET {SHOPEE_AUTH_PAGE_BASE_URL}/api/v2/shop/auth_partner?partner_id&timestamp&sign&redirect`
  (ký như Public API: `partner_id + path + timestamp`); sàn chuyển về `redirect` kèm `code` + `shop_id`;
  đổi mã bằng `POST /api/v2/auth/token/get` (body `code`, `partner_id`, `shop_id`).
- TikTok: trang `GET {TIKTOK_AUTH_PAGE_BASE_URL}/open/authorize?service_id=…` (không ký); sàn chuyển về Redirect URL
  đã đăng ký kèm `code`; đổi mã bằng `GET /api/v2/token/get` (`app_key`, `app_secret`, `auth_code`,
  `grant_type=authorized_code`); danh sách shop bằng `GET /authorization/202309/shops` (header `x-tts-access-token`).
Chưa xác minh (GIẢ ĐỊNH, ghi ở SPEC §16): sàn có trả lại `state` / nối `&code=` vào redirect đã có query hay không.

Khóa ứng dụng (partner_key, app_secret) chỉ dùng để ký / gọi máy chủ-tới-máy chủ; URL đưa cho trình duyệt chỉ chứa
`partner_id`, `timestamp`, `sign` (chữ ký, không phải khóa) và `service_id` — những thứ sàn yêu cầu công khai.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx2

from app.connectors import http_retry
from app.connectors.shopee_client import LoiApiShopee
from app.connectors.tiktok_client import LoiApiTikTok

DUONG_DAN_SHOPEE_TRANG = "/api/v2/shop/auth_partner"
DUONG_DAN_SHOPEE_DOI_MA = "/api/v2/auth/token/get"
DUONG_DAN_TIKTOK_TRANG = "/open/authorize"
DUONG_DAN_TIKTOK_DOI_MA = "/api/v2/token/get"
DUONG_DAN_TIKTOK_SHOPS = "/authorization/202309/shops"


def _ky_shopee_public(partner_key, partner_id, duong_dan, timestamp):
    chuoi = f"{partner_id}{duong_dan}{timestamp}"
    return hmac.new(partner_key.encode("utf-8"), chuoi.encode("utf-8"), hashlib.sha256).hexdigest()


def _ky_tiktok(app_secret, duong_dan, tham_so, than=""):
    cac_cap = "".join(f"{k}{tham_so[k]}" for k in sorted(tham_so) if k not in ("sign", "access_token"))
    chuoi_bao = app_secret + duong_dan + cac_cap + than + app_secret
    return hmac.new(app_secret.encode("utf-8"), chuoi_bao.encode("utf-8"), hashlib.sha256).hexdigest()


def tao_url_uy_quyen_shopee(cau_hinh, redirect, bay_gio=None):
    """Địa chỉ trang ủy quyền Shopee (đã ký) để mở bằng trình duyệt; `redirect` là nơi sàn chuyển về."""
    timestamp = int(bay_gio if bay_gio is not None else time.time())
    tham_so = {
        "partner_id": cau_hinh.SHOPEE_PARTNER_ID,
        "timestamp": timestamp,
        "sign": _ky_shopee_public(cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.SHOPEE_PARTNER_ID, DUONG_DAN_SHOPEE_TRANG, timestamp),
        "redirect": redirect,
    }
    return f"{cau_hinh.SHOPEE_AUTH_PAGE_BASE_URL.rstrip('/')}{DUONG_DAN_SHOPEE_TRANG}?{urlencode(tham_so)}"


def tao_url_uy_quyen_tiktok(cau_hinh, state):
    """Địa chỉ trang ủy quyền TikTok. `state` là mã chống giả mạo do ta tự gắn (chưa xác minh sàn thật trả lại)."""
    tham_so = {"service_id": cau_hinh.TIKTOK_SERVICE_ID, "state": state}
    return f"{cau_hinh.TIKTOK_AUTH_PAGE_BASE_URL.rstrip('/')}{DUONG_DAN_TIKTOK_TRANG}?{urlencode(tham_so)}"


def doi_ma_shopee(cau_hinh, code, shop_id, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                  cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
    """Đổi `code` (một lần, sống 10 phút) lấy token Shopee.

    Trả: dict `{access_token, refresh_token, expire_in, shop_id_list}` (trong `response`, cùng khuôn endpoint làm mới).
    Lỗi: LoiApiShopee (sàn từ chối, ví dụ `invalid_code`), http_retry.LoiHetLanThuLai (quá tải mãi).
    """
    def gui():
        timestamp = int(time.time())
        tham_so = {
            "partner_id": cau_hinh.SHOPEE_PARTNER_ID, "timestamp": timestamp,
            "sign": _ky_shopee_public(cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.SHOPEE_PARTNER_ID, DUONG_DAN_SHOPEE_DOI_MA, timestamp),
        }
        than = {"code": code, "partner_id": cau_hinh.SHOPEE_PARTNER_ID}
        if shop_id:
            than["shop_id"] = int(shop_id)
        return http.request("POST", DUONG_DAN_SHOPEE_DOI_MA, params=tham_so, json=than)

    with httpx2.Client(base_url=cau_hinh.SHOPEE_BASE_URL, timeout=30) as http:
        phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_shopee, so_lan_gui_toi_da, cho_co_ban_giay, ham_ngu)
    ket_qua = http_retry.doc_json_an_toan(phan_hoi)
    if ket_qua.get("error"):
        raise LoiApiShopee(DUONG_DAN_SHOPEE_DOI_MA, ket_qua["error"], ket_qua.get("message", ""))
    return ket_qua["response"]


def doi_ma_tiktok(cau_hinh, auth_code, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                  cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
    """Đổi `auth_code` (một lần, sống 30 phút) lấy token TikTok. Trả dict `data` {access_token, refresh_token}.

    Lỗi: LoiApiTikTok (sàn từ chối), http_retry.LoiHetLanThuLai.
    """
    def gui():
        return http.get(DUONG_DAN_TIKTOK_DOI_MA, params={
            "app_key": cau_hinh.TIKTOK_APP_KEY, "app_secret": cau_hinh.TIKTOK_APP_SECRET,
            "auth_code": auth_code,
            # Đúng là 'authorized_code' — KHÔNG phải 'authorization_code' như OAuth chuẩn (Pipeline/Tiktok/tiktok_auth.py).
            "grant_type": "authorized_code",
        })

    with httpx2.Client(base_url=cau_hinh.TIKTOK_AUTH_BASE_URL, timeout=30) as http:
        phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_tiktok, so_lan_gui_toi_da, cho_co_ban_giay, ham_ngu)
    ket_qua = http_retry.doc_json_an_toan(phan_hoi)
    if ket_qua.get("code") != 0:
        raise LoiApiTikTok(DUONG_DAN_TIKTOK_DOI_MA, ket_qua.get("code"), ket_qua.get("message", ""))
    return ket_qua["data"]


def lay_shop_tiktok(cau_hinh, access_token, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                    cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
    """Các shop mà token này được ủy quyền: list `{id, name, region, seller_type, cipher, code}`.

    Cần `cipher` (= shop_ref trong platform_tokens) và `name` — hai thứ chỉ có sau khi ủy quyền.
    """
    def gui():
        tham_so = {"app_key": cau_hinh.TIKTOK_APP_KEY, "timestamp": str(int(time.time()))}
        tham_so["sign"] = _ky_tiktok(cau_hinh.TIKTOK_APP_SECRET, DUONG_DAN_TIKTOK_SHOPS, tham_so)
        return http.get(DUONG_DAN_TIKTOK_SHOPS, params=tham_so, headers={
            "content-type": "application/json", "x-tts-access-token": access_token})

    with httpx2.Client(base_url=cau_hinh.TIKTOK_BASE_URL, timeout=30) as http:
        phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_tiktok, so_lan_gui_toi_da, cho_co_ban_giay, ham_ngu)
    ket_qua = http_retry.doc_json_an_toan(phan_hoi)
    if ket_qua.get("code") != 0:
        raise LoiApiTikTok(DUONG_DAN_TIKTOK_SHOPS, ket_qua.get("code"), ket_qua.get("message", ""))
    return ket_qua["data"]["shops"]
