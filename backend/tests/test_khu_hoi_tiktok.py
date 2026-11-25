from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from app.config import settings
from app.connectors.tiktok_client import TikTokClient
from app.etl import loader, tiktok_api_transform, tiktok_parser
from app.etl.loader import COT_CHUAN_TIKTOK
from app.etl.status_mapper import gom_nhom_trang_thai_api

pytestmark = pytest.mark.cham

FILE_TIKTOK = Path(__file__).resolve().parents[2] / "data" / "samples" / "tiktok_orders_anonymized.csv"
GIO_VN = timezone(timedelta(hours=7))
TU_LUC = int(datetime(2026, 1, 1, tzinfo=GIO_VN).timestamp())
DEN_LUC = int(datetime(2026, 10, 1, tzinfo=GIO_VN).timestamp())
KHOA = ["order_id", "sku"]
SHOP = [
    ("Shop A", settings.TIKTOK_SHOP_A_CIPHER, settings.TIKTOK_SHOP_A_ACCESS_TOKEN),
    ("Shop B", settings.TIKTOK_SHOP_B_CIPHER, settings.TIKTOK_SHOP_B_ACCESS_TOKEN),
]

NGOAI_LE = {
    "order_status_raw": "file lưu chữ tiếng Việt, API lưu mã tiếng Anh — kiểm: gom nhóm ra cùng order_status (đã duyệt 04/11)",
    "data_source": "theo định nghĩa: 'file' / 'api' (đã duyệt 04/11)",
    # is_affiliate và variation không còn là ngoại lệ.
    "returned_quantity": "file điền Sku Quantity of return cả cho đơn hủy; API không có nguồn → 0 (§3.2, §21.2)",
}

DOANH_THU_TONG = 7538502584
DOANH_THU_THEO_THANG = {
    "2026-01": 963328583, "2026-02": 1056998596, "2026-03": 1459153482, "2026-04": 1014538449,
    "2026-05": 800122017, "2026-06": 566274001, "2026-07": 814595996, "2026-08": 863491460,
}


def keo_va_chuan_hoa(may_chu):
    cac_bang, tong_bo_dem, so_line_item = [], {}, 0
    for ten_shop, shop_cipher, access_token in SHOP:
        with TikTokClient(may_chu.url, may_chu.url, settings.TIKTOK_APP_KEY, settings.TIKTOK_APP_SECRET,
                          shop_cipher, access_token, ham_ngu=lambda so_giay: None) as client:
            ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
        so_line_item += sum(len(don["line_items"]) for don in ket_qua["don_hang"])
        bang, bo_dem = tiktok_api_transform.chuan_hoa_api_tiktok(ket_qua, ten_shop)
        cac_bang.append(bang)
        for khoa, so in bo_dem.items():
            tong_bo_dem[khoa] = tong_bo_dem.get(khoa, 0) + so
    return pd.concat(cac_bang, ignore_index=True), tong_bo_dem, so_line_item


@pytest.fixture(scope="module")
def dap_an():
    return tiktok_parser.chuan_hoa_file_tiktok(FILE_TIKTOK)


@pytest.fixture(scope="module")
def duong_api(bat_may_chu_gia_lap):
    return keo_va_chuan_hoa(bat_may_chu_gia_lap())


@pytest.fixture(scope="module")
def gop(dap_an, duong_api):
    return dap_an[0].merge(duong_api[0], on=KHOA, how="outer", suffixes=("_file", "_api"), indicator=True)


def bang_nhau(cot_file, cot_api):
    cung_thieu = cot_file.isna() & cot_api.isna()
    la_so = all(pd.api.types.is_numeric_dtype(c) and not pd.api.types.is_bool_dtype(c) for c in (cot_file, cot_api))
    if la_so:
        return cung_thieu | ((cot_file - cot_api).abs() < 1e-9)
    return cung_thieu | (cot_file == cot_api)


def bang_khac_biet(gop, cac_cot):
    cac_phan = []
    for cot in cac_cot:
        lech = ~bang_nhau(gop[f"{cot}_file"], gop[f"{cot}_api"])
        phan = gop.loc[lech, KHOA + [f"{cot}_file", f"{cot}_api"]]
        phan.columns = KHOA + ["file", "api"]
        cac_phan.append(phan.assign(cot=cot))
    return pd.concat(cac_phan, ignore_index=True)[KHOA + ["cot", "file", "api"]]


def doanh_thu(bang):
    return bang[(bang["order_status"] != "cancelled") & ~bang["is_returned"]]["nmv_after_tax"]


def test_cung_tap_khoa_7540_dong(gop):
    assert (gop["_merge"] == "both").all(), gop["_merge"].value_counts().to_dict()
    assert len(gop) == 7540


def test_moi_cot_chuan_bang_nhau_tru_ngoai_le(gop):
    cac_cot = [cot for cot in COT_CHUAN_TIKTOK if cot not in KHOA and cot not in NGOAI_LE]
    khac = bang_khac_biet(gop, cac_cot)
    assert khac.empty, (
        f"{len(khac)} ô khác nhau — theo cột: {khac['cot'].value_counts().to_dict()}\n"
        + khac.head(30).to_string()
    )


