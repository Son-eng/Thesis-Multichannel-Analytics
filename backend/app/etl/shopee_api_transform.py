"""JSON API Shopee → DataFrame cột chuẩn (SPEC §21.1) — đường nạp CHÍNH.

Đầu vào: kết quả `ShopeeClient.keo_don()` — {"don_hang": [đơn thô], "escrow":
[phần tử escrow thô]}. Đầu ra: đúng COT_CHUAN_SHOPEE mà loader.py kiểm tra, và
dict 5 bộ đếm chất lượng (§3.3), giống hệt khuôn của đường file.

Dùng CHUNG cleaners.py, status_mapper.py (bảng tra API §6.4) và các mapping
JSON với đường file — không gọi lại parser CSV. Nhờ vậy test khứ hồi (§21.5)
so được hai đường mà không tự so với chính mình.

Luồng:
    trải phẳng: 1 dòng = 1 phần tử item_list của 1 đơn (§21.1)
    → ghép seller_discount từ escrow theo (order_sn, item_id, model_id)
    → tính từng cột chuẩn → đếm 5 bộ đếm
"""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_SHOPEE
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_api


def trai_phang_don(cac_don):
    """Đơn thô → DataFrame, mỗi dòng là một phần tử item_list kèm các trường mức đơn.

    Nhận: list đơn khuôn get_order_detail (có item_list, recipient_address).
    Trả: DataFrame cột: order_sn, order_status, create_time, state, và các
    trường của item (item_id, model_id, item_sku, model_sku, item_name,
    model_name, model_quantity_purchased, model_original_price,
    model_discounted_price, returned_qty).
    """
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
    """{(order_sn, item_id, model_id): seller_discount} từ các phần tử CÓ escrow_detail.

    Phần tử không có escrow_detail (fail_error, §16 mục 6) bị bỏ qua: các dòng
    của đơn đó sẽ không tra được → NMV tạm tính (§7.5).
    """
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
    """NMV mức dòng và cờ tạm tính (§7.5, §21.1).

    Nhận: bảng đã trải phẳng; Series seller_discount (NaN = đơn chưa có escrow).
    Trả: (Series nmv, Series nmv_is_provisional).
    Có escrow: model_original_price × SL − seller_discount (cùng công thức
    đường file). Chưa có escrow: model_discounted_price × SL — số người mua
    trả cho dòng đó, đánh dấu tạm tính; lượt đồng bộ sau có escrow thì upsert
    ghi đè bằng số chính xác.
    """
    so_luong = bang["model_quantity_purchased"]
    nmv_chinh_xac = bang["model_original_price"] * so_luong - seller_discount
    nmv_tam_tinh = bang["model_discounted_price"] * so_luong
    la_tam_tinh = seller_discount.isna()
    return nmv_chinh_xac.where(~la_tam_tinh, nmv_tam_tinh), la_tam_tinh


def chuan_hoa_api_shopee(ket_qua_keo, ten_shop):
    """Chuẩn hóa kết quả một lượt kéo API Shopee thành dữ liệu sẵn sàng nạp CSDL.

    Nhận: ket_qua_keo — dict từ ShopeeClient.keo_don(); ten_shop — tên gian
    hàng gắn với token (dòng platform_tokens, §21.1).
    Trả: tuple (DataFrame COT_CHUAN_SHOPEE, dict 5 bộ đếm §3.3) — cùng khuôn
    với shopee_parser.chuan_hoa_file_shopee.
    """
    bang = trai_phang_don(ket_qua_keo["don_hang"])
    if bang.empty:
        return pd.DataFrame(columns=COT_CHUAN_SHOPEE), dict.fromkeys(
            ["rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
             "rows_province_unmapped", "rows_product_unmapped"], 0)
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["shopee"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    # sku: item_sku → dự phòng model_sku → "UNKNOWN". Pipeline cũ dùng
    # model_sku trước — cố ý đảo để giữ đúng quy tắc §5.1 đã kiểm chứng (§21.1).
    # Dùng CHUNG hàm với đường file (cleaners, chỉ dẫn 013).
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
    # §21.4: đơn CÓ trong báo cáo affiliate (get_conversion_report) → True. Cờ
    # theo ĐƠN (mọi dòng của đơn cùng giá trị — đã kiểm trên dữ liệu mẫu).
    # Không có phần "affiliate" trong kết quả kéo (hoặc rỗng) = không có thông
    # tin = shop tự bán → False (cùng quy tắc "ô rỗng → False").
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
