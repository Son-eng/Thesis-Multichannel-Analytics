import threading
import time

import pytest
from sqlalchemy import text

from app.config import settings
from app.connectors.shopee_client import ShopeeClient
from app.database import SessionLocal, engine
from app.services import token_store

pytestmark = [pytest.mark.db, pytest.mark.cham]

TEN_SHOP_TEST = "ZZ_TEST_FOR_UPDATE"


@pytest.fixture
def shop_test_that(engine_test):
    with SessionLocal() as phien:
        phien.execute(text("DELETE FROM platform_tokens WHERE shop_name = :s"), {"s": TEN_SHOP_TEST})
        phien.execute(text(
            "INSERT INTO platform_tokens (platform, shop_name, shop_ref, access_token, refresh_token, access_expires_at, refresh_expires_at) "
            "VALUES ('shopee', :s, :ref, :acc, :ref_tok, now() + interval '4 hours', now() + interval '30 days')"),
            {"s": TEN_SHOP_TEST, "ref": str(settings.SHOPEE_SHOP_ID), "acc": settings.SHOPEE_ACCESS_TOKEN,
             "ref_tok": settings.SHOPEE_REFRESH_TOKEN})
        phien.commit()
    try:
        yield
    finally:
        with SessionLocal() as phien:
            phien.execute(text("DELETE FROM platform_tokens WHERE shop_name = :s"), {"s": TEN_SHOP_TEST})
            phien.commit()


def doc_token_that():
    with SessionLocal() as phien:
        return phien.execute(text("SELECT access_token, refresh_token FROM platform_tokens WHERE shop_name = :s"),
                             {"s": TEN_SHOP_TEST}).one()


def chay_hai_thread(may_chu, *, thread_1_cho_giay):
    da_vao_giao_dich = threading.Event()
    cac_refresh_da_gui = []
    ket_qua = {}

    def lam_moi(ten, cho):
        client = ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                              settings.SHOPEE_SHOP_ID, settings.SHOPEE_ACCESS_TOKEN)

        def ham_lam_moi(refresh_token, shop_ref):
            cac_refresh_da_gui.append((ten, refresh_token))
            if ten == "t1":
                da_vao_giao_dich.set()
                time.sleep(cho)
            return client.goi_lam_moi_token(refresh_token, shop_ref)
        try:
            with client:
                ket_qua[ten] = token_store.lam_moi_va_ghi("shopee", TEN_SHOP_TEST, ham_lam_moi)
        except Exception as loi:
            ket_qua[ten] = loi

    t1 = threading.Thread(target=lam_moi, args=("t1", thread_1_cho_giay))
    t2 = threading.Thread(target=lam_moi, args=("t2", 0))
    t1.start()
    assert da_vao_giao_dich.wait(timeout=20)
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    return ket_qua["t1"], ket_qua["t2"], cac_refresh_da_gui


def test_hai_thread_cung_lam_moi_mot_shop_refresh_cu_chi_dung_1_lan_va_ca_hai_deu_co_token_hop_le(
        shop_test_that, bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    ket_qua_1, ket_qua_2, refresh_da_gui = chay_hai_thread(may_chu, thread_1_cho_giay=1.5)

    assert isinstance(ket_qua_1, dict), ket_qua_1
    assert isinstance(ket_qua_2, dict), ket_qua_2
    assert ket_qua_1["refresh_token"] != ket_qua_2["refresh_token"]
    # Refresh ban đầu chỉ được gửi cho sàn đúng một lần; thread 2 phải đợi rồi dùng refresh mới.
    refresh_ban_dau = [ten for ten, refresh in refresh_da_gui if refresh == settings.SHOPEE_REFRESH_TOKEN]
    assert refresh_ban_dau == ["t1"]
    assert ("t2", ket_qua_1["refresh_token"]) in refresh_da_gui
    access_cuoi, refresh_cuoi = doc_token_that()
    assert (access_cuoi, refresh_cuoi) == (ket_qua_2["access_token"], ket_qua_2["refresh_token"])
    with ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                      settings.SHOPEE_SHOP_ID, access_cuoi) as client:
        assert client.lay_chi_tiet(["KHONG_CO"]) == []


def test_thread_hai_phai_doi_khoa_cua_thread_mot(shop_test_that, bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    bat_dau = time.monotonic()
    ket_qua_1, ket_qua_2, _ = chay_hai_thread(may_chu, thread_1_cho_giay=1.5)
    assert isinstance(ket_qua_1, dict) and isinstance(ket_qua_2, dict)
    assert time.monotonic() - bat_dau >= 1.5
