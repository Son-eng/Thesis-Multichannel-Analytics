import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.config import settings
from app.connectors import http_retry
from app.connectors.tiktok_client import CUA_SO_GIAY, LoiApiTikTok, TikTokClient, chia_cua_so
from app.services import token_store

GIO_VN = timezone(timedelta(hours=7))
TU_LUC = int(datetime(2026, 1, 1, tzinfo=GIO_VN).timestamp())
DEN_LUC = int(datetime(2026, 10, 1, tzinfo=GIO_VN).timestamp())
MUOI_LAM_NGAY = 15 * 86400

SHOP = {
    "Shop A": (settings.TIKTOK_SHOP_A_CIPHER, settings.TIKTOK_SHOP_A_ACCESS_TOKEN, settings.TIKTOK_SHOP_A_REFRESH_TOKEN),
    "Shop B": (settings.TIKTOK_SHOP_B_CIPHER, settings.TIKTOK_SHOP_B_ACCESS_TOKEN, settings.TIKTOK_SHOP_B_REFRESH_TOKEN),
}
MONG_DOI = {"Shop A": (5364, 5377, 89), "Shop B": (2162, 2163, 50)}   # (đơn, dòng, dòng hoàn)


def khong_ngu(so_giay):
    """(giữ một dòng)"""


def tao_client(may_chu, ten_shop="Shop A", **them):
    shop_cipher, access_token, _ = SHOP[ten_shop]
    return TikTokClient(
        may_chu.url, may_chu.url, settings.TIKTOK_APP_KEY, settings.TIKTOK_APP_SECRET,
        them.pop("shop_cipher", shop_cipher), them.pop("access_token", access_token), ham_ngu=khong_ngu, **them,
    )


def so_dong(cac_don):
    return len({(don["id"], li["sku_id"]) for don in cac_don for li in don["line_items"]})


def so_dong_hoan(finance):
    return sum(
        gd["revenue_breakdown"]["refund_subtotal_before_discount_amount"] != "0"
        for du_lieu in finance.values() for gd in du_lieu["sku_transactions"]
    )


class SoTokenTrongBoNho:
    def __init__(self, client, refresh_token):
        self.client = client
        self.refresh_token = refresh_token
        self.so_lan = 0

    def khi_can_lam_moi(self):
        moi = self.client.goi_lam_moi_token(self.refresh_token, self.client.shop_cipher)
        self.refresh_token = moi["refresh_token"]
        self.so_lan += 1
        return moi["access_token"]


def test_chia_cua_so_ge_lt_noi_dung_tai_lt():
    cac_cua_so = chia_cua_so(0, 40 * 86400)
    assert cac_cua_so == [(0, MUOI_LAM_NGAY), (MUOI_LAM_NGAY, 2 * MUOI_LAM_NGAY), (2 * MUOI_LAM_NGAY, 40 * 86400)]
    for (_, lt_truoc), (ge_sau, _) in zip(cac_cua_so, cac_cua_so[1:]):
        assert ge_sau == lt_truoc
    assert all(lt - ge <= CUA_SO_GIAY for ge, lt in cac_cua_so)


def test_chia_cua_so_bien():
    assert chia_cua_so(5, 6) == [(5, 6)]
    assert chia_cua_so(5, 5) == []


@pytest.mark.cham
@pytest.mark.parametrize("ten_shop", ["Shop A", "Shop B"])
def test_keo_du_don_dong_va_dong_hoan_theo_shop(bat_may_chu_gia_lap, ten_shop):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu, ten_shop) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    so_don, so_dong_mong_doi, so_hoan = MONG_DOI[ten_shop]
    ma_don = [don["id"] for don in ket_qua["don_hang"]]
    assert len(ma_don) == len(set(ma_don)) == so_don
    assert so_dong(ket_qua["don_hang"]) == so_dong_mong_doi
    assert set(ket_qua["finance"]) == {don["id"] for don in ket_qua["don_hang"] if don["status"] == "COMPLETED"}
    assert so_dong_hoan(ket_qua["finance"]) == so_hoan
    assert all("is_returned" not in don for don in ket_qua["don_hang"])


def test_keo_theo_update_time_mac_dinh_cung_du(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(), "Shop B") as client:
        cac_don = client.lay_don(TU_LUC, DEN_LUC)
    assert len({don["id"] for don in cac_don}) == len(cac_don) == 2162


