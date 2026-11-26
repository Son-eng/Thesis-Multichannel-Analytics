from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from app.config import settings
from app.connectors.shopee_client import ShopeeClient
from app.etl import loader, shopee_api_transform, shopee_parser
from app.etl.loader import COT_CHUAN_SHOPEE
from app.etl.status_mapper import gom_nhom_trang_thai_api

pytestmark = pytest.mark.cham

FILE_SHOPEE = Path(__file__).resolve().parents[2] / "data" / "samples" / "shopee_orders_anonymized.csv"
GIO_VN = timezone(timedelta(hours=7))
TU_LUC = int(datetime(2026, 7, 1, tzinfo=GIO_VN).timestamp())
DEN_LUC = int(datetime(2026, 10, 1, tzinfo=GIO_VN).timestamp())
KHOA = ["order_id", "sku"]

NGOAI_LE = {
    "order_created_at": "đường file Shopee chỉ có ngày → NULL; đường API có giờ",
    "order_status": "19 dòng trạng thái rỗng → file 'unknown', API sinh COMPLETED",
    "order_status_raw": "file lưu chữ tiếng Việt, API lưu mã tiếng Anh — kiểm: gom nhóm ra cùng order_status",
    "data_source": "theo định nghĩa: 'file' / 'api'",
}

DOANH_THU_TONG = Decimal("1908961059")
DOANH_THU_THEO_THANG = {"2026-07": 1068925905, "2026-08": 840035154}


def keo_va_chuan_hoa(may_chu):
    with ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY, settings.SHOPEE_SHOP_ID,
                      settings.SHOPEE_ACCESS_TOKEN, ham_ngu=lambda so_giay: None) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    return shopee_api_transform.chuan_hoa_api_shopee(ket_qua, settings.SHOPEE_SHOP_NAME)


@pytest.fixture(scope="module")
def dap_an():
    return shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, settings.SHOPEE_SHOP_NAME)


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


def test_cung_tap_khoa(gop):
    assert (gop["_merge"] == "both").all(), gop["_merge"].value_counts().to_dict()
    assert len(gop) == 1774


def test_moi_cot_chuan_bang_nhau_tru_ngoai_le(gop):
    cac_cot = [cot for cot in COT_CHUAN_SHOPEE if cot not in KHOA and cot not in NGOAI_LE]
    khac = bang_khac_biet(gop, cac_cot)
    assert khac.empty, (
        f"{len(khac)} ô khác nhau — theo cột: {khac['cot'].value_counts().to_dict()}\n"
        + khac.head(30).to_string()
    )


def test_ngoai_le_order_created_at(gop):
    assert gop["order_created_at_file"].isna().all()
    assert gop["order_created_at_api"].notna().all()
    # Giờ của API khớp khung giờ của file (275/275 dòng ở dữ liệu thật).
    gio_api = gop["order_created_at_api"].dt.hour.astype(str) + "H - " + (gop["order_created_at_api"].dt.hour + 1).astype(str) + "H"
    assert (gio_api == gop["hour_bucket_file"]).all()


def test_ngoai_le_order_status_dung_19_dong_rong(gop):
    khac = gop[gop["order_status_file"] != gop["order_status_api"]]
    assert len(khac) == 19
    assert set(khac["order_status_file"]) == {"unknown"} and set(khac["order_status_api"]) == {"completed"}
    assert khac["order_status_raw_file"].isna().all()


def test_ngoai_le_order_status_raw_gom_nhom_ra_cung_nhom(gop):
    nhom_tu_ma_api = gop["order_status_raw_api"].apply(gom_nhom_trang_thai_api, args=("shopee",))
    assert (nhom_tu_ma_api == gop["order_status_api"]).all()


def test_ngoai_le_data_source(gop):
    assert set(gop["data_source_file"]) == {"file"} and set(gop["data_source_api"]) == {"api"}


def test_is_affiliate_khop_du_771_dong_khong_phai_ngoai_le(gop):
    assert (gop["is_affiliate_file"] == gop["is_affiliate_api"]).all()
    assert gop["is_affiliate_api"].sum() == 771
    assert gop.loc[gop["is_affiliate_api"], "order_id"].nunique() == 764


def test_bo_dem_khop_tru_trang_thai_rong(dap_an, duong_api):
    bo_dem_file, bo_dem_api = dap_an[1], duong_api[1]
    assert (bo_dem_file["rows_status_unknown"], bo_dem_api["rows_status_unknown"]) == (19, 0)
    for khoa in ["rows_sku_fallback", "rows_sku_unknown", "rows_province_unmapped", "rows_product_unmapped"]:
        assert bo_dem_api[khoa] == bo_dem_file[khoa], khoa


def test_doanh_thu_tong_va_theo_thang(duong_api):
    bang = duong_api[0]
    assert doanh_thu(bang).sum() == DOANH_THU_TONG
    theo_thang = doanh_thu(bang).groupby(bang["order_date"].dt.strftime("%Y-%m")).sum().to_dict()
    assert theo_thang == DOANH_THU_THEO_THANG
    assert not bang["nmv_is_provisional"].any()


@pytest.mark.db
def test_nap_csdl_2_lan_luy_dang(duong_api, phien_test, ket_noi_test):
    bang = duong_api[0]
    sql_doanh_thu = "SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'shopee' AND order_status <> 'cancelled' AND is_returned = FALSE"

    assert loader.upsert_don_hang(phien_test, "shopee", bang, None) == (1774, 0)
    phien_test.flush()
    assert ket_noi_test.execute(text(sql_doanh_thu)).scalar_one() == DOANH_THU_TONG

    assert loader.upsert_don_hang(phien_test, "shopee", bang, None) == (0, 1774)
    phien_test.flush()
    assert ket_noi_test.execute(text("SELECT count(*) FROM orders WHERE platform = 'shopee'")).scalar_one() == 1774
    assert ket_noi_test.execute(text(sql_doanh_thu)).scalar_one() == DOANH_THU_TONG
    assert ket_noi_test.execute(text(
        "SELECT count(*) FROM orders WHERE platform = 'shopee' AND data_source = 'api' AND source_file IS NULL")).scalar_one() == 1774


def test_completed_only_nmv_tam_tinh_va_so_lech(bat_may_chu_gia_lap, dap_an):
    """Đơn chưa có escrow là NMV tạm tính: 1.005 dòng, doanh thu thấp hơn số chính xác 143.269.636, toàn bộ ở tháng 8."""
    bang, _ = keo_va_chuan_hoa(bat_may_chu_gia_lap(MOCK_ESCROW_MODE="completed_only"))
    chua_hoan_tat = bang["order_status_raw"] != "COMPLETED"
    assert (bang["nmv_is_provisional"] == chua_hoan_tat).all()
    assert bang["nmv_is_provisional"].sum() == 1005

    gop = dap_an[0].merge(bang, on=KHOA, suffixes=("_file", "_api"))
    chinh_xac = ~gop["nmv_is_provisional_api"]
    assert (gop.loc[chinh_xac, "nmv_file"] == gop.loc[chinh_xac, "nmv_api"]).all()
    assert (gop["nmv_file"] != gop["nmv_api"]).sum() == 100

    assert doanh_thu(bang).sum() == 1765691423
    assert doanh_thu(bang).sum() - int(DOANH_THU_TONG) == -143269636
    theo_thang = doanh_thu(bang).groupby(bang["order_date"].dt.strftime("%Y-%m")).sum().to_dict()
    assert theo_thang == {"2026-07": 1068925905, "2026-08": 696765518}
