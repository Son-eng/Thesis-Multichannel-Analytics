"""Gọi thử máy chủ giả lập đang chạy như một client thật, ký lại độc lập theo tài liệu; dùng để demo, không phải luồng chạy hệ thống.
Chạy (từ mock_platform/, máy chủ ở cổng 8001): ..\\backend\\.venv\\Scripts\\python scripts\\goi_thu.py [tom-tat|keo-du|loi|lam-moi|dem-loi 300]
Refresh Shopee chỉ dùng được một lần: chạy lam-moi lần hai sẽ bị từ chối, khởi động lại máy chủ để có lại token.
"""

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

THU_MUC_MOCK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THU_MUC_MOCK))
import config  # noqa: E402

DAU_THANG_7 = 1782838800
DAU_NAM_2026 = 1767200400
MUOI_LAM_NGAY = 15 * 86400


def gui(url_goc, phuong_thuc, duong_dan, tham_so, than=None, header=None):
    url = url_goc + duong_dan + "?" + urllib.parse.urlencode(tham_so)
    du_lieu = None if than is None else than.encode("utf-8")
    yeu_cau = urllib.request.Request(url, data=du_lieu, method=phuong_thuc, headers=header or {})
    try:
        with urllib.request.urlopen(yeu_cau, timeout=30) as phan_hoi:
            return phan_hoi.status, json.loads(phan_hoi.read())
    except urllib.error.HTTPError as loi:
        return loi.code, json.loads(loi.read())


class Shopee:
    """Client Shopee: ký `partner_id + path + timestamp [+ access_token + shop_id]` bằng HMAC-SHA256."""

    def __init__(self, url_goc, cau_hinh):
        self.url_goc = url_goc
        self.ch = cau_hinh
        self.access_token = cau_hinh.SHOPEE_ACCESS_TOKEN

    def tham_so_chung(self, duong_dan, la_shop_api=True, timestamp=None):
        timestamp = int(time.time()) if timestamp is None else timestamp
        access_token, shop_id = (self.access_token, self.ch.SHOPEE_SHOP_ID) if la_shop_api else ("", "")
        chuoi = f"{self.ch.SHOPEE_PARTNER_ID}{duong_dan}{timestamp}{access_token}{shop_id}"
        chu_ky = hmac.new(self.ch.SHOPEE_PARTNER_KEY.encode(), chuoi.encode(), hashlib.sha256).hexdigest()
        tham_so = {"partner_id": self.ch.SHOPEE_PARTNER_ID, "timestamp": timestamp, "sign": chu_ky}
        if la_shop_api:
            tham_so.update(access_token=access_token, shop_id=shop_id)
        return tham_so

    def get(self, duong_dan, tham_so_rieng, **sua):
        return gui(self.url_goc, "GET", duong_dan, {**self.tham_so_chung(duong_dan, **sua), **tham_so_rieng})

    def post(self, duong_dan, than, la_shop_api=True, tham_so_sua=None):
        tham_so = {**self.tham_so_chung(duong_dan, la_shop_api), **(tham_so_sua or {})}
        return gui(self.url_goc, "POST", duong_dan, tham_so, json.dumps(than), {"content-type": "application/json"})

    def danh_sach(self, tu_luc, den_luc, cursor="", page_size=100):
        return self.get("/api/v2/order/get_order_list", {
            "time_range_field": "create_time", "time_from": tu_luc, "time_to": den_luc,
            "page_size": page_size, "cursor": cursor,
        })


