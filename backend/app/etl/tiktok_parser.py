"""Đọc file CSV TikTok → DataFrame cột chuẩn (SPEC §5.2) — đường nạp file dự phòng.

Luồng: đọc đúng các cột cần dùng → làm sạch sku → tính từng cột chuẩn bằng
các hàm có sẵn trong cleaners.py / status_mapper.py → đếm 5 chỉ số chất lượng
dữ liệu (§3.3).

Khác Shopee ở 3 chỗ: file có cột `Shop` (một file chứa nhiều gian hàng), có
giờ tạo đơn đến từng giây (nên tự tính được ngày và khung giờ), và không có
chuỗi dự phòng sku.

Kết quả của parser này là "đáp án" cho test khứ hồi của đường API (§21.5).
"""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_TIKTOK
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_file

# Chỉ đọc các cột này (usecols): file gốc có 14 cột thông tin cá nhân (§5.2),
# không đọc thì PII không bao giờ vào bộ nhớ. Tên viết đúng chính tả gốc,
# không .lower() (cùng quy tắc với Shopee, §5.1 CẢNH BÁO 1).
# KHÔNG đọc các cột công thức của Lark Base, hệ thống tự tính lại (§2.2):
# `NMV Sau Thuế`, `Khung Giờ Ra Đơn`, `SKU Sản Phẩm` (thay bằng product_map.json
# để đường file và đường API tra mã sản phẩm theo cùng một bảng, §21.2).
COT_CAN_DOC = [
    "Shop",
    "Order ID",
    "Seller SKU",
    "Created Time",
    "Order Status",
    "Cancelation/Return Type",
    "Product Name",
    "Variation",
    "Quantity",
    "Sku Quantity of return",
    "SKU Unit Original Price",
    "SKU Subtotal Before Discount",
    "SKU Seller Discount",
    "SKU Subtotal After Discount",
    "Order Amount",
    "Nguồn Doanh Thu",
    "Province",
]

# Giá trị gán khi `Seller SKU` rỗng. Dùng cùng giá trị với cuối chuỗi dự
# phòng của Shopee (§5.1) để sku luôn NOT NULL (§4.1). Dữ liệu mẫu: 0 dòng.
SKU_KHONG_XAC_DINH = "UNKNOWN"

# Giá trị `Cancelation/Return Type` của đơn hoàn hàng (§5.2).
LOAI_HOAN_HANG = "Return/Refund"

# Nguồn doanh thu "shop tự bán" của TikTok. Mọi giá trị khác (AFF_*) là
# affiliate (§21.4).
NGUON_TU_BAN_TIKTOK = "Inhouse"


def doc_csv_tiktok(duong_dan):
    """Đọc các cột cần dùng của file CSV TikTok.

    Nhận: đường dẫn file CSV xuất từ Lark Base (utf-8-sig).
    Trả: DataFrame chỉ gồm COT_CAN_DOC, mọi ô là chuỗi, ô rỗng là NaN.
    Cần hàm này để gom cách đọc file vào một chỗ — cùng lý do với
    doc_csv_shopee.
    """
    # dtype=str quan trọng nhất ở cột `Order ID`: số 18 chữ số, để pandas tự
    # đoán kiểu thì có thể thành số thực và mất các chữ số cuối.
    return pd.read_csv(duong_dan, usecols=COT_CAN_DOC, dtype=str, encoding="utf-8-sig")


def tao_cot_sku(cot_seller_sku):
    """Dựng cột sku từ `Seller SKU`: làm sạch theo §5.2, ô rỗng → "UNKNOWN".

    Nhận: Series `Seller SKU` thô.
    Trả: Series sku không còn NaN.
    Cần hàm này vì sku là khóa chống trùng, NOT NULL (§4.1). Ô chỉ gồm khoảng
    trắng / dấu nháy sau khi làm sạch thành "" — cũng coi là rỗng, nếu không
    sẽ thành một SKU rỗng trong CSDL.
    """
    sku_da_lam_sach = cleaners.lam_sach_seller_sku_tiktok(cot_seller_sku)
    sku_rong = sku_da_lam_sach.isna() | (sku_da_lam_sach == "")
    return sku_da_lam_sach.mask(sku_rong, SKU_KHONG_XAC_DINH)


def tinh_nmv_tiktok(tong_truoc_giam_gia, nguoi_ban_giam_gia):
    """Tính NMV mức dòng của TikTok: SKU Subtotal Before Discount − SKU Seller Discount (§7.5).

    Nhận: 2 Series số cùng độ dài.
    Trả: Series NMV (VND).
    Cần hàm này vì NMV theo định nghĩa của công ty chỉ trừ phần NGƯỜI BÁN tự
    giảm giá; phần sàn giảm (`SKU Platform Discount`) sàn bù lại cho người bán
    nên không trừ. Công thức khớp cột Lark 7.540/7.540 dòng (§17.8).
    """
    return tong_truoc_giam_gia - nguoi_ban_giam_gia


