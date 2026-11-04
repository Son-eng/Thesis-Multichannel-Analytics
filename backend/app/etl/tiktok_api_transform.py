"""JSON API TikTok → DataFrame cột chuẩn (SPEC §21.2) — đường nạp CHÍNH.

Đầu vào: kết quả `TikTokClient.keo_don()` của MỘT shop — {"don_hang": [đơn
thô], "finance": {order_id: data thô}}. Đầu ra: đúng COT_CHUAN_TIKTOK và dict
5 bộ đếm (§3.3), cùng khuôn với tiktok_parser.chuan_hoa_file_tiktok.

Dùng CHUNG cleaners.py, status_mapper.py (bảng tra API §6.4) và mapping JSON
với đường file — không gọi parser CSV (§21.5).

Luồng:
    trải phẳng line_items (1 line item = 1 sản phẩm, đã tách theo số lượng)
    → GỘP các line item cùng (đơn, sku_id) thành 1 dòng chuẩn (§21.2):
        số lượng = số line item, các trường tiền cộng dồn
    → is_returned từ Finance: refund_subtotal_before_discount_amount ≠ 0
    → tính các cột còn lại → đếm 5 bộ đếm
"""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_TIKTOK
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_api

SKU_KHONG_XAC_DINH = cleaners.SKU_KHONG_XAC_DINH
CAP_TINH = "L1"     # recipient_address.district_info: tỉnh/thành ở cấp L1 (§21.2)
COT_TIEN_LINE_ITEM = ["original_price", "sale_price", "seller_discount", "platform_discount"]
COT_BO_DEM = ["rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
              "rows_province_unmapped", "rows_product_unmapped"]


def tinh_cua_don(don):
    """Tên tỉnh cấp L1 trong recipient_address.district_info, hoặc None nếu không có."""
    cac_cap = don.get("recipient_address", {}).get("district_info", [])
    return next((cap["address_name"] for cap in cac_cap if cap.get("address_level") == CAP_TINH), None)


def trai_phang_line_item(cac_don):
    """Đơn thô → DataFrame, mỗi dòng là MỘT line item kèm các trường mức đơn."""
    cac_dong = []
    for don in cac_don:
        muc_don = {
            "order_id": don["id"],
            "status": don["status"],
            "create_time": don["create_time"],
            "total_amount": don.get("payment", {}).get("total_amount"),
            "province": tinh_cua_don(don),
        }
        for line_item in don["line_items"]:
            cac_dong.append({**muc_don, **line_item})
    return pd.DataFrame(cac_dong)


def gop_theo_sku(line_item):
    """Gộp các line item cùng (order_id, sku_id) thành 1 dòng mức SKU (§21.2).

    Nhận: bảng line item, cột tiền đã là số.
    Trả: DataFrame mỗi dòng một (order_id, sku_id): quantity = số line item;
    tổng original_price / sale_price / seller_discount; các trường mô tả lấy
    từ line item đầu (giống nhau trong cùng SKU của cùng đơn).
    sort=False: giữ thứ tự xuất hiện như sàn trả, để đọc bảng dễ đối chiếu.
    """
    nhom = line_item.groupby(["order_id", "sku_id"], sort=False)
    gop = nhom.agg(
        status=("status", "first"),
        create_time=("create_time", "first"),
        total_amount=("total_amount", "first"),
        province=("province", "first"),
        seller_sku=("seller_sku", "first"),
        product_name=("product_name", "first"),
        sku_name=("sku_name", "first"),
        # Giá gốc 1 sản phẩm = original_price của 1 line item. Line item đầu
        # có thể nhận phần dư khi sàn chia tiền (§19.4), nhưng original_price
        # luôn chia hết theo số lượng (7.540/7.540, §17.8), nên dùng được.
        unit_price=("original_price", "first"),
        quantity=("original_price", "size"),
        tong_original_price=("original_price", "sum"),
        tong_sale_price=("sale_price", "sum"),
        tong_seller_discount=("seller_discount", "sum"),
    )
    return gop.reset_index()


def tap_sku_hoan(finance):
    """{(order_id, sku_id)} có refund_subtotal_before_discount_amount ≠ 0 (§21.2).

    So "≠ 0" chứ không "< 0": tài liệu không nói rõ dấu của khoản hoàn.
    So sau khi đổi sang số: "0", "0.00", "-0" đều là 0.
    """
    tap = set()
    for ma_don, du_lieu in finance.items():
        for giao_dich in du_lieu.get("sku_transactions", []):
            khoan_hoan = giao_dich["revenue_breakdown"]["refund_subtotal_before_discount_amount"]
            if float(khoan_hoan) != 0:
                tap.add((ma_don, giao_dich["sku_id"]))
    return tap