class TikTok:
    """Client TikTok một shop: ký path + {key}{value} (sắp xếp, bỏ sign/access_token) + body, bọc app_secret."""

    def __init__(self, url_goc, cau_hinh, shop_cipher, access_token):
        self.url_goc = url_goc
        self.ch = cau_hinh
        self.shop_cipher = shop_cipher
        self.access_token = access_token

    def goi(self, phuong_thuc, duong_dan, tham_so_rieng=None, than="", timestamp=None):
        tham_so = {
            "app_key": self.ch.TIKTOK_APP_KEY,
            "timestamp": str(int(time.time()) if timestamp is None else timestamp),
            "shop_cipher": self.shop_cipher,
            **(tham_so_rieng or {}),
        }
        chuoi = duong_dan + "".join(f"{k}{tham_so[k]}" for k in sorted(tham_so)) + than
        bao = self.ch.TIKTOK_APP_SECRET + chuoi + self.ch.TIKTOK_APP_SECRET
        tham_so["sign"] = hmac.new(self.ch.TIKTOK_APP_SECRET.encode(), bao.encode(), hashlib.sha256).hexdigest()
        header = {"content-type": "application/json", "x-tts-access-token": self.access_token}
        # Body đã serialize một lần ở nơi gọi; ký và gửi cùng một chuỗi.
        return gui(self.url_goc, phuong_thuc, duong_dan, tham_so, than if phuong_thuc == "POST" else None, header)

    def tim_don(self, loc, page_size=100, page_token="", **them):
        than = json.dumps(loc, separators=(",", ":"))
        return self.goi("POST", "/order/202309/orders/search",
                        {"page_size": str(page_size), "page_token": page_token, **them}, than)

    def finance(self, ma_don):
        return self.goi("GET", f"/finance/202501/orders/{ma_don}/statement_transactions")


def cac_shop_tiktok(url_goc, ch):
    return {
        "Shop A": TikTok(url_goc, ch, "MOCK_CIPHER_SHOP_A", ch.TIKTOK_SHOP_A_ACCESS_TOKEN),
        "Shop B": TikTok(url_goc, ch, "MOCK_CIPHER_SHOP_B", ch.TIKTOK_SHOP_B_ACCESS_TOKEN),
    }


def lam_moi_tiktok(url_goc, ch, refresh_token):
    return gui(url_goc, "GET", "/api/v2/token/refresh", {
        "app_key": ch.TIKTOK_APP_KEY, "app_secret": ch.TIKTOK_APP_SECRET,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    })


def in_dong(nhan, ma_http, phan_hoi, them=""):
    ma = phan_hoi.get("error", phan_hoi.get("code"))
    print(f"  {nhan:<46} HTTP {ma_http}  {('ma=' + repr(ma)):<26} {them}")


def tom_tat(url_goc, ch):
    """Gọi mỗi endpoint một lần, in kết quả ngắn."""
    shopee = Shopee(url_goc, ch)
    print("Shopee")
    ma_http, ph = shopee.danh_sach(DAU_THANG_7, DAU_THANG_7 + MUOI_LAM_NGAY, page_size=3)
    cac_ma = [d["order_sn"] for d in ph.get("response", {}).get("order_list", [])]
    in_dong("get_order_list (01–16/07, 3 đơn)", ma_http, ph, f"more={ph.get('response', {}).get('more')} {cac_ma}")
    ma_http, ph = shopee.get("/api/v2/order/get_order_detail",
                             {"order_sn_list": ",".join(cac_ma), "response_optional_fields": "item_list"})
    so_sp = sum(len(d["item_list"]) for d in ph.get("response", {}).get("order_list", []))
    in_dong("get_order_detail (3 đơn trên)", ma_http, ph, f"{so_sp} dòng sản phẩm")
    ma_http, ph = shopee.post("/api/v2/payment/get_escrow_detail_batch", {"order_sn_list": cac_ma})
    co_escrow = sum("escrow_detail" in p for p in ph.get("response", []))
    in_dong("get_escrow_detail_batch (3 đơn trên)", ma_http, ph, f"{co_escrow} đơn có escrow, warning={ph.get('warning')}")

    print("TikTok")
    for ten, khach in cac_shop_tiktok(url_goc, ch).items():
        ma_http, ph = khach.tim_don({"create_time_ge": DAU_NAM_2026, "create_time_lt": int(time.time())}, page_size=2)
        in_dong(f"orders/search {ten} (2 đơn)", ma_http, ph, f"total_count={ph.get('data', {}).get('total_count')}")
        _, ph = khach.tim_don({"order_status": "COMPLETED"}, page_size=1)
        don = ph.get("data", {}).get("orders", [])
        if don:
            ma_http, ph = khach.finance(don[0]["id"])
            in_dong(f"Finance {ten} đơn {don[0]['id']}", ma_http, ph, f"{ph.get('data', {}).get('total_count')} giao dịch SKU")


