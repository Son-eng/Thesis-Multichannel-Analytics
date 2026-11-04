"""Test khóa dòng `SELECT … FOR UPDATE` của `token_store.lam_moi_va_ghi` bằng 2 THREAD (QUY_TRINH bước 11, chỉ dẫn 009 điểm 2).

Hai thread, MỖI thread một kết nối CSDL thật CÓ COMMIT, cùng làm mới token của
MỘT shop Shopee với máy chủ giả lập qua socket thật. Refresh_token Shopee chỉ
dùng được 1 lần, nên nếu không có khóa thì hai thread cùng đọc refresh_token cũ
và thread chậm hơn bị sàn từ chối.

KHÁC mọi test DB khác: không thể dùng giao dịch rollback (cần commit thật để
thread kia nhìn thấy). Vì vậy dùng một shop RIÊNG (`ZZ_TEST_FOR_UPDATE`) và
fixture tự xóa dòng đó trong `finally` — dữ liệu thật của sinh viên không bị đụng.
"""

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
    """Một dòng platform_tokens thật (commit) cho shop thử; xóa sạch khi xong, kể cả khi test lỗi."""
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
    """Thread 1 vào `lam_moi_va_ghi`, giữ khóa dòng, rồi MỚI gọi sàn sau `thread_1_cho_giay`;
    thread 2 bắt đầu khi thread 1 đã nắm khóa. Trả (kết quả thread 1, kết quả thread 2, refresh đã gửi cho sàn)."""
    da_vao_giao_dich = threading.Event()
    cac_refresh_da_gui = []
    ket_qua = {}

    def lam_moi(ten, cho):
        client = ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                              settings.SHOPEE_SHOP_ID, settings.SHOPEE_ACCESS_TOKEN)

        def ham_lam_moi(refresh_token, shop_ref):
            cac_refresh_da_gui.append((ten, refresh_token))
            if ten == "t1":
                da_vao_giao_dich.set()           # đã giữ khóa dòng (nếu có khóa), chưa gọi sàn
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

    # Cả hai lượt kết thúc thành công, mỗi lượt nhận một cặp token MỚI khác nhau.
    assert isinstance(ket_qua_1, dict), ket_qua_1
    assert isinstance(ket_qua_2, dict), ket_qua_2
    assert ket_qua_1["refresh_token"] != ket_qua_2["refresh_token"]
    # Refresh cũ (ban đầu) chỉ được gửi cho sàn đúng 1 lần — thread 2 phải đợi rồi dùng refresh MỚI của thread 1.
    refresh_ban_dau = [ten for ten, refresh in refresh_da_gui if refresh == settings.SHOPEE_REFRESH_TOKEN]
    assert refresh_ban_dau == ["t1"]
    assert ("t2", ket_qua_1["refresh_token"]) in refresh_da_gui
    # CSDL giữ cặp token của lần làm mới SAU CÙNG, và token đó dùng được thật với sàn.
    access_cuoi, refresh_cuoi = doc_token_that()
    assert (access_cuoi, refresh_cuoi) == (ket_qua_2["access_token"], ket_qua_2["refresh_token"])
    with ShopeeClient(may_chu.url, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                      settings.SHOPEE_SHOP_ID, access_cuoi) as client:
        assert client.lay_chi_tiet(["KHONG_CO"]) == []


def test_thread_hai_phai_doi_khoa_cua_thread_mot(shop_test_that, bat_may_chu_gia_lap):
    """Thread 2 chỉ chạy `ham_lam_moi` SAU khi thread 1 commit: thời điểm gọi sàn của thread 2 muộn hơn thời gian thread 1 giữ khóa."""
    may_chu = bat_may_chu_gia_lap()
    bat_dau = time.monotonic()
    ket_qua_1, ket_qua_2, _ = chay_hai_thread(may_chu, thread_1_cho_giay=1.5)
    assert isinstance(ket_qua_1, dict) and isinstance(ket_qua_2, dict)
    assert time.monotonic() - bat_dau >= 1.5                          # thread 2 không thể xong trước khi thread 1 nhả khóa