def chuan_hoa_api_tiktok(ket_qua_keo, ten_shop):
    """Chuẩn hóa kết quả một lượt kéo API TikTok của một shop thành dữ liệu sẵn sàng nạp CSDL.

    Nhận: ket_qua_keo — dict từ TikTokClient.keo_don(); ten_shop — tên gian
    hàng gắn với shop_cipher (dòng platform_tokens, §21.2).
    Trả: tuple (DataFrame COT_CHUAN_TIKTOK, dict 5 bộ đếm §3.3).
    """
    line_item = trai_phang_line_item(ket_qua_keo["don_hang"])
    if line_item.empty:
        return pd.DataFrame(columns=COT_CHUAN_TIKTOK), dict.fromkeys(COT_BO_DEM, 0)
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["tiktok"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    # Tài liệu: mọi trường tiền của TikTok là chuỗi → đổi sang số trước khi cộng.
    for cot in COT_TIEN_LINE_ITEM:
        line_item[cot] = cleaners.doi_chuoi_tien_sang_so(line_item[cot])
    bang = gop_theo_sku(line_item)

    # Cùng hàm làm sạch `Seller SKU` với đường file (§5.2); rỗng → "UNKNOWN".
    sku_da_lam_sach = cleaners.lam_sach_seller_sku_tiktok(bang["seller_sku"])
    sku = sku_da_lam_sach.mask(sku_da_lam_sach.isna() | (sku_da_lam_sach == ""), SKU_KHONG_XAC_DINH)

    sku_hoan = tap_sku_hoan(ket_qua_keo["finance"])
    la_hoan = pd.Series([khoa in sku_hoan for khoa in zip(bang["order_id"], bang["sku_id"])], index=bang.index)
    # NMV = Σ (original_price − seller_discount) — cùng công thức đường file (§7.5).
    nmv = bang["tong_original_price"] - bang["tong_seller_discount"]
    thoi_diem_tao = cleaners.doi_timestamp_api_sang_gio_vn(bang["create_time"])

    bang_chuan = pd.DataFrame(index=bang.index)
    bang_chuan["shop_name"] = ten_shop
    bang_chuan["order_id"] = bang["order_id"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    bang_chuan["order_date"] = thoi_diem_tao.dt.normalize()
    bang_chuan["order_created_at"] = thoi_diem_tao
    bang_chuan["order_status_raw"] = bang["status"]
    bang_chuan["order_status"] = bang["status"].apply(gom_nhom_trang_thai_api, args=("tiktok",))
    bang_chuan["is_returned"] = la_hoan
    bang_chuan["product_name"] = bang["product_name"]
    bang_chuan["variation"] = bang["sku_name"]
    bang_chuan["quantity"] = bang["quantity"]
    # §21.2 không ánh xạ cột này cho đường API: không trường nào của
    # orders/search hay Finance tương ứng `Sku Quantity of return`. Ghi 0;
    # cột vốn CẤM dùng tính tỷ lệ hoàn (§3.2) — tỷ lệ hoàn dùng is_returned.
    bang_chuan["returned_quantity"] = 0
    bang_chuan["unit_price"] = bang["unit_price"]
    bang_chuan["sku_subtotal_after_discount"] = bang["tong_sale_price"]
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # MỨC ĐƠN (§7.4): payment.total_amount lặp lại trên mọi dòng của đơn — CẤM SUM theo dòng.
    bang_chuan["order_amount"] = cleaners.doi_chuoi_tien_sang_so(bang["total_amount"])
    # Nguồn đường API là affiliate_seller/orders/search — làm ở lượt 10c
    # (chỉ dẫn 013). Chưa có thì không có thông tin = shop tự bán (§21.4).
    bang_chuan["is_affiliate"] = False
    bang_chuan["province"] = bang["province"].apply(cleaners.normalize_province, args=(bang_tinh,))
    bang_chuan["province_raw"] = bang["province"]
    bang_chuan["hour_bucket"] = cleaners.tinh_khung_gio(thoi_diem_tao)
    bang_chuan["data_source"] = "api"

    bo_dem = {
        # TikTok không có chuỗi dự phòng sku (§5.2) — giống đường file.
        "rows_sku_fallback": 0,
        "rows_sku_unknown": int((sku == SKU_KHONG_XAC_DINH).sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan[COT_CHUAN_TIKTOK], bo_dem