def keo_du(url_goc, ch):
    """Kéo hết dữ liệu như connector sẽ làm, đếm và in để đối chiếu với CSV."""
    shopee = Shopee(url_goc, ch)
    cac_ma = []
    tu_luc, het_luc = DAU_THANG_7, DAU_THANG_7 + 62 * 86400
    while tu_luc < het_luc:
        den_luc = min(tu_luc + MUOI_LAM_NGAY, het_luc)
        cursor = ""
        while True:
            _, ph = shopee.danh_sach(tu_luc, den_luc, cursor)
            cac_ma += [d["order_sn"] for d in ph["response"]["order_list"]]
            if not ph["response"]["more"]:
                break
            cursor = ph["response"]["next_cursor"]
        tu_luc = den_luc + 1
    so_dong = 0
    for dau in range(0, len(cac_ma), 50):
        _, ph = shopee.get("/api/v2/order/get_order_detail",
                           {"order_sn_list": ",".join(cac_ma[dau:dau + 50]), "response_optional_fields": "item_list"})
        so_dong += sum(len(d["item_list"]) for d in ph["response"]["order_list"])
    print(f"Shopee: {len(cac_ma)} đơn ({len(set(cac_ma))} không trùng), {so_dong} dòng sản phẩm   [CSV: 1761 đơn, 1774 dòng]")

    tong_hoan = 0
    for ten, khach in cac_shop_tiktok(url_goc, ch).items():
        cac_don, page_token = [], ""
        while True:
            _, ph = khach.tim_don({"create_time_ge": DAU_NAM_2026, "create_time_lt": int(time.time())},
                                  page_token=page_token, sort_order="ASC")
            cac_don += ph["data"]["orders"]
            page_token = ph["data"]["next_page_token"]
            if page_token == "":
                break
        so_dong = len({(d["id"], li["sku_id"]) for d in cac_don for li in d["line_items"]})
        so_hoan = 0
        for don in cac_don:
            if don["status"] == "COMPLETED":
                _, ph = khach.finance(don["id"])
                so_hoan += sum(gd["revenue_breakdown"]["refund_subtotal_before_discount_amount"] != "0"
                               for gd in ph["data"]["sku_transactions"])
        tong_hoan += so_hoan
        print(f"TikTok {ten}: {len(cac_don)} đơn, {so_dong} dòng, {so_hoan} dòng hoàn (Finance)")
    print(f"TikTok tổng dòng hoàn: {tong_hoan}   [CSV: 7526 đơn, 7540 dòng, 139 dòng hoàn]")


def loi(url_goc, ch):
    """Gửi các yêu cầu sai cố ý, in mã lỗi máy chủ trả."""
    shopee = Shopee(url_goc, ch)
    bay_gio = int(time.time())
    print("Shopee")
    in_dong("page_size = 101", *shopee.danh_sach(DAU_THANG_7, DAU_THANG_7 + 86400, page_size=101))
    in_dong("cửa sổ 15 ngày + 1 giây", *shopee.danh_sach(DAU_THANG_7, DAU_THANG_7 + MUOI_LAM_NGAY + 1))
    in_dong("order_sn_list 51 mã", *shopee.get("/api/v2/order/get_order_detail",
                                                {"order_sn_list": ",".join(f"MA{i}" for i in range(51))}))
    in_dong("timestamp lệch 301 giây", *shopee.get("/api/v2/order/get_order_detail", {"order_sn_list": "X"},
                                                    timestamp=bay_gio - 301))
    tham_so = shopee.tham_so_chung("/api/v2/order/get_order_detail")
    in_dong("sai chữ ký", *gui(url_goc, "GET", "/api/v2/order/get_order_detail",
                               {**tham_so, "sign": "0" * 64, "order_sn_list": "X"}))
    shopee.access_token = "token_bia"
    in_dong("access_token sai", *shopee.get("/api/v2/order/get_order_detail", {"order_sn_list": "X"}))

    print("TikTok")
    khach = cac_shop_tiktok(url_goc, ch)["Shop A"]
    in_dong("page_size = 101", *khach.tim_don({}, page_size=101))
    in_dong("timestamp lệch 301 giây", *khach.goi("POST", "/order/202309/orders/search",
                                                   {"page_size": "10"}, "{}", timestamp=bay_gio - 301))
    khach.access_token = ch.TIKTOK_SHOP_B_ACCESS_TOKEN
    in_dong("token Shop B gửi cho Shop A", *khach.tim_don({}))


