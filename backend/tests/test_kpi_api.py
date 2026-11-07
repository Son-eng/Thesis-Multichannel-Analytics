"""Test endpoint dashboard và đối chiếu (SPEC §7, §8, §9.2–§9.4, §12.1.0–§12.1.2, §17).

Chạy trên dữ liệu mẫu ĐÃ NẠP trong CSDL thật (chỉ đọc, không ghi). Chưa nạp đủ thì test tự skip kèm lý do.
Hai nguồn đáp án:
- số cố định chép nguyên từ SPEC §17 / §9.4 / §12.1;
- đối chiếu ĐỘC LẬP: parser đọc file mẫu (pandas) → tính lại cùng chỉ số → so với kết quả SQL của kpi_service.
"""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.deps import yeu_cau_dang_nhap
from app.database import SessionLocal
from app.etl import shopee_parser, tiktok_parser
from app.main import tao_ung_dung
from app.models.user import User
from app.services import alert_service, kpi_service

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
SO_DONG_MAU = {"orders_shopee": 1774, "orders_tiktok": 7540}

KHOA_CHI_SO_SO = {"value", "previous", "pct_change", "previous_zero"}
KHOA_CHI_SO_TY_LE = {"value", "previous", "change_pp"}
KHOA_METRICS = {"revenue", "order_count", "order_count_all", "quantity_sold", "aov",
                "cancel_rate", "return_rate", "affiliate_share"}
KHOA_KPI = {"platform", "granularity", "period", "status", "current", "previous", "period_complete", "data_max_date",
            "metrics", "previous_full", "alert", "data_quality", "daily"}

DOANH_THU_THANG_TIKTOK = {                                                  # §17.3
    "2026-01": 963328583, "2026-02": 1056998596, "2026-03": 1459153482, "2026-04": 1014538449,
    "2026-05": 800122017, "2026-06": 566274001, "2026-07": 814595996, "2026-08": 863491460}


@pytest.fixture(scope="module")
def du_lieu_mau_da_nap():
    with SessionLocal() as phien:
        for bang, so_dong in SO_DONG_MAU.items():
            if phien.execute(text(f"SELECT count(*) FROM {bang}")).scalar_one() != so_dong:
                pytest.skip(f"{bang} chưa nạp đủ {so_dong} dòng dữ liệu mẫu (python -m app.etl.nap_file …)")


@pytest.fixture(scope="module")
def client(du_lieu_mau_da_nap):
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    # Người dùng giả (test chỉ-đọc, không ghi CSDL); việc đòi đăng nhập kiểm ở test_auth_api.
    ung_dung.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=-1, username="nguoi_thu", role="user")
    with TestClient(ung_dung) as c:
        yield c


@pytest.fixture(scope="module")
def bang_file():
    """Đáp án độc lập: bảng chuẩn do parser tạo từ file mẫu ẩn danh."""
    shopee, _ = shopee_parser.chuan_hoa_file_shopee(THU_MUC_MAU / "shopee_orders_anonymized.csv", "Shop C")
    tiktok, _ = tiktok_parser.chuan_hoa_file_tiktok(THU_MUC_MAU / "tiktok_orders_anonymized.csv")
    for bang in (shopee, tiktok):
        bang["order_date"] = pd.to_datetime(bang["order_date"])
        bang["hop_le"] = (bang["order_status"] != "cancelled") & (~bang["is_returned"])
    return {"shopee": shopee, "tiktok": tiktok}


def lay(client, duong_dan, **tham_so):
    phan_hoi = client.get(duong_dan, params=tham_so)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()


# ---------------------------------------------------------------- /filters

def test_filters_dung_khuon_va_so_that(client):
    shopee = lay(client, "/api/shopee/filters")
    assert set(shopee) == {"platform", "shops", "product_codes", "data_min_date", "data_max_date"}
    assert shopee["shops"] == ["Shop C"] and len(shopee["product_codes"]) == 10
    assert (shopee["data_min_date"], shopee["data_max_date"]) == ("2026-07-01", "2026-08-16")
    assert shopee["product_codes"] == sorted(shopee["product_codes"])
    tiktok = lay(client, "/api/tiktok/filters")
    assert tiktok["shops"] == ["Shop A", "Shop B"] and len(tiktok["product_codes"]) == 13
    assert (tiktok["data_min_date"], tiktok["data_max_date"]) == ("2026-01-01", "2026-08-23")


