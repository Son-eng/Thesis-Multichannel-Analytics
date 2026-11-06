"""Test cảnh báo biến động: `alert_service` và `GET /api/{platform}/alerts` (SPEC §9, §12.1.1.8, §17.3).

Dữ liệu mẫu đã nạp trong CSDL thật (chỉ đọc). Ngoài số cố định của SPEC còn có đối chiếu độc lập: tính lại
danh sách cảnh báo bằng pandas từ file mẫu cho nhiều tổ hợp (mức × bộ lọc × ngưỡng) rồi so với endpoint.
"""

from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.etl import shopee_parser, tiktok_parser
from app.main import tao_ung_dung
from app.services import alert_service, kpi_service

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
SO_DONG_MAU = {"orders_shopee": 1774, "orders_tiktok": 7540}
KHOA_ALERT = {"platform", "granularity", "threshold_pct", "items"}
KHOA_MUC = {"period", "previous_period", "revenue", "revenue_previous", "pct_change", "previous_zero", "period_complete"}


@pytest.fixture(scope="module")
def du_lieu_mau_da_nap():
    with SessionLocal() as phien:
        for bang, so_dong in SO_DONG_MAU.items():
            if phien.execute(text(f"SELECT count(*) FROM {bang}")).scalar_one() != so_dong:
                pytest.skip(f"{bang} chưa nạp đủ {so_dong} dòng dữ liệu mẫu")


@pytest.fixture(scope="module")
def client(du_lieu_mau_da_nap):
    with TestClient(tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)) as c:
        yield c


@pytest.fixture(scope="module")
def bang_file():
    shopee, _ = shopee_parser.chuan_hoa_file_shopee(THU_MUC_MAU / "shopee_orders_anonymized.csv", "Shop C")
    tiktok, _ = tiktok_parser.chuan_hoa_file_tiktok(THU_MUC_MAU / "tiktok_orders_anonymized.csv")
    for bang in (shopee, tiktok):
        bang["order_date"] = pd.to_datetime(bang["order_date"]).dt.date
        bang["hop_le"] = (bang["order_status"] != "cancelled") & (~bang["is_returned"])
    return {"shopee": shopee, "tiktok": tiktok}


def lay(client, san, **tham_so):
    phan_hoi = client.get(f"/api/{san}/alerts", params=tham_so)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi.json()


# ---------------------------------------------------------------- số cố định §9.1, §17.3

def test_muc_thang_tiktok_dung_1_canh_bao_2026_04(client):
    du_lieu = lay(client, "tiktok", granularity="month")
    assert set(du_lieu) == KHOA_ALERT and du_lieu["threshold_pct"] == -30.0
    assert len(du_lieu["items"]) == 1
    muc = du_lieu["items"][0]
    assert set(muc) == KHOA_MUC
    assert muc == {"period": "2026-04", "previous_period": "2026-03", "revenue": 1014538449,
                   "revenue_previous": 1459153482, "pct_change": -30.5, "previous_zero": False, "period_complete": True}


def test_muc_thang_shopee_khong_co_canh_bao(client):
    du_lieu = lay(client, "shopee", granularity="month")
    assert du_lieu["items"] == [] and du_lieu["platform"] == "shopee" and du_lieu["granularity"] == "month"


def test_thang_5_va_6_tiktok_giam_nhung_duoi_nguong_nen_khong_canh_bao(client):
    cac_ky = [m["period"] for m in lay(client, "tiktok", granularity="month")["items"]]
    assert "2026-05" not in cac_ky and "2026-06" not in cac_ky           # −21,1% và −29,2%
    for ma_ky, pct in (("2026-05", -21.1), ("2026-06", -29.2)):
        du_lieu = client.get("/api/tiktok/kpi", params={"granularity": "month", "period": ma_ky}).json()
        assert du_lieu["metrics"]["revenue"]["pct_change"] == pct and du_lieu["alert"]["triggered"] is False


def test_kpi_alert_dung_voi_thang_4(client):
    du_lieu = client.get("/api/tiktok/kpi", params={"granularity": "month", "period": "2026-04"}).json()
    assert du_lieu["alert"] == {"triggered": True, "threshold_pct": -30.0}
    assert du_lieu["metrics"]["revenue"]["pct_change"] == -30.5


