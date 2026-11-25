import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import httpx2
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.services import token_store

pytestmark = pytest.mark.db

BAY_GIO = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def kho(tao_phien_test, ket_noi_test, monkeypatch):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    return token_store


def doc_dong(ket_noi, san, ten_shop):
    return ket_noi.execute(
        text("SELECT * FROM platform_tokens WHERE platform = :p AND shop_name = :s"), {"p": san, "s": ten_shop}
    ).mappings().one()


def theo_quy_uoc_cot(ket_noi, thoi_diem):
    return ket_noi.execute(text("SELECT CAST(:t AS timestamp)"), {"t": thoi_diem}).scalar_one()


class SanGia:
    def __init__(self, refresh_hop_le):
        self.refresh_hop_le = {refresh_hop_le}
        self.so_lan = 0

    def lam_moi(self, refresh_token, shop_ref):
        if refresh_token not in self.refresh_hop_le:
            raise RuntimeError("error_auth: refresh_token không hợp lệ hoặc đã dùng")
        self.refresh_hop_le.remove(refresh_token)
        self.so_lan += 1
        moi = f"refresh_moi_{self.so_lan}"
        self.refresh_hop_le.add(moi)
        return {"access_token": f"access_moi_{self.so_lan}", "refresh_token": moi, "expire_in": 14400}


def test_nap_san_3_shop_dung_gia_tri_va_han(kho, ket_noi_test):
    assert kho.nap_san_tu_cau_hinh(settings, BAY_GIO) == 3

    shopee = doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)
    assert shopee["shop_ref"] == str(settings.SHOPEE_SHOP_ID)
    assert (shopee["access_token"], shopee["refresh_token"]) == (settings.SHOPEE_ACCESS_TOKEN, settings.SHOPEE_REFRESH_TOKEN)
    assert shopee["access_expires_at"] == theo_quy_uoc_cot(ket_noi_test, BAY_GIO + timedelta(hours=4))
    assert shopee["refresh_expires_at"] == theo_quy_uoc_cot(ket_noi_test, BAY_GIO + timedelta(days=30))

    shop_a = doc_dong(ket_noi_test, "tiktok", settings.TIKTOK_SHOP_A_NAME)
    assert shop_a["shop_ref"] == settings.TIKTOK_SHOP_A_CIPHER
    assert shop_a["access_expires_at"] == theo_quy_uoc_cot(ket_noi_test, BAY_GIO + timedelta(days=7))
    assert shop_a["refresh_expires_at"] is None
    assert doc_dong(ket_noi_test, "tiktok", settings.TIKTOK_SHOP_B_NAME)["shop_ref"] == settings.TIKTOK_SHOP_B_CIPHER


def test_nap_lai_khong_ghi_de_token_dang_dung(kho, ket_noi_test):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    ket_noi_test.execute(text("UPDATE platform_tokens SET access_token = 'token_moi_nhat' WHERE platform = 'shopee'"))
    assert kho.nap_san_tu_cau_hinh(settings, BAY_GIO + timedelta(days=1)) == 0
    assert doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)["access_token"] == "token_moi_nhat"
    assert ket_noi_test.execute(text("SELECT count(*) FROM platform_tokens")).scalar_one() == 3


def test_nap_bo_sung_shop_con_thieu(kho, ket_noi_test):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    ket_noi_test.execute(text("DELETE FROM platform_tokens WHERE shop_name = :s"), {"s": settings.TIKTOK_SHOP_B_NAME})
    assert kho.nap_san_tu_cau_hinh(settings, BAY_GIO) == 1


def test_doc_token(kho):
    assert kho.doc_token("shopee", settings.SHOPEE_SHOP_NAME) is None
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    dong = kho.doc_token("shopee", settings.SHOPEE_SHOP_NAME)
    assert dong.access_token == settings.SHOPEE_ACCESS_TOKEN


def test_lam_moi_ghi_token_moi(kho, ket_noi_test):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    san = SanGia(settings.SHOPEE_REFRESH_TOKEN)
    luc_lam_moi = BAY_GIO + timedelta(hours=3)

    token_moi = kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, san.lam_moi, luc_lam_moi)
    dong = doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)
    assert (dong["access_token"], dong["refresh_token"]) == ("access_moi_1", "refresh_moi_1") == (
        token_moi["access_token"], token_moi["refresh_token"])
    assert dong["access_expires_at"] == theo_quy_uoc_cot(ket_noi_test, luc_lam_moi + timedelta(seconds=14400))
    kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, san.lam_moi, luc_lam_moi)
    assert doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)["refresh_token"] == "refresh_moi_2"


