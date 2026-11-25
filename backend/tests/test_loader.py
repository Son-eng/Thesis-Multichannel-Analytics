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
    bang_trung = shopee.head(4).copy()
    bang_trung.loc[3, "order_id"] = bang_trung.loc[0, "order_id"]
    bang_trung.loc[3, "sku"] = bang_trung.loc[0, "sku"]
    with pytest.raises(ValueError, match="lặp lại"):
        loader.kiem_cot_va_khoa(bang_trung, loader.COT_CHUAN_SHOPEE)


def test_du_lieu_mau_dung_hop_dong(shopee, tiktok):
    loader.kiem_cot_va_khoa(shopee, loader.COT_CHUAN_SHOPEE)
    loader.kiem_cot_va_khoa(tiktok, loader.COT_CHUAN_TIKTOK)


def test_doi_sang_kieu_python(shopee, tiktok):
    dong_shopee = loader.doi_sang_dong_python(shopee.head(1))[0]
    dong_tiktok = loader.doi_sang_dong_python(tiktok.head(1))[0]

    assert type(dong_shopee["order_date"]) is datetime.date
    assert type(dong_tiktok["order_date"]) is datetime.date
    assert dong_shopee["order_created_at"] is None
    assert type(dong_tiktok["order_created_at"]) is datetime.datetime
    for gia_tri in list(dong_shopee.values()) + list(dong_tiktok.values()):
        assert not isinstance(gia_tri, np.generic)


def test_nan_thanh_none(shopee):
    dong_rong = shopee[shopee["order_status_raw"].isna()].head(1)
    dong = loader.doi_sang_dong_python(dong_rong)[0]
    assert dong["order_status_raw"] is None


def test_bang_rong_dung_cot_khong_ghi_gi_va_khong_loi(shopee, tiktok):
    assert loader.upsert_don_hang(None, "shopee", shopee.iloc[0:0], None) == (0, 0)
    assert loader.upsert_don_hang(None, "tiktok", tiktok.iloc[0:0], None) == (0, 0)


def test_bang_rong_sai_cot_van_bi_chan(shopee):
    with pytest.raises(ValueError, match="không đúng cột chuẩn"):
        loader.upsert_don_hang(None, "shopee", shopee.iloc[0:0].drop(columns=["nmv"]), None)