def lam_moi(url_goc, ch):
    """Làm mới token 2 sàn; Shopee thử lại bằng refresh cũ để thấy bị từ chối."""
    shopee = Shopee(url_goc, ch)
    than = {"refresh_token": ch.SHOPEE_REFRESH_TOKEN, "partner_id": ch.SHOPEE_PARTNER_ID, "shop_id": ch.SHOPEE_SHOP_ID}
    print("Shopee")
    ma_http, ph = shopee.post("/api/v2/auth/access_token/get", than, la_shop_api=False)
    in_dong("làm mới lần 1 (refresh trong .env)", ma_http, ph, f"expire_in={ph.get('response', {}).get('expire_in')}")
    in_dong("làm mới lần 2 (CÙNG refresh cũ)", *shopee.post("/api/v2/auth/access_token/get", than, la_shop_api=False))
    print("TikTok")
    ma_http, ph = lam_moi_tiktok(url_goc, ch, ch.TIKTOK_SHOP_A_REFRESH_TOKEN)
    in_dong("làm mới Shop A", ma_http, ph, f"trường trả về: {sorted(ph.get('data', {}))}")
    in_dong("làm mới Shop A lần 2 (refresh cũ vẫn dùng được)", *lam_moi_tiktok(url_goc, ch, ch.TIKTOK_SHOP_A_REFRESH_TOKEN))
    in_dong("refresh bịa", *lam_moi_tiktok(url_goc, ch, "khong_ton_tai"))


def dem_loi(url_goc, ch, so_lan):
    shopee = Shopee(url_goc, ch)
    khach = cac_shop_tiktok(url_goc, ch)["Shop A"]
    loi_shopee = sum(
        shopee.get("/api/v2/order/get_order_detail", {"order_sn_list": "X"})[0] == 429 for _ in range(so_lan)
    )
    loi_tiktok = sum(khach.tim_don({}, page_size=1)[1]["code"] == 36009002 for _ in range(so_lan))
    print(f"Shopee: {loi_shopee}/{so_lan} yêu cầu bị HTTP 429 error_rate_limit ({loi_shopee / so_lan:.1%})")
    print(f"TikTok: {loi_tiktok}/{so_lan} yêu cầu bị code 36009002 ({loi_tiktok / so_lan:.1%})")


def main():
    bo_doc = argparse.ArgumentParser(description="Gọi thử máy chủ giả lập đang chạy.")
    bo_doc.add_argument("che_do", nargs="?", default="tom-tat", choices=["tom-tat", "keo-du", "loi", "lam-moi", "dem-loi"])
    bo_doc.add_argument("so_lan", nargs="?", type=int, default=300, help="số yêu cầu mỗi sàn cho dem-loi")
    bo_doc.add_argument("--url", default="http://127.0.0.1:8001")
    tham_so = bo_doc.parse_args()
    ch = config.doc_cau_hinh()

    if tham_so.che_do == "tom-tat":
        tom_tat(tham_so.url, ch)
    elif tham_so.che_do == "keo-du":
        keo_du(tham_so.url, ch)
    elif tham_so.che_do == "loi":
        loi(tham_so.url, ch)
    elif tham_so.che_do == "lam-moi":
        lam_moi(tham_so.url, ch)
    else:
        dem_loi(tham_so.url, ch, tham_so.so_lan)


if __name__ == "__main__":
    main()
