"""Gửi HTTP có thử lại, chờ tăng dần; nhận diện lỗi theo cả mã HTTP lẫn body vì sàn hay trả lỗi kèm HTTP 200."""

import time

import httpx2

# Mã lỗi thử lại được, đã gặp thật khi chạy với sàn.
LOI_QUA_TAI_SHOPEE = "error_rate_limit"
MA_QUA_TAI_TIKTOK = 36009002
MA_LOI_NOI_BO_TIKTOK = 36009003

# Quá tải TikTok chờ lâu hơn lỗi nội bộ, gọi lại nhanh thì lại quá tải tiếp.
HE_SO_CHO_THUONG = 1
HE_SO_CHO_QUA_TAI_TIKTOK = 2

SO_LAN_GUI_TOI_DA = 5
CHO_CO_BAN_GIAY = 1.0


class LoiHetLanThuLai(Exception):
    def __init__(self, so_lan_gui, lan_cuoi):
        super().__init__(f"Thử {so_lan_gui} lần vẫn lỗi tạm thời: {mo_ta(lan_cuoi)}")
        self.so_lan_gui = so_lan_gui
        self.lan_cuoi = lan_cuoi


def mo_ta(phan_hoi_hoac_loi):
    """Mô tả ngắn cho thông báo lỗi, không in token hay body đầy đủ."""
    if isinstance(phan_hoi_hoac_loi, Exception):
        return f"{type(phan_hoi_hoac_loi).__name__}: {phan_hoi_hoac_loi}"
    return f"HTTP {phan_hoi_hoac_loi.status_code}"


def doc_json_an_toan(phan_hoi):
    try:
        du_lieu = phan_hoi.json()
    except ValueError:
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def phan_loai_shopee(phan_hoi):
    if phan_hoi.status_code == 429 or doc_json_an_toan(phan_hoi).get("error") == LOI_QUA_TAI_SHOPEE:
        return HE_SO_CHO_THUONG
    return None


def phan_loai_tiktok(phan_hoi):
    ma = doc_json_an_toan(phan_hoi).get("code")
    if ma == MA_QUA_TAI_TIKTOK:
        return HE_SO_CHO_QUA_TAI_TIKTOK
    if ma == MA_LOI_NOI_BO_TIKTOK:
        return HE_SO_CHO_THUONG
    return None


def goi_co_thu_lai(gui_yeu_cau, phan_loai, so_lan_toi_da=SO_LAN_GUI_TOI_DA,
                   cho_co_ban_giay=CHO_CO_BAN_GIAY, ham_ngu=time.sleep):
    """Gửi một yêu cầu, thử lại khi gặp lỗi tạm thời."""
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
        if lan < so_lan_toi_da - 1:
            ham_ngu(cho_co_ban_giay * he_so * 2 ** lan)
    raise LoiHetLanThuLai(so_lan_toi_da, lan_cuoi)
