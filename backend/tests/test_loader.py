"""Test phần của loader.py chạy được KHÔNG cần CSDL: kiểm hợp đồng và đổi kiểu dữ liệu.

Phần ghi xuống CSDL thật (upsert, đếm thêm mới / cập nhật) ở test_nap_file_db.py.
"""

import datetime
from pathlib import Path

import numpy as np
import pytest

from app.etl import loader, shopee_parser, tiktok_parser

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"


@pytest.fixture(scope="module")
def shopee():
    return shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, "Shop C")[0]


@pytest.fixture(scope="module")
def tiktok():
    return tiktok_parser.chuan_hoa_file_tiktok(FILE_TIKTOK)[0]


def test_thieu_hoac_thua_cot_bao_loi_ro(shopee):
    bang_sai = shopee.drop(columns=["nmv"]).assign(cot_la=1)
    with pytest.raises(ValueError, match=r"thiếu \['nmv'\], thừa \['cot_la'\]"):
        loader.kiem_cot_va_khoa(bang_sai, loader.COT_CHUAN_SHOPEE)


def test_trung_khoa_trong_cung_du_lieu_bao_loi(shopee):
    # Chép khóa của dòng 0 sang dòng 3. Không dùng pd.concat: nối cột toàn NaT
    # (order_created_at của Shopee) sinh DeprecationWarning của numpy 2.5 bên
    # trong pandas 2.2.3.
    bang_trung = shopee.head(4).copy()
    bang_trung.loc[3, "order_id"] = bang_trung.loc[0, "order_id"]
    bang_trung.loc[3, "sku"] = bang_trung.loc[0, "sku"]
    with pytest.raises(ValueError, match="lặp lại"):
        loader.kiem_cot_va_khoa(bang_trung, loader.COT_CHUAN_SHOPEE)


def test_du_lieu_mau_dung_hop_dong(shopee, tiktok):
    # Không raise = qua kiểm.
    loader.kiem_cot_va_khoa(shopee, loader.COT_CHUAN_SHOPEE)
    loader.kiem_cot_va_khoa(tiktok, loader.COT_CHUAN_TIKTOK)


def test_doi_sang_kieu_python(shopee, tiktok):
    dong_shopee = loader.doi_sang_dong_python(shopee.head(1))[0]
    dong_tiktok = loader.doi_sang_dong_python(tiktok.head(1))[0]

    # order_date là date (không kèm giờ), không phải pandas.Timestamp.
    assert type(dong_shopee["order_date"]) is datetime.date
    assert type(dong_tiktok["order_date"]) is datetime.date
    # NaT của Shopee (file không có giờ tạo đơn) → None, không phải NaT.
    assert dong_shopee["order_created_at"] is None
    assert type(dong_tiktok["order_created_at"]) is datetime.datetime
    # Không còn kiểu numpy nào lọt xuống CSDL.
    for gia_tri in list(dong_shopee.values()) + list(dong_tiktok.values()):
        assert not isinstance(gia_tri, np.generic)


def test_nan_thanh_none(shopee):
    # 19 dòng Shopee có trạng thái gốc rỗng → order_status_raw là NaN.
    dong_rong = shopee[shopee["order_status_raw"].isna()].head(1)
    dong = loader.doi_sang_dong_python(dong_rong)[0]
    assert dong["order_status_raw"] is None