def test_is_returned_khop_du_139_khong_phai_ngoai_le(gop):
    assert (gop["is_returned_file"] == gop["is_returned_api"]).all()
    assert gop["is_returned_api"].sum() == 139


def test_dong_tach_theo_so_luong_gop_lai_dung_muc_dong(gop, duong_api):
    for cot in ["quantity", "unit_price", "sku_subtotal_after_discount", "nmv", "nmv_after_tax"]:
        assert bang_nhau(gop[f"{cot}_file"], gop[f"{cot}_api"]).all(), cot
    assert duong_api[0]["quantity"].sum() == duong_api[2] == 7636
    assert (gop["quantity_api"] > 1).sum() == 87


def test_order_amount_muc_don_dung_7_4(gop, duong_api):
    bang = duong_api[0]
    assert (bang.groupby("order_id")["order_amount"].nunique() == 1).all()
    mot_dong_moi_don = gop.drop_duplicates("order_id")
    assert bang_nhau(mot_dong_moi_don["order_amount_file"], mot_dong_moi_don["order_amount_api"]).all()
    assert bang.drop_duplicates("order_id")["order_amount"].sum() == gop.drop_duplicates("order_id")["order_amount_file"].sum()
    assert bang["order_id"].nunique() == 7526


def test_ngoai_le_order_status_raw_gom_nhom_ra_cung_nhom(gop):
    nhom_tu_ma_api = gop["order_status_raw_api"].apply(gom_nhom_trang_thai_api, args=("tiktok",))
    assert (nhom_tu_ma_api == gop["order_status_api"]).all()
    assert (gop["order_status_file"] == gop["order_status_api"]).all()


def test_ngoai_le_data_source(gop):
    assert set(gop["data_source_file"]) == {"file"} and set(gop["data_source_api"]) == {"api"}


def test_is_affiliate_khop_du_4297_dong_khong_phai_ngoai_le(gop):
    assert (gop["is_affiliate_file"] == gop["is_affiliate_api"]).all()
    assert gop["is_affiliate_api"].sum() == 4297
    assert gop.loc[gop["is_affiliate_api"], "order_id"].nunique() == 4294


def test_ngoai_le_returned_quantity(gop):
    assert (gop["returned_quantity_api"] == 0).all()
    assert (gop["returned_quantity_file"] > 0).sum() == 2308
    # 2.308 = 2.177 dòng đơn hủy + 131 dòng hoàn, nên không dùng cột này tính tỷ lệ hoàn; is_returned khớp đủ 139.
    hoan = gop["is_returned_api"]
    assert (gop.loc[hoan, "returned_quantity_file"] > 0).sum() == 131
    assert (gop.loc[~hoan & (gop["returned_quantity_file"] > 0), "order_status_file"] == "cancelled").all()


def test_variation_khop_sau_khi_parser_strip(gop):
    assert (gop["variation_file"] == gop["variation_api"]).all()
    assert not gop["variation_file"].str.endswith(" ").any()


def test_bo_dem_khop(dap_an, duong_api):
    assert duong_api[1] == dap_an[1] == {
        "rows_sku_fallback": 0, "rows_sku_unknown": 0, "rows_status_unknown": 0,
        "rows_province_unmapped": 0, "rows_product_unmapped": 0}


def test_doanh_thu_tong_va_theo_thang(duong_api):
    bang = duong_api[0]
    assert doanh_thu(bang).sum() == DOANH_THU_TONG
    theo_thang = doanh_thu(bang).groupby(bang["order_date"].dt.strftime("%Y-%m")).sum().to_dict()
    assert theo_thang == DOANH_THU_THEO_THANG


@pytest.mark.db
def test_nap_csdl_2_lan_luy_dang(duong_api, phien_test, ket_noi_test):
    bang = duong_api[0]
    sql_doanh_thu = "SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'tiktok' AND order_status <> 'cancelled' AND is_returned = FALSE"

    assert loader.upsert_don_hang(phien_test, "tiktok", bang, None) == (7540, 0)
    phien_test.flush()
    assert ket_noi_test.execute(text(sql_doanh_thu)).scalar_one() == DOANH_THU_TONG

    assert loader.upsert_don_hang(phien_test, "tiktok", bang, None) == (0, 7540)
    phien_test.flush()
    assert ket_noi_test.execute(text("SELECT count(*) FROM orders WHERE platform = 'tiktok'")).scalar_one() == 7540
    assert ket_noi_test.execute(text(sql_doanh_thu)).scalar_one() == DOANH_THU_TONG
    assert ket_noi_test.execute(text(
        "SELECT count(*) FROM orders WHERE platform = 'tiktok' AND data_source = 'api' AND source_file IS NULL")).scalar_one() == 7540
    assert ket_noi_test.execute(text(
        "SELECT count(*) FROM orders WHERE platform = 'tiktok' AND is_returned")).scalar_one() == 139