def test_ranh_gioi_cua_so_ge_lt(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    cipher_a = SHOP["Shop A"][0]
    cac_don = may_chu.ung_dung.state.du_lieu_tiktok_theo_cipher[cipher_a]["don_hang"]
    don_x = next(don for don in cac_don.values() if don["create_time"] > TU_LUC + 30 * 86400)
    moc = don_x["create_time"]
    tu_luc, den_luc = moc - MUOI_LAM_NGAY, moc + MUOI_LAM_NGAY
    assert chia_cua_so(tu_luc, den_luc)[0][1] == moc

    with tao_client(may_chu, "Shop A") as client:
        ma_don = [don["id"] for don in client.lay_don(tu_luc, den_luc, truong_thoi_gian="create_time")]
    mong_doi = {ma for ma, don in cac_don.items() if tu_luc <= don["create_time"] < den_luc}
    assert ma_don.count(don_x["id"]) == 1
    assert len(ma_don) == len(set(ma_don))
    assert set(ma_don) == mong_doi


@pytest.mark.cham
def test_token_het_han_tu_lam_moi_roi_tiep_tuc(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_TIKTOK_ACCESS_TTL_SECONDS=2)
    with tao_client(may_chu, "Shop A") as client:
        so = SoTokenTrongBoNho(client, settings.TIKTOK_SHOP_A_REFRESH_TOKEN)
        client.khi_can_lam_moi = so.khi_can_lam_moi
        lan_1 = [don["id"] for don in client.lay_don(TU_LUC, TU_LUC + 86400, "create_time")]
        time.sleep(3)
        lan_2 = [don["id"] for don in client.lay_don(TU_LUC, TU_LUC + 86400, "create_time")]
    assert so.so_lan == 1 and lan_2 == lan_1 and lan_1


def test_token_cua_shop_khac_lam_moi_1_lan_roi_bao_loi(bat_may_chu_gia_lap):
    so_lan = []

    def lam_moi_ra_token_hong():
        so_lan.append(1)
        return "token_van_sai"
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu, "Shop A", access_token=settings.TIKTOK_SHOP_B_ACCESS_TOKEN,
                    khi_can_lam_moi=lam_moi_ra_token_hong) as client:
        with pytest.raises(LoiApiTikTok) as loi:
            client.lay_don(TU_LUC, TU_LUC + 86400)
    assert loi.value.ma_loi == 9990003 and len(so_lan) == 1


def test_khong_co_callback_thi_bao_loi_ngay(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(), access_token="token_bia") as client:
        with pytest.raises(LoiApiTikTok) as loi:
            client.lay_finance("123")
    assert loi.value.ma_loi == 9990003


def test_lam_moi_token_dung_auth_base_url_khong_ky(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap()) as client:
        moi = client.goi_lam_moi_token(settings.TIKTOK_SHOP_A_REFRESH_TOKEN, client.shop_cipher)
        assert set(moi) == {"access_token", "refresh_token"}
        client.access_token = moi["access_token"]
        assert client.lay_finance("123")["sku_transactions"] == []
        with pytest.raises(LoiApiTikTok) as loi:
            client.goi_lam_moi_token("refresh_bia", client.shop_cipher)
    assert loi.value.ma_loi == 9990006


def test_sai_app_secret_bao_sai_chu_ky_khong_lam_moi(bat_may_chu_gia_lap):
    so_lan = []
    may_chu = bat_may_chu_gia_lap()
    client = TikTokClient(may_chu.url, may_chu.url, settings.TIKTOK_APP_KEY, "secret_sai", SHOP["Shop A"][0],
                          settings.TIKTOK_SHOP_A_ACCESS_TOKEN, khi_can_lam_moi=lambda: so_lan.append(1), ham_ngu=khong_ngu)
    with client, pytest.raises(LoiApiTikTok) as loi:
        client.lay_don(TU_LUC, TU_LUC + 86400)
    assert loi.value.ma_loi == 9990001 and so_lan == []


@pytest.mark.cham
def test_qua_tai_30_phan_tram_van_keo_du(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_FAULT_RATE=0.3, MOCK_FAULT_SEED=11)
    with tao_client(may_chu, "Shop B", so_lan_gui_toi_da=10) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    assert len({don["id"] for don in ket_qua["don_hang"]}) == len(ket_qua["don_hang"]) == 2162
    assert so_dong(ket_qua["don_hang"]) == 2163
    assert so_dong_hoan(ket_qua["finance"]) == 50


def test_qua_tai_mai_thi_bao_het_lan_thu(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(MOCK_FAULT_RATE=1)) as client:
        with pytest.raises(http_retry.LoiHetLanThuLai) as loi:
            client.lay_finance("123")
    assert loi.value.lan_cuoi.json()["code"] == 36009002


