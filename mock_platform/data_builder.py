"""Sinh dữ liệu cho máy chủ giả lập từ 2 file CSV ẩn danh (SPEC §19.4).

Chạy một lần lúc máy chủ khởi động, giữ kết quả trong bộ nhớ, KHÔNG ghi ra
file JSON nào.

Hướng đi NGƯỢC với parser của đường file: parser đọc CSV ra cột chuẩn; file
này đọc CSV ra đúng khuôn trường mà API của sàn trả về (cột "Sinh từ CSV" ở
§21.1, §21.2). Tên trường lấy từ tài liệu:
- Shopee `get_order_detail`: tên trường ở §21.1, đã đối chiếu dữ liệu API thật (§17.8).
- Shopee escrow: `Pipeline/Shopee/ESCROW_FIELD_REFERENCE.md` (`order_income.items[]`).
- TikTok: `Pipeline/Tiktok/Orders/Get Order List.md`,
  `Pipeline/Tiktok/Finance/Get Transactions by Order.md`.
Chỉ sinh những trường mà §21 dùng tới. Trường nào tài liệu có mà hệ thống
không dùng thì không sinh, để không phải tự bịa giá trị cho nó.

KHÔNG import gì từ backend/, KHÔNG gọi parser của backend. Test khứ hồi ở
bước 10 (§21.5) so "CSV → parser" với "CSV → file này → HTTP → connector →
transform". Nếu file này dùng lại parser thì hai nhánh chung code, và test chỉ
còn tự so với chính mình.

Kết quả chỉ là dict/list Python. Ghép thành phản hồi HTTP (code, message,
phân trang…) là việc của shopee_routes.py / tiktok_routes.py.
"""

import hashlib
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

THU_MUC_MAU = Path(__file__).resolve().parent.parent / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"

# Mọi mốc thời gian trong CSV là giờ Việt Nam; API trả epoch (giây, UTC).
GIO_VN = timezone(timedelta(hours=7))

# File Shopee không có cột shop; dữ liệu mẫu là một shop (§19.4).
SHOP_SHOPEE = "Shop C"

# shop_cipher GIẢ cho 2 shop TikTok — mỗi shop một giá trị, như thật (§19.4).
# Không phải bí mật (cipher chỉ để chỉ shop nào), nên để thẳng ở đây.
SHOP_CIPHER_TIKTOK = {
    "Shop A": "MOCK_CIPHER_SHOP_A",
    "Shop B": "MOCK_CIPHER_SHOP_B",
}

# Đổi ngược trạng thái CSV → mã API (§6.4, bảng "Đổi ngược").
TRANG_THAI_SHOPEE = {
    "Hoàn thành": "COMPLETED",
    "Đã nhận được hàng": "COMPLETED",
    "Đã giao": "TO_CONFIRM_RECEIVE",
    "Đang giao": "SHIPPED",
    "Chờ giao hàng": "PROCESSED",
    "Chờ xác nhận": "UNPAID",
    "Đã hủy": "CANCELLED",
    # 19 dòng rỗng → COMPLETED (chốt 12/10, §6.4): API thật không bao giờ
    # trả trạng thái rỗng, và 3/3 đơn rỗng có trong API thật là COMPLETED.
    "": "COMPLETED",
}
# Trạng thái này có ngày hạn trả hàng ở cuối chuỗi (14 biến thể trong dữ liệu
# mẫu) nên so theo tiền tố, không tra bảng.
TIEN_TO_DA_NHAN_HANG = "Người mua xác nhận đã nhận được hàng"

TRANG_THAI_TIKTOK = {
    "Đã hoàn tất": "COMPLETED",
    "Đã hủy": "CANCELLED",
    "Cần vận chuyển": "AWAITING_SHIPMENT",
    # Giả định (§6.4): CSV không phân biệt đang giao / đã giao.
    "Đã vận chuyển": "IN_TRANSIT",
}

# Chỉ đơn đã quyết toán mới có dữ liệu Finance (§20.2).
TRANG_THAI_DA_QUYET_TOAN = "COMPLETED"
LOAI_HOAN_HANG = "Return/Refund"

