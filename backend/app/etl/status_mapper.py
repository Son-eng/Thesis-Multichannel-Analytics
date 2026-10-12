"""Gom trạng thái đơn hàng gốc của từng sàn về 5 nhóm chuẩn (SPEC §6).

Vì sao có 2 bảng tra tách riêng: file CSV ghi trạng thái bằng chuỗi tiếng Việt
("Đã hủy"), còn API trả mã tiếng Anh ("CANCELLED"). Hai bộ giá trị không giao
nhau, trộn chung một bảng thì khó đọc và khó đối chiếu với SPEC (§6.1–6.2 cho
file, §6.4 cho API).

Giá trị không có trong bảng, hoặc rỗng → "unknown" kèm log cảnh báo, KHÔNG làm
hỏng cả lượt nạp (§6.3). "unknown" vẫn được tính doanh thu (§7.1).
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

TRANG_THAI_KHONG_XAC_DINH = "unknown"

# Đường FILE — SPEC §6.1 (Shopee, 7 chuỗi cố định) và §6.2 (TikTok).
BANG_TRANG_THAI_FILE = {
    "shopee": {
        "Hoàn thành": "completed",
        "Đã nhận được hàng": "completed",
        "Đã giao": "delivered",
        "Đang giao": "shipping",
        "Chờ giao hàng": "pending",
        "Chờ xác nhận": "pending",
        "Đã hủy": "cancelled",
    },
    "tiktok": {
        "Đã hoàn tất": "completed",
        "Đã vận chuyển": "shipping",
        "Cần vận chuyển": "pending",
        "Đã hủy": "cancelled",
    },
}

# 15 biến thể trạng thái Shopee có nhúng mốc ngày, ví dụ:
# "Người mua xác nhận đã nhận được hàng, tuy nhiên ... tới ngày 2026-08-15."
# Chỉ so phần đầu chuỗi vì mốc ngày đổi theo từng file (SPEC §6.1).
TIEN_TO_SHOPEE_DA_NHAN_HANG = "Người mua xác nhận đã nhận được hàng"

# Đường API — SPEC §6.4.
BANG_TRANG_THAI_API = {
    "shopee": {
        "COMPLETED": "completed",
        # Có trừ doanh thu hay không do returned_qty quyết định, không do
        # trạng thái (sinh viên chốt 12/10).
        "TO_RETURN": "completed",
        "TO_CONFIRM_RECEIVE": "delivered",
        "SHIPPED": "shipping",
        "UNPAID": "pending",
        "READY_TO_SHIP": "pending",
        "PROCESSED": "pending",
        # Mới xin hủy, chưa hủy hẳn — đơn vẫn có thể giao tiếp (chốt 12/10).
        "IN_CANCEL": "pending",
        "INVOICE_PENDING": "pending",
        "CANCELLED": "cancelled",
    },
    "tiktok": {
        "COMPLETED": "completed",
        "DELIVERED": "delivered",
        "AWAITING_COLLECTION": "shipping",
        "IN_TRANSIT": "shipping",
        "PARTIALLY_SHIPPING": "shipping",
        "UNPAID": "pending",
        "ON_HOLD": "pending",
        "AWAITING_SHIPMENT": "pending",
        "CANCELLED": "cancelled",
    },
}


def gom_nhom_trang_thai_file(trang_thai_goc, san):
    """Gom trạng thái đọc từ file CSV về nhóm chuẩn.

    Nhận: trang_thai_goc — chuỗi tiếng Việt trong file (có thể NaN);
    san — "shopee" hoặc "tiktok".
    Trả: một trong completed / delivered / shipping / pending / cancelled,
    hoặc "unknown" nếu rỗng hay không khớp.
    Cần hàm này vì Shopee có 22 cách viết trạng thái, TikTok 4 cách, mà KPI
    chỉ lọc theo 5 nhóm (§6, §7.1).
    """
    if pd.isna(trang_thai_goc) or trang_thai_goc.strip() == "":
        logger.warning("Trạng thái %s rỗng, gán '%s'", san, TRANG_THAI_KHONG_XAC_DINH)
        return TRANG_THAI_KHONG_XAC_DINH

    # Bỏ khoảng trắng thừa ở 2 đầu: "Đã hủy " và "Đã hủy" là một trạng thái.
    trang_thai = trang_thai_goc.strip()

    if san == "shopee" and trang_thai.startswith(TIEN_TO_SHOPEE_DA_NHAN_HANG):
        return "completed"

    bang_cua_san = BANG_TRANG_THAI_FILE[san]
    if trang_thai in bang_cua_san:
        return bang_cua_san[trang_thai]

    logger.warning("Trạng thái %s lạ '%s', gán '%s'", san, trang_thai, TRANG_THAI_KHONG_XAC_DINH)
    return TRANG_THAI_KHONG_XAC_DINH


def gom_nhom_trang_thai_api(ma_trang_thai, san):
    """Gom mã trạng thái API về nhóm chuẩn.

    Nhận: ma_trang_thai — mã tiếng Anh do API trả (ví dụ "READY_TO_SHIP");
    san — "shopee" hoặc "tiktok".
    Trả: một trong 5 nhóm chuẩn, hoặc "unknown" nếu rỗng hay không có trong
    bảng (sàn thêm mã mới thì hệ thống vẫn chạy, chỉ ghi log).
    Cần hàm này vì đường API là nguồn chính (§1) và trả mã khác hẳn file.
    """
    if pd.isna(ma_trang_thai) or ma_trang_thai.strip() == "":
        logger.warning("Mã trạng thái API %s rỗng, gán '%s'", san, TRANG_THAI_KHONG_XAC_DINH)
        return TRANG_THAI_KHONG_XAC_DINH

    # So khớp đúng chữ hoa như tài liệu API — không .upper() để một mã viết
    # sai kiểu chữ lộ ra ở log thay vì bị nuốt im lặng.
    bang_cua_san = BANG_TRANG_THAI_API[san]
    if ma_trang_thai in bang_cua_san:
        return bang_cua_san[ma_trang_thai]

    logger.warning("Mã trạng thái API %s lạ '%s', gán '%s'",
                   san, ma_trang_thai, TRANG_THAI_KHONG_XAC_DINH)
    return TRANG_THAI_KHONG_XAC_DINH
