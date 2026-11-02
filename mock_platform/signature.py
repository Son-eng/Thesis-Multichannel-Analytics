"""Tính và kiểm chữ ký, kiểm timestamp của yêu cầu gửi tới máy chủ giả lập (SPEC §19.3 mục 1–2).

Hai sàn cùng dùng HMAC-SHA256 nhưng chuỗi đem ký khác hẳn nhau, nên mỗi sàn
một hàm riêng, không gộp chung (cùng lý do với 2 connector, SPEC §13).

File này chỉ trả đúng/sai. Đổi "sai" thành mã lỗi của từng sàn là việc của
route, vì mã lỗi khác nhau giữa 2 sàn và phải lấy từ tài liệu (§19.3).

Nguồn thuật toán:
- Shopee: `Pipeline/Shopee/shopeeapideveloperguidetomtat (1).md` mục 5.
- TikTok: `Pipeline/Tiktok/Authorization/Sign your API request.md`.
"""

import hashlib
import hmac

# Cả 2 tài liệu: yêu cầu phải gửi trong vòng 5 phút kể từ timestamp.
LECH_THOI_GIAN_TOI_DA_GIAY = 5 * 60

# Hai tham số không bao giờ được đưa vào chuỗi ký TikTok (bước 1 tài liệu).
THAM_SO_KHONG_KY_TIKTOK = {"sign", "access_token"}


def chuoi_co_so_shopee(partner_id, duong_dan, timestamp, access_token="", shop_id=""):
    """Chuỗi cơ sở Shopee: các phần nối liền, không ký tự phân tách.

    Nhận: partner_id, đường dẫn API (ví dụ "/api/v2/order/get_order_list"),
    timestamp; access_token và shop_id chỉ có ở Shop API.
    Trả: chuỗi `partner_id + path + timestamp + access_token + shop_id`.
    Public API (`auth/access_token/get`) không có 2 phần cuối — để mặc định ""
    thì cùng một hàm ra đúng `partner_id + path + timestamp` như tài liệu.
    """
    return f"{partner_id}{duong_dan}{timestamp}{access_token}{shop_id}"


def tinh_chu_ky_shopee(partner_key, partner_id, duong_dan, timestamp, access_token="", shop_id=""):
    """Chữ ký Shopee: HMAC-SHA256(chuỗi cơ sở, khóa = partner_key), dạng hex."""
    chuoi = chuoi_co_so_shopee(partner_id, duong_dan, timestamp, access_token, shop_id)
    return hmac.new(partner_key.encode("utf-8"), chuoi.encode("utf-8"), hashlib.sha256).hexdigest()


def chuoi_can_ky_tiktok(duong_dan, tham_so_query, body=""):
    """Chuỗi TikTok sau bước 4 của tài liệu, CHƯA bọc app_secret.

    Nhận: đường dẫn API, dict tham số query (giá trị là chuỗi như trên URL),
    body là CHUỖI đúng như đã nhận — không phải dict.
    Trả: path + {key}{value} theo key sắp xếp alphabet (bỏ sign, access_token)
    + body.
    Nhận body dạng chuỗi chứ không nhận dict: phải ký đúng chuỗi đã gửi đi.
    Serialize lại từ dict có thể đổi thứ tự trường hay khoảng trắng → chữ ký
    lệch (bẫy tài liệu đã cảnh báo, §20.1).
    Mọi endpoint của máy chủ giả lập dùng JSON, không có multipart/form-data,
    nên luôn ghép body (tài liệu chỉ bỏ body khi là multipart).
    """
    cac_cap = [
        f"{khoa}{tham_so_query[khoa]}"
        for khoa in sorted(tham_so_query)
        if khoa not in THAM_SO_KHONG_KY_TIKTOK
    ]
    return duong_dan + "".join(cac_cap) + body


def tinh_chu_ky_tiktok(app_secret, duong_dan, tham_so_query, body=""):
    """Chữ ký TikTok: HMAC-SHA256(app_secret + chuỗi + app_secret, khóa = app_secret), dạng hex."""
    chuoi_bao = app_secret + chuoi_can_ky_tiktok(duong_dan, tham_so_query, body) + app_secret
    return hmac.new(app_secret.encode("utf-8"), chuoi_bao.encode("utf-8"), hashlib.sha256).hexdigest()


def chu_ky_khop(chu_ky_nhan, chu_ky_dung):
    """So 2 chữ ký. Dùng compare_digest thay cho == để thời gian so không lộ
    ra chữ ký đúng tới ký tự thứ mấy (thói quen đúng khi so chuỗi bí mật)."""
    return hmac.compare_digest(str(chu_ky_nhan), chu_ky_dung)


def thoi_gian_hop_le(timestamp, bay_gio):
    """Timestamp có nằm trong ±5 phút quanh thời điểm máy chủ nhận không.

    Nhận: timestamp như client gửi (chuỗi hoặc số), bay_gio — epoch giây của
    máy chủ (truyền vào để test cố định được thời điểm).
    Trả: True nếu là số nguyên và lệch không quá 5 phút; chuỗi không phải số → False.
    Lệch cả 2 chiều đều từ chối: tài liệu không nói chỉ chặn timestamp cũ.
    """
    try:
        gia_tri = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(bay_gio - gia_tri) <= LECH_THOI_GIAN_TOI_DA_GIAY
