"""Tính và kiểm chữ ký, timestamp; mỗi sàn một hàm vì chuỗi đem ký khác hẳn nhau."""

import hashlib
import hmac

LECH_THOI_GIAN_TOI_DA_GIAY = 5 * 60

THAM_SO_KHONG_KY_TIKTOK = {"sign", "access_token"}


def chuoi_co_so_shopee(partner_id, duong_dan, timestamp, access_token="", shop_id=""):
    """Public API không có access_token và shop_id, để mặc định ""."""
    return f"{partner_id}{duong_dan}{timestamp}{access_token}{shop_id}"


def tinh_chu_ky_shopee(partner_key, partner_id, duong_dan, timestamp, access_token="", shop_id=""):
    chuoi = chuoi_co_so_shopee(partner_id, duong_dan, timestamp, access_token, shop_id)
    return hmac.new(partner_key.encode("utf-8"), chuoi.encode("utf-8"), hashlib.sha256).hexdigest()


def chuoi_can_ky_tiktok(duong_dan, tham_so_query, body=""):
    """Nhận body dạng chuỗi để ký đúng chuỗi đã gửi; serialize lại từ dict có thể làm lệch chữ ký."""
    cac_cap = [
        f"{khoa}{tham_so_query[khoa]}"
        for khoa in sorted(tham_so_query)
        if khoa not in THAM_SO_KHONG_KY_TIKTOK
    ]
    return duong_dan + "".join(cac_cap) + body


def tinh_chu_ky_tiktok(app_secret, duong_dan, tham_so_query, body=""):
    chuoi_bao = app_secret + chuoi_can_ky_tiktok(duong_dan, tham_so_query, body) + app_secret
    return hmac.new(app_secret.encode("utf-8"), chuoi_bao.encode("utf-8"), hashlib.sha256).hexdigest()


def chu_ky_khop(chu_ky_nhan, chu_ky_dung):
    """So bằng compare_digest để thời gian so không lộ thông tin về chữ ký."""
    return hmac.compare_digest(str(chu_ky_nhan), chu_ky_dung)


def thoi_gian_hop_le(timestamp, bay_gio):
    try:
        gia_tri = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(bay_gio - gia_tri) <= LECH_THOI_GIAN_TOI_DA_GIAY
