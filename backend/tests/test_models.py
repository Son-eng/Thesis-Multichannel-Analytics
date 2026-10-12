"""Test model SQLAlchemy khớp hợp đồng đầu ra của các module chuẩn hóa — KHÔNG cần CSDL.

Bước 7 sẽ ghi thẳng DataFrame của parser vào bảng. Nếu tên cột trong
COT_CHUAN_* (loader.py) lệch tên cột của model — gõ sai một chữ, hoặc sau này
thêm cột ở một bên mà quên bên kia — thì lúc nạp mới lỗi, hoặc tệ hơn là cột
bị bỏ qua im lặng. Test này bắt lệch ngay khi chạy pytest.

Việc schema thật trong PostgreSQL khớp SPEC §3 được kiểm trên CSDL thật ở
bước 6, kết quả ghi trong TRACKLOG.
"""

import pytest

from app.etl.loader import COT_CHUAN_SHOPEE, COT_CHUAN_TIKTOK
from app.models.order_shopee import OrderShopee
from app.models.order_tiktok import OrderTiktok

# Cột có trong bảng nhưng module chuẩn hóa KHÔNG tạo ra (docstring loader.py):
# id / uploaded_at / updated_at do CSDL và upsert tự đặt; source_file do nơi gọi biết.
COT_KHONG_DO_PARSER_TAO = {"id", "uploaded_at", "updated_at", "source_file"}


@pytest.mark.parametrize("model, cot_chuan", [
    (OrderShopee, COT_CHUAN_SHOPEE),
    (OrderTiktok, COT_CHUAN_TIKTOK),
])
def test_cot_chuan_la_tap_con_dung_cua_cot_model(model, cot_chuan):
    cot_model = set(model.__table__.columns.keys())

    # Mọi cột parser trả về đều có trong bảng (không lệch tên)...
    assert set(cot_chuan) - cot_model == set()
    # ...và phần bảng có mà parser không có đúng bằng 4 cột đã biết lý do.
    assert cot_model - set(cot_chuan) == COT_KHONG_DO_PARSER_TAO


@pytest.mark.parametrize("model, cot_chuan", [
    (OrderShopee, COT_CHUAN_SHOPEE),
    (OrderTiktok, COT_CHUAN_TIKTOK),
])
def test_thu_tu_cot_chuan_theo_thu_tu_bang(model, cot_chuan):
    # loader.py hứa "thứ tự theo CREATE TABLE ở §3" — kiểm lời hứa đó.
    cot_model_theo_thu_tu = []
    for ten_cot in model.__table__.columns.keys():
        if ten_cot not in COT_KHONG_DO_PARSER_TAO:
            cot_model_theo_thu_tu.append(ten_cot)
    assert cot_chuan == cot_model_theo_thu_tu


def test_khoa_chong_trung_dung_order_id_sku():
    # Upsert ở bước 7 dựa vào đúng ràng buộc này (SPEC §4).
    for model, ten_rang_buoc in [(OrderShopee, "uq_shopee_order_sku"), (OrderTiktok, "uq_tiktok_order_sku")]:
        rang_buoc_theo_ten = {}
        for mot_rang_buoc in model.__table__.constraints:
            rang_buoc_theo_ten[mot_rang_buoc.name] = mot_rang_buoc
        cot_cua_khoa = [cot.name for cot in rang_buoc_theo_ten[ten_rang_buoc].columns]
        assert cot_cua_khoa == ["order_id", "sku"]