# ---------------------------------------------------------------- /kpi — số §17.2, §9.4

@pytest.mark.parametrize("san, doanh_thu, don_hop_le, tong_don, so_luong, aov", [
    ("shopee", 1908961059, 1165, 1761, 1182, 1638593),
    ("tiktok", 7538502584, 5211, 7526, 5292, 1446652),
])
def test_kpi_ca_nam_khop_17_2(client, san, doanh_thu, don_hop_le, tong_don, so_luong, aov):
    du_lieu = lay(client, f"/api/{san}/kpi", granularity="year", period="2026")
    metrics = du_lieu["metrics"]
    assert metrics["revenue"]["value"] == doanh_thu
    assert metrics["order_count"]["value"] == don_hop_le
    assert metrics["order_count_all"]["value"] == tong_don
    assert metrics["quantity_sold"]["value"] == so_luong
    assert metrics["aov"]["value"] == aov


def test_kpi_shopee_2026_08_cat_cung_so_ngay(client):
    du_lieu = lay(client, "/api/shopee/kpi", granularity="month", period="2026-08")
    assert set(du_lieu) == KHOA_KPI and set(du_lieu["metrics"]) == KHOA_METRICS
    assert du_lieu["status"] == "ok" and du_lieu["period_complete"] is False
    assert du_lieu["current"] == {"date_from": "2026-08-01", "date_to": "2026-08-16"}
    assert du_lieu["previous"] == {"period": "2026-07", "date_from": "2026-07-01", "date_to": "2026-07-16"}
    assert du_lieu["data_max_date"] == "2026-08-16"
    assert du_lieu["metrics"]["revenue"] == {"value": 840035154, "previous": 624277755, "pct_change": 34.6,
                                             "previous_zero": False}
    assert du_lieu["previous_full"] == {"period": "2026-07", "revenue": 1068925905, "pct_change_if_used": -21.4}
    assert du_lieu["alert"] == {"triggered": False, "threshold_pct": -30.0}


def test_kpi_tiktok_2026_08(client):
    du_lieu = lay(client, "/api/tiktok/kpi", granularity="month", period="2026-08")
    assert du_lieu["metrics"]["revenue"] == {"value": 863491460, "previous": 579379192, "pct_change": 49.0,
                                             "previous_zero": False}
    assert du_lieu["previous"]["date_to"] == "2026-07-23"
    assert du_lieu["previous_full"] == {"period": "2026-07", "revenue": 814595996, "pct_change_if_used": 6.0}


@pytest.mark.parametrize("ma_ky, doanh_thu", sorted(DOANH_THU_THANG_TIKTOK.items()))
def test_kpi_tiktok_tung_thang_khop_17_3(client, ma_ky, doanh_thu):
    assert lay(client, "/api/tiktok/kpi", granularity="month", period=ma_ky)["metrics"]["revenue"]["value"] == doanh_thu


def test_kpi_shopee_thang_7_la_thang_dau_nen_khong_co_ky_truoc(client):
    du_lieu = lay(client, "/api/shopee/kpi", granularity="month", period="2026-07")
    assert du_lieu["status"] == "insufficient_data" and du_lieu["previous"] is None
    assert du_lieu["metrics"]["revenue"]["value"] == 1068925905 and du_lieu["period_complete"] is True
    assert du_lieu["previous_full"] is None


@pytest.mark.parametrize("san, muc, ma_ky", [("shopee", "quarter", "2026-Q3"), ("shopee", "year", "2026"),
                                             ("tiktok", "year", "2026")])
def test_kpi_insufficient_data_khi_khong_ton_tai_ky_truoc(client, san, muc, ma_ky):
    du_lieu = lay(client, f"/api/{san}/kpi", granularity=muc, period=ma_ky)
    assert du_lieu["status"] == "insufficient_data" and du_lieu["previous"] is None
    assert du_lieu["metrics"]["revenue"]["value"] is not None                    # kỳ này vẫn có số
    for ten in ("revenue", "order_count", "order_count_all", "quantity_sold", "aov"):
        chi_so = du_lieu["metrics"][ten]
        assert (chi_so["previous"], chi_so["pct_change"], chi_so["previous_zero"]) == (None, None, False)
    for ten in ("cancel_rate", "return_rate", "affiliate_share"):
        assert (du_lieu["metrics"][ten]["previous"], du_lieu["metrics"][ten]["change_pp"]) == (None, None)
    assert du_lieu["alert"]["triggered"] is False


