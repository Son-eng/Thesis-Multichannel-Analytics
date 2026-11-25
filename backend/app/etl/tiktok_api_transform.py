# JSON API TikTok thành DataFrame cột chuẩn; mỗi line item là một sản phẩm nên gộp theo (đơn, sku_id)
## Mỗi sản phẩm lẻ là 1 dòng, gộp các sản phẩm cùng SKU thành 1 dòng, cộng dồn giảm giá và số lượng
## Nhận diện đơn hoàn hàng từ finance API 
import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_TIKTOK
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_api

SKU_KHONG_XAC_DINH = cleaners.SKU_KHONG_XAC_DINH
CAP_TINH = "L1"
COT_TIEN_LINE_ITEM = ["original_price", "sale_price", "seller_discount", "platform_discount"]
COT_BO_DEM = ["rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
              "rows_province_unmapped", "rows_product_unmapped"]


def tinh_cua_don(don):
    cac_cap = don.get("recipient_address", {}).get("district_info", [])
    return next((cap["address_name"] for cap in cac_cap if cap.get("address_level") == CAP_TINH), None)


def trai_phang_line_item(cac_don):
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
    """Gộp các line item cùng (order_id, sku_id) thành 1 dòng mức SKU."""
    nhom = line_item.groupby(["order_id", "sku_id"], sort=False)
    gop = nhom.agg(
        status=("status", "first"),
        create_time=("create_time", "first"),
        total_amount=("total_amount", "first"),
        province=("province", "first"),
        seller_sku=("seller_sku", "first"),
        product_name=("product_name", "first"),
        sku_name=("sku_name", "first"),
        # original_price luôn chia hết theo số lượng nên lấy của một line item là đúng.
        unit_price=("original_price", "first"),
        quantity=("original_price", "size"),
        tong_original_price=("original_price", "sum"),
        tong_sale_price=("sale_price", "sum"),
        tong_seller_discount=("seller_discount", "sum"),
    )
    return gop.reset_index()


def tap_sku_hoan(finance):
    """Hoàn hàng lấy từ Finance: khoản hoàn khác 0 (không rõ dấu nên không so < 0)."""
    tap = set()
    for ma_don, du_lieu in finance.items():
        for giao_dich in du_lieu.get("sku_transactions", []):
            khoan_hoan = giao_dich["revenue_breakdown"]["refund_subtotal_before_discount_amount"]
            if float(khoan_hoan) != 0:
                tap.add((ma_don, giao_dich["sku_id"]))
    return tap


def tap_sku_affiliate(cac_don_affiliate):
    return {(don["id"], sku["sku_id"]) for don in cac_don_affiliate for sku in don["skus"]}


def chuan_hoa_api_tiktok(ket_qua_keo, ten_shop):
    line_item = trai_phang_line_item(ket_qua_keo["don_hang"])
    if line_item.empty:
        return pd.DataFrame(columns=COT_CHUAN_TIKTOK), dict.fromkeys(COT_BO_DEM, 0)
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["tiktok"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    # Mọi trường tiền của TikTok là chuỗi, đổi sang số trước khi cộng.
    for cot in COT_TIEN_LINE_ITEM:
        line_item[cot] = cleaners.doi_chuoi_tien_sang_so(line_item[cot])
    bang = gop_theo_sku(line_item)

    sku_da_lam_sach = cleaners.lam_sach_seller_sku_tiktok(bang["seller_sku"])
    sku = sku_da_lam_sach.mask(sku_da_lam_sach.isna() | (sku_da_lam_sach == ""), SKU_KHONG_XAC_DINH)

    sku_hoan = tap_sku_hoan(ket_qua_keo["finance"])
    la_hoan = pd.Series([khoa in sku_hoan for khoa in zip(bang["order_id"], bang["sku_id"])], index=bang.index)
    # NMV = tổng (original_price − seller_discount), cùng công thức đường file.
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
    # API không có số lượng hoàn nên ghi 0; tỷ lệ hoàn dùng is_returned.
    bang_chuan["returned_quantity"] = 0
    bang_chuan["unit_price"] = bang["unit_price"]
    bang_chuan["sku_subtotal_after_discount"] = bang["tong_sale_price"]
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # Mức đơn, lặp lại trên mọi dòng của đơn, không được SUM theo dòng.
    bang_chuan["order_amount"] = cleaners.doi_chuoi_tien_sang_so(bang["total_amount"])
    # Cặp (đơn, sku_id) có trong báo cáo affiliate thì True; không có thông tin thì coi là shop tự bán.
    sku_affiliate = tap_sku_affiliate(ket_qua_keo.get("affiliate", []))
    bang_chuan["is_affiliate"] = pd.Series(
        [khoa in sku_affiliate for khoa in zip(bang["order_id"], bang["sku_id"])], index=bang.index, dtype=bool)
    bang_chuan["province"] = bang["province"].apply(cleaners.normalize_province, args=(bang_tinh,))
    bang_chuan["province_raw"] = bang["province"]
    bang_chuan["hour_bucket"] = cleaners.tinh_khung_gio(thoi_diem_tao)
    bang_chuan["data_source"] = "api"

    bo_dem = {
        "rows_sku_fallback": 0,
        "rows_sku_unknown": int((sku == SKU_KHONG_XAC_DINH).sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan[COT_CHUAN_TIKTOK], bo_dem
