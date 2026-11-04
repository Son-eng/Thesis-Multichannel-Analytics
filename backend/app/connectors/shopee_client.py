"""Connector Shopee — ký, gửi, thử lại, phân trang, làm mới token (SPEC §20.1–§20.3).

CHỈ nói chuyện HTTP: trả JSON thô của sàn, không tính NMV, không gom trạng
thái, không lọc đơn (§18.3). Không biết CSDL: access_token đưa vào lúc tạo,
và khi token bị từ chối thì gọi callback `khi_can_lam_moi` (nơi gọi — sync_job
— nối callback đó với token_store.lam_moi_va_ghi).

Thứ tự gọi trong một lượt (§20.2):
    lay_ma_don()     get_order_list, chia cửa sổ ≤ 15 ngày, đi hết cursor
    lay_chi_tiet()   get_order_detail, lô 50
    lay_escrow()     get_escrow_detail_batch, lô 50
    lay_don_affiliate()  get_conversion_report, theo khoảng ngày tạo của các đơn vừa kéo
`keo_don()` gọi lần lượt cả bốn.

Thuật toán ký (tài liệu tóm tắt Shopee mục 5):
    Shop API:   HMAC-SHA256(partner_key, partner_id + path + timestamp + access_token + shop_id)
    Public API: HMAC-SHA256(partner_key, partner_id + path + timestamp)
"""

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

# Giới hạn của sàn (§19.2).
CUA_SO_TOI_DA_GIAY = 15 * 24 * 60 * 60
SO_DON_MOI_TRANG = 100
SO_MA_MOI_LO = 50
# Trường get_order_detail mà tầng chuẩn hóa cần (§21.1); mặc định sàn trả ít trường.
TRUONG_CHI_TIET = "item_list,recipient_address"


class LoiApiShopee(Exception):
    """Sàn trả lỗi không thử lại được (sai tham số, sai chữ ký, token…). `ma_loi` là trường `error`."""

    def __init__(self, duong_dan, ma_loi, thong_diep):
        super().__init__(f"Shopee {duong_dan}: {ma_loi} — {thong_diep}")
        self.duong_dan = duong_dan
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


def chia_cua_so(tu_luc, den_luc):
    """Chia [tu_luc, den_luc] thành các cửa sổ ≤ 15 ngày, mỗi cửa sổ lấy CẢ HAI đầu.

    Nhận: 2 mốc epoch giây.
    Trả: list (time_from, time_to). Cửa sổ sau bắt đầu từ time_to của cửa sổ
    trước + 1 — vì Shopee lấy cả hai đầu (§16 mục 8, §20.2): bắt đầu đúng tại
    time_to thì đơn nằm đúng mốc ranh giới bị lấy 2 lần.
    Ví dụ: chia_cua_so(0, 40 ngày) → [(0, 15n), (15n+1, 30n+1), (30n+2, 40n)].
    """
    cac_cua_so = []
    dau = tu_luc
    while dau <= den_luc:
        cuoi = min(dau + CUA_SO_TOI_DA_GIAY, den_luc)
        cac_cua_so.append((dau, cuoi))
        dau = cuoi + 1
    return cac_cua_so


def chia_lo(danh_sach, co_lo):
    """Cắt danh sách thành các lô liên tiếp tối đa co_lo phần tử."""
    return [danh_sach[dau:dau + co_lo] for dau in range(0, len(danh_sach), co_lo)]


