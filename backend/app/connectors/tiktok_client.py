"""Connector TikTok Shop — ký, gửi, thử lại, phân trang, làm mới token (SPEC §20.1–§20.3, §19.2).

CHỈ nói chuyện HTTP: trả JSON thô, không đánh `is_returned`, không gom trạng
thái (§18.3 — việc của bước 10). Không biết CSDL: cùng cách callback làm mới
token với ShopeeClient (§20.1).

Thứ tự gọi trong một lượt, cho MỘT shop (§20.2):
    lay_don()      orders/search, chia cửa sổ [ge, lt), đi hết page_token
    lay_finance()  statement_transactions — chỉ gọi cho đơn COMPLETED
`keo_don()` gọi lần lượt cả hai.

Thuật toán ký (`Pipeline/Tiktok/Authorization/Sign your API request.md`):
    HMAC-SHA256(app_secret, app_secret + path + {key}{value}… + body + app_secret)
    — key sắp xếp alphabet, bỏ `sign` và `access_token`; access_token gửi ở
    header `x-tts-access-token`, không ký.
Body POST được serialize ĐÚNG MỘT LẦN rồi dùng cùng chuỗi đó để ký và gửi
(§20.1): để thư viện tự serialize lại từ dict có thể đổi khoảng trắng → sai chữ ký.
"""

import hashlib
import hmac
import json
import time

import httpx2

from app.connectors import http_retry

DUONG_DAN_ORDERS_SEARCH = "/order/202309/orders/search"
DUONG_DAN_FINANCE = "/finance/202501/orders/{order_id}/statement_transactions"
DUONG_DAN_LAM_MOI_TOKEN = "/api/v2/token/refresh"

SO_DON_MOI_TRANG = 100
# Tài liệu orders/search không giới hạn độ dài khoảng thời gian. Vẫn chia
# cửa sổ 15 ngày như Shopee: mỗi lượt phân trang ngắn, lỗi giữa chừng chỉ phải
# kéo lại một cửa sổ, và hai connector cùng một cách nghĩ.
CUA_SO_GIAY = 15 * 24 * 60 * 60
TRANG_THAI_DA_QUYET_TOAN = "COMPLETED"

# Mã "token sai / hết hạn" → làm mới một lần rồi gọi lại. Đây là MÃ QUY ƯỚC
# của máy chủ giả lập (§19.2, §16 mục 7): tài liệu TikTok đã lưu không có mã
# thật. Chạy với sàn thật thì phải thay tập này bằng mã thật (SDK EcomPHP gom
# lỗi token vào nhóm bắt đầu bằng 105).
MA_TOKEN_KHONG_HOP_LE = {9990003, 9990004}


class LoiApiTikTok(Exception):
    """Sàn trả `code` khác 0 không thử lại được. `ma_loi` là trường `code`."""

    def __init__(self, duong_dan, ma_loi, thong_diep):
        super().__init__(f"TikTok {duong_dan}: {ma_loi} — {thong_diep}")
        self.duong_dan = duong_dan
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


def chia_cua_so(tu_luc, den_luc, do_dai_giay=CUA_SO_GIAY):
    """Chia [tu_luc, den_luc) thành các cửa sổ [ge, lt) nối tiếp.

    Nhận: 2 mốc epoch giây; độ dài tối đa mỗi cửa sổ.
    Trả: list (ge, lt). Cửa sổ sau bắt đầu ĐÚNG TẠI lt của cửa sổ trước — vì
    TikTok lấy mốc đầu, không lấy mốc cuối (tài liệu: "on or after" /
    "before"; §20.2). Bắt đầu tại lt + 1 thì đơn nằm đúng mốc lt bị sót.
    Khác Shopee (`to + 1`) vì Shopee lấy cả hai đầu.
    """
    cac_cua_so = []
    dau = tu_luc
    while dau < den_luc:
        cuoi = min(dau + do_dai_giay, den_luc)
        cac_cua_so.append((dau, cuoi))
        dau = cuoi
    return cac_cua_so


