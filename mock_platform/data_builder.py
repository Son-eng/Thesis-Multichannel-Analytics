"""Sinh dữ liệu theo khuôn API của sàn từ hai file CSV ẩn danh; không dùng parser của backend để test khứ hồi không tự so với chính nó."""

import hashlib
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

THU_MUC_MAU = Path(__file__).resolve().parent.parent / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"

# Mốc thời gian trong CSV là giờ Việt Nam; API trả epoch giây UTC.
GIO_VN = timezone(timedelta(hours=7))

SHOP_SHOPEE = "Shop C"

# shop_cipher giả, không phải bí mật.
SHOP_CIPHER_TIKTOK = {
    "Shop A": "MOCK_CIPHER_SHOP_A",
    "Shop B": "MOCK_CIPHER_SHOP_B",
}

TRANG_THAI_SHOPEE = {
    "Hoàn thành": "COMPLETED",
    "Đã nhận được hàng": "COMPLETED",
    "Đã giao": "TO_CONFIRM_RECEIVE",
    "Đang giao": "SHIPPED",
    "Chờ giao hàng": "PROCESSED",
    "Chờ xác nhận": "UNPAID",
    "Đã hủy": "CANCELLED",
    # Dòng có trạng thái rỗng thì coi là COMPLETED, vì API thật không trả trạng thái rỗng.
    "": "COMPLETED",
}
# Trạng thái này có ngày hạn trả hàng ở cuối chuỗi nên so theo tiền tố.
TIEN_TO_DA_NHAN_HANG = "Người mua xác nhận đã nhận được hàng"

TRANG_THAI_TIKTOK = {
    "Đã hoàn tất": "COMPLETED",
    "Đã hủy": "CANCELLED",
    "Cần vận chuyển": "AWAITING_SHIPMENT",
    # CSV không phân biệt đang giao và đã giao.
    "Đã vận chuyển": "IN_TRANSIT",
}

# Chỉ đơn đã quyết toán mới có dữ liệu Finance.
TRANG_THAI_DA_QUYET_TOAN = "COMPLETED"
LOAI_HOAN_HANG = "Return/Refund"

# Giá trị khác và không rỗng (AFF_*) là đơn affiliate.
COT_NGUON_DOANH_THU = "Nguồn Doanh Thu"
NGUON_TU_BAN_SHOPEE = "ADS"
NGUON_TU_BAN_TIKTOK = "Inhouse"

COT_THOI_GIAN_TIKTOK = ["Paid Time", "RTS Time", "Shipped Time", "Delivered Time", "Cancelled Time"]


def doc_csv(duong_dan):
    """Ô rỗng giữ là "" chứ không thành NaN; tên cột chuẩn hóa NFC vì một số cột Shopee ở dạng tách dấu."""
    bang = pd.read_csv(duong_dan, dtype=str, keep_default_na=False)
    bang.columns = [unicodedata.normalize("NFC", ten_cot) for ten_cot in bang.columns]
    bang = bang.apply(lambda cot: cot.str.strip())
    return bang.to_dict("records")


def so_nguyen(chuoi):
    gia_tri = float(chuoi.replace(",", ""))
    if not gia_tri.is_integer():
        raise ValueError(f"Giá trị không phải số nguyên: {chuoi!r}")
    return int(gia_tri)


def sang_epoch(thoi_diem):
    return int(thoi_diem.replace(tzinfo=GIO_VN).timestamp())


def sinh_id_on_dinh(*cac_phan):
    chuoi = "|".join(cac_phan)
    ma_bam = hashlib.sha256(chuoi.encode("utf-8")).hexdigest()
    return int(ma_bam[:15], 16)


def la_dong_affiliate(dong, nguon_tu_ban):
    nguon = dong[COT_NGUON_DOANH_THU]
    return nguon != "" and nguon != nguon_tu_ban


def chia_deu(tong, so_phan):
    moi_phan = tong // so_phan
    phan_du = tong - moi_phan * so_phan
    return [moi_phan + phan_du] + [moi_phan] * (so_phan - 1)


def doi_trang_thai_shopee(trang_thai_csv):
    if trang_thai_csv.startswith(TIEN_TO_DA_NHAN_HANG):
        return "COMPLETED"
    if trang_thai_csv not in TRANG_THAI_SHOPEE:
        raise ValueError(f"Trạng thái Shopee chưa có trong bảng đổi ngược §6.4: {trang_thai_csv!r}")
    return TRANG_THAI_SHOPEE[trang_thai_csv]


