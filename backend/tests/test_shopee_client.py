import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.config import settings
from app.connectors import http_retry
from app.connectors.shopee_client import CUA_SO_TOI_DA_GIAY, LoiApiShopee, ShopeeClient, chia_cua_so
from app.services import token_store

GIO_VN = timezone(timedelta(hours=7))
TU_LUC = int(datetime(2026, 7, 1, tzinfo=GIO_VN).timestamp())
DEN_LUC = int(datetime(2026, 10, 1, tzinfo=GIO_VN).timestamp())
MUOI_LAM_NGAY = 15 * 86400


def khong_ngu(so_giay):
    """(giữ một dòng)"""


def tao_client(may_chu, **them):
    return ShopeeClient(
        may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY, settings.SHOPEE_SHOP_ID,
        them.pop("access_token", settings.SHOPEE_ACCESS_TOKEN), ham_ngu=khong_ngu, **them,
    )


def don_cua_mock(may_chu):
    return may_chu.ung_dung.state.du_lieu_shopee["don_hang"]


class SoTokenTrongBoNho:
    def __init__(self, client):
        self.client = client
        self.refresh_token = settings.SHOPEE_REFRESH_TOKEN
        self.so_lan = 0

    def khi_can_lam_moi(self):
        moi = self.client.goi_lam_moi_token(self.refresh_token, str(settings.SHOPEE_SHOP_ID))
        self.refresh_token = moi["refresh_token"]
        self.so_lan += 1
        return moi["access_token"]


def test_chia_cua_so_lien_tiep_khong_chong_khong_ho():
    cac_cua_so = chia_cua_so(0, 40 * 86400)
    assert cac_cua_so == [(0, MUOI_LAM_NGAY), (MUOI_LAM_NGAY + 1, 2 * MUOI_LAM_NGAY + 1),
                          (2 * MUOI_LAM_NGAY + 2, 40 * 86400)]
    for (_, cuoi_truoc), (dau_sau, _) in zip(cac_cua_so, cac_cua_so[1:]):
        assert dau_sau == cuoi_truoc + 1
    assert all(cuoi - dau <= CUA_SO_TOI_DA_GIAY for dau, cuoi in cac_cua_so)


def test_chia_cua_so_bien():
    assert chia_cua_so(5, 5) == [(5, 5)]
    assert chia_cua_so(0, MUOI_LAM_NGAY) == [(0, MUOI_LAM_NGAY)]
    assert chia_cua_so(10, 9) == []