def test_muc_quy_nam_shopee_khong_co_canh_bao_vi_khong_du_ky(client):
    for muc in ("quarter", "year"):
        assert lay(client, "shopee", granularity=muc)["items"] == []
    assert lay(client, "tiktok", granularity="year")["items"] == []


# ---------------------------------------------------------------- ngưỡng lấy từ cấu hình

def test_nguong_20_lam_ca_ba_thang_4_5_6_deu_canh_bao(client, monkeypatch):
    monkeypatch.setattr(settings, "ALERT_DROP_THRESHOLD_PCT", 20.0)
    du_lieu = lay(client, "tiktok", granularity="month")
    assert du_lieu["threshold_pct"] == -20.0
    assert {m["period"]: m["pct_change"] for m in du_lieu["items"]} == {"2026-04": -30.5, "2026-05": -21.1, "2026-06": -29.2}
    ky = client.get("/api/tiktok/kpi", params={"granularity": "month", "period": "2026-05"}).json()
    assert ky["alert"] == {"triggered": True, "threshold_pct": -20.0}


def test_nguong_cao_hon_thi_het_canh_bao(client, monkeypatch):
    monkeypatch.setattr(settings, "ALERT_DROP_THRESHOLD_PCT", 31.0)
    assert lay(client, "tiktok", granularity="month")["items"] == []


# ---------------------------------------------------------------- không bao giờ cảnh báo khi thiếu kỳ trước / kỳ trước = 0

@pytest.mark.parametrize("pct, ket_qua", [(None, False), (0.0, False), (-29.99, False), (-30.0, True), (-80.0, True)])
def test_quy_tac_co_canh_bao(pct, ket_qua):
    assert alert_service.co_canh_bao(pct, 30) is ket_qua


def test_ky_truoc_bang_0_khong_chia_cho_0_khong_canh_bao():
    assert kpi_service.thay_doi_phan_tram_tho(0, 0) is None and kpi_service.thay_doi_phan_tram_tho(100, 0) is None
    assert alert_service.co_canh_bao(kpi_service.thay_doi_phan_tram_tho(0, 0), 30) is False


def test_san_pham_co_ky_truoc_bang_0_khong_xuat_hien_trong_alerts(client):
    """M21 TikTok không bán ở tháng 2 và tháng 4 (previous_zero ở các tháng sau) → không bao giờ có trong items."""
    ky_truoc_bang_0 = client.get("/api/tiktok/top-products", params={"period": "2026-03", "limit": 100}).json()["items"]
    assert any(m["product_code"] == "M21" and m["previous_zero"] for m in ky_truoc_bang_0)
    for ma in ("M21", "M8 AIR", "M9 MAX"):
        for muc in lay(client, "tiktok", granularity="month", product_code=ma)["items"]:
            assert muc["revenue_previous"] > 0 and muc["previous_zero"] is False and muc["pct_change"] <= -30


def test_ky_khong_co_du_lieu_khong_bi_coi_la_giam_100_phan_tram(client):
    """Shopee tháng 1–6 không có dòng nào: không được sinh cảnh báo kiểu −100%."""
    du_lieu = lay(client, "shopee", granularity="month")
    assert du_lieu["items"] == []
    du_lieu = lay(client, "tiktok", granularity="month", shop_name="Shop A", product_code="M21")
    for muc in du_lieu["items"]:
        assert muc["revenue"] > 0


# ---------------------------------------------------------------- đối chiếu độc lập với pandas

