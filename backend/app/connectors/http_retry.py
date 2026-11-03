"""Gửi yêu cầu HTTP có thử lại, thời gian chờ tăng dần — dùng chung cho 2 client (SPEC §20.1).

Phần dùng chung DUY NHẤT giữa 2 sàn (§13: "chỉ phần thử lại là dùng chung thật
sự"). Ký, phân trang, làm mới token của 2 sàn khác hẳn nhau nên nằm ở từng client.

Luồng một lần gọi `goi_co_thu_lai()`:
    gửi → phân loại phản hồi:
        thành công, hoặc lỗi KHÔNG thử lại (sai tham số, sai chữ ký, token…)
            → trả phản hồi cho client tự đọc
        lỗi tạm thời (quá tải, lỗi nội bộ sàn, lỗi mạng)
            → ngủ  cho_co_ban × he_so × 2^lần  rồi gửi lại
    hết số lần → ném LoiHetLanThuLai

Nhận diện lỗi theo CẢ mã HTTP lẫn body (§20.1, chốt 03/11/2026): Shopee báo
quá tải bằng HTTP 429 + `error_rate_limit`, mọi lỗi khác HTTP 200 + `error`;
TikTok luôn HTTP 200 + `code`. Vì vậy KHÔNG dùng raise_for_status().
"""

import time

import httpx2

# Mã lỗi thử lại được — kế thừa từ Pipeline, đã gặp thật (§20.1).
LOI_QUA_TAI_SHOPEE = "error_rate_limit"
MA_QUA_TAI_TIKTOK = 36009002
MA_LOI_NOI_BO_TIKTOK = 36009003

# Hệ số chờ: quá tải TikTok chờ lâu hơn lỗi nội bộ (§20.1) — gặp quá tải mà
# gọi lại nhanh thì lại quá tải tiếp.
HE_SO_CHO_THUONG = 1
HE_SO_CHO_QUA_TAI_TIKTOK = 2

SO_LAN_GUI_TOI_DA = 5
CHO_CO_BAN_GIAY = 1.0


class LoiHetLanThuLai(Exception):
    """Đã gửi đủ số lần mà vẫn gặp lỗi tạm thời. `lan_cuoi` là phản hồi hoặc ngoại lệ của lần cuối."""

    def __init__(self, so_lan_gui, lan_cuoi):
        super().__init__(f"Thử {so_lan_gui} lần vẫn lỗi tạm thời: {mo_ta(lan_cuoi)}")
        self.so_lan_gui = so_lan_gui
        self.lan_cuoi = lan_cuoi


def mo_ta(phan_hoi_hoac_loi):
    """Mô tả ngắn để ghi vào thông báo lỗi (không in token, không in body đầy đủ)."""
    if isinstance(phan_hoi_hoac_loi, Exception):
        return f"{type(phan_hoi_hoac_loi).__name__}: {phan_hoi_hoac_loi}"
    return f"HTTP {phan_hoi_hoac_loi.status_code}"


def doc_json_an_toan(phan_hoi):
    """Body dạng dict, hoặc {} nếu body không phải JSON object (để phân loại không văng lỗi)."""
    try:
        du_lieu = phan_hoi.json()
    except ValueError:
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def phan_loai_shopee(phan_hoi):
    """Hệ số chờ nếu phản hồi Shopee là lỗi thử lại được, None nếu không thử lại.

    Quá tải nhận diện bằng HTTP 429 HOẶC body `error = error_rate_limit`: kiểm
    cả hai, để vẫn đúng nếu sàn thật báo quá tải theo một trong hai cách.
    """
    if phan_hoi.status_code == 429 or doc_json_an_toan(phan_hoi).get("error") == LOI_QUA_TAI_SHOPEE:
        return HE_SO_CHO_THUONG
    return None


def phan_loai_tiktok(phan_hoi):
    """Hệ số chờ nếu phản hồi TikTok là lỗi thử lại được (36009002 chờ lâu hơn 36009003), None nếu không."""
    ma = doc_json_an_toan(phan_hoi).get("code")
    if ma == MA_QUA_TAI_TIKTOK:
        return HE_SO_CHO_QUA_TAI_TIKTOK
    if ma == MA_LOI_NOI_BO_TIKTOK:
        return HE_SO_CHO_THUONG
    return None


def goi_co_thu_lai(gui_yeu_cau, phan_loai, so_lan_toi_da=SO_LAN_GUI_TOI_DA,
                   cho_co_ban_giay=CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
    """Gửi một yêu cầu, thử lại khi gặp lỗi tạm thời.

    Nhận:
        gui_yeu_cau — hàm không tham số, gửi yêu cầu và trả httpx2.Response.
            Mỗi lần thử gọi lại hàm này, nên nơi gọi có thể ký lại với
            timestamp mới (timestamp cũ có thể quá 5 phút sau vài lần chờ).
        phan_loai — phan_loai_shopee / phan_loai_tiktok.
        so_lan_toi_da — tổng số lần GỬI (kể cả lần đầu).
        cho_co_ban_giay, ham_ngu — test truyền ham_ngu giả để khỏi ngủ thật.
    Trả: httpx2.Response của lần gửi cuối (thành công, hoặc lỗi không thử lại).
    Lỗi: LoiHetLanThuLai khi hết số lần mà vẫn lỗi tạm thời.

    Lỗi mạng (httpx2.TransportError: không kết nối được, hết giờ chờ, kết nối
    bị đóng) cũng thử lại với hệ số thường: lỗi đường truyền thường chỉ thoáng
    qua, bỏ cả lượt đồng bộ vì một lần rớt mạng là quá tay.
    """
    lan_cuoi = None
    for lan in range(so_lan_toi_da):
        try:
            phan_hoi = gui_yeu_cau()
        except httpx2.TransportError as loi:
            lan_cuoi, he_so = loi, HE_SO_CHO_THUONG
        else:
            he_so = phan_loai(phan_hoi)
            if he_so is None:
                return phan_hoi
            lan_cuoi = phan_hoi
        # Lần cuối thì không ngủ nữa — đằng nào cũng bỏ cuộc.
        if lan < so_lan_toi_da - 1:
            ham_ngu(cho_co_ban_giay * he_so * 2 ** lan)
    raise LoiHetLanThuLai(so_lan_toi_da, lan_cuoi)