def thoi_gian_shopee(dong):
    """update_time lấy muộn nhất trong các mốc, vì có dòng ngày hủy sớm hơn ngày đặt."""
    ngay_dat = datetime.strptime(dong["Ngày đặt hàng"], "%Y/%m/%d")
    gio_dau_khung = int(dong["Khung Giờ Ra Đơn"].split("H")[0])
    thoi_diem_tao = ngay_dat + timedelta(hours=gio_dau_khung)

    cac_moc = [thoi_diem_tao]
    if dong["Thời gian hoàn thành đơn hàng"]:
        cac_moc.append(datetime.strptime(dong["Thời gian hoàn thành đơn hàng"], "%Y-%m-%d %H:%M"))
    if dong["Ngày hủy thành công"]:
        cac_moc.append(datetime.strptime(dong["Ngày hủy thành công"], "%Y-%m-%d"))
    return sang_epoch(thoi_diem_tao), sang_epoch(max(cac_moc))


def tao_don_shopee(dong):
    """Phần mức đơn lấy từ dòng đầu, vì các trường này giống nhau ở mọi dòng của đơn."""
    create_time, update_time = thoi_gian_shopee(dong)
    return {
        "order_sn": dong["Mã đơn hàng"],
        "order_status": doi_trang_thai_shopee(dong["Trạng Thái Đơn Hàng"]),
        "create_time": create_time,
        "update_time": update_time,
        # Giả định đã có quyền dữ liệu nhạy cảm, API thật hiện trả "****".
        "recipient_address": {"state": dong["Tỉnh/Thành phố"]},
        "item_list": [],
    }


def tao_mat_hang_shopee(dong):
    khoa_san_pham = dong["SKU sản phẩm"] or dong["Tên sản phẩm"]
    return {
        "item_id": sinh_id_on_dinh("item", khoa_san_pham),
        "item_name": dong["Tên sản phẩm"],
        "item_sku": dong["SKU sản phẩm"],
        "model_id": sinh_id_on_dinh("model", khoa_san_pham, dong["SKU phân loại hàng"], dong["Tên phân loại hàng"]),
        "model_name": dong["Tên phân loại hàng"],
        "model_sku": dong["SKU phân loại hàng"],
        "model_quantity_purchased": so_nguyen(dong["Số lượng"]),
        "model_original_price": so_nguyen(dong["Giá gốc"]),
        # Chỉ dùng cho NMV tạm tính khi đơn chưa có escrow.
        "model_discounted_price": so_nguyen(dong["Giá ưu đãi"]),
        "returned_qty": so_nguyen(dong["Số lượng sản phẩm được hoàn trả"]),
    }


def dung_du_lieu_shopee(duong_dan=FILE_SHOPEE):
    """Escrow sinh cho mọi đơn; công tắc MOCK_ESCROW_MODE lọc ở tầng route."""
    don_hang = {}
    escrow = {}
    affiliate = {}
    for dong in doc_csv(duong_dan):
        ma_don = dong["Mã đơn hàng"]
        if ma_don not in don_hang:
            don_hang[ma_don] = tao_don_shopee(dong)
            escrow[ma_don] = {"order_sn": ma_don, "order_income": {"items": []}}
        if la_dong_affiliate(dong, NGUON_TU_BAN_SHOPEE):
            affiliate[ma_don] = don_hang[ma_don]["create_time"]

        mat_hang = tao_mat_hang_shopee(dong)
        don_hang[ma_don]["item_list"].append(mat_hang)
        escrow[ma_don]["order_income"]["items"].append({
            "item_id": mat_hang["item_id"],
            "model_id": mat_hang["model_id"],
            # Cả dòng, không chia theo số lượng: giá gốc × SL − trợ giá là số người mua trả.
            "seller_discount": so_nguyen(dong["Người bán trợ giá"]),
        })
    return {"shop_name": SHOP_SHOPEE, "don_hang": don_hang, "escrow": escrow, "affiliate": affiliate}


def doi_trang_thai_tiktok(trang_thai_csv):
    if trang_thai_csv not in TRANG_THAI_TIKTOK:
        raise ValueError(f"Trạng thái TikTok chưa có trong bảng đổi ngược §6.4: {trang_thai_csv!r}")
    return TRANG_THAI_TIKTOK[trang_thai_csv]


