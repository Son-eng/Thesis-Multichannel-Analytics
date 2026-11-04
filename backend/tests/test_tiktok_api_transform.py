"""Test đơn vị `app/etl/tiktok_api_transform.py` (SPEC §21.2) — JSON dựng tay, không mạng, không CSDL.

So khớp toàn bộ với đường file nằm ở test_khu_hoi_tiktok.py (§21.5).
"""

import pandas as pd

from app.etl import tiktok_api_transform
from app.etl.loader import COT_CHUAN_TIKTOK


def line_item(sku_id="111", seller_sku="BU01'", goc="1000000", giam_nguoi_ban="300000", giam_san="50000", stt=0):
    gia_ban = str(int(goc) - int(giam_nguoi_ban) - int(giam_san))
    return {"id": f"li{sku_id}{stt}", "sku_id": sku_id, "seller_sku": seller_sku, "product_name": "Máy chườm",
            "sku_name": "Màu be", "original_price": goc, "seller_discount": giam_nguoi_ban,
            "platform_discount": giam_san, "sale_price": gia_ban}


def don(ma="O1", trang_thai="COMPLETED", cac_line_item=None, tong_tien="1300000", tinh="Hồ Chí Minh",
        create_time=1767200400 + 9 * 3600):
    return {"id": ma, "status": trang_thai, "create_time": create_time, "update_time": create_time,
            "payment": {"total_amount": tong_tien},
            "recipient_address": {"district_info": [{"address_level": "L0", "address_name": "Việt Nam"},
                                                    {"address_level": "L1", "address_name": tinh}]},
            "line_items": cac_line_item or [line_item()]}


def giao_dich(sku_id="111", khoan_hoan="0"):
    return {"sku_id": sku_id, "revenue_breakdown": {"refund_subtotal_before_discount_amount": khoan_hoan}}


def chuan_hoa(cac_don, finance=None):
    return tiktok_api_transform.chuan_hoa_api_tiktok({"don_hang": cac_don, "finance": finance or {}}, "Shop A")


def test_dung_va_du_cot_chuan():
    bang, _ = chuan_hoa([don()])
    assert list(bang.columns) == COT_CHUAN_TIKTOK


def test_gop_line_item_cung_sku_thanh_mot_dong():
    """3 line item cùng sku_id (đã tách từ 1 dòng SL 3, phần dư dồn line item đầu, §19.4) → 1 dòng SL 3."""
    ba_line_item = [line_item(giam_nguoi_ban="100002", stt=0), line_item(giam_nguoi_ban="100000", stt=1),
                    line_item(giam_nguoi_ban="100000", stt=2)]
    bang, _ = chuan_hoa([don(cac_line_item=ba_line_item)])
    assert len(bang) == 1
    dong = bang.iloc[0]
    assert dong["quantity"] == 3
    assert dong["unit_price"] == 1_000_000
    assert dong["nmv"] == 3 * 1_000_000 - 300_002
    assert dong["sku_subtotal_after_discount"] == 3 * 1_000_000 - 300_002 - 150_000
    assert dong["nmv_after_tax"] == round((3_000_000 - 300_002) / 1.08)


def test_hai_sku_khac_nhau_hai_dong_order_amount_muc_don():
    hai = [line_item(sku_id="111", seller_sku="BU01"), line_item(sku_id="222", seller_sku="M15")]
    bang, _ = chuan_hoa([don(cac_line_item=hai, tong_tien="2600000")])
    assert sorted(bang["sku"]) == ["BU01", "M15"]
    # MỨC ĐƠN (§7.4): cùng giá trị trên mọi dòng của đơn — không chia, không cộng.
    assert list(bang["order_amount"]) == [2_600_000, 2_600_000]


def test_is_returned_tu_finance_khac_0():
    hai = [line_item(sku_id="111", seller_sku="BU01"), line_item(sku_id="222", seller_sku="M15")]
    finance = {"O1": {"sku_transactions": [giao_dich("111", "-1000000"), giao_dich("222", "0")]}}
    bang, _ = chuan_hoa([don(cac_line_item=hai)], finance)
    assert bang.set_index("sku")["is_returned"].to_dict() == {"BU01": True, "M15": False}


def test_is_returned_khong_phu_thuoc_dau_va_cach_viet_so_0():
    finance = {"O1": {"sku_transactions": [giao_dich("111", "1000000")]},
               "O2": {"sku_transactions": [giao_dich("111", "0.00")]},
               "O3": {"sku_transactions": [giao_dich("111", "-0")]}}
    bang, _ = chuan_hoa([don("O1"), don("O2"), don("O3")], finance)
    assert bang.set_index("order_id")["is_returned"].to_dict() == {"O1": True, "O2": False, "O3": False}


def test_don_khong_co_finance_thi_khong_hoan():
    bang, _ = chuan_hoa([don(trang_thai="CANCELLED")])
    assert not bang.iloc[0]["is_returned"]


def test_sku_lam_sach_tinh_thoi_gian_trang_thai():
    bang, _ = chuan_hoa([don(trang_thai="IN_TRANSIT")])
    dong = bang.iloc[0]
    assert dong["sku"] == "BU01"                                        # bỏ dấu nháy (§5.2)
    assert dong["product_code"] == "BU01"
    assert dong["order_created_at"] == pd.Timestamp("2026-01-01 09:00:00")
    assert dong["order_date"] == pd.Timestamp("2026-01-01")
    assert dong["hour_bucket"] == "9H - 10H"
    assert (dong["order_status_raw"], dong["order_status"]) == ("IN_TRANSIT", "shipping")
    assert (dong["province"], dong["province_raw"]) == ("Hồ Chí Minh", "Hồ Chí Minh")   # cấp L1, không lấy L0
    assert dong["data_source"] == "api"


def test_returned_quantity_va_is_affiliate_chua_co_nguon_api():
    bang, _ = chuan_hoa([don()], {"O1": {"sku_transactions": [giao_dich("111", "-1000000")]}})
    assert bang.iloc[0]["returned_quantity"] == 0       # §21.2 không ánh xạ
    assert not bang.iloc[0]["is_affiliate"]             # lượt 10c


def test_bo_dem():
    bang, bo_dem = chuan_hoa([don(trang_thai="MA_LA", tinh="Tỉnh không có", cac_line_item=[line_item(seller_sku="''")])])
    assert bang.iloc[0]["sku"] == "UNKNOWN"
    assert bo_dem == {"rows_sku_fallback": 0, "rows_sku_unknown": 1, "rows_status_unknown": 1,
                      "rows_province_unmapped": 1, "rows_product_unmapped": 1}


def test_luot_keo_rong():
    bang, bo_dem = chuan_hoa([])
    assert bang.empty and list(bang.columns) == COT_CHUAN_TIKTOK
    assert set(bo_dem.values()) == {0}