def test_kpi_no_data_khong_bao_gio_la_0(client):
    du_lieu = lay(client, "/api/shopee/kpi", granularity="month", period="2026-03")
    assert du_lieu["status"] == "no_data"
    for ten in ("revenue", "order_count", "order_count_all", "quantity_sold", "aov"):
        assert du_lieu["metrics"][ten]["value"] is None and du_lieu["metrics"][ten]["pct_change"] is None
    for ten in ("cancel_rate", "return_rate", "affiliate_share"):
        assert du_lieu["metrics"][ten]["value"] is None
    assert du_lieu["daily"] is None and du_lieu["alert"]["triggered"] is False
    assert du_lieu["data_quality"] == {"rows_status_unknown": None, "revenue_status_unknown": None,
                                       "rows_nmv_provisional": None}


def test_kpi_tieu_chi_chat_luong_du_lieu(client):
    shopee = lay(client, "/api/shopee/kpi", granularity="year", period="2026")["data_quality"]
    assert shopee == {"rows_status_unknown": 19, "revenue_status_unknown": 29814813, "rows_nmv_provisional": 0}
    tiktok = lay(client, "/api/tiktok/kpi", granularity="year", period="2026")["data_quality"]
    assert tiktok == {"rows_status_unknown": 0, "revenue_status_unknown": 0, "rows_nmv_provisional": None}


def test_kpi_muc_ngay_khong_cat_va_khong_co_daily(client):
    du_lieu = lay(client, "/api/shopee/kpi", granularity="day", period="2026-08-16")
    assert du_lieu["period_complete"] is True and du_lieu["daily"] is None
    assert du_lieu["current"] == {"date_from": "2026-08-16", "date_to": "2026-08-16"}
    assert du_lieu["previous"] == {"period": "2026-08-15", "date_from": "2026-08-15", "date_to": "2026-08-15"}
    assert du_lieu["previous_full"] is None


def test_kpi_mac_dinh_la_ky_chua_ngay_du_lieu_moi_nhat(client):
    assert lay(client, "/api/shopee/kpi")["period"] == "2026-08"
    assert lay(client, "/api/tiktok/kpi", granularity="quarter")["period"] == "2026-Q3"
    assert lay(client, "/api/shopee/kpi", granularity="day")["period"] == "2026-08-16"


def test_kpi_daily_dai_dung_so_ngay_va_cong_lai_bang_doanh_thu(client):
    du_lieu = lay(client, "/api/shopee/kpi", granularity="month", period="2026-08")
    daily = du_lieu["daily"]
    assert len(daily) == 16 and [d["day_index"] for d in daily] == list(range(1, 17))
    assert (daily[0]["date"], daily[0]["previous_date"]) == ("2026-08-01", "2026-07-01")
    assert (daily[-1]["date"], daily[-1]["previous_date"]) == ("2026-08-16", "2026-07-16")
    assert sum(d["current"] for d in daily) == du_lieu["metrics"]["revenue"]["value"]
    assert sum(d["previous"] for d in daily) == du_lieu["metrics"]["revenue"]["previous"]
    assert all(isinstance(d["current"], int) for d in daily)                        # ngày không đơn là 0 chứ không null


def test_kpi_tung_chi_so_dung_khuon(client):
    metrics = lay(client, "/api/tiktok/kpi", granularity="month", period="2026-08")["metrics"]
    for ten in ("revenue", "order_count", "order_count_all", "quantity_sold", "aov"):
        assert set(metrics[ten]) == KHOA_CHI_SO_SO
    for ten in ("cancel_rate", "return_rate", "affiliate_share"):
        assert set(metrics[ten]) == KHOA_CHI_SO_TY_LE


def test_kpi_loc_theo_shop_va_ma_san_pham_cong_lai_bang_tong(client):
    tong = lay(client, "/api/tiktok/kpi", granularity="year", period="2026")["metrics"]["revenue"]["value"]
    theo_shop = [lay(client, "/api/tiktok/kpi", granularity="year", period="2026", shop_name=s)["metrics"]["revenue"]["value"]
                 for s in ("Shop A", "Shop B")]
    assert sum(theo_shop) == tong and all(theo_shop)
    cac_ma = lay(client, "/api/tiktok/filters")["product_codes"]
    theo_ma = [lay(client, "/api/tiktok/kpi", granularity="year", period="2026", product_code=m)["metrics"]["revenue"]["value"]
               for m in cac_ma]
    assert sum(theo_ma) == tong                                                      # dữ liệu mẫu không có dòng thiếu mã