def thoi_gian_tiktok(dong):
    thoi_diem_tao = datetime.strptime(dong["Created Time"], "%d/%m/%Y %H:%M:%S")
    cac_moc = [thoi_diem_tao]
    for ten_cot in COT_THOI_GIAN_TIKTOK:
        if dong[ten_cot]:
            cac_moc.append(datetime.strptime(dong[ten_cot], "%d/%m/%Y %H:%M:%S"))
    return sang_epoch(thoi_diem_tao), sang_epoch(max(cac_moc))


def tao_don_tiktok(dong):
    create_time, update_time = thoi_gian_tiktok(dong)
    return {
        "id": dong["Order ID"],
        "status": doi_trang_thai_tiktok(dong["Order Status"]),
        "create_time": create_time,
        "update_time": update_time,
        "payment": {"total_amount": str(so_nguyen(dong["Order Amount"]))},
        "recipient_address": {
            "district_info": [{"address_level": "L1", "address_name": dong["Province"]}],
        },
        "line_items": [],
    }


def tach_line_item(dong):
    """Tách một dòng CSV TikTok số lượng n thành n line item."""
    so_luong = so_nguyen(dong["Quantity"])
    gia_goc = chia_deu(so_nguyen(dong["SKU Subtotal Before Discount"]), so_luong)
    giam_nguoi_ban = chia_deu(so_nguyen(dong["SKU Seller Discount"]), so_luong)
    giam_san = chia_deu(so_nguyen(dong["SKU Platform Discount"]), so_luong)

    cac_line_item = []
    for thu_tu in range(so_luong):
        cac_line_item.append({
            # Id giả, tất định theo (đơn, SKU, thứ tự).
            "id": str(sinh_id_on_dinh("line_item", dong["Order ID"], dong["SKU ID"], str(thu_tu))),
            "sku_id": dong["SKU ID"],
            # Giữ nguyên dấu nháy như CSV, làm sạch là việc của transform.
            "seller_sku": dong["Seller SKU"],
            "product_name": dong["Product Name"],
            "sku_name": dong["Variation"],
            "original_price": str(gia_goc[thu_tu]),
            "seller_discount": str(giam_nguoi_ban[thu_tu]),
            "platform_discount": str(giam_san[thu_tu]),
            "sale_price": str(gia_goc[thu_tu] - giam_nguoi_ban[thu_tu] - giam_san[thu_tu]),
        })
    return cac_line_item


def tao_giao_dich_sku(dong):
    """Dòng hoàn hàng thì khoản hoàn = −(SKU Subtotal Before Discount), dòng khác bằng 0."""
    if dong["Cancelation/Return Type"] == LOAI_HOAN_HANG:
        khoan_hoan = -so_nguyen(dong["SKU Subtotal Before Discount"])
    else:
        khoan_hoan = 0
    return {
        "sku_id": dong["SKU ID"],
        "revenue_breakdown": {"refund_subtotal_before_discount_amount": str(khoan_hoan)},
    }


def dung_du_lieu_tiktok(duong_dan=FILE_TIKTOK):
    """Finance chỉ có cho đơn COMPLETED; affiliate theo từng (đơn, sku_id)."""
    cac_shop = {
        ten_shop: {"shop_cipher": shop_cipher, "don_hang": {}, "finance": {}, "affiliate": {}}
        for ten_shop, shop_cipher in SHOP_CIPHER_TIKTOK.items()
    }
    for dong in doc_csv(duong_dan):
        if dong["Shop"] not in cac_shop:
            raise ValueError(f"Shop TikTok chưa có shop_cipher giả: {dong['Shop']!r}")
        shop = cac_shop[dong["Shop"]]

        ma_don = dong["Order ID"]
        if ma_don not in shop["don_hang"]:
            shop["don_hang"][ma_don] = tao_don_tiktok(dong)
        don = shop["don_hang"][ma_don]
        don["line_items"].extend(tach_line_item(dong))

        if la_dong_affiliate(dong, NGUON_TU_BAN_TIKTOK):
            muc_affiliate = shop["affiliate"].setdefault(ma_don, {"create_time": don["create_time"], "skus": []})
            muc_affiliate["skus"].append(dong["SKU ID"])

        if don["status"] == TRANG_THAI_DA_QUYET_TOAN:
            shop["finance"].setdefault(ma_don, []).append(tao_giao_dich_sku(dong))
        elif dong["Cancelation/Return Type"] == LOAI_HOAN_HANG:
            # Đơn chưa quyết toán không có Finance nên dòng hoàn sẽ mất khỏi đường API; báo lỗi để không mất âm thầm.
            raise ValueError(f"Dòng hoàn hàng thuộc đơn chưa COMPLETED: {ma_don}")
    return cac_shop
