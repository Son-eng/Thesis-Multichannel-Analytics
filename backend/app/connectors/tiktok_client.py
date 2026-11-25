"""Connector TikTok Shop; body POST serialize đúng một lần rồi dùng cùng chuỗi để ký và gửi, nếu không sẽ sai chữ ký."""

import hashlib
import hmac
import json
import time

import httpx2

from app.connectors import http_retry

DUONG_DAN_ORDERS_SEARCH = "/order/202309/orders/search"
DUONG_DAN_FINANCE = "/finance/202501/orders/{order_id}/statement_transactions"
DUONG_DAN_LAM_MOI_TOKEN = "/api/v2/token/refresh"
DUONG_DAN_AFFILIATE = "/affiliate_seller/202410/orders/search"

SO_DON_MOI_TRANG = 100
# Vẫn chia cửa sổ 15 ngày để lỗi giữa chừng chỉ phải kéo lại một cửa sổ.
CUA_SO_GIAY = 15 * 24 * 60 * 60
TRANG_THAI_DA_QUYET_TOAN = "COMPLETED"

# Mã lỗi token là mã quy ước của máy chủ giả lập; chạy với sàn thật phải thay bằng mã thật.
MA_TOKEN_KHONG_HOP_LE = {9990003, 9990004}


class LoiApiTikTok(Exception):
    def __init__(self, duong_dan, ma_loi, thong_diep):
        super().__init__(f"TikTok {duong_dan}: {ma_loi} — {thong_diep}")
        self.duong_dan = duong_dan
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


def chia_cua_so(tu_luc, den_luc, do_dai_giay=CUA_SO_GIAY):
    """Chia [tu_luc, den_luc) thành các cửa sổ [ge, lt) nối tiếp."""
    cac_cua_so = []
    dau = tu_luc
    while dau < den_luc:
        cuoi = min(dau + do_dai_giay, den_luc)
        cac_cua_so.append((dau, cuoi))
        dau = cuoi
    return cac_cua_so


