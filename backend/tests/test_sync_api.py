import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.database import lay_phien_db
from app.main import tao_ung_dung
from app.services import token_store
from app.sync import sync_job

pytestmark = pytest.mark.db

MAU_GIO_VN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$")
KHOA_SYNC_RUN = {"id", "platform", "shop_name", "source", "trigger_type", "triggered_by", "file_name", "window_from",
                 "window_to", "started_at", "finished_at", "status", "error_message", "api_calls", "orders_fetched",
                 "rows_total", "rows_inserted", "rows_updated", "quality"}
KHOA_CHAT_LUONG = {"rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown", "rows_province_unmapped",
                   "rows_product_unmapped"}


def tat_ca_token():
    return [settings.SHOPEE_ACCESS_TOKEN, settings.SHOPEE_REFRESH_TOKEN,
            settings.TIKTOK_SHOP_A_ACCESS_TOKEN, settings.TIKTOK_SHOP_A_REFRESH_TOKEN,
            settings.TIKTOK_SHOP_B_ACCESS_TOKEN, settings.TIKTOK_SHOP_B_REFRESH_TOKEN]


def khong_lo_token(phan_hoi):
    noi_dung = phan_hoi.text
    for token in tat_ca_token():
        assert token not in noi_dung
    assert "access_token" not in noi_dung.replace("access_expires_at", "") and "refresh_token" not in noi_dung.replace("refresh_expires_at", "")


@pytest.fixture
def api(phien_test, ket_noi_test, tao_phien_test, monkeypatch, tieu_de_admin):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    cac_lan_chay = []

    def chay_nen_gia(cac_shop, cac_khoa, cac_run_id):
        cac_lan_chay.append({"shops": list(cac_shop), "khoa": list(cac_khoa), "run_ids": list(cac_run_id)})

    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, ham_chay_nen=chay_nen_gia)
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung, headers=tieu_de_admin) as client:
        yield client, cac_lan_chay
    for lan in cac_lan_chay:
        for khoa in lan["khoa"]:
            khoa.nha()


def them_luot(ket_noi, san, shop, source="api", status="success", **cot):
    cot_ghi = {"platform": san, "shop_name": shop, "source": source, "status": status, **cot}
    ket_noi.execute(text(f"INSERT INTO sync_runs ({', '.join(cot_ghi)}) VALUES ({', '.join(':' + k for k in cot_ghi)})"), cot_ghi)


def test_status_dung_khuon_va_khong_co_token(api, ket_noi_test):
    client, _ = api
    them_luot(ket_noi_test, "shopee", "Shop C", finished_at=datetime(2026, 8, 23, 9, 40, 7))
    them_luot(ket_noi_test, "tiktok", "Shop A", status="running", started_at=datetime(2026, 8, 23, 9, 50, 2))
    phan_hoi = client.get("/api/sync/status")
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()

    assert set(du_lieu) == {"interval_minutes", "platforms", "shops"}
    assert du_lieu["interval_minutes"] == settings.SYNC_INTERVAL_MINUTES
    assert du_lieu["platforms"]["shopee"] == {"running": False, "running_since": None}
    assert du_lieu["platforms"]["tiktok"] == {"running": True, "running_since": "2026-08-23T16:50:02+07:00"}
    assert [(s["platform"], s["shop_name"]) for s in du_lieu["shops"]] == [
        ("shopee", "Shop C"), ("tiktok", "Shop A"), ("tiktok", "Shop B")]
    shopee = du_lieu["shops"][0]
    assert set(shopee) == {"platform", "shop_name", "last_success_at", "access_expires_at", "refresh_expires_at", "token_status"}
    assert shopee["last_success_at"] == "2026-08-23T16:40:07+07:00"
    assert du_lieu["shops"][1]["last_success_at"] is None
    for muc in (shopee["access_expires_at"], shopee["refresh_expires_at"]):
        assert MAU_GIO_VN.match(muc)
    khong_lo_token(phan_hoi)


def test_token_status_ok_expiring_expired_va_tiktok_null_la_ok(api, ket_noi_test):
    client, _ = api
    ket_noi_test.execute(text("UPDATE platform_tokens SET refresh_expires_at = now() + interval '30 days' WHERE platform = 'shopee'"))
    ket_noi_test.execute(text("UPDATE platform_tokens SET refresh_expires_at = now() + interval '3 days' WHERE shop_name = 'Shop A'"))
    ket_noi_test.execute(text("UPDATE platform_tokens SET refresh_expires_at = now() - interval '1 minute' WHERE shop_name = 'Shop B'"))
    trang_thai = {s["shop_name"]: s["token_status"] for s in client.get("/api/sync/status").json()["shops"]}
    assert trang_thai == {"Shop C": "ok", "Shop A": "expiring", "Shop B": "expired"}

    ket_noi_test.execute(text("UPDATE platform_tokens SET refresh_expires_at = NULL WHERE platform = 'tiktok'"))
    cac_shop = client.get("/api/sync/status").json()["shops"]
    assert [s["token_status"] for s in cac_shop if s["platform"] == "tiktok"] == ["ok", "ok"]
    assert all(s["refresh_expires_at"] is None for s in cac_shop if s["platform"] == "tiktok")


