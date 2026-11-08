"""Test model SQLAlchemy `Order` khớp hợp đồng đầu ra của các module chuẩn hóa — KHÔNG cần CSDL.

Loader ghi DataFrame của bộ chuẩn hóa vào bảng chung `orders`. Nếu tên cột trong COT_CHUAN_* / COT_CHUNG (loader.py)
lệch tên cột của model — gõ sai một chữ, hoặc sau này thêm cột ở một bên mà quên bên kia — thì lúc nạp mới lỗi, hoặc
tệ hơn là cột bị bỏ qua im lặng. Test này bắt lệch ngay khi chạy pytest.

Việc schema thật trong PostgreSQL khớp SPEC §3 được kiểm trên CSDL thật (test_nap_file_db.py, test_orders_gop_bang.py).
"""

import pytest

from app.etl.loader import COT_CHUAN_SHOPEE, COT_CHUAN_TIKTOK, COT_CHUNG, COT_KHOA, COT_MAC_DINH
from app.models.order import Order

# Cột có trong bảng nhưng module chuẩn hóa KHÔNG tạo ra: id / uploaded_at / updated_at do CSDL và upsert tự đặt;
# source_file do nơi gọi biết; platform do loader đặt theo sàn của lượt nạp.
COT_KHONG_DO_PARSER_TAO = {"id", "platform", "uploaded_at", "updated_at", "source_file"}

COT_CHI_SHOPEE = {"nmv_is_provisional"}
COT_CHI_TIKTOK = {"sku_subtotal_after_discount", "order_amount"}


def test_cot_chung_la_hop_cua_hai_sang_va_khop_cot_model():
    cot_model = set(Order.__table__.columns.keys())
    assert set(COT_CHUNG) == set(COT_CHUAN_SHOPEE) | set(COT_CHUAN_TIKTOK)
    assert set(COT_CHUNG) - cot_model == set()                       # không cột nào của loader vắng trong bảng
    assert cot_model - set(COT_CHUNG) == COT_KHONG_DO_PARSER_TAO     # phần bảng có thêm đúng 5 cột đã biết lý do


def test_thu_tu_cot_chung_theo_thu_tu_bang():
    cot_model_theo_thu_tu = [c for c in Order.__table__.columns.keys() if c not in COT_KHONG_DO_PARSER_TAO]
    assert COT_CHUNG == cot_model_theo_thu_tu


@pytest.mark.parametrize("cot_chuan, cot_rieng_sang_kia", [
    (COT_CHUAN_SHOPEE, COT_CHI_TIKTOK),
    (COT_CHUAN_TIKTOK, COT_CHI_SHOPEE),
])
def test_cot_chuan_moi_san_la_tap_con_cua_cot_chung_va_thieu_dung_cot_cua_san_kia(cot_chuan, cot_rieng_sang_kia):
    assert set(cot_chuan) <= set(COT_CHUNG)
    assert set(COT_CHUNG) - set(cot_chuan) == cot_rieng_sang_kia


def test_cot_rieng_tung_san_cho_phep_null_tru_cot_co_mac_dinh():
    cot_bang = Order.__table__.columns
    for ten in COT_CHI_TIKTOK:
        assert cot_bang[ten].nullable, ten                           # Shopee không có → NULL
    # nmv_is_provisional: NOT NULL DEFAULT false (TikTok luôn false) — chọn cột chung thay vì nullable.
    assert not cot_bang["nmv_is_provisional"].nullable
    assert COT_MAC_DINH == {"nmv_is_provisional": False}


def test_khoa_chong_trung_gom_ca_san():
    # Upsert dựa vào đúng ràng buộc này (SPEC §4): order_id của hai sàn thuộc hai hệ mã nên khóa có cả platform.
    rang_buoc_theo_ten = {r.name: r for r in Order.__table__.constraints}
    assert [c.name for c in rang_buoc_theo_ten["uq_orders_platform_order_sku"].columns] == ["platform", "order_id", "sku"]
    assert COT_KHOA == ["platform", "order_id", "sku"]


def test_cac_rang_buoc_check_va_chi_muc_dau_bang_platform():
    rang_buoc_theo_ten = {r.name: r for r in Order.__table__.constraints}
    assert "'shopee'" in str(rang_buoc_theo_ten["ck_orders_platform"].sqltext) and "'tiktok'" in str(rang_buoc_theo_ten["ck_orders_platform"].sqltext)
    assert "'api'" in str(rang_buoc_theo_ten["ck_orders_data_source"].sqltext)
    chi_muc = {i.name: [c.name for c in i.columns] for i in Order.__table__.indexes}
    assert chi_muc == {
        "idx_orders_platform_date": ["platform", "order_date"],
        "idx_orders_platform_status": ["platform", "order_status"],
        "idx_orders_platform_shop": ["platform", "shop_name"],
        "idx_orders_platform_sku": ["platform", "sku"],
        "idx_orders_platform_product": ["platform", "product_code"],
    }


def test_platform_not_null():
    assert not Order.__table__.columns["platform"].nullable
