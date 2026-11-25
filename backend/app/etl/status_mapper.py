# Gom trạng thái đơn hàng
## Gom trạng thái đơn hàng về 5 trạng thái chuẩn
## Nhận diện 15 biến thể trạng thái có gắn ngày tháng về completed
import logging

import pandas as pd

logger = logging.getLogger(__name__)

TRANG_THAI_KHONG_XAC_DINH = "unknown"

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

# Trạng thái Shopee có nhúng mốc ngày nên chỉ so phần đầu chuỗi.
TIEN_TO_SHOPEE_DA_NHAN_HANG = "Người mua xác nhận đã nhận được hàng"

BANG_TRANG_THAI_API = {
    "shopee": {
        "COMPLETED": "completed",
        # Có trừ doanh thu hay không do returned_qty quyết định, không do trạng thái.
        "TO_RETURN": "completed",
        "TO_CONFIRM_RECEIVE": "delivered",
        "SHIPPED": "shipping",
        "UNPAID": "pending",
        "READY_TO_SHIP": "pending",
        "PROCESSED": "pending",
        # Mới xin hủy, chưa hủy hẳn nên đơn vẫn có thể giao.
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
    if pd.isna(trang_thai_goc) or trang_thai_goc.strip() == "":
        logger.warning("Trạng thái %s rỗng, gán '%s'", san, TRANG_THAI_KHONG_XAC_DINH)
        return TRANG_THAI_KHONG_XAC_DINH

    trang_thai = trang_thai_goc.strip()

    if san == "shopee" and trang_thai.startswith(TIEN_TO_SHOPEE_DA_NHAN_HANG):
        return "completed"

    bang_cua_san = BANG_TRANG_THAI_FILE[san]
    if trang_thai in bang_cua_san:
        return bang_cua_san[trang_thai]

    logger.warning("Trạng thái %s lạ '%s', gán '%s'", san, trang_thai, TRANG_THAI_KHONG_XAC_DINH)
    return TRANG_THAI_KHONG_XAC_DINH


def gom_nhom_trang_thai_api(ma_trang_thai, san):
    """Mã lạ thì trả "unknown" và ghi log, sàn thêm mã mới hệ thống vẫn chạy."""
    if pd.isna(ma_trang_thai) or ma_trang_thai.strip() == "":
        logger.warning("Mã trạng thái API %s rỗng, gán '%s'", san, TRANG_THAI_KHONG_XAC_DINH)
        return TRANG_THAI_KHONG_XAC_DINH

    # Không .upper() để mã sai kiểu chữ lộ ra ở log thay vì bị nuốt.
    bang_cua_san = BANG_TRANG_THAI_API[san]
    if ma_trang_thai in bang_cua_san:
        return bang_cua_san[ma_trang_thai]

    logger.warning("Mã trạng thái API %s lạ '%s', gán '%s'",
                   san, ma_trang_thai, TRANG_THAI_KHONG_XAC_DINH)
    return TRANG_THAI_KHONG_XAC_DINH