# Cột nguồn doanh thu và giá trị "shop tự bán" của mỗi sàn (§21.4): giá trị khác
# và KHÔNG rỗng (các nhãn AFF_*) là đơn affiliate. Tự viết lại, không import
# từ backend (backend dùng cleaners.xac_dinh_affiliate cho đường file).
COT_NGUON_DOANH_THU = "Nguồn Doanh Thu"
NGUON_TU_BAN_SHOPEE = "ADS"
NGUON_TU_BAN_TIKTOK = "Inhouse"

COT_THOI_GIAN_TIKTOK = ["Paid Time", "RTS Time", "Shipped Time", "Delivered Time", "Cancelled Time"]


def doc_csv(duong_dan):
    """Đọc CSV thành list dict, mọi ô là chuỗi đã bỏ khoảng trắng hai đầu.

    Nhận: đường dẫn file CSV ẩn danh.
    Trả: list dict {tên cột: chuỗi}, theo đúng thứ tự dòng trong file.
    Cần hàm này vì cả 2 sàn cùng phải xử lý 3 điểm của file xuất:
    - keep_default_na=False: ô rỗng là "" chứ không thành NaN, nên không bao
      giờ dính bẫy chuỗi "nan" của pandas 2.2 (§5.1 CẢNH BÁO 2).
    - Ô "trống" của Shopee thực ra là một dấu cách → strip cho về "".
    - 8 tên cột Shopee (có `Giá ưu đãi`) viết ở dạng Unicode tổ hợp (NFD), gõ
      tên cột thường thì tra không thấy → chuẩn hóa NFC. NFC không đổi chữ
      hoa/thường nên 2 cột `Tổng số tiền N/người mua thanh toán` vẫn tách
      riêng (§5.1 CẢNH BÁO 1).
    """
    bang = pd.read_csv(duong_dan, dtype=str, keep_default_na=False)
    bang.columns = [unicodedata.normalize("NFC", ten_cot) for ten_cot in bang.columns]
    bang = bang.apply(lambda cot: cot.str.strip())
    return bang.to_dict("records")


def so_nguyen(chuoi):
    """Đổi chuỗi số tiền / số lượng của CSV thành int.

    Nhận: chuỗi như "865000", "1,415,000" hoặc "2.28e+06" (§2.3).
    Trả: int. Báo lỗi nếu giá trị không phải số nguyên.
    Cần hàm này vì Shopee ghi giá ở dạng ký hiệu khoa học — int("2.28e+06")
    vỡ, nên phải qua float. Kiểm phần lẻ để không âm thầm cắt mất tiền.
    """
    gia_tri = float(chuoi.replace(",", ""))
    if not gia_tri.is_integer():
        raise ValueError(f"Giá trị không phải số nguyên: {chuoi!r}")
    return int(gia_tri)


def sang_epoch(thoi_diem):
    """Đổi datetime theo giờ VN (không gắn múi giờ) sang epoch giây như API trả."""
    return int(thoi_diem.replace(tzinfo=GIO_VN).timestamp())


def sinh_id_on_dinh(*cac_phan):
    """Sinh id số tất định từ các chuỗi đầu vào — ID GIẢ, không phải id thật của sàn.

    Nhận: các chuỗi xác định đối tượng (ví dụ "item", SKU).
    Trả: int dương < 2^60 — cùng đầu vào luôn ra cùng id, chạy lại ra y hệt.
    Cần hàm này vì CSV không có item_id / model_id / id line item mà API có.
    Dùng sha256 chứ không dùng hash() của Python: hash() đổi giá trị mỗi lần
    chạy chương trình, id sẽ khác nhau giữa 2 lần khởi động máy chủ.
    """
    chuoi = "|".join(cac_phan)
    ma_bam = hashlib.sha256(chuoi.encode("utf-8")).hexdigest()
    return int(ma_bam[:15], 16)