def test_status_voi_csdl_trong_van_dung_khuon(api, ket_noi_test):
    client, _ = api
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    du_lieu = client.get("/api/sync/status").json()
    assert du_lieu["shops"] == [] and set(du_lieu["platforms"]) == {"shopee", "tiktok"}


def test_runs_dung_khuon_sap_moi_nhat_truoc_va_phan_trang(api, ket_noi_test):
    client, _ = api
    for gio in range(5):
        them_luot(ket_noi_test, "shopee", "Shop C", started_at=datetime(2026, 8, 23, 1 + gio, 0, 0),
                  rows_inserted=gio, api_calls=3, orders_fetched=8, rows_total=8, rows_updated=3, rows_sku_fallback=6,
                  window_from=datetime(2026, 8, 23, gio, 30), window_to=datetime(2026, 8, 23, gio, 40))
    them_luot(ket_noi_test, "shopee", "Shop C", source="file_manual", file_name="a.csv", trigger_type="manual",
              started_at=datetime(2026, 8, 23, 0, 0, 0))

    toan_bo = client.get("/api/sync/runs").json()
    assert set(toan_bo) == {"total", "page", "page_size", "items"}
    assert (toan_bo["total"], toan_bo["page"], toan_bo["page_size"]) == (6, 1, 20)
    muc = toan_bo["items"][0]
    assert set(muc) == KHOA_SYNC_RUN and set(muc["quality"]) == KHOA_CHAT_LUONG
    assert muc["triggered_by"] is None and muc["source"] == "api" and muc["trigger_type"] == "schedule"
    assert MAU_GIO_VN.match(muc["started_at"]) and MAU_GIO_VN.match(muc["window_from"]) and muc["finished_at"] is None
    assert muc["started_at"] == "2026-08-23T12:00:00+07:00"
    assert muc["quality"]["rows_sku_fallback"] == 6 and (muc["api_calls"], muc["orders_fetched"]) == (3, 8)
    gio_bat_dau = [m["started_at"] for m in toan_bo["items"]]
    assert gio_bat_dau == sorted(gio_bat_dau, reverse=True)

    trang_2 = client.get("/api/sync/runs", params={"page": 2, "page_size": 4}).json()
    assert (trang_2["total"], trang_2["page"], trang_2["page_size"], len(trang_2["items"])) == (6, 2, 4, 2)
    assert [m["id"] for m in trang_2["items"]] == [m["id"] for m in toan_bo["items"][4:]]


def test_runs_loc_theo_platform_source_status(api, ket_noi_test):
    client, _ = api
    them_luot(ket_noi_test, "shopee", "Shop C")
    them_luot(ket_noi_test, "tiktok", "Shop A", status="failed", error_message="loi")
    them_luot(ket_noi_test, "tiktok", None, source="file_auto")
    dem = lambda **tham_so: client.get("/api/sync/runs", params=tham_so).json()["total"]
    assert (dem(), dem(platform="tiktok"), dem(source="file_auto"), dem(status="failed")) == (3, 2, 1, 1)
    assert dem(platform="tiktok", source="api", status="failed") == 1
    assert client.get("/api/sync/runs", params={"platform": "tiktok", "status": "failed"}).json()["items"][0]["error_message"] == "loi"