@pytest.mark.cham
@pytest.mark.db
def test_noi_voi_token_store_ghi_token_moi_vao_csdl(bat_may_chu_gia_lap, ket_noi_test, tao_phien_test, monkeypatch):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    may_chu = bat_may_chu_gia_lap(MOCK_TIKTOK_ACCESS_TTL_SECONDS=2)
    luc_bat_dau = datetime.now().astimezone()

    with tao_client(may_chu, "Shop A") as client:
        client.khi_can_lam_moi = lambda: token_store.lam_moi_va_ghi(
            "tiktok", settings.TIKTOK_SHOP_A_NAME, client.goi_lam_moi_token)["access_token"]
        time.sleep(3)
        assert len(client.lay_don(TU_LUC, TU_LUC + 86400, "create_time")) > 0

    dong = ket_noi_test.execute(text(
        "SELECT access_token, access_expires_at, refresh_expires_at, "
        "       access_expires_at - CAST(:luc AS timestamp) AS con_lai "
        "FROM platform_tokens WHERE platform = 'tiktok' AND shop_name = :s"),
        {"luc": luc_bat_dau, "s": settings.TIKTOK_SHOP_A_NAME}).mappings().one()
    assert dong["access_token"] == client.access_token != settings.TIKTOK_SHOP_A_ACCESS_TOKEN
    assert dong["refresh_expires_at"] is None
    assert timedelta(days=7) <= dong["con_lai"] < timedelta(days=7, minutes=1)


def cap_don_sku_affiliate(cac_don_affiliate):
    return {(don["id"], sku["sku_id"]) for don in cac_don_affiliate for sku in don["skus"]}


@pytest.mark.cham
@pytest.mark.parametrize("ten_shop, so_dong", [("Shop A", 2763), ("Shop B", 1534)])
def test_keo_don_kem_don_affiliate_theo_shop(bat_may_chu_gia_lap, ten_shop, so_dong):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu, ten_shop) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    shop = may_chu.ung_dung.state.du_lieu_tiktok_theo_cipher[SHOP[ten_shop][0]]
    mong_doi = {(ma, sku_id) for ma, muc in shop["affiliate"].items() for sku_id in muc["skus"]}
    assert cap_don_sku_affiliate(ket_qua["affiliate"]) == mong_doi and len(mong_doi) == so_dong
    ma_don = [don["id"] for don in ket_qua["affiliate"]]
    assert len(ma_don) == len(set(ma_don))


def test_lay_don_affiliate_ranh_gioi_cua_so_ge_lt(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    affiliate = may_chu.ung_dung.state.du_lieu_tiktok_theo_cipher[SHOP["Shop A"][0]]["affiliate"]
    ma_x, moc = next((ma, muc["create_time"]) for ma, muc in affiliate.items() if muc["create_time"] > TU_LUC + 30 * 86400)
    tu_luc, den_luc = moc - MUOI_LAM_NGAY, moc + MUOI_LAM_NGAY
    assert chia_cua_so(tu_luc, den_luc)[0][1] == moc
    with tao_client(may_chu, "Shop A") as client:
        ma_don = [don["id"] for don in client.lay_don_affiliate(tu_luc, den_luc)]
    assert ma_don.count(ma_x) == 1 and len(ma_don) == len(set(ma_don))
    assert set(ma_don) == {ma for ma, muc in affiliate.items() if tu_luc <= muc["create_time"] < den_luc}


def test_keo_don_khong_co_don_thi_khong_goi_don_affiliate(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(), "Shop A") as client:
        ket_qua = client.keo_don(TU_LUC - 400 * 86400, TU_LUC - 399 * 86400, truong_thoi_gian="create_time")
    assert ket_qua == {"don_hang": [], "finance": {}, "affiliate": []}


def test_keo_don_don_affiliate_nam_dung_create_time_lon_nhat_van_co_mat(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    affiliate = may_chu.ung_dung.state.du_lieu_tiktok_theo_cipher[SHOP["Shop A"][0]]["affiliate"]
    ma_x, muc = next((ma, muc) for ma, muc in affiliate.items() if muc["create_time"] > TU_LUC + 30 * 86400)
    moc = muc["create_time"]
    with tao_client(may_chu, "Shop A") as client:
        ket_qua = client.keo_don(moc, moc + 1, truong_thoi_gian="create_time")
    assert ma_x in {don["id"] for don in ket_qua["don_hang"]}
    assert ma_x in {don["id"] for don in ket_qua["affiliate"]}