# ---------------------------------------------------------------- đối chiếu độc lập với parser (pandas)

@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_doi_chieu_pandas_moi_thang_doanh_thu_don_va_ty_le(client, bang_file, san):
    bang = bang_file[san]
    bang["thang"] = bang["order_date"].dt.strftime("%Y-%m")
    for thang, nhom in bang.groupby("thang"):
        hop_le = nhom[nhom["hop_le"]]
        du_lieu = lay(client, f"/api/{san}/kpi", granularity="month", period=thang)["metrics"]
        assert du_lieu["revenue"]["value"] == int(hop_le["nmv_after_tax"].sum()), thang
        assert du_lieu["order_count"]["value"] == hop_le["order_id"].nunique(), thang
        assert du_lieu["order_count_all"]["value"] == nhom["order_id"].nunique(), thang
        assert du_lieu["quantity_sold"]["value"] == int(hop_le["quantity"].sum()), thang
        huy = nhom[nhom["order_status"] == "cancelled"]["order_id"].nunique()
        hoan = nhom[nhom["is_returned"]]["order_id"].nunique()
        assert du_lieu["cancel_rate"]["value"] == pytest.approx(huy / nhom["order_id"].nunique() * 100, abs=0.051), thang
        assert du_lieu["return_rate"]["value"] == pytest.approx(hoan / nhom["order_id"].nunique() * 100, abs=0.051), thang
        aff = int(hop_le[hop_le["is_affiliate"]]["nmv_after_tax"].sum())
        assert du_lieu["affiliate_share"]["value"] == pytest.approx(aff / hop_le["nmv_after_tax"].sum() * 100, abs=0.051), thang


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_by_affiliate_khop_dong_va_doanh_thu_cua_duong_file(client, bang_file, san):
    bang = bang_file[san]
    hop_le = bang[bang["hop_le"]]
    du_lieu = lay(client, f"/api/{san}/by-affiliate", granularity="year", period="2026")
    assert set(du_lieu) == {"platform", "period", "status", "affiliate", "self_sold"}
    assert set(du_lieu["affiliate"]) == {"revenue", "order_count", "share_pct"}
    for khoa, co in (("affiliate", True), ("self_sold", False)):
        phan = hop_le[hop_le["is_affiliate"] == co]
        assert du_lieu[khoa]["revenue"] == int(phan["nmv_after_tax"].sum())
        assert du_lieu[khoa]["order_count"] == phan["order_id"].nunique()
    assert du_lieu["affiliate"]["revenue"] + du_lieu["self_sold"]["revenue"] == int(hop_le["nmv_after_tax"].sum())
    assert du_lieu["affiliate"]["share_pct"] + du_lieu["self_sold"]["share_pct"] == pytest.approx(100, abs=0.11)
    # Số dòng affiliate của đường file (tất cả trạng thái) khớp CSDL: 771 / 4.297.
    with SessionLocal() as phien:
        so_dong = phien.execute(text(f"SELECT count(*) FROM orders_{san} WHERE is_affiliate")).scalar_one()
    assert so_dong == int(bang["is_affiliate"].sum()) == {"shopee": 771, "tiktok": 4297}[san]


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_by_province_khop_pandas(client, bang_file, san):
    bang = bang_file[san]
    hop_le = bang[bang["hop_le"]]
    du_lieu = lay(client, f"/api/{san}/by-province", granularity="year", period="2026")
    assert set(du_lieu) == {"platform", "period", "status", "province_count", "items"}
    cac_muc = du_lieu["items"]
    assert set(cac_muc[0]) == {"province", "order_count", "revenue", "share_pct", "is_other"}
    theo_tinh = hop_le.groupby("province")["nmv_after_tax"].sum().astype(int).to_dict()
    assert {m["province"]: m["revenue"] for m in cac_muc} == theo_tinh
    assert sum(m["revenue"] for m in cac_muc) == int(hop_le["nmv_after_tax"].sum())
    assert du_lieu["province_count"] == len([t for t in theo_tinh if t != "Khác"])
    doanh_thu = [m["revenue"] for m in cac_muc if not m["is_other"]]
    assert doanh_thu == sorted(doanh_thu, reverse=True)
    if any(m["is_other"] for m in cac_muc):
        assert cac_muc[-1]["is_other"] is True


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
def test_by_hour_du_24_phan_tu_va_khop_pandas(client, bang_file, san):
    bang = bang_file[san]
    hop_le = bang[bang["hop_le"]]
    du_lieu = lay(client, f"/api/{san}/by-hour", granularity="year", period="2026")
    cac_muc = du_lieu["items"]
    assert len(cac_muc) == 24 and [m["hour"] for m in cac_muc] == list(range(24))
    assert set(cac_muc[0]) == {"hour", "label", "order_count", "revenue", "share_pct"}
    theo_gio = hop_le.groupby("hour_bucket")["order_id"].nunique().to_dict()
    for m in cac_muc:
        assert m["order_count"] == theo_gio.get(m["label"], 0), m["label"]
    assert sum(m["order_count"] for m in cac_muc) == hop_le["order_id"].nunique()
    assert sum(m["revenue"] for m in cac_muc) == int(hop_le["nmv_after_tax"].sum())
    assert sum(m["share_pct"] for m in cac_muc) == pytest.approx(100, abs=1.3)        # 24 giá trị làm tròn 1 chữ số


