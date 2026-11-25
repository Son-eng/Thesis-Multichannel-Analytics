# Khách gọi API Shopee
## Ký chữ ký số
## Chia thời gian kéo đơn -> tránh lỗi vượt giới hạn
## Kéo danh sách mã đơn -> chia 50 đơn/lần và thấy thông tin tiền ký quỹ
## Tự gọi endpoint làm mới access token

import hashlib
import hmac
import time

import httpx2

from app.connectors import http_retry

DUONG_DAN_ORDER_LIST = "/api/v2/order/get_order_list"
DUONG_DAN_ORDER_DETAIL = "/api/v2/order/get_order_detail"
DUONG_DAN_ESCROW_BATCH = "/api/v2/payment/get_escrow_detail_batch"
DUONG_DAN_LAM_MOI_TOKEN = "/api/v2/auth/access_token/get"
DUONG_DAN_CONVERSION = "/api/v2/ams/get_conversion_report"

CUA_SO_TOI_DA_GIAY = 15 * 24 * 60 * 60
SO_DON_MOI_TRANG = 100
SO_MA_MOI_LO = 50
# Mặc định sàn trả ít trường, phải xin thêm các trường cần cho bước chuẩn hóa.
TRUONG_CHI_TIET = "item_list,recipient_address"


class LoiApiShopee(Exception):
    """Lỗi sàn trả về mà không thử lại được; ma_loi là trường error."""

    def __init__(self, duong_dan, ma_loi, thong_diep):
        super().__init__(f"Shopee {duong_dan}: {ma_loi} — {thong_diep}")
        self.duong_dan = duong_dan
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


def chia_cua_so(tu_luc, den_luc):
    """Chia [tu_luc, den_luc] thành các cửa sổ ≤ 15 ngày, mỗi cửa sổ lấy cả hai đầu."""
    cac_cua_so = []
    dau = tu_luc
    while dau <= den_luc:
        cuoi = min(dau + CUA_SO_TOI_DA_GIAY, den_luc)
        cac_cua_so.append((dau, cuoi))
        dau = cuoi + 1
    return cac_cua_so


def chia_lo(danh_sach, co_lo):
    return [danh_sach[dau:dau + co_lo] for dau in range(0, len(danh_sach), co_lo)]