def la_dong_affiliate(dong, nguon_tu_ban):
    """Dòng CSV có phải đơn affiliate không (§21.4).

    True khi `Nguồn Doanh Thu` CÓ giá trị và khác giá trị tự bán; ô rỗng →
    False (chốt 12/10/2026: không có thông tin = shop tự bán). `doc_csv` đã
    strip nên ô chỉ có khoảng trắng đã là "".
    """
    nguon = dong[COT_NGUON_DOANH_THU]
    return nguon != "" and nguon != nguon_tu_ban


def chia_deu(tong, so_phan):
    """Chia một số tiền nguyên thành so_phan phần, phần dư dồn vào phần đầu (§19.4).

    Nhận: tổng (int), số phần (int ≥ 1).
    Trả: list so_phan số nguyên, cộng lại đúng bằng tổng.
    Ví dụ: chia_deu(10, 3) → [4, 3, 3].
    """
    moi_phan = tong // so_phan
    phan_du = tong - moi_phan * so_phan
    return [moi_phan + phan_du] + [moi_phan] * (so_phan - 1)


# ---------------------------------------------------------------- Shopee

def doi_trang_thai_shopee(trang_thai_csv):
    """Đổi trạng thái CSV Shopee → mã API (§6.4). Giá trị lạ → báo lỗi ngay.

    Báo lỗi thay vì gán mặc định: dữ liệu giả lập phải đúng từng dòng, gán bừa
    một mã thì test khứ hồi lệch mà không ai biết vì sao.
    """
    if trang_thai_csv.startswith(TIEN_TO_DA_NHAN_HANG):
        return "COMPLETED"
    if trang_thai_csv not in TRANG_THAI_SHOPEE:
        raise ValueError(f"Trạng thái Shopee chưa có trong bảng đổi ngược §6.4: {trang_thai_csv!r}")
    return TRANG_THAI_SHOPEE[trang_thai_csv]


def thoi_gian_shopee(dong):
    """Tính (create_time, update_time) epoch của một đơn Shopee (§19.4).

    create_time: CSV chỉ có ngày, nên lấy ngày đặt + giờ đầu của khung giờ,
    phút và giây bằng 0 (khớp API thật 275/275 dòng, §17.8).
    update_time: muộn nhất trong create_time, giờ hoàn thành, ngày hủy.
    Phải gộp cả create_time vì 42 dòng có ngày hủy SỚM hơn ngày đặt; bỏ
    create_time ra thì update_time < create_time — điều API thật không trả.
    """
    ngay_dat = datetime.strptime(dong["Ngày đặt hàng"], "%Y/%m/%d")
    # "13H - 14H" → 13
    gio_dau_khung = int(dong["Khung Giờ Ra Đơn"].split("H")[0])
    thoi_diem_tao = ngay_dat + timedelta(hours=gio_dau_khung)

    cac_moc = [thoi_diem_tao]
    if dong["Thời gian hoàn thành đơn hàng"]:
        cac_moc.append(datetime.strptime(dong["Thời gian hoàn thành đơn hàng"], "%Y-%m-%d %H:%M"))
    if dong["Ngày hủy thành công"]:
        # Cột này chỉ có ngày → tính là 00:00 giờ VN.
        cac_moc.append(datetime.strptime(dong["Ngày hủy thành công"], "%Y-%m-%d"))
    return sang_epoch(thoi_diem_tao), sang_epoch(max(cac_moc))


def tao_don_shopee(dong):
    """Dựng phần mức ĐƠN của một đơn Shopee (khuôn `get_order_detail`), item_list rỗng.

    Lấy từ dòng đầu tiên của đơn: đã kiểm trên dữ liệu mẫu, ngày, khung giờ,
    trạng thái, tỉnh, giờ hoàn thành, ngày hủy giống nhau ở mọi dòng cùng đơn.
    """
    create_time, update_time = thoi_gian_shopee(dong)
    return {
        "order_sn": dong["Mã đơn hàng"],
        "order_status": doi_trang_thai_shopee(dong["Trạng Thái Đơn Hàng"]),
        "create_time": create_time,
        "update_time": update_time,
        # GIẢ ĐỊNH đã có quyền dữ liệu nhạy cảm — API thật hiện trả "****" (§21.1).
        "recipient_address": {"state": dong["Tỉnh/Thành phố"]},
        "item_list": [],
    }