@pytest.mark.parametrize("tham_so", [{"platform": "lazada"}, {"source": "mang"}, {"status": "xong"},
                                      {"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_runs_tham_so_sai_tra_422(api, tham_so):
    assert api[0].get("/api/sync/runs", params=tham_so).status_code == 422


def test_runs_triggered_by_la_object_khi_co_nguoi_chay(api, ket_noi_test):
    client, _ = api
    ket_noi_test.execute(text("INSERT INTO users (id, username, password_hash, role) VALUES (9001, 'admin.vh', 'x', 'admin')"))
    them_luot(ket_noi_test, "shopee", "Shop C", trigger_type="manual", triggered_by=9001)
    assert client.get("/api/sync/runs").json()["items"][0]["triggered_by"] == {"id": 9001, "username": "admin.vh"}


def test_post_202_tao_dong_running_cho_moi_shop_va_goi_chay_nen(api, ket_noi_test):
    client, cac_lan_chay = api
    phan_hoi = client.post("/api/sync/tiktok")
    assert phan_hoi.status_code == 202
    run_ids = phan_hoi.json()["run_ids"]
    assert set(phan_hoi.json()) == {"run_ids"} and len(run_ids) == 2
    cac_dong = ket_noi_test.execute(text("SELECT platform, shop_name, source, trigger_type, status, triggered_by "
                                         "FROM sync_runs ORDER BY id")).all()
    ma_admin = ket_noi_test.execute(text("SELECT id FROM users WHERE username = 'admin_thu'")).scalar_one()
    assert cac_dong == [("tiktok", "Shop A", "api", "manual", "running", ma_admin),
                        ("tiktok", "Shop B", "api", "manual", "running", ma_admin)]
    assert [lan["run_ids"] for lan in cac_lan_chay] == [run_ids]
    assert cac_lan_chay[0]["shops"] == [("tiktok", "Shop A"), ("tiktok", "Shop B")]
    khong_lo_token(phan_hoi)


def test_post_409_khi_dang_chay_dung_khuon_va_khong_tao_dong_moi(api, ket_noi_test):
    client, cac_lan_chay = api
    assert client.post("/api/sync/tiktok").status_code == 202
    so_dong_truoc = ket_noi_test.execute(text("SELECT count(*) FROM sync_runs")).scalar_one()

    phan_hoi = client.post("/api/sync/tiktok")
    assert phan_hoi.status_code == 409
    assert phan_hoi.json() == {"detail": {"code": "sync_running", "message": "TikTok Shop đang có lượt đồng bộ chạy"}}
    assert ket_noi_test.execute(text("SELECT count(*) FROM sync_runs")).scalar_one() == so_dong_truoc
    assert len(cac_lan_chay) == 1

    assert client.post("/api/sync/shopee").status_code == 202
    for khoa in cac_lan_chay[0]["khoa"]:
        khoa.nha()
    assert client.post("/api/sync/tiktok").status_code == 202


def test_post_409_ca_khi_chi_mot_trong_hai_shop_dang_chay_va_nha_khoa_da_gianh(api, ket_noi_test):
    client, cac_lan_chay = api
    khoa_shop_b = sync_job.thu_giu_khoa("tiktok", "Shop B")
    try:
        assert client.post("/api/sync/tiktok").status_code == 409
        khoa_shop_a = sync_job.thu_giu_khoa("tiktok", "Shop A")
        assert khoa_shop_a is not None
        khoa_shop_a.nha()
    finally:
        khoa_shop_b.nha()
    assert ket_noi_test.execute(text("SELECT count(*) FROM sync_runs")).scalar_one() == 0
    assert cac_lan_chay == []


def test_post_nen_status_thay_running(api):
    client, _ = api
    client.post("/api/sync/shopee")
    trang_thai = client.get("/api/sync/status").json()["platforms"]
    assert trang_thai["shopee"]["running"] is True and MAU_GIO_VN.match(trang_thai["shopee"]["running_since"])
    assert trang_thai["tiktok"]["running"] is False


def test_post_san_la_tra_422_va_chua_co_shop_tra_404(api, ket_noi_test):
    client, _ = api
    assert client.post("/api/sync/lazada").status_code == 422
    ket_noi_test.execute(text("DELETE FROM platform_tokens WHERE platform = 'shopee'"))
    phan_hoi = client.post("/api/sync/shopee")
    assert phan_hoi.status_code == 404 and phan_hoi.json()["detail"]["code"] == "no_shop"


def test_cac_phan_hoi_khong_bao_gio_co_token(api, ket_noi_test):
    client, _ = api
    them_luot(ket_noi_test, "shopee", "Shop C", status="failed", error_message="Lỗi đã được làm sạch")
    for phan_hoi in (client.get("/api/sync/status"), client.get("/api/sync/runs"), client.post("/api/sync/shopee")):
        khong_lo_token(phan_hoi)
    dong_token = ket_noi_test.execute(text("SELECT access_token, refresh_token FROM platform_tokens")).all()
    noi_dung = client.get("/api/sync/status").text + client.get("/api/sync/runs").text
    for access, refresh in dong_token:
        assert access not in noi_dung and refresh not in noi_dung


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_luot_chay_nen_mac_dinh_chay_tung_shop_va_nha_khoa(monkeypatch):
    from app.api import sync as api_sync
    cac_lan_goi, khoa_cua_shop = [], []
    for ten in ("Shop A", "Shop B"):
        khoa_cua_shop.append(sync_job.thu_giu_khoa("tiktok", ten))

    def dong_bo_gia(san, ten_shop, trigger, nguoi, khoa=None, run_id=None):
        cac_lan_goi.append((san, ten_shop, trigger, nguoi, run_id))
        if ten_shop == "Shop A":
            raise RuntimeError("loi ngoai du kien")
        khoa.nha()
    monkeypatch.setattr(sync_job, "dong_bo_mot_shop", dong_bo_gia)

    api_sync.chay_nen_mac_dinh([("tiktok", "Shop A"), ("tiktok", "Shop B")], khoa_cua_shop, [11, 12])
    han_cho = datetime.now() + timedelta(seconds=10)
    while sync_job.dang_chay("tiktok", "Shop A") or sync_job.dang_chay("tiktok", "Shop B"):
        assert datetime.now() < han_cho, "khóa không được nhả"
    assert cac_lan_goi == [("tiktok", "Shop A", "manual", None, 11)]