def test_keo_du_1761_don_1774_dong(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    ma_don = [don["order_sn"] for don in ket_qua["don_hang"]]
    assert len(ma_don) == len(set(ma_don)) == 1761
    assert sum(len(don["item_list"]) for don in ket_qua["don_hang"]) == 1774
    assert all("recipient_address" in don for don in ket_qua["don_hang"])
    assert len(ket_qua["escrow"]) == 1761 and all("escrow_detail" in phan for phan in ket_qua["escrow"])


def test_keo_theo_update_time_mac_dinh_cung_du(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu) as client:
        ma_don = client.lay_ma_don(TU_LUC, DEN_LUC)
    assert len(ma_don) == len(set(ma_don)) == 1761


def test_ranh_gioi_cua_so_khong_sot_khong_trung(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    cac_don = don_cua_mock(may_chu)
    don_x = next(don for don in cac_don.values() if don["create_time"] > TU_LUC + 20 * 86400)
    moc = don_x["create_time"]
    tu_luc, den_luc = moc - MUOI_LAM_NGAY, moc + MUOI_LAM_NGAY
    assert chia_cua_so(tu_luc, den_luc)[0][1] == moc

    with tao_client(may_chu) as client:
        ma_don = client.lay_ma_don(tu_luc, den_luc, truong_thoi_gian="create_time")
    mong_doi = {ma for ma, don in cac_don.items() if tu_luc <= don["create_time"] <= den_luc}
    so_don_tren_moc = sum(don["create_time"] == moc for don in cac_don.values())
    assert so_don_tren_moc >= 1
    assert ma_don.count(don_x["order_sn"]) == 1
    assert len(ma_don) == len(set(ma_don))
    assert set(ma_don) == mong_doi


def test_escrow_completed_only_tra_ve_don_khong_co_escrow(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_ESCROW_MODE="completed_only")
    with tao_client(may_chu) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    hoan_tat = {don["order_sn"] for don in ket_qua["don_hang"] if don["order_status"] == "COMPLETED"}
    co_escrow = {phan["escrow_detail"]["order_sn"] for phan in ket_qua["escrow"] if "escrow_detail" in phan}
    khong_escrow = {phan["order_sn"] for phan in ket_qua["escrow"] if "escrow_detail" not in phan}
    assert co_escrow == hoan_tat
    assert khong_escrow and co_escrow | khong_escrow == {don["order_sn"] for don in ket_qua["don_hang"]}
    assert all(phan.get("fail_error") for phan in ket_qua["escrow"] if "escrow_detail" not in phan)


@pytest.mark.cham
def test_token_het_han_tu_lam_moi_roi_tiep_tuc(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_SHOPEE_ACCESS_TTL_SECONDS=2)
    with tao_client(may_chu) as client:
        so = SoTokenTrongBoNho(client)
        client.khi_can_lam_moi = so.khi_can_lam_moi
        ma_lan_1 = client.lay_ma_don(TU_LUC, TU_LUC + 86400, "create_time")
        assert so.so_lan == 0
        time.sleep(3)
        ma_lan_2 = client.lay_ma_don(TU_LUC, TU_LUC + 86400, "create_time")
        assert so.so_lan == 1 and ma_lan_2 == ma_lan_1
        time.sleep(3)
        assert client.lay_ma_don(TU_LUC, TU_LUC + 86400, "create_time") == ma_lan_1
        assert so.so_lan == 2


def test_lam_moi_xong_van_error_auth_thi_bao_loi_chi_lam_moi_1_lan(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    so_lan = []

    def lam_moi_ra_token_hong():
        so_lan.append(1)
        return "token_van_sai"
    with tao_client(may_chu, access_token="token_sai", khi_can_lam_moi=lam_moi_ra_token_hong) as client:
        with pytest.raises(LoiApiShopee) as loi:
            client.lay_ma_don(TU_LUC, TU_LUC + 86400)
    assert loi.value.ma_loi == "error_auth" and len(so_lan) == 1


def test_khong_co_callback_thi_error_auth_bao_loi_ngay(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(), access_token="token_sai") as client:
        with pytest.raises(LoiApiShopee, match="error_auth"):
            client.lay_chi_tiet(["X"])


def test_refresh_cu_dung_lan_2_bi_tu_choi(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap()) as client:
        moi = client.goi_lam_moi_token(settings.SHOPEE_REFRESH_TOKEN, str(settings.SHOPEE_SHOP_ID))
        assert moi["expire_in"] == 4 * 3600 and moi["access_token"] and moi["refresh_token"]
        with pytest.raises(LoiApiShopee) as loi:
            client.goi_lam_moi_token(settings.SHOPEE_REFRESH_TOKEN, str(settings.SHOPEE_SHOP_ID))
    assert loi.value.ma_loi == "error_auth"


def test_sai_khoa_bao_error_sign_khong_lam_moi(bat_may_chu_gia_lap):
    so_lan = []
    may_chu = bat_may_chu_gia_lap()
    client = ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, "khoa_sai", settings.SHOPEE_SHOP_ID,
                          settings.SHOPEE_ACCESS_TOKEN, khi_can_lam_moi=lambda: so_lan.append(1), ham_ngu=khong_ngu)
    with client, pytest.raises(LoiApiShopee, match="error_sign"):
        client.lay_chi_tiet(["X"])
    assert so_lan == []


def test_qua_tai_30_phan_tram_van_keo_du(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_FAULT_RATE=0.3, MOCK_FAULT_SEED=9)
    with tao_client(may_chu, so_lan_gui_toi_da=10) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    assert len({don["order_sn"] for don in ket_qua["don_hang"]}) == len(ket_qua["don_hang"]) == 1761
    assert sum(len(don["item_list"]) for don in ket_qua["don_hang"]) == 1774
    assert len(ket_qua["escrow"]) == 1761


def test_qua_tai_mai_thi_bao_het_lan_thu(bat_may_chu_gia_lap):
    with tao_client(bat_may_chu_gia_lap(MOCK_FAULT_RATE=1)) as client:
        with pytest.raises(http_retry.LoiHetLanThuLai):
            client.lay_chi_tiet(["X"])


@pytest.mark.cham
@pytest.mark.db
def test_noi_voi_token_store_ghi_token_moi_vao_csdl(bat_may_chu_gia_lap, ket_noi_test, tao_phien_test, monkeypatch):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    may_chu = bat_may_chu_gia_lap(MOCK_SHOPEE_ACCESS_TTL_SECONDS=2)

    with tao_client(may_chu) as client:
        client.khi_can_lam_moi = lambda: token_store.lam_moi_va_ghi(
            "shopee", settings.SHOPEE_SHOP_NAME, client.goi_lam_moi_token)["access_token"]
        time.sleep(3)
        assert len(client.lay_ma_don(TU_LUC, TU_LUC + 86400, "create_time")) > 0

    dong = ket_noi_test.execute(text(
        "SELECT access_token, refresh_token FROM platform_tokens WHERE platform = 'shopee'")).mappings().one()
    assert dong["access_token"] == client.access_token != settings.SHOPEE_ACCESS_TOKEN
    assert dong["refresh_token"] != settings.SHOPEE_REFRESH_TOKEN


@pytest.mark.cham
def test_keo_don_kem_bao_cao_affiliate_du_764_don(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu) as client:
        ket_qua = client.keo_don(TU_LUC, DEN_LUC, truong_thoi_gian="create_time")
    ma_affiliate = [muc["order_sn"] for muc in ket_qua["affiliate"]]
    assert len(ma_affiliate) == len(set(ma_affiliate)) == 764
    assert set(ma_affiliate) == set(may_chu.ung_dung.state.du_lieu_shopee["affiliate"])
    assert set(ma_affiliate) <= {don["order_sn"] for don in ket_qua["don_hang"]}


def test_lay_don_affiliate_ranh_gioi_cua_so(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    affiliate = may_chu.ung_dung.state.du_lieu_shopee["affiliate"]
    ma_x, moc = next((ma, tg) for ma, tg in sorted(affiliate.items(), key=lambda m: m[1]) if tg > TU_LUC + 20 * 86400)
    tu_luc, den_luc = moc - MUOI_LAM_NGAY, moc + MUOI_LAM_NGAY
    assert chia_cua_so(tu_luc, den_luc)[0][1] == moc
    with tao_client(may_chu) as client:
        cac_ma = [muc["order_sn"] for muc in client.lay_don_affiliate(tu_luc, den_luc)]
    assert cac_ma.count(ma_x) == 1 and len(cac_ma) == len(set(cac_ma))
    assert set(cac_ma) == {ma for ma, tg in affiliate.items() if tu_luc <= tg <= den_luc}


def test_keo_don_khong_co_don_thi_khong_goi_bao_cao_affiliate(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with tao_client(may_chu) as client:
        ket_qua = client.keo_don(TU_LUC - 400 * 86400, TU_LUC - 399 * 86400, truong_thoi_gian="create_time")
    assert ket_qua == {"don_hang": [], "escrow": [], "affiliate": []}