def tao_mat_hang_shopee(dong):
    """Dựng một phần tử `item_list[]` từ một dòng CSV Shopee (§21.1).

    item_id / model_id là id GIẢ, sinh tất định: cùng sản phẩm → cùng item_id,
    cùng phân loại → cùng model_id. Khóa sản phẩm là `SKU sản phẩm`; 6 dòng
    rỗng SKU thì dùng tên sản phẩm (cả 6 cùng một tên, §5.1).
    """
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
        # Chỉ dùng cho NMV tạm tính khi đơn chưa có escrow (§7.5, §21.1).
        "model_discounted_price": so_nguyen(dong["Giá ưu đãi"]),
        "returned_qty": so_nguyen(dong["Số lượng sản phẩm được hoàn trả"]),
    }


def dung_du_lieu_shopee(duong_dan=FILE_SHOPEE):
    """Dựng toàn bộ dữ liệu Shopee cho máy chủ giả lập.

    Nhận: đường dẫn CSV Shopee ẩn danh (mặc định file mẫu).
    Trả: dict
        shop_name — "Shop C"
        don_hang  — {order_sn: đơn khuôn get_order_detail}, theo thứ tự CSV
        escrow    — {order_sn: {order_sn, order_income: {items: [{item_id, model_id, seller_discount}]}}}
        affiliate — {order_sn: create_time} của các đơn affiliate (§21.4), cho
                    get_conversion_report. Cờ đồng nhất theo đơn: 0 đơn trong
                    dữ liệu mẫu có dòng affiliate lẫn dòng tự bán.
    Escrow sinh cho MỌI đơn; công tắc MOCK_ESCROW_MODE (§19.2) lọc ở tầng route.
    """
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
            # Cả dòng, không chia theo số lượng: Giá gốc × SL − Người bán trợ
            # giá = số người mua trả, đúng 22/22 dòng SL > 1 (§17.8).
            "seller_discount": so_nguyen(dong["Người bán trợ giá"]),
        })
    return {"shop_name": SHOP_SHOPEE, "don_hang": don_hang, "escrow": escrow, "affiliate": affiliate}


# ---------------------------------------------------------------- TikTok

def doi_trang_thai_tiktok(trang_thai_csv):
    """Đổi trạng thái CSV TikTok → mã API (§6.4). Giá trị lạ → báo lỗi ngay."""
    if trang_thai_csv not in TRANG_THAI_TIKTOK:
        raise ValueError(f"Trạng thái TikTok chưa có trong bảng đổi ngược §6.4: {trang_thai_csv!r}")
    return TRANG_THAI_TIKTOK[trang_thai_csv]


def thoi_gian_tiktok(dong):
    """Tính (create_time, update_time) epoch của một đơn TikTok (§19.4).

    update_time: muộn nhất trong create_time và 5 cột mốc của đơn. Gộp
    create_time vì cùng lý do với Shopee (dữ liệu mẫu TikTok: 0 dòng lệch).
    """
    thoi_diem_tao = datetime.strptime(dong["Created Time"], "%d/%m/%Y %H:%M:%S")
    cac_moc = [thoi_diem_tao]
    for ten_cot in COT_THOI_GIAN_TIKTOK:
        if dong[ten_cot]:
            cac_moc.append(datetime.strptime(dong[ten_cot], "%d/%m/%Y %H:%M:%S"))
    return sang_epoch(thoi_diem_tao), sang_epoch(max(cac_moc))


def tao_don_tiktok(dong):
    """Dựng phần mức ĐƠN của một đơn TikTok (khuôn `orders[]`), line_items rỗng.

    Lấy từ dòng đầu của đơn: trạng thái, giờ tạo, shop, tỉnh, Order Amount và
    các cột thời gian giống nhau ở mọi dòng cùng đơn (đã kiểm trên dữ liệu mẫu).
    """
    create_time, update_time = thoi_gian_tiktok(dong)
    return {
        "id": dong["Order ID"],
        "status": doi_trang_thai_tiktok(dong["Order Status"]),
        "create_time": create_time,
        "update_time": update_time,
        # Tài liệu: mọi trường tiền là string.
        "payment": {"total_amount": str(so_nguyen(dong["Order Amount"]))},
        # Tỉnh ở cấp L1 (§21.2). Chỉ sinh cấp hệ thống dùng tới.
        "recipient_address": {
            "district_info": [{"address_level": "L1", "address_name": dong["Province"]}],
        },
        "line_items": [],
    }


