"""JSON API Shopee thành DataFrame cột chuẩn."""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_SHOPEE
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_api


def trai_phang_don(cac_don):
    cac_dong = []
    for don in cac_don:
        muc_don = {
            "order_sn": don["order_sn"],
            "order_status": don["order_status"],
            "create_time": don["create_time"],
            "state": don.get("recipient_address", {}).get("state"),
        }
        for mat_hang in don["item_list"]:
            cac_dong.append({**muc_don, **mat_hang})
    return pd.DataFrame(cac_dong)


def bang_seller_discount(cac_phan_tu_escrow):
    """Đơn chưa có escrow bị bỏ qua ở đây, các dòng của đơn đó sẽ là NMV tạm tính."""
    bang = {}
    for phan_tu in cac_phan_tu_escrow:
        if "escrow_detail" not in phan_tu:
            continue
        chi_tiet = phan_tu["escrow_detail"]
        for mat_hang in chi_tiet["order_income"]["items"]:
            khoa = (chi_tiet["order_sn"], mat_hang["item_id"], mat_hang["model_id"])
            bang[khoa] = mat_hang["seller_discount"]
    return bang


def tinh_nmv(bang, seller_discount):
    """Có escrow: giá gốc × SL − seller_discount; chưa có: giá đã giảm × SL, đánh dấu tạm tính, lượt sau upsert lại số chính xác."""
    so_luong = bang["model_quantity_purchased"]
    nmv_chinh_xac = bang["model_original_price"] * so_luong - seller_discount
    nmv_tam_tinh = bang["model_discounted_price"] * so_luong
    la_tam_tinh = seller_discount.isna()
    return nmv_chinh_xac.where(~la_tam_tinh, nmv_tam_tinh), la_tam_tinh


def chuan_hoa_api_shopee(ket_qua_keo, ten_shop):
    bang = trai_phang_don(ket_qua_keo["don_hang"])
    if bang.empty:
        return pd.DataFrame(columns=COT_CHUAN_SHOPEE), dict.fromkeys(
            ["rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
             "rows_province_unmapped", "rows_product_unmapped"], 0)
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["shopee"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    # sku lấy item_sku, dự phòng model_sku rồi "UNKNOWN", dùng chung hàm với đường file.
    sku_san_pham = cleaners.lam_sach_o_sku(bang["item_sku"])
    sku_phan_loai = cleaners.lam_sach_o_sku(bang["model_sku"])
    sku = cleaners.dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)

    tra_escrow = bang_seller_discount(ket_qua_keo["escrow"])
    khoa_dong = zip(bang["order_sn"], bang["item_id"], bang["model_id"])
    seller_discount = pd.Series([tra_escrow.get(khoa) for khoa in khoa_dong], index=bang.index, dtype="float64")
    nmv, la_tam_tinh = tinh_nmv(bang, seller_discount)

    thoi_diem_tao = cleaners.doi_timestamp_api_sang_gio_vn(bang["create_time"])

    bang_chuan = pd.DataFrame(index=bang.index)
    bang_chuan["shop_name"] = ten_shop
    bang_chuan["order_id"] = bang["order_sn"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    bang_chuan["order_date"] = thoi_diem_tao.dt.normalize()
    bang_chuan["order_created_at"] = thoi_diem_tao
    bang_chuan["order_status_raw"] = bang["order_status"]
    bang_chuan["order_status"] = bang["order_status"].apply(gom_nhom_trang_thai_api, args=("shopee",))
    bang_chuan["is_returned"] = bang["returned_qty"] > 0
    bang_chuan["product_name"] = bang["item_name"]
    bang_chuan["variation"] = bang["model_name"]
    bang_chuan["quantity"] = bang["model_quantity_purchased"]
    bang_chuan["returned_quantity"] = bang["returned_qty"]
    bang_chuan["unit_price"] = bang["model_original_price"]
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    bang_chuan["nmv_is_provisional"] = la_tam_tinh
    # Đơn có trong báo cáo affiliate thì True; không có thông tin affiliate thì coi là shop tự bán.
    ma_don_affiliate = {muc["order_sn"] for muc in ket_qua_keo.get("affiliate", [])}
    bang_chuan["is_affiliate"] = bang["order_sn"].isin(ma_don_affiliate)
    bang_chuan["province"] = bang["state"].apply(cleaners.normalize_province, args=(bang_tinh,))
    bang_chuan["province_raw"] = bang["state"]
    bang_chuan["hour_bucket"] = cleaners.tinh_khung_gio(thoi_diem_tao)
    bang_chuan["data_source"] = "api"

    bo_dem = {
        "rows_sku_fallback": int((sku_san_pham.isna() & sku_phan_loai.notna()).sum()),
        "rows_sku_unknown": int((sku_san_pham.isna() & sku_phan_loai.isna()).sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan[COT_CHUAN_SHOPEE], bo_dem
