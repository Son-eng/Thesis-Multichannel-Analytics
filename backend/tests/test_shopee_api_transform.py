"""Test đơn vị `app/etl/shopee_api_transform.py` (SPEC §21.1, §7.5) — JSON dựng tay, không mạng, không CSDL.

So khớp toàn bộ với đường file nằm ở test_khu_hoi_shopee.py (test khứ hồi §21.5).
"""

import pandas as pd

from app.etl import shopee_api_transform
from app.etl.loader import COT_CHUAN_SHOPEE


def mat_hang(item_sku="BU01", model_sku="BU01", item_id=1, model_id=10, gia_goc=1_000_000,
             gia_uu_dai=800_000, so_luong=2, so_hoan=0):
    return {"item_id": item_id, "item_name": "Máy chườm", "item_sku": item_sku, "model_id": model_id,
            "model_name": "", "model_sku": model_sku, "model_quantity_purchased": so_luong,
            "model_original_price": gia_goc, "model_discounted_price": gia_uu_dai, "returned_qty": so_hoan}


def don(order_sn="A1", trang_thai="COMPLETED", cac_mat_hang=None, tinh="Thành phố Hồ Chí Minh",
        create_time=1782838800 + 13 * 3600):
    return {"order_sn": order_sn, "order_status": trang_thai, "create_time": create_time,
            "update_time": create_time, "recipient_address": {"state": tinh},
            "item_list": cac_mat_hang or [mat_hang()]}


def escrow(order_sn="A1", item_id=1, model_id=10, tro_gia=300_000):
    return {"escrow_detail": {"order_sn": order_sn, "order_income": {
        "items": [{"item_id": item_id, "model_id": model_id, "seller_discount": tro_gia}]}}}


def chuan_hoa(cac_don, cac_escrow):
    return shopee_api_transform.chuan_hoa_api_shopee({"don_hang": cac_don, "escrow": cac_escrow}, "Shop C")


def test_dung_va_du_cot_chuan():
    bang, _ = chuan_hoa([don()], [escrow()])
    assert list(bang.columns) == COT_CHUAN_SHOPEE


def test_nmv_co_escrow_la_gia_goc_nhan_sl_tru_tro_gia():
    bang, _ = chuan_hoa([don()], [escrow(tro_gia=300_000)])
    dong = bang.iloc[0]
    assert dong["nmv"] == 1_000_000 * 2 - 300_000
    assert dong["nmv_after_tax"] == round(1_700_000 / 1.08)
    assert not dong["nmv_is_provisional"]


def test_khong_co_escrow_thi_tam_tinh_bang_gia_uu_dai():
    """Phần tử lỗi {order_sn, fail_error} của escrow lô (§16 mục 6) → NMV tạm tính (§7.5)."""
    loi = {"order_sn": "A1", "fail_error": "mock_escrow_not_available", "fail_message": ""}
    bang, _ = chuan_hoa([don()], [loi])
    dong = bang.iloc[0]
    assert dong["nmv"] == 800_000 * 2
    assert dong["nmv_is_provisional"]


def test_escrow_ghep_dung_tung_mat_hang_theo_item_model():
    hai_mat_hang = [mat_hang(item_id=1, model_id=10), mat_hang(item_sku="M15", model_sku="M15", item_id=2, model_id=20)]
    phan_tu = {"escrow_detail": {"order_sn": "A1", "order_income": {"items": [
        {"item_id": 2, "model_id": 20, "seller_discount": 50_000},
        {"item_id": 1, "model_id": 10, "seller_discount": 300_000},
    ]}}}
    bang, _ = chuan_hoa([don(cac_mat_hang=hai_mat_hang)], [phan_tu])
    assert bang.set_index("sku")["nmv"].to_dict() == {"BU01": 1_700_000, "M15": 1_950_000}


def test_sku_du_phong_va_bo_dem():
    cac_mat_hang = [
        mat_hang(item_sku="", model_sku="M21 live", item_id=1),       # dự phòng
        mat_hang(item_sku="  ", model_sku="", item_id=2, model_id=20),  # cả hai rỗng → UNKNOWN
    ]
    bang, bo_dem = chuan_hoa([don(cac_mat_hang=cac_mat_hang, trang_thai="MA_LA")], [])
    assert list(bang["sku"]) == ["M21 live", "UNKNOWN"]
    assert bo_dem["rows_sku_fallback"] == 1 and bo_dem["rows_sku_unknown"] == 1
    assert bo_dem["rows_status_unknown"] == 2                     # mã trạng thái lạ → unknown
    # "M21 live" có trong product_map (SKU điền tay, §5.4); chỉ "UNKNOWN" không tra được.
    assert list(bang["product_code"].isna()) == [False, True]
    assert bo_dem["rows_product_unmapped"] == 1


def test_thoi_gian_trang_thai_tinh_khung_gio():
    bang, _ = chuan_hoa([don(trang_thai="TO_CONFIRM_RECEIVE")], [escrow()])
    dong = bang.iloc[0]
    assert dong["order_created_at"] == pd.Timestamp("2026-07-01 13:00:00")     # giờ VN
    assert dong["order_date"] == pd.Timestamp("2026-07-01")
    assert dong["hour_bucket"] == "13H - 14H"
    assert (dong["order_status_raw"], dong["order_status"]) == ("TO_CONFIRM_RECEIVE", "delivered")
    assert dong["province"] == "Hồ Chí Minh" and dong["province_raw"] == "Thành phố Hồ Chí Minh"
    assert dong["data_source"] == "api"


def test_hoan_hang_theo_returned_qty():
    bang, _ = chuan_hoa([don(cac_mat_hang=[mat_hang(so_hoan=2)])], [escrow()])
    assert bang.iloc[0]["is_returned"] and bang.iloc[0]["returned_quantity"] == 2


def test_chua_co_nguon_affiliate_thi_false():
    """get_conversion_report là bước 16 (tùy chọn) → chưa có thông tin = shop tự bán (§21.4)."""
    bang, _ = chuan_hoa([don()], [escrow()])
    assert not bang["is_affiliate"].any()


def test_luot_keo_rong():
    bang, bo_dem = chuan_hoa([], [])
    assert bang.empty and list(bang.columns) == COT_CHUAN_SHOPEE
    assert set(bo_dem.values()) == {0}