def tao_bang_chuan(bang_goc, sku):
    """Tính toàn bộ cột chuẩn của bảng orders_tiktok từ các cột đã đọc.

    Nhận: bang_goc — kết quả doc_csv_tiktok; sku — kết quả tao_cot_sku.
    Trả: DataFrame đúng và đủ các cột COT_CHUAN_TIKTOK, theo đúng thứ tự đó,
    cùng chỉ số dòng với file.
    Cần hàm này để mọi quy tắc ánh xạ cột của §5.2 nằm ở một chỗ.
    """
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["tiktok"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    thoi_gian_tao_don = cleaners.doc_thoi_gian_tiktok(bang_goc["Created Time"])
    tong_truoc_giam_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Subtotal Before Discount"])
    nguoi_ban_giam_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Seller Discount"])
    nmv = tinh_nmv_tiktok(tong_truoc_giam_gia, nguoi_ban_giam_gia)

    bang_chuan = pd.DataFrame(index=bang_goc.index)
    bang_chuan["shop_name"] = bang_goc["Shop"]
    bang_chuan["order_id"] = bang_goc["Order ID"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    # Bỏ phần giờ, giữ kiểu ngày-giờ lúc 0h — cùng kiểu với order_date của
    # Shopee để 2 bảng xử lý theo kỳ bằng cùng một cách.
    bang_chuan["order_date"] = thoi_gian_tao_don.dt.normalize()
    bang_chuan["order_created_at"] = thoi_gian_tao_don
    bang_chuan["order_status_raw"] = bang_goc["Order Status"]
    # `Order Status` quyết định trạng thái; `Cancelation/Return Type` không
    # ghi đè. 4 dòng "Cancel" mà "Đã hoàn tất" vẫn là completed (§5.2).
    bang_chuan["order_status"] = bang_goc["Order Status"].apply(
        gom_nhom_trang_thai_file, args=("tiktok",)
    )
    # KHÔNG dùng `Sku Quantity of return` > 0: TikTok điền cột đó cả cho đơn
    # hủy, ra 2.308 dòng thay vì 139 (§3.2). Ô rỗng so "==" ra False.
    bang_chuan["is_returned"] = bang_goc["Cancelation/Return Type"] == LOAI_HOAN_HANG
    bang_chuan["product_name"] = bang_goc["Product Name"]
    bang_chuan["variation"] = bang_goc["Variation"]
    bang_chuan["quantity"] = pd.to_numeric(bang_goc["Quantity"], errors="raise")
    # Giữ để truy vết, CẤM dùng tính tỷ lệ hoàn — lý do như is_returned ở trên.
    bang_chuan["returned_quantity"] = pd.to_numeric(bang_goc["Sku Quantity of return"], errors="raise")
    bang_chuan["unit_price"] = cleaners.doi_chuoi_tien_sang_so(bang_goc["SKU Unit Original Price"])
    bang_chuan["sku_subtotal_after_discount"] = cleaners.doi_chuoi_tien_sang_so(
        bang_goc["SKU Subtotal After Discount"]
    )
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # MỨC ĐƠN: giá trị lặp lại trên mọi dòng của cùng đơn — CẤM SUM theo dòng (§7.4).
    bang_chuan["order_amount"] = cleaners.doi_chuoi_tien_sang_so(bang_goc["Order Amount"])
    bang_chuan["is_affiliate"] = bang_goc["Nguồn Doanh Thu"] != NGUON_TU_BAN_TIKTOK
    bang_chuan["province"] = bang_goc["Province"].apply(
        cleaners.normalize_province, args=(bang_tinh,)
    )
    bang_chuan["province_raw"] = bang_goc["Province"]
    # Tự tính từ giờ tạo đơn, không đọc cột `Khung Giờ Ra Đơn` (công thức Lark):
    # đường API cũng phải tính đúng cách này (§21.2), khớp 7.540/7.540 (§17.8).
    bang_chuan["hour_bucket"] = cleaners.tinh_khung_gio(thoi_gian_tao_don)
    bang_chuan["data_source"] = "file"

    return bang_chuan[COT_CHUAN_TIKTOK]


def chuan_hoa_file_tiktok(duong_dan):
    """Chuẩn hóa một file CSV TikTok thành dữ liệu sẵn sàng nạp CSDL.

    Nhận: đường dẫn file CSV. Không cần tên shop: file có cột `Shop`.
    Trả: tuple (DataFrame cột chuẩn COT_CHUAN_TIKTOK, dict 5 bộ đếm chất
    lượng của §3.3 — khóa trùng tên cột của bảng sync_runs).
    Cần hàm này làm cửa vào duy nhất của đường file TikTok (§2.4).
    """
    bang_goc = doc_csv_tiktok(duong_dan)
    sku = tao_cot_sku(bang_goc["Seller SKU"])
    bang_chuan = tao_bang_chuan(bang_goc, sku)

    # Đếm các chỗ đã sửa dữ liệu bẩn âm thầm (§3.3). TikTok không có chuỗi
    # dự phòng sku nên rows_sku_fallback luôn bằng 0.
    bo_dem = {
        "rows_sku_fallback": 0,
        "rows_sku_unknown": int((sku == SKU_KHONG_XAC_DINH).sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan, bo_dem