def tach_line_item(dong):
    """Tách một dòng CSV TikTok số lượng n thành n line item (§19.4).

    Nhận: một dòng CSV TikTok.
    Trả: list n line item. 3 khoản tiền chia đều cho n, phần dư dồn vào line
    item đầu, nên cộng n line item lại đúng bằng dòng CSV.
    `sale_price` không chia từ cột `SKU Subtotal After Discount` mà tính bằng
    original_price − seller_discount − platform_discount của chính line item
    đó. Đẳng thức này đúng ở 7.540/7.540 dòng CSV, nên tổng vẫn khớp; còn chia
    riêng cột After thì phần dư (1 dòng không chia hết) có thể rơi lệch, làm
    từng line item sai đẳng thức.
    """
    so_luong = so_nguyen(dong["Quantity"])
    gia_goc = chia_deu(so_nguyen(dong["SKU Subtotal Before Discount"]), so_luong)
    giam_nguoi_ban = chia_deu(so_nguyen(dong["SKU Seller Discount"]), so_luong)
    giam_san = chia_deu(so_nguyen(dong["SKU Platform Discount"]), so_luong)

    cac_line_item = []
    for thu_tu in range(so_luong):
        cac_line_item.append({
            # Id GIẢ, tất định theo (đơn, SKU, thứ tự).
            "id": str(sinh_id_on_dinh("line_item", dong["Order ID"], dong["SKU ID"], str(thu_tu))),
            "sku_id": dong["SKU ID"],
            # Giữ nguyên dấu nháy như CSV; làm sạch là việc của transform (§21.2).
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
    """Dựng một phần tử `sku_transactions[]` của Finance từ một dòng CSV (§19.4).

    Dòng hoàn hàng → khoản hoàn = −(SKU Subtotal Before Discount); dòng khác → 0.
    Viết dạng chuỗi đúng kiểu `string` của tài liệu. Chỉ sinh trường mà §21.2
    dùng; các trường tiền khác tài liệu có nhưng không KPI nào cần.
    """
    if dong["Cancelation/Return Type"] == LOAI_HOAN_HANG:
        khoan_hoan = -so_nguyen(dong["SKU Subtotal Before Discount"])
    else:
        khoan_hoan = 0
    return {
        "sku_id": dong["SKU ID"],
        "revenue_breakdown": {"refund_subtotal_before_discount_amount": str(khoan_hoan)},
    }


def dung_du_lieu_tiktok(duong_dan=FILE_TIKTOK):
    """Dựng toàn bộ dữ liệu TikTok cho máy chủ giả lập, tách theo shop.

    Nhận: đường dẫn CSV TikTok ẩn danh (mặc định file mẫu).
    Trả: {tên shop: {shop_cipher, don_hang: {id: đơn khuôn orders[]},
                     finance: {id: [sku_transactions…]},
                     affiliate: {id: {create_time, skus: [sku_id…]}}}}
    Finance chỉ có cho đơn COMPLETED (chỉ đơn đã quyết toán mới có, §20.2).
    Affiliate theo từng (đơn, sku_id) vì affiliate_seller/orders/search trả
    skus[] (§21.4); mọi trạng thái đơn đều có mặt nếu `Nguồn Doanh Thu` là AFF_*.
    """
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
            # Đơn chưa quyết toán không có Finance → dòng hoàn này sẽ biến mất
            # khỏi đường API. Dữ liệu mẫu: 0 dòng (139/139 hoàn là COMPLETED).
            # Báo lỗi để không âm thầm mất một dòng hoàn khi đổi file mẫu.
            raise ValueError(f"Dòng hoàn hàng thuộc đơn chưa COMPLETED: {ma_don}")
    return cac_shop