class ShopeeClient:
    """Connector cho MỘT shop Shopee.

    Dùng lớp vì access_token là trạng thái đổi giữa chừng (sau khi làm mới),
    mọi yêu cầu sau phải dùng token mới. Dùng được với `with` để đóng kết nối.
    """

    def __init__(self, base_url, partner_id, partner_key, shop_id, access_token,
                 khi_can_lam_moi=None, so_lan_gui_toi_da=http_retry.SO_LAN_GUI_TOI_DA,
                 cho_co_ban_giay=http_retry.CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
        """Nhận:
            base_url, partner_id, partner_key, shop_id — từ cấu hình (§20.4).
            access_token — token hiện tại, đọc từ platform_tokens.
            khi_can_lam_moi — hàm không tham số, làm mới token và trả
                access_token MỚI (sync_job nối với token_store.lam_moi_va_ghi
                + goi_lam_moi_token). None thì gặp error_auth là báo lỗi luôn.
            so_lan_gui_toi_da, cho_co_ban_giay, ham_ngu — truyền xuống http_retry.
        """
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.access_token = access_token
        self.khi_can_lam_moi = khi_can_lam_moi
        self.so_lan_gui_toi_da = so_lan_gui_toi_da
        self.cho_co_ban_giay = cho_co_ban_giay
        self.ham_ngu = ham_ngu
        # Số yêu cầu HTTP đã gửi (kể cả lần thử lại) — sync_job ghi vào sync_runs.api_calls.
        self.so_lan_goi = 0
        self._http = httpx2.Client(base_url=base_url, timeout=30)

    def __enter__(self):
        return self

    def __exit__(self, *loi):
        self.close()

    def close(self):
        self._http.close()

    # ---------------- Ký và gửi ----------------

    def tham_so_chung(self, duong_dan, la_shop_api=True):
        """Tham số chung đã ký, với timestamp LÚC GỌI (mỗi lần thử lại ký lại)."""
        timestamp = int(time.time())
        access_token, shop_id = (self.access_token, self.shop_id) if la_shop_api else ("", "")
        chuoi_co_so = f"{self.partner_id}{duong_dan}{timestamp}{access_token}{shop_id}"
        chu_ky = hmac.new(self.partner_key.encode("utf-8"), chuoi_co_so.encode("utf-8"), hashlib.sha256).hexdigest()
        tham_so = {"partner_id": self.partner_id, "timestamp": timestamp, "sign": chu_ky}
        if la_shop_api:
            tham_so.update(access_token=access_token, shop_id=shop_id)
        return tham_so

    def _gui_mot_lan(self, phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api):
        """Gửi qua http_retry. Trả JSON (dict) của phản hồi không phải lỗi tạm thời."""
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
        """Gọi một endpoint, trả JSON thô khi thành công.

        Gặp `error_auth` ở Shop API (token sai hoặc hết hạn) thì làm mới token
        ĐÚNG MỘT LẦN qua `khi_can_lam_moi` rồi gọi lại (§20.1). Lần gọi lại
        vẫn error_auth thì báo lỗi — làm mới mãi sẽ tiêu hết refresh_token
        mà không giải quyết được gì.
        Lỗi: LoiApiShopee (lỗi của sàn), http_retry.LoiHetLanThuLai (quá tải mãi).
        """
        ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api)
        if ket_qua.get("error") == "error_auth" and la_shop_api and self.khi_can_lam_moi is not None:
            self.access_token = self.khi_can_lam_moi()
            ket_qua = self._gui_mot_lan(phuong_thuc, duong_dan, tham_so_rieng, than, la_shop_api)
        if ket_qua.get("error"):
            raise LoiApiShopee(duong_dan, ket_qua["error"], ket_qua.get("message", ""))
        return ket_qua

    # ---------------- Làm mới token ----------------

    def goi_lam_moi_token(self, refresh_token, shop_ref):
        """Đổi refresh_token lấy cặp token mới (Public API: chữ ký không có access_token, shop_id).

        Đây là `ham_lam_moi` đưa cho token_store.lam_moi_va_ghi: nhận
        (refresh_token, shop_ref) đọc từ dòng đã khóa trong CSDL.
        Trả: dict {access_token, refresh_token, expire_in} — trong `response`
        theo khuôn chung của tài liệu (§16 mục 8).
        Không cập nhật self.access_token: chỉ token_store ghi xong mới là chắc chắn.
        """
        than = {"refresh_token": refresh_token, "partner_id": self.partner_id, "shop_id": int(shop_ref)}
        return self.goi("POST", DUONG_DAN_LAM_MOI_TOKEN, than=than, la_shop_api=False)["response"]

    # ---------------- Kéo dữ liệu ----------------

    def lay_ma_don(self, tu_luc, den_luc, truong_thoi_gian="update_time"):
        """Mọi order_sn có truong_thoi_gian trong [tu_luc, den_luc].

        Chia cửa sổ ≤ 15 ngày (chia_cua_so), mỗi cửa sổ đi hết cursor.
        Không khử trùng: chia cửa sổ đúng thì không có trùng; có trùng là
        dấu hiệu chia sai — để lộ ra cho test thấy, không che đi.
        """
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
        """Chi tiết đơn (kèm item_list, recipient_address), lô 50 mã. Trả list đơn thô theo thứ tự sàn trả."""
        cac_don = []
        for lo in chia_lo(cac_ma_don, SO_MA_MOI_LO):
            du_lieu = self.goi("GET", DUONG_DAN_ORDER_DETAIL, {
                "order_sn_list": ",".join(lo), "response_optional_fields": TRUONG_CHI_TIET,
            })["response"]
            cac_don += du_lieu["order_list"]
        return cac_don

    def lay_escrow(self, cac_ma_don):
        """Phần tử escrow thô, lô 50 mã.

        Trả MỌI phần tử sàn trả về, kể cả đơn không có escrow (phần tử
        `{order_sn, fail_error, …}`, §16 mục 6): quyết định "không có escrow →
        NMV tạm tính" là quy tắc của tầng chuẩn hóa (§7.5, bước 10), không phải
        của connector.
        """
        cac_phan_tu = []
        for lo in chia_lo(cac_ma_don, SO_MA_MOI_LO):
            cac_phan_tu += self.goi("POST", DUONG_DAN_ESCROW_BATCH, than={"order_sn_list": lo})["response"]
        return cac_phan_tu

    def lay_don_affiliate(self, tu_luc, den_luc):
        """Các phần tử thô `{order_sn}` của báo cáo affiliate có ngày đặt trong [tu_luc, den_luc] (§21.4).

        Chia cửa sổ ≤ 15 ngày như get_order_list (tài liệu không nói độ dài
        tối đa của một yêu cầu; chia nhỏ là lựa chọn an toàn), cùng quy tắc
        cửa sổ lấy cả hai đầu. Phân trang bằng page_no từ 1 (giả định, §16 mục 10).
        Không khử trùng: báo cáo thật có thể có nhiều dòng cho một đơn
        (tài liệu bàn giao: 1.295 đơn / 1.303 dòng) — tầng chuẩn hóa dùng tập.
        """
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
        """Một lượt kéo theo §20.2: danh sách mã → chi tiết → escrow → (bước 4) báo cáo affiliate.

        Báo cáo affiliate kéo theo KHOẢNG NGÀY TẠO của các đơn vừa kéo (nhỏ
        nhất → lớn nhất `create_time`): kéo theo ngày tạo vì báo cáo lọc theo
        ngày đặt, còn cửa sổ của lượt này có thể là `update_time` (§20.3).
        Trả: {"don_hang": [đơn thô], "escrow": [phần tử escrow thô],
              "affiliate": [phần tử thô {order_sn}]}.
        """
        cac_ma = self.lay_ma_don(tu_luc, den_luc, truong_thoi_gian)
        cac_don = self.lay_chi_tiet(cac_ma)
        if cac_don:
            ngay_tao = [don["create_time"] for don in cac_don]
            cac_affiliate = self.lay_don_affiliate(min(ngay_tao), max(ngay_tao))
        else:
            cac_affiliate = []
        return {"don_hang": cac_don, "escrow": self.lay_escrow(cac_ma), "affiliate": cac_affiliate}