def tinh_canh_bao_pandas(bang, muc, nguong, shop=None, ma=None):
    """Tính lại danh sách cảnh báo từ DataFrame của parser, KHÔNG dùng code của kpi_service/alert_service."""
    # Khoảng dữ liệu là của TOÀN sàn (§9.2), không phải của phần đã lọc.
    ngay_min, ngay_max = bang["order_date"].min(), bang["order_date"].max()
    if shop:
        bang = bang[bang["shop_name"] == shop]
    if ma:
        bang = bang[bang["product_code"] == ma]
    hop_le = bang[bang["hop_le"]]
    tien = hop_le.groupby("order_date")["nmv_after_tax"].sum().astype(int).to_dict()
    co_dong = set(bang["order_date"])

    def dau_ky(d):
        if muc == "day":
            return d
        if muc == "month":
            return d.replace(day=1)
        if muc == "quarter":
            return d.replace(month=(d.month - 1) // 3 * 3 + 1, day=1)
        return d.replace(month=1, day=1)

    def them_thang(d, n):
        t = d.year * 12 + d.month - 1 + n
        return d.replace(year=t // 12, month=t % 12 + 1, day=1)

    def cuoi_ky(d):
        buoc = {"month": 1, "quarter": 3, "year": 12}.get(muc)
        return d if muc == "day" else them_thang(d, buoc) - timedelta(days=1)

    ket_qua, d = [], dau_ky(ngay_min)
    while d <= dau_ky(ngay_max):
        cuoi = cuoi_ky(d)
        day_du = muc == "day" or ngay_max >= cuoi
        den = cuoi if day_du else ngay_max
        truoc_dau = d - timedelta(days=1) if muc == "day" else them_thang(d, -{"month": 1, "quarter": 3, "year": 12}[muc])
        if truoc_dau >= ngay_min:
            truoc_den = min(cuoi_ky(truoc_dau), truoc_dau + (den - d)) if not day_du else cuoi_ky(truoc_dau)
            n = (den - d).days + 1
            cac_ngay = [d + timedelta(days=i) for i in range(n)]
            nay = sum(tien.get(x, 0) for x in cac_ngay)
            truoc = sum(tien.get(truoc_dau + timedelta(days=i), 0) for i in range((truoc_den - truoc_dau).days + 1))
            if any(x in co_dong for x in cac_ngay) and truoc > 0 and (nay - truoc) * 100 / truoc <= -nguong:
                ket_qua.append((d, nay, truoc))
        d = d + timedelta(days=1) if muc == "day" else them_thang(d, {"month": 1, "quarter": 3, "year": 12}[muc])
    return ket_qua


@pytest.mark.parametrize("san", ["shopee", "tiktok"])
@pytest.mark.parametrize("muc", ["day", "month", "quarter", "year"])
@pytest.mark.parametrize("nguong", [20.0, 30.0, 45.0])
def test_doi_chieu_pandas_cac_muc_va_nguong(client, bang_file, monkeypatch, san, muc, nguong):
    monkeypatch.setattr(settings, "ALERT_DROP_THRESHOLD_PCT", nguong)
    bang = bang_file[san]
    mong_doi = tinh_canh_bao_pandas(bang, muc, nguong)
    thuc_te = lay(client, san, granularity=muc)["items"]
    assert [(m["revenue"], m["revenue_previous"]) for m in thuc_te] == [(n, t) for _, n, t in mong_doi]
    assert len(thuc_te) == len(mong_doi)


@pytest.mark.parametrize("bo_loc", [{"shop_name": "Shop A"}, {"shop_name": "Shop B"}, {"product_code": "M15"},
                                    {"product_code": "M21"}, {"shop_name": "Shop A", "product_code": "BU01"}])
def test_doi_chieu_pandas_voi_bo_loc_tiktok(client, bang_file, monkeypatch, bo_loc):
    monkeypatch.setattr(settings, "ALERT_DROP_THRESHOLD_PCT", 30.0)
    bang = bang_file["tiktok"]
    for muc in ("month", "quarter"):
        mong_doi = tinh_canh_bao_pandas(bang, muc, 30.0, bo_loc.get("shop_name"), bo_loc.get("product_code"))
        thuc_te = lay(client, "tiktok", granularity=muc, **bo_loc)["items"]
        assert [(m["revenue"], m["revenue_previous"]) for m in thuc_te] == [(n, t) for _, n, t in mong_doi], (muc, bo_loc)


def test_tham_so_sai_tra_422(client):
    assert client.get("/api/lazada/alerts").status_code == 422
    assert client.get("/api/shopee/alerts", params={"granularity": "week"}).status_code == 422