class TikTokClient:
    """Connector cho MỘT shop TikTok (một shop_cipher, một access_token)."""

    def __init__(self, base_url, auth_base_url, app_key, app_secret, shop_cipher, access_token,
                 khi_can_lam_moi=None, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                 cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
        """Nhận:
            base_url — open-api (đơn, Finance); auth_base_url — máy chủ auth
                (làm mới token). Với máy chủ giả lập hai địa chỉ trùng nhau.
            app_key, app_secret, shop_cipher — từ cấu hình (§20.4).
            access_token — token hiện tại, đọc từ platform_tokens.
            khi_can_lam_moi — hàm không tham số, trả access_token MỚI (cùng
                cách nối với ShopeeClient, §20.1).
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_cipher = shop_cipher
        self.access_token = access_token
        self.khi_can_lam_moi = khi_can_lam_moi
        self.so_lan_gui_toi_da = so_lan_gui_toi_da
        self.cho_co_ban_giay = cho_co_ban_giay
        self.ham_ngu = ham_ngu
        self._http = httpx2.Client(base_url=base_url, timeout=30)
        self._http_auth = httpx2.Client(base_url=auth_base_url, timeout=30)

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        self.close()

    def close(self):
        self._http.close()
        self._http_auth.close()

    # ---------------- Ký và gửi ----------------

    def ky(self, duong_dan, tham_so, than):
        """Chữ ký của một yêu cầu: tham_so là dict chuỗi đúng như sẽ gửi, than là CHUỖI body."""
        cac_cap = "".join(f"{khoa}{tham_so[khoa]}" for khoa in sorted(tham_so) if khoa not in ("sign", "access_token"))
        chuoi_bao = self.app_secret + duong_dan + cac_cap + than + self.app_secret
        return hmac.new(self.app_secret.encode("utf-8"), chuoi_bao.encode("utf-8"), hashlib.sha256).hexdigest()

    def _gui_mot_lan(self, phuong_thuc, duong_dan, tham_so_rieng, than):
        """Gửi qua http_retry (ký lại với timestamp mới mỗi lần thử). Trả JSON (dict)."""
        def gui():
            tham_so = {"app_key": self.app_key, "timestamp": str(int(time.time())),
                       "shop_cipher": self.shop_cipher, **(tham_so_rieng or {})}
            tham_so["sign"] = self.ky(duong_dan, tham_so, than)
            # content=than: gửi ĐÚNG chuỗi đã ký, không đưa dict cho httpx2 tự serialize.
            return self._http.request(
                phuong_thuc, duong_dan, params=tham_so, content=than.encode("utf-8") if than else None,
                headers={"content-type": "application/json", "x-tts-access-token": self.access_token},
            )
        phan_hoi = http_retry.goi_co_thu_lai(
            gui, http_retry.phan_loai_tiktok, self.so_lan_gui_toi_da, self.cho_co_ban_giay, self.ham_ngu
        )
        return http_retry.doc_json_an_toan(phan_hoi)

    def goi(self, phuong_thuc, duong_dan, tham_so_rieng=None, than=""):
        """Gọi một endpoint open-api, trả JSON thô khi `code == 0`.

        `than` là CHUỖI đã serialize (nơi gọi serialize một lần). Gặp mã token
        sai/hết hạn thì làm mới ĐÚNG MỘT LẦN qua khi_can_lam_moi rồi gọi lại.
        Lỗi: LoiApiTikTok (code khác 0), http_retry.LoiHetLanThuLai (quá tải mãi).
        """
        ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than)
        if ket_qua.get("code") in MA_TOKEN_KHONG_HOP_LE and self.khi_can_lam_moi is not None:
            self.access_token = self.khi_can_lam_moi()
            ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than)
        if ket_qua.get("code") != 0:
            raise LoiApiTikTok(duong_dan, ket_qua.get("code"), ket_qua.get("message", ""))
        return ket_qua

    # ---------------- Làm mới token ----------------

    def goi_lam_moi_token(self, refresh_token, shop_ref):
        """Đổi refresh_token lấy cặp token mới ở máy chủ auth (không ký — theo SDK EcomPHP, §19.2).

        Đây là `ham_lam_moi` đưa cho token_store.lam_moi_va_ghi; shop_ref
        (shop_cipher) không cần cho yêu cầu này, nhận để cùng chữ ký hàm với Shopee.
        Trả: dict `data` — {access_token, refresh_token}. Không có trường hạn
        sống: token_store tự tính 7 ngày / NULL (§12.1.3.2).
        """
        def gui():
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

    # ---------------- Kéo dữ liệu ----------------

    def lay_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Mọi đơn (đầy đủ, gồm line_items) có truong_thoi_gian trong [tu_luc, den_luc).

        Mỗi cửa sổ: body {truong_ge, truong_lt} serialize MỘT lần, rồi đi hết
        page_token. Sắp ASC theo chính trường đang lọc để thứ tự ổn định.
        Không khử trùng — chia cửa sổ sai thì trùng lộ ra cho test thấy.
        """
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
        """`data` thô của statement_transactions cho một đơn (order_id, sku_transactions, total_count)."""
        return self.goi("GET", DUONG_DAN_FINANCE.format(order_id=ma_don))["data"]

    def keo_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Một lượt kéo theo §20.2: đơn → Finance cho từng đơn COMPLETED.

        Chỉ gọi Finance cho đơn COMPLETED vì dữ liệu Finance chỉ có sau quyết
        toán (§20.2) — đây là quy tắc GỌI API, không phải quy tắc nghiệp vụ;
        đánh `is_returned` từ Finance là việc của bước 10.
        Trả: {"don_hang": [đơn thô], "finance": {order_id: data thô}}.
        """
        cac_don = self.lay_don(tu_luc, den_luc, truong_thoi_gian)
        finance = {
            don["id"]: self.lay_finance(don["id"])
            for don in cac_don if don["status"] == TRANG_THAI_DA_QUYET_TOAN
        }
        return {"don_hang": cac_don, "finance": finance}