def test_tiktok_lam_moi_han_7_ngay_refresh_null(kho, ket_noi_test):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    ham = lambda refresh, cipher: {"access_token": "a", "refresh_token": refresh}
    kho.lam_moi_va_ghi("tiktok", settings.TIKTOK_SHOP_A_NAME, ham, BAY_GIO)
    dong = doc_dong(ket_noi_test, "tiktok", settings.TIKTOK_SHOP_A_NAME)
    assert dong["access_expires_at"] == theo_quy_uoc_cot(ket_noi_test, BAY_GIO + timedelta(days=7))
    assert dong["refresh_expires_at"] is None


def test_ham_lam_moi_truyen_dung_refresh_va_shop_ref(kho):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    da_nhan = []
    kho.lam_moi_va_ghi("tiktok", settings.TIKTOK_SHOP_B_NAME,
                       lambda r, c: da_nhan.append((r, c)) or {"access_token": "a", "refresh_token": "r"}, BAY_GIO)
    assert da_nhan == [(settings.TIKTOK_SHOP_B_REFRESH_TOKEN, settings.TIKTOK_SHOP_B_CIPHER)]


def test_san_tu_choi_thi_csdl_giu_nguyen(kho, ket_noi_test):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    with pytest.raises(RuntimeError, match="error_auth"):
        kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, SanGia("refresh_khac").lam_moi, BAY_GIO)
    assert doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)["refresh_token"] == settings.SHOPEE_REFRESH_TOKEN


def test_chua_nap_san_thi_bao_loi(kho):
    with pytest.raises(LookupError):
        kho.lam_moi_va_ghi("shopee", "Shop khong co", SanGia("x").lam_moi, BAY_GIO)


@pytest.fixture
def commit_se_loi(tao_phien_test, monkeypatch):
    def tao_phien_loi():
        phien = tao_phien_test()

        def commit_loi():
            raise OperationalError("COMMIT", {}, Exception("server closed the connection unexpectedly"))
        phien.commit = commit_loi
        return phien
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_loi)


def test_ghi_loi_sau_lam_moi_hau_qua_voi_shopee(kho, ket_noi_test, commit_se_loi):
    ket_noi_test.execute(text(
        "INSERT INTO platform_tokens (platform, shop_name, shop_ref, access_token, refresh_token, access_expires_at) "
        "VALUES ('shopee', :s, '200001', 'access_cu', 'refresh_cu', now())"), {"s": settings.SHOPEE_SHOP_NAME})
    san = SanGia("refresh_cu")

    with pytest.raises(token_store.LoiGhiTokenSauLamMoi) as loi:
        kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, san.lam_moi, BAY_GIO)

    dong = doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)
    assert (dong["access_token"], dong["refresh_token"]) == ("access_cu", "refresh_cu")
    assert loi.value.token_moi["refresh_token"] == "refresh_moi_1"
    assert "refresh_moi_1" not in str(loi.value) and "access_moi_1" not in str(loi.value)
    assert isinstance(loi.value.__cause__, OperationalError)
    # Sàn đã vô hiệu refresh cũ nên làm mới bằng token trong CSDL bị từ chối.
    with pytest.raises(RuntimeError, match="error_auth"):
        san.lam_moi(dong["refresh_token"], dong["shop_ref"])


def test_ghi_loi_sau_lam_moi_voi_may_chu_gia_lap_that(kho, ket_noi_test, bat_may_chu_gia_lap, tao_phien_test, monkeypatch):
    kho.nap_san_tu_cau_hinh(settings, BAY_GIO)
    may_chu = bat_may_chu_gia_lap()
    duong_dan = "/api/v2/auth/access_token/get"

    def lam_moi_shopee_that(refresh_token, shop_ref):
        timestamp = int(time.time())
        chu_ky = hmac.new(settings.SHOPEE_PARTNER_KEY.encode(),
                          f"{settings.SHOPEE_PARTNER_ID}{duong_dan}{timestamp}".encode(), hashlib.sha256).hexdigest()
        phan_hoi = httpx2.post(may_chu.url + duong_dan,
                               params={"partner_id": settings.SHOPEE_PARTNER_ID, "timestamp": timestamp, "sign": chu_ky},
                               json={"refresh_token": refresh_token, "partner_id": settings.SHOPEE_PARTNER_ID,
                                     "shop_id": int(shop_ref)}).json()
        if phan_hoi["error"]:
            raise RuntimeError(phan_hoi["error"])
        return phan_hoi["response"]

    kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, lam_moi_shopee_that)
    def commit_hong():
        raise OperationalError("COMMIT", {}, Exception("mat ket noi"))

    def tao_phien_loi():
        phien = tao_phien_test()
        phien.commit = commit_hong
        return phien
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_loi)
    with pytest.raises(token_store.LoiGhiTokenSauLamMoi):
        kho.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, lam_moi_shopee_that)

    dong = doc_dong(ket_noi_test, "shopee", settings.SHOPEE_SHOP_NAME)
    with pytest.raises(RuntimeError, match="error_auth"):
        lam_moi_shopee_that(dong["refresh_token"], dong["shop_ref"])