# ---------------------------------------------------------------- /revenue-trend

def test_revenue_trend_tiktok_khop_17_3_va_by_product_cong_dung(client):
    du_lieu = lay(client, "/api/tiktok/revenue-trend", granularity="month")
    assert set(du_lieu) == {"platform", "granularity", "top_product_codes", "items"}
    assert {m["period"]: m["revenue"] for m in du_lieu["items"]} == DOANH_THU_THANG_TIKTOK
    top = du_lieu["top_product_codes"]
    assert len(top) == 4
    for muc in du_lieu["items"]:
        assert set(muc) == {"period", "revenue", "order_count", "period_complete", "by_product"}
        assert [p["product_code"] for p in muc["by_product"]] == top + [None]
        assert sum(p["revenue"] for p in muc["by_product"]) == muc["revenue"]
    assert [m["period_complete"] for m in du_lieu["items"]] == [True] * 7 + [False]


def test_revenue_trend_top_ma_la_4_ma_lon_nhat_toan_khoang(client, bang_file):
    bang = bang_file["tiktok"]
    theo_ma = bang[bang["hop_le"]].groupby("product_code")["nmv_after_tax"].sum().sort_values(ascending=False)
    assert lay(client, "/api/tiktok/revenue-trend", granularity="month")["top_product_codes"] == list(theo_ma.index[:4])


def test_revenue_trend_ky_khong_co_du_lieu_la_null_khong_phai_0(client):
    du_lieu = lay(client, "/api/shopee/revenue-trend", granularity="month", date_from="2026-01-01", date_to="2026-08-16")
    cac_muc = {m["period"]: m for m in du_lieu["items"]}
    assert list(cac_muc) == [f"2026-0{i}" for i in range(1, 9)]
    for ky in ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"):
        assert cac_muc[ky]["revenue"] is None and cac_muc[ky]["order_count"] is None and cac_muc[ky]["by_product"] is None
    assert cac_muc["2026-07"]["revenue"] == 1068925905 and cac_muc["2026-08"]["revenue"] == 840035154
    assert sum(p["revenue"] for p in cac_muc["2026-08"]["by_product"]) == 840035154


def test_revenue_trend_ma_khong_ban_trong_ky_van_co_phan_tu_voi_0(client):
    du_lieu = lay(client, "/api/tiktok/revenue-trend", granularity="month")
    for muc in du_lieu["items"]:
        assert len(muc["by_product"]) == 5 and all(isinstance(p["revenue"], int) for p in muc["by_product"])


def test_revenue_trend_theo_ngay_va_cat_theo_khoang(client):
    du_lieu = lay(client, "/api/shopee/revenue-trend", granularity="day", date_from="2026-08-10", date_to="2026-08-16")
    assert [m["period"] for m in du_lieu["items"]] == [f"2026-08-{d}" for d in range(10, 17)]
    thang = lay(client, "/api/shopee/revenue-trend", granularity="month", date_from="2026-08-10", date_to="2026-08-16")
    assert sum(m["revenue"] for m in du_lieu["items"]) == thang["items"][0]["revenue"]


