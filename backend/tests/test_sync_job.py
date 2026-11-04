"""Test `app/sync/sync_job.py` — một lượt đồng bộ API cho một (sàn, shop) (SPEC §18.2, §20).

Mọi test gọi máy chủ giả lập qua SOCKET THẬT (fixture bat_may_chu_gia_lap) và
CSDL PostgreSQL thật, trong giao dịch bị rollback ở cuối (conftest.py): các
module sync_job / token_store được trỏ sang phiên của test nên dữ liệu thật
(1.774 / 7.540 dòng sinh viên đã nạp) không bị đụng.
Khóa advisory đi qua kết nối RIÊNG (không nằm trong giao dịch test) nên vẫn là khóa thật.
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.config import settings
from app.models.sync_run import SyncRun
from app.services import token_store
from app.sync import sync_job

pytestmark = pytest.mark.db

GIO_VN = timezone(timedelta(hours=7))
DOANH_THU_SHOPEE = 1908961059
DOANH_THU_TIKTOK = 7538502584
SQL_DOANH_THU = ("SELECT COALESCE(SUM(nmv_after_tax), 0) FROM {bang} "
                 "WHERE order_status <> 'cancelled' AND is_returned = FALSE")
BAY_GIO = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def khong_ngu(so_giay):
    """Thay time.sleep."""


@pytest.fixture
def sync(tao_phien_test, ket_noi_test, monkeypatch):
    """sync_job + token_store dùng phiên của test; platform_tokens rỗng (xóa trong giao dịch test)."""
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(sync_job, "SessionLocal", tao_phien_test)
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    return sync_job


@pytest.fixture
def tro_ve_mock(monkeypatch):
    """Hàm trỏ BASE_URL của backend sang một máy chủ giả lập."""
    def tro(may_chu):
        for ten in ["SHOPEE_BASE_URL", "TIKTOK_BASE_URL", "TIKTOK_AUTH_BASE_URL"]:
            monkeypatch.setattr(settings, ten, may_chu.url)
    return tro


def doc_luot(ket_noi, run_id):
    return ket_noi.execute(text("SELECT * FROM sync_runs WHERE id = :i"), {"i": run_id}).mappings().one()


def gia_tri(ket_noi, cau_sql, **tham_so):
    return ket_noi.execute(text(cau_sql), tham_so).scalar_one()


# ---------- Khóa chống chạy chồng ----------

def test_khoa_advisory_chi_mot_nguoi_giu_mot_shop():
    khoa_1 = sync_job.thu_giu_khoa("shopee", "Shop C")
    assert khoa_1 is not None
    assert sync_job.thu_giu_khoa("shopee", "Shop C") is None            # cùng (sàn, shop) → từ chối, không đợi
    khoa_khac_shop = sync_job.thu_giu_khoa("shopee", "Shop D")
    khoa_khac_san = sync_job.thu_giu_khoa("tiktok", "Shop C")
    assert khoa_khac_shop is not None and khoa_khac_san is not None     # khác shop / khác sàn không chặn nhau
    khoa_1.nha()
    khoa_1.nha()                                                        # nhả nhiều lần vẫn an toàn
    khoa_lai = sync_job.thu_giu_khoa("shopee", "Shop C")
    assert khoa_lai is not None                                         # nhả rồi thì giành lại được
    for khoa in (khoa_lai, khoa_khac_shop, khoa_khac_san):
        khoa.nha()


def test_dang_chay_tham_do_khoa_roi_nha():
    assert not sync_job.dang_chay("tiktok", "Shop A")
    khoa = sync_job.thu_giu_khoa("tiktok", "Shop A")
    assert sync_job.dang_chay("tiktok", "Shop A")
    khoa.nha()
    assert not sync_job.dang_chay("tiktok", "Shop A")


def test_dang_co_luot_chay_thi_bo_luot_khong_tao_dong_sync_runs(sync, ket_noi_test):
    khoa = sync_job.thu_giu_khoa("shopee", settings.SHOPEE_SHOP_NAME)
    try:
        assert sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME) is None
    finally:
        khoa.nha()
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM sync_runs") == 0


# ---------- Cửa sổ kéo (§20.3) ----------

def them_luot_thanh_cong(ket_noi, san, shop, window_to, source="api", status="success"):
    ket_noi.execute(text(
        "INSERT INTO sync_runs (platform, shop_name, source, status, window_to) VALUES (:p, :s, :src, :st, :w)"),
        {"p": san, "s": shop, "src": source, "st": status, "w": window_to})


def test_cua_so_backfill_khi_chua_co_luot_thanh_cong(sync, phien_test):
    cua_so = sync.tinh_cua_so(phien_test, "shopee", "Shop C", BAY_GIO)
    assert cua_so["loai"] == "backfill" and cua_so["truong"] == "create_time"
    assert cua_so["tu"] == datetime(2026, 1, 1, tzinfo=GIO_VN)           # SYNC_BACKFILL_FROM, 0h giờ VN
    assert cua_so["den"] == BAY_GIO


def test_cua_so_dinh_ky_lui_lookback_ngay_theo_update_time(sync, phien_test, ket_noi_test):
    them_luot_thanh_cong(ket_noi_test, "shopee", "Shop C", BAY_GIO - timedelta(hours=1))
    cua_so = sync.tinh_cua_so(phien_test, "shopee", "Shop C", BAY_GIO)
    assert cua_so["loai"] == "dinh_ky" and cua_so["truong"] == "update_time"
    assert cua_so["tu"] == BAY_GIO - timedelta(days=settings.SYNC_LOOKBACK_DAYS)


def test_cua_so_gian_doan_mo_rong_ve_moc_luot_thanh_cong_cuoi(sync, phien_test, ket_noi_test):
    moc = BAY_GIO - timedelta(days=settings.SYNC_LOOKBACK_DAYS + 7)
    them_luot_thanh_cong(ket_noi_test, "shopee", "Shop C", moc)
    cua_so = sync.tinh_cua_so(phien_test, "shopee", "Shop C", BAY_GIO)
    assert cua_so["loai"] == "gian_doan" and cua_so["tu"] == moc and cua_so["truong"] == "update_time"


def test_cua_so_chi_tinh_luot_thanh_cong_duong_api_cua_dung_shop(sync, phien_test, ket_noi_test):
    gan = BAY_GIO - timedelta(hours=1)
    them_luot_thanh_cong(ket_noi_test, "shopee", "Shop C", gan, status="failed")      # lượt hỏng không tính
    them_luot_thanh_cong(ket_noi_test, "shopee", "Shop C", gan, source="file_manual")  # đường file không tính
    them_luot_thanh_cong(ket_noi_test, "shopee", "Shop khac", gan)                    # shop khác không tính
    them_luot_thanh_cong(ket_noi_test, "tiktok", "Shop C", gan)                       # sàn khác không tính
    assert sync.tinh_cua_so(phien_test, "shopee", "Shop C", BAY_GIO)["loai"] == "backfill"


# ---------- Tiện ích ----------

def test_lam_sach_thong_diep_che_token_trong_url_va_gia_tri_da_biet():
    url = "https://x/api?access_token=ABC123&sign=deadbeef&shop_id=1&partner_key=KHOA"
    sach = sync_job.lam_sach_thong_diep(f"ConnectError: {url}, refresh_token=XYZ va GIA_TRI_RIENG", ["GIA_TRI_RIENG", ""])
    for bi_mat in ["ABC123", "deadbeef", "KHOA", "XYZ", "GIA_TRI_RIENG"]:
        assert bi_mat not in sach
    assert "shop_id=1" in sach                                           # tham số không bí mật giữ nguyên
    assert len(sync_job.lam_sach_thong_diep("x" * 5000)) == sync_job.DO_DAI_TOI_DA_LOI


def test_don_dep_luot_treo(sync, phien_test, ket_noi_test):
    ket_noi_test.execute(text("INSERT INTO sync_runs (platform, shop_name, source, status) VALUES "
                              "('shopee', 'Shop C', 'api', 'running'), ('shopee', 'Shop C', 'file_manual', 'running')"))
    assert sync.don_dep_luot_treo(phien_test) == 1                       # chỉ lượt API; lượt file không bị đụng
    trang_thai = {d["source"]: d["status"] for d in ket_noi_test.execute(text("SELECT source, status FROM sync_runs")).mappings()}
    assert trang_thai == {"api": "failed", "file_manual": "running"}


# ---------- Đồng bộ đầy đủ qua mock socket thật ----------

@pytest.mark.cham
def test_dong_bo_shopee_day_du_doanh_thu_va_so_lieu_luot(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    tro_ve_mock(bat_may_chu_gia_lap())
    run_id = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, ham_ngu=khong_ngu)

    luot = doc_luot(ket_noi_test, run_id)
    assert (luot["status"], luot["source"], luot["trigger_type"], luot["error_message"]) == ("success", "api", "schedule", None)
    assert luot["triggered_by"] is None and luot["finished_at"] is not None
    assert (luot["orders_fetched"], luot["rows_total"], luot["rows_inserted"], luot["rows_updated"]) == (1761, 1774, 1774, 0)
    assert luot["api_calls"] > 20                                         # cửa sổ 15 ngày × nhiều trang + chi tiết + escrow + affiliate
    assert (luot["rows_sku_fallback"], luot["rows_sku_unknown"], luot["rows_status_unknown"],
            luot["rows_province_unmapped"], luot["rows_product_unmapped"]) == (6, 0, 0, 0, 0)   # §3.3: unknown = 0 ở đường API
    assert luot["window_from"] is not None and luot["window_to"] is not None
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_shopee")) == DOANH_THU_SHOPEE
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee WHERE data_source = 'api' AND is_affiliate") == 771


@pytest.mark.cham
def test_dong_bo_tiktok_hai_shop_doanh_thu_hoan_va_affiliate(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    tro_ve_mock(bat_may_chu_gia_lap())
    cac_run = [sync.dong_bo_mot_shop("tiktok", ten, ham_ngu=khong_ngu)
               for ten in (settings.TIKTOK_SHOP_A_NAME, settings.TIKTOK_SHOP_B_NAME)]
    cac_luot = [doc_luot(ket_noi_test, run_id) for run_id in cac_run]
    assert [luot["status"] for luot in cac_luot] == ["success", "success"]
    assert [(l["orders_fetched"], l["rows_inserted"]) for l in cac_luot] == [(5364, 5377), (2162, 2163)]
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_tiktok")) == DOANH_THU_TIKTOK
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_tiktok WHERE is_returned") == 139
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_tiktok WHERE is_affiliate") == 4297


@pytest.mark.cham
def test_luy_dang_dong_bo_2_lan_cung_cua_so(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    """§21.5 mục 5: lần 2 trên cùng cửa sổ → rows_inserted = 0, CSDL không đổi."""
    tro_ve_mock(bat_may_chu_gia_lap())
    cua_so = {"tu": datetime(2026, 7, 1, tzinfo=GIO_VN), "den": datetime(2026, 10, 1, tzinfo=GIO_VN), "truong": "create_time"}
    lan_1 = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, cua_so=cua_so, ham_ngu=khong_ngu)
    anh_chup = ket_noi_test.execute(text("SELECT md5(string_agg(t::text, '|' ORDER BY order_id, sku)) FROM "
                                         "(SELECT order_id, sku, order_status, nmv, nmv_after_tax, is_affiliate, is_returned "
                                         "FROM orders_shopee) t")).scalar_one()
    lan_2 = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, cua_so=cua_so, ham_ngu=khong_ngu)

    luot_1, luot_2 = doc_luot(ket_noi_test, lan_1), doc_luot(ket_noi_test, lan_2)
    assert (luot_1["rows_inserted"], luot_1["rows_updated"]) == (1774, 0)
    assert (luot_2["rows_inserted"], luot_2["rows_updated"]) == (0, 1774)
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee") == 1774
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_shopee")) == DOANH_THU_SHOPEE
    assert ket_noi_test.execute(text("SELECT md5(string_agg(t::text, '|' ORDER BY order_id, sku)) FROM "
                                     "(SELECT order_id, sku, order_status, nmv, nmv_after_tax, is_affiliate, is_returned "
                                     "FROM orders_shopee) t")).scalar_one() == anh_chup


@pytest.mark.cham
def test_lan_dinh_ky_sau_backfill_khong_them_dong_khi_khong_co_don_moi(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    """Backfill rồi chạy định kỳ: dữ liệu mẫu cũ (07–08/2026) nằm ngoài cửa sổ lookback → 0 đơn, CSDL không đổi."""
    tro_ve_mock(bat_may_chu_gia_lap())
    lan_1 = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, ham_ngu=khong_ngu)
    lan_2 = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, ham_ngu=khong_ngu)
    assert doc_luot(ket_noi_test, lan_1)["rows_inserted"] == 1774
    luot_2 = doc_luot(ket_noi_test, lan_2)
    assert (luot_2["status"], luot_2["orders_fetched"], luot_2["rows_total"], luot_2["rows_inserted"]) == ("success", 0, 0, 0)
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee") == 1774


# ---------- Lỗi ----------

def dat_token_hong(ket_noi, san, shop):
    ket_noi.execute(text("UPDATE platform_tokens SET access_token = 'TOKEN_BIA_ACC', refresh_token = 'TOKEN_BIA_REF' "
                         "WHERE platform = :p AND shop_name = :s"), {"p": san, "s": shop})


def test_mot_shop_loi_khong_chan_shop_con_lai(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    tro_ve_mock(bat_may_chu_gia_lap())
    sync.token_store.nap_san_tu_cau_hinh(settings)
    dat_token_hong(ket_noi_test, "tiktok", settings.TIKTOK_SHOP_A_NAME)
    cua_so = {"tu": datetime(2026, 1, 1, tzinfo=GIO_VN), "den": datetime(2026, 1, 8, tzinfo=GIO_VN), "truong": "create_time"}

    run_hong = sync.dong_bo_mot_shop("tiktok", settings.TIKTOK_SHOP_A_NAME, cua_so=cua_so, ham_ngu=khong_ngu)
    run_tot = sync.dong_bo_mot_shop("tiktok", settings.TIKTOK_SHOP_B_NAME, cua_so=cua_so, ham_ngu=khong_ngu)

    hong, tot = doc_luot(ket_noi_test, run_hong), doc_luot(ket_noi_test, run_tot)
    assert hong["status"] == "failed" and hong["finished_at"] is not None
    assert hong["rows_inserted"] == 0 and hong["error_message"]
    assert "TOKEN_BIA" not in hong["error_message"]                      # không lộ token vào nhật ký
    assert tot["status"] == "success" and tot["rows_inserted"] > 0
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_tiktok WHERE shop_name = :s",
                   s=settings.TIKTOK_SHOP_A_NAME) == 0                   # shop hỏng không để lại dòng đơn nào


def test_shop_chua_co_token_thi_failed_khong_nem_loi(sync, ket_noi_test):
    run_id = sync.dong_bo_mot_shop("shopee", "Shop khong ton tai", ham_ngu=khong_ngu)
    luot = doc_luot(ket_noi_test, run_id)
    assert luot["status"] == "failed" and "Shop khong ton tai" in luot["error_message"]
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM platform_tokens WHERE shop_name = 'Shop khong ton tai'") == 0


def test_refresh_token_het_han_thi_bao_uy_quyen_lai_khong_goi_san(sync, ket_noi_test, monkeypatch):
    sync.token_store.nap_san_tu_cau_hinh(settings)
    ket_noi_test.execute(text("UPDATE platform_tokens SET refresh_expires_at = now() - interval '1 day' "
                              "WHERE platform = 'shopee'"))
    goi_tao_client = []
    monkeypatch.setattr(sync_job, "tao_client", lambda *a, **k: goi_tao_client.append(1))
    run_id = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, ham_ngu=khong_ngu)
    luot = doc_luot(ket_noi_test, run_id)
    assert luot["status"] == "failed" and "ủy quyền lại" in luot["error_message"]
    assert goi_tao_client == []                                          # không tạo connector, không gọi sàn vô ích


TOKEN_MOI = {"access_token": "ACC_MOI_BI_MAT", "refresh_token": "REF_MOI_BI_MAT",
             "access_expires_at": BAY_GIO + timedelta(hours=4), "refresh_expires_at": None}


def lam_token_sap_het_han(ket_noi, san):
    """access_token còn 1 phút → lượt đồng bộ phải làm mới TRƯỚC khi kéo (§18.2 bước 3)."""
    ket_noi.execute(text("UPDATE platform_tokens SET access_expires_at = now() + interval '1 minute' WHERE platform = :p"),
                    {"p": san})


def lam_moi_ghi_loi(monkeypatch):
    """Giả lập: sàn đã cấp token mới nhưng commit lỗi (LoiGhiTokenSauLamMoi)."""
    def lam_moi_loi(san, ten_shop, ham_lam_moi, bay_gio=None):
        raise token_store.LoiGhiTokenSauLamMoi(san, ten_shop, dict(TOKEN_MOI))
    monkeypatch.setattr(token_store, "lam_moi_va_ghi", lam_moi_loi)


def test_ghi_loi_token_thi_thu_ghi_lai_trong_phien_moi_roi_di_tiep(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock,
                                                                  monkeypatch):
    tro_ve_mock(bat_may_chu_gia_lap())
    sync.token_store.nap_san_tu_cau_hinh(settings)
    lam_token_sap_het_han(ket_noi_test, "shopee")
    lam_moi_ghi_loi(monkeypatch)
    cac_lan_ghi, cac_lan_ngu = [], []

    def ghi_token_lan_thu_ba_moi_duoc(san, ten_shop, token_moi):
        cac_lan_ghi.append(1)
        if len(cac_lan_ghi) < 3:
            raise RuntimeError("mat ket noi CSDL")
    monkeypatch.setattr(token_store, "ghi_token", ghi_token_lan_thu_ba_moi_duoc)
    # Token mới là token GIẢ nên kéo thật sẽ bị mock từ chối → chỉ kiểm nhánh ghi lại, nên ép cửa sổ rỗng (0 đơn).
    cua_so = {"tu": datetime(2025, 1, 1, tzinfo=GIO_VN), "den": datetime(2025, 1, 2, tzinfo=GIO_VN), "truong": "create_time"}
    monkeypatch.setattr(sync_job.ShopeeClient, "keo_don", lambda self, *a: {"don_hang": [], "escrow": [], "affiliate": []})

    run_id = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, cua_so=cua_so, ham_ngu=cac_lan_ngu.append)
    luot = doc_luot(ket_noi_test, run_id)
    assert luot["status"] == "success", luot["error_message"]
    assert len(cac_lan_ghi) == 3 and len(cac_lan_ngu) == 2                # thử 3 lần, chờ giữa các lần (tăng dần)
    assert cac_lan_ngu[0] < cac_lan_ngu[1]


def test_ghi_loi_token_het_so_lan_thi_failed_can_uy_quyen_lai_va_khong_lo_token(
        sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock, monkeypatch, caplog):
    tro_ve_mock(bat_may_chu_gia_lap())
    sync.token_store.nap_san_tu_cau_hinh(settings)
    lam_token_sap_het_han(ket_noi_test, "shopee")
    lam_moi_ghi_loi(monkeypatch)
    so_lan_ghi = []

    def ghi_token_luon_loi(san, ten_shop, token_moi):
        so_lan_ghi.append(1)
        raise RuntimeError("mat ket noi CSDL")
    monkeypatch.setattr(token_store, "ghi_token", ghi_token_luon_loi)

    with caplog.at_level(logging.DEBUG):
        run_id = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, ham_ngu=khong_ngu)

    luot = doc_luot(ket_noi_test, run_id)
    assert luot["status"] == "failed"
    assert "ủy quyền lại" in luot["error_message"]
    assert len(so_lan_ghi) == sync_job.SO_LAN_GHI_LAI_TOKEN
    # Không bao giờ ghi token ra nhật ký / log.
    for bi_mat in ["ACC_MOI_BI_MAT", "REF_MOI_BI_MAT", settings.SHOPEE_ACCESS_TOKEN, settings.SHOPEE_REFRESH_TOKEN]:
        assert bi_mat not in luot["error_message"]
        assert bi_mat not in caplog.text
    # token_status = "expired" cho shop này (refresh_expires_at đã bị đánh dấu quá khứ).
    han = gia_tri(ket_noi_test, "SELECT refresh_expires_at <= now() FROM platform_tokens WHERE platform = 'shopee'")
    assert han is True


def test_token_sap_het_han_duoc_lam_moi_truoc_khi_keo(sync, ket_noi_test, bat_may_chu_gia_lap, tro_ve_mock):
    tro_ve_mock(bat_may_chu_gia_lap())
    sync.token_store.nap_san_tu_cau_hinh(settings)
    lam_token_sap_het_han(ket_noi_test, "shopee")
    cua_so = {"tu": datetime(2026, 7, 1, tzinfo=GIO_VN), "den": datetime(2026, 7, 3, tzinfo=GIO_VN), "truong": "create_time"}

    run_id = sync.dong_bo_mot_shop("shopee", settings.SHOPEE_SHOP_NAME, cua_so=cua_so, ham_ngu=khong_ngu)
    assert doc_luot(ket_noi_test, run_id)["status"] == "success"
    dong = ket_noi_test.execute(text("SELECT access_token, refresh_token, access_expires_at > now() + interval '1 hour' AS con_han "
                                     "FROM platform_tokens WHERE platform = 'shopee'")).mappings().one()
    assert dong["access_token"] != settings.SHOPEE_ACCESS_TOKEN and dong["refresh_token"] != settings.SHOPEE_REFRESH_TOKEN
    assert dong["con_han"]