class TikTokClient:
    def __init__(self, base_url, auth_base_url, app_key, app_secret, shop_cipher, access_token,
                 khi_can_lam_moi=None, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                 cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_cipher = shop_cipher
        self.access_token = access_token
        self.khi_can_lam_moi = khi_can_lam_moi
        self.so_lan_gui_toi_da = so_lan_gui_toi_da
        self.cho_co_ban_giay = cho_co_ban_giay
        self.ham_ngu = ham_ngu
        # Số yêu cầu HTTP đã gửi, kể cả lần thử lại.
        self.so_lan_goi = 0
        self._http = httpx2.Client(base_url=base_url, timeout=30)
        self._http_auth = httpx2.Client(base_url=auth_base_url, timeout=30)

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        self.close()

    def close(self):
        self._http.close()
        self._http_auth.close()

    def ky(self, duong_dan, tham_so, than):
        cac_cap = "".join(f"{khoa}{tham_so[khoa]}" for khoa in sorted(tham_so) if khoa not in ("sign", "access_token"))
        chuoi_bao = self.app_secret + duong_dan + cac_cap + than + self.app_secret
        return hmac.new(self.app_secret.encode("utf-8"), chuoi_bao.encode("utf-8"), hashlib.sha256).hexdigest()

    def _gui_mot_lan(self, phuong_thuc, duong_dan, tham_so_rieng, than):
        """Ký lại với timestamp mới mỗi lần thử."""
        def gui():
            self.so_lan_goi += 1
            tham_so = {"app_key": self.app_key, "timestamp": str(int(time.time())),
                       "shop_cipher": self.shop_cipher, **(tham_so_rieng or {})}
            tham_so["sign"] = self.ky(duong_dan, tham_so, than)
            # gửi đúng chuỗi đã ký, không để httpx2 tự serialize lại
            return self._http.request(
                phuong_thuc, duong_dan, params=tham_so, content=than.encode("utf-8") if than else None,
                headers={"content-type": "application/json", "x-tts-access-token": self.access_token},
            )
        phan_hoi = http_retry.goi_co_thu_lai(
            gui, http_retry.phan_loai_tiktok, self.so_lan_gui_toi_da, self.cho_co_ban_giay, self.ham_ngu
        )
        return http_retry.doc_json_an_toan(phan_hoi)

    def goi(self, phuong_thuc, duong_dan, tham_so_rieng=None, than=""):
        """Gặp mã token sai hoặc hết hạn thì làm mới đúng một lần rồi gọi lại."""
        ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than)
        if ket_qua.get("code") in MA_TOKEN_KHONG_HOP_LE and self.khi_can_lam_moi is not None:
            self.access_token = self.khi_can_lam_moi()
            ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than)
        if ket_qua.get("code") != 0:
            raise LoiApiTikTok(duong_dan, ket_qua.get("code"), ket_qua.get("message", ""))
        return ket_qua

    def goi_lam_moi_token(self, refresh_token, shop_ref):
        """TikTok không trả hạn sống của token, token_store tự tính."""
        def gui():
            self.so_lan_goi += 1
            return self._http_auth.get(DUONG_DAN_LAM_MOI_TOKEN, params={
                "app_key": self.app_key, "app_secret": self.app_secret,
                "refresh_token": refresh_token, "grant_type": "refresh_token",
            })
        ket_qua = http_retry.doc_json_an_toan(http_retry.goi_co_thu_lai(
            gui, http_retry.phan_loai_tiktok, self.so_lan_gui_toi_da, self.cho_co_ban_giay, self.ham_ngu
        ))
        if ket_qua.get("code") != 0:
            raise LoiApiTikTok(DUONG_DAN_LAM_MOI_TOKEN, ket_qua.get("code"), ket_qua.get("message", ""))
        return ket_qua["data"]

    def lay_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Sắp theo chính trường đang lọc để phân trang ổn định; không khử trùng để lỗi chia cửa sổ lộ ra."""
        cac_don = []
        for ge, lt in chia_cua_so(tu_luc, den_luc):
            than = json.dumps({f"{truong_thoi_gian}_ge": ge, f"{truong_thoi_gian}_lt": lt}, separators=(",", ":"))
            page_token = ""
            while True:
                du_lieu = self.goi("POST", DUONG_DAN_ORDERS_SEARCH, {
                    "page_size": str(SO_DON_MOI_TRANG), "page_token": page_token,
                    "sort_field": truong_thoi_gian, "sort_order": "ASC",
                }, than)["data"]
                cac_don += du_lieu["orders"]
                page_token = du_lieu["next_page_token"]
                if page_token == "":
                    break
        return cac_don

    def lay_finance(self, ma_don):
        return self.goi("GET", DUONG_DAN_FINANCE.format(order_id=ma_don))["data"]

    def lay_don_affiliate(self, tu_luc, den_luc):
        cac_don = []
        for ge, lt in chia_cua_so(tu_luc, den_luc):
            than = json.dumps({"create_time_ge": ge, "create_time_lt": lt}, separators=(",", ":"))
            page_token = ""
            while True:
                du_lieu = self.goi("POST", DUONG_DAN_AFFILIATE, {
                    "page_size": str(SO_DON_MOI_TRANG), "page_token": page_token,
                }, than)["data"]
                cac_don += du_lieu["orders"]
                page_token = du_lieu["next_page_token"]
                if page_token == "":
                    break
        return cac_don

    def keo_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Chỉ gọi Finance cho đơn COMPLETED vì dữ liệu quyết toán chỉ có sau khi hoàn tất; TikTok không có thông tin hoàn hàng ở chỗ khác."""
        cac_don = self.lay_don(tu_luc, den_luc, truong_thoi_gian)
        finance = {
            don["id"]: self.lay_finance(don["id"])
            for don in cac_don if don["status"] == TRANG_THAI_DA_QUYET_TOAN
        }
        if cac_don:
            ngay_tao = [don["create_time"] for don in cac_don]
            cac_affiliate = self.lay_don_affiliate(min(ngay_tao), max(ngay_tao) + 1)
        else:
            cac_affiliate = []
        return {"don_hang": cac_don, "finance": finance, "affiliate": cac_affiliate}