# ---------------------------------------------------------------- /top-products

def test_top_products_tiktok_2026_07_so_that_muc_10(client):
    du_lieu = lay(client, "/api/tiktok/top-products", period="2026-07", limit=2)
    assert set(du_lieu) == {"platform", "period", "status", "items"} and du_lieu["status"] == "ok"
    assert [(m["product_code"], m["revenue"], m["pct_change"]) for m in du_lieu["items"]] == [
        ("M15", 328663138, 26.8), ("BU01", 252093194, 41.1)]
    assert set(du_lieu["items"][0]) == {"product_code", "revenue", "quantity", "share_pct", "pct_change", "previous_zero"}


def test_top_products_nhom_theo_product_code_va_cong_dung_doanh_thu(client, bang_file):
    for san, so_ma in (("shopee", 10), ("tiktok", 13)):
        du_lieu = lay(client, f"/api/{san}/top-products", granularity="year", period="2026", limit=100)
        assert len(du_lieu["items"]) == so_ma and du_lieu["status"] == "insufficient_data"
        bang = bang_file[san]
        theo_ma = bang[bang["hop_le"]].groupby("product_code")["nmv_after_tax"].sum().astype(int).to_dict()
        assert {m["product_code"]: m["revenue"] for m in du_lieu["items"]} == theo_ma
        assert sum(m["share_pct"] for m in du_lieu["items"]) == pytest.approx(100, abs=0.7)
        assert all(m["pct_change"] is None and m["previous_zero"] is False for m in du_lieu["items"])


def test_top_products_san_pham_khong_ban_o_ky_truoc_la_previous_zero(client):
    du_lieu = lay(client, "/api/shopee/top-products", period="2026-08", limit=100)
    muc = next(m for m in du_lieu["items"] if m["product_code"] == "M9 MAX")
    assert muc["previous_zero"] is True and muc["pct_change"] is None and muc["revenue"] > 0
    assert all(m["previous_zero"] is False for m in du_lieu["items"] if m["product_code"] != "M9 MAX")


def test_top_products_sap_theo_quantity_va_gioi_han_limit(client, bang_file):
    theo_sl = lay(client, "/api/tiktok/top-products", period="2026-07", limit=3, sort_by="quantity")["items"]
    assert len(theo_sl) == 3 and [m["quantity"] for m in theo_sl] == sorted((m["quantity"] for m in theo_sl), reverse=True)
    bang = bang_file["tiktok"]
    thang_3 = bang[bang["hop_le"] & (bang["order_date"].dt.strftime("%Y-%m") == "2026-03")]
    dau = thang_3.groupby("product_code")["nmv_after_tax"].sum().sort_values(ascending=False).index[0]
    assert lay(client, "/api/tiktok/top-products", period="2026-03", limit=100)["items"][0]["product_code"] == dau


def test_top_products_no_data(client):
    du_lieu = lay(client, "/api/shopee/top-products", period="2026-03")
    assert du_lieu["status"] == "no_data" and du_lieu["items"] == []


# ---------------------------------------------------------------- /api/compare/platforms

def test_compare_chi_co_hai_khoa_san_khong_co_total(client):
    du_lieu = lay(client, "/api/compare/platforms", granularity="month", period="2026-08")
    assert set(du_lieu) == {"granularity", "period", "shopee", "tiktok"}
    assert "total" not in du_lieu and "total" not in du_lieu["shopee"]
    khoa_san = {"status", "data_max_date", "period_complete", "current", "previous", "metrics",
                "by_hour", "by_product", "by_province_top"}
    for san in ("shopee", "tiktok"):
        assert set(du_lieu[san]) == khoa_san and set(du_lieu[san]["metrics"]) == KHOA_METRICS
        assert len(du_lieu[san]["by_hour"]) == 24
        assert set(du_lieu[san]["by_hour"][0]) == {"hour", "label", "order_count", "share_pct"}
        assert set(du_lieu[san]["by_product"][0]) == {"product_code", "revenue", "quantity"}
        assert set(du_lieu[san]["by_province_top"][0]) == {"province", "revenue", "share_pct"}
        assert len(du_lieu[san]["by_province_top"]) == 10
        assert all(t["province"] != "Khác" for t in du_lieu[san]["by_province_top"])