class ShopeeClient:
    """Dùng lớp vì access_token đổi giữa chừng sau khi làm mới."""

    def __init__(self, base_url, partner_id, partner_key, shop_id, access_token,
                 khi_can_lam_moi=None, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                 cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.access_token = access_token
        self.khi_can_lam_moi = khi_can_lam_moi
        self.so_lan_gui_toi_da = so_lan_gui_toi_da
        self.cho_co_ban_giay = cho_co_ban_giay
        self.ham_ngu = ham_ngu
        # Số yêu cầu HTTP đã gửi, kể cả lần thử lại.
        self.so_lan_goi = 0
        self._http = httpx2.Client(base_url=base_url, timeout=30)

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        self.close()

    def close(self):
        self._http.close()

    def tham_so_chung(self, duong_dan, la_shop_api=True):
        timestamp = int(time.time())
        access_token, shop_id = (self.access_token, self.shop_id) if la_shop_api else ("", "")
        chuoi_co_so = f"{self.partner_id}{duong_dan}{timestamp}{access_token}{shop_id}"
        chu_ky = hmac.new(self.partner_key.encode("utf-8"), chuoi_co_so.encode("utf-8"), hashlib.sha256).hexdigest()
        tham_so = {"partner_id": self.partner_id, "timestamp": timestamp, "sign": chu_ky}
        if la_shop_api:
            tham_so.update(access_token=access_token, shop_id=shop_id)
        return tham_so

    def _gui_mot_lan(self, phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api):
        def gui():
            self.so_lan_goi += 1
            return self._http.request(
                phuong_thuc, duong_dan,
                params={**self.tham_so_chung(duong_dan, la_shop_api), **(tham_so_rieng or {})},
                json=than,
            )
        phan_hoi = http_retry.goi_co_thu_lai(
            gui, http_retry.phan_loai_shopee, self.so_lan_gui_toi_da, self.cho_co_ban_giay, self.ham_ngu
        )
        return http_retry.doc_json_an_toan(phan_hoi)

    def goi(self, phuong_thuc, duong_dan, tham_so_rieng=None, than=None, la_shop_api=True):
        """Gặp error_auth thì làm mới token đúng một lần rồi gọi lại; làm mới mãi sẽ tiêu hết refresh_token."""
        ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api)
        if ket_qua.get("error") == "error_auth" and la_shop_api and self.khi_can_lam_moi is not None:
            self.access_token = self.khi_can_lam_moi()
            ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api)
        if ket_qua.get("error"):
            raise LoiApiShopee(duong_dan, ket_qua["error"], ket_qua.get("message", ""))
        return ket_qua

    def goi_lam_moi_token(self, refresh_token, shop_ref):
        """Không cập nhật self.access_token, chỉ khi token_store ghi xong mới chắc chắn."""
        than = {"refresh_token": refresh_token, "partner_id": self.partner_id, "shop_id": int(shop_ref)}
        return self.goi("POST", DUONG_DAN_LAM_MOI_TOKEN, than=than, la_shop_api=False)["response"]

    def lay_ma_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Mọi order_sn có truong_thoi_gian trong [tu_luc, den_luc]."""
        cac_ma = []
        for time_from, time_to in chia_cua_so(tu_luc, den_luc):
            cursor = ""
            while True:
                du_lieu = self.goi("GET", DUONG_DAN_ORDER_LIST, {
                    "time_range_field": truong_thoi_gian, "time_from": time_from, "time_to": time_to,
                    "page_size": SO_DON_MOI_TRANG, "cursor": cursor,
                })["response"]
                cac_ma += [don["order_sn"] for don in du_lieu["order_list"]]
                if not du_lieu["more"]:
                    break
                cursor = du_lieu["next_cursor"]
        return cac_ma

    def lay_chi_tiet(self, cac_ma_don):
        cac_don = []
        for lo in chia_lo(cac_ma_don, SO_MA_MOI_LO):
            du_lieu = self.goi("GET", DUONG_DAN_ORDER_DETAIL, {
                "order_sn_list": ",".join(lo), "response_optional_fields": TRUONG_CHI_TIET,
            })["response"]
            cac_don += du_lieu["order_list"]
        return cac_don

    def lay_escrow(self, cac_ma_don):
        """Trả cả đơn không có escrow; quyết định NMV tạm tính là việc của bước chuẩn hóa."""
        cac_phan_tu = []
        for lo in chia_lo(cac_ma_don, SO_MA_MOI_LO):
            cac_phan_tu += self.goi("POST", DUONG_DAN_ESCROW_BATCH, than={"order_sn_list": lo})["response"]
        return cac_phan_tu

    def lay_don_affiliate(self, tu_luc, den_luc):
        cac_phan_tu = []
        for time_from, time_to in chia_cua_so(tu_luc, den_luc):
            so_trang = 1
            while True:
                du_lieu = self.goi("GET", DUONG_DAN_CONVERSION, {
                    "place_order_time_start": time_from, "place_order_time_end": time_to,
                    "page_no": so_trang, "page_size": SO_DON_MOI_TRANG,
                })["response"]
                cac_phan_tu += du_lieu["list"]
                if not du_lieu["has_more"]:
                    break
                so_trang += 1
        return cac_phan_tu

    def keo_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Một lượt kéo theo: danh sách mã → chi tiết → escrow → báo cáo affiliate."""
        cac_ma = self.lay_ma_don(tu_luc, den_luc, truong_thoi_gian)
        cac_don = self.lay_chi_tiet(cac_ma)
        if cac_don:
            ngay_tao = [don["create_time"] for don in cac_don]
            cac_affiliate = self.lay_don_affiliate(min(ngay_tao), max(ngay_tao))
        else:
            cac_affiliate = []
        return {"don_hang": cac_don, "escrow": self.lay_escrow(cac_ma), "affiliate": cac_affiliate}