def test_compare_moi_san_cat_theo_max_order_date_cua_chinh_no(client):
    du_lieu = lay(client, "/api/compare/platforms", granularity="month", period="2026-08")
    assert du_lieu["shopee"]["data_max_date"] == "2026-08-16" and du_lieu["tiktok"]["data_max_date"] == "2026-08-23"
    assert du_lieu["shopee"]["previous"]["date_to"] == "2026-07-16"
    assert du_lieu["tiktok"]["previous"]["date_to"] == "2026-07-23"
    assert du_lieu["shopee"]["metrics"]["revenue"]["pct_change"] == 34.6
    assert du_lieu["tiktok"]["metrics"]["revenue"]["pct_change"] == 49.0
    assert du_lieu["shopee"]["period_complete"] is False and du_lieu["tiktok"]["period_complete"] is False


def test_compare_thang_3_shopee_no_data_cac_danh_sach_rong(client):
    du_lieu = lay(client, "/api/compare/platforms", granularity="month", period="2026-03")
    shopee = du_lieu["shopee"]
    assert shopee["status"] == "no_data"
    assert shopee["by_hour"] == [] and shopee["by_product"] == [] and shopee["by_province_top"] == []
    assert all(chi_so["value"] is None for chi_so in shopee["metrics"].values())
    assert du_lieu["tiktok"]["status"] == "ok" and du_lieu["tiktok"]["metrics"]["revenue"]["value"] == 1459153482


def test_compare_khong_co_period_dung_ky_moi_nhat_cua_hai_san(client):
    du_lieu = lay(client, "/api/compare/platforms")
    assert du_lieu["period"] == "2026-08" and du_lieu["granularity"] == "month"


def test_compare_by_product_khop_doanh_thu_cua_san(client):
    du_lieu = lay(client, "/api/compare/platforms", granularity="month", period="2026-08")
    for san in ("shopee", "tiktok"):
        assert sum(m["revenue"] for m in du_lieu[san]["by_product"]) == du_lieu[san]["metrics"]["revenue"]["value"]


# ---------------------------------------------------------------- lỗi tham số, CORS, quy tắc §7.4

@pytest.mark.parametrize("duong_dan, tham_so", [
    ("/api/shopee/kpi", {"granularity": "month", "period": "2026-Q3"}),
    ("/api/shopee/kpi", {"granularity": "year", "period": "2026-08"}),
    ("/api/tiktok/kpi", {"granularity": "quarter", "period": "2026-Q5"}),
    ("/api/tiktok/top-products", {"granularity": "day", "period": "2026-13-45"}),
    ("/api/compare/platforms", {"period": "abc"}),
])
def test_ky_sai_dinh_dang_tra_422_invalid_period(client, duong_dan, tham_so):
    phan_hoi = client.get(duong_dan, params=tham_so)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_period"


@pytest.mark.parametrize("duong_dan, tham_so", [
    ("/api/lazada/kpi", {}), ("/api/shopee/kpi", {"granularity": "week"}),
    ("/api/shopee/top-products", {"limit": 0}), ("/api/shopee/top-products", {"sort_by": "ten"}),
])
def test_tham_so_la_tra_422(client, duong_dan, tham_so):
    assert client.get(duong_dan, params=tham_so).status_code == 422


def test_cors_cho_phep_origin_cua_vite_va_chan_origin_la(client):
    cho_phep = client.options("/api/shopee/kpi", headers={"Origin": "http://localhost:5173",
                                                          "Access-Control-Request-Method": "GET"})
    assert cho_phep.headers.get("access-control-allow-origin") == "http://localhost:5173"
    la = client.options("/api/shopee/kpi", headers={"Origin": "http://evil.example",
                                                    "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in la.headers
    assert client.get("/api/shopee/filters", headers={"Origin": "http://localhost:5173"}) \
        .headers["access-control-allow-origin"] == "http://localhost:5173"


def test_khong_sql_nao_cong_thang_cot_muc_don():
    """§7.4: `order_amount` (mức đơn của TikTok) chỉ được xuất hiện ở hằng số khai báo, không ở câu SQL nào."""
    ma_nguon = Path(kpi_service.__file__).read_text(encoding="utf-8")
    assert kpi_service.ORDER_LEVEL_COLUMNS == {"orders_shopee": [], "orders_tiktok": ["order_amount"]}
    assert ma_nguon.count("order_amount") == 1
    assert "SUM(order_amount" not in ma_nguon.replace(" ", "")


def test_moi_sum_trong_sql_chi_tren_cot_muc_dong():
    ma_nguon = Path(kpi_service.__file__).read_text(encoding="utf-8")
    import re
    cot_sum = set(re.findall(r"SUM\((\w+)\)", ma_nguon))
    assert cot_sum <= {"nmv_after_tax", "quantity"}


# ---------------------------------------------------------------- hàm thuần (không cần CSDL)

def test_lam_tron_nua_len_va_thay_doi_phan_tram():
    assert kpi_service.lam_tron_1(0.25) == 0.3 and kpi_service.lam_tron_1(-0.25) == -0.3
    assert kpi_service.thay_doi_phan_tram(1014538449, 1459153482) == -30.5
    assert kpi_service.thay_doi_phan_tram(5, 0) is None and kpi_service.thay_doi_phan_tram(5, None) is None
    assert kpi_service.thay_doi_phan_tram(None, 5) is None


def test_chi_so_so_cac_tinh_huong_12_1_0_2():
    f = kpi_service.chi_so_so
    assert f(120, 100, True) == {"value": 120, "previous": 100, "pct_change": 20.0, "previous_zero": False}
    assert f(120, 0, True) == {"value": 120, "previous": 0, "pct_change": None, "previous_zero": True}
    assert f(120, None, False) == {"value": 120, "previous": None, "pct_change": None, "previous_zero": False}
    assert f(None, 100, True) == {"value": None, "previous": 100, "pct_change": None, "previous_zero": False}
    assert f(5, None, True, truoc_khong_xac_dinh=True) == {"value": 5, "previous": None, "pct_change": None, "previous_zero": True}


def test_chi_so_ty_le_ky_truoc_khong_co_don_thi_null():
    f = kpi_service.chi_so_ty_le
    assert f(30, 100, 20, 100, True) == {"value": 30.0, "previous": 20.0, "change_pp": 10.0}
    assert f(30, 100, 0, 0, True) == {"value": 30.0, "previous": None, "change_pp": None}
    assert f(30, 100, None, None, False) == {"value": 30.0, "previous": None, "change_pp": None}


def test_xac_dinh_ky_cat_cung_so_ngay_cac_muc():
    from datetime import date
    ky = kpi_service.xac_dinh_ky("month", "2026-08", date(2026, 7, 1), date(2026, 8, 16))
    assert (ky["den"], ky["day_du"], ky["truoc"]["den"]) == (date(2026, 8, 16), False, date(2026, 7, 16))
    # Kỳ trước ngắn hơn: 31/03 chưa đủ → tháng 2 chỉ có 28 ngày, phải kẹp ở cuối tháng 2.
    ky = kpi_service.xac_dinh_ky("month", "2026-03", date(2026, 1, 1), date(2026, 3, 30))
    assert ky["truoc"]["den"] == date(2026, 2, 28)
    ky = kpi_service.xac_dinh_ky("quarter", "2026-Q3", date(2026, 1, 1), date(2026, 8, 23))
    assert (ky["truoc"]["ky"], ky["truoc"]["den"], ky["day_du"]) == ("2026-Q2", date(2026, 5, 24), False)   # 01/07→23/08 = 54 ngày; 01/04 + 53 ngày
    ky = kpi_service.xac_dinh_ky("day", "2026-08-16", date(2026, 7, 1), date(2026, 8, 16))
    assert (ky["day_du"], ky["truoc"]["dau"], ky["truoc"]["den"]) == (True, date(2026, 8, 15), date(2026, 8, 15))
    ky = kpi_service.xac_dinh_ky("year", "2026", date(2026, 1, 1), date(2026, 8, 23))
    assert ky["truoc"] is None
    assert kpi_service.xac_dinh_ky("month", None, date(2026, 7, 1), date(2026, 8, 16))["ky"] == "2026-08"


def test_co_canh_bao_dung_nguong_va_khong_bao_gio_voi_none():
    assert alert_service.co_canh_bao(-30.0, 30) is True
    assert alert_service.co_canh_bao(-29.99, 30) is False
    assert alert_service.co_canh_bao(None, 30) is False
