"""Test bảng token trong bộ nhớ và file cấu hình mẫu (PROMPT Phần C mục 3, SPEC §19.3 mục 3).

Thời điểm được truyền vào tay (bay_gio) nên test "hết hạn sau 4 giờ / 7 ngày"
chạy tức thì, không phải chờ.
"""

from pathlib import Path

import pytest

import config
import tokens

T0 = 1_700_000_000


def kho_shopee():
    kho = tokens.KhoToken(tokens.SHOPEE_HAN_ACCESS_GIAY, tokens.SHOPEE_HAN_REFRESH_GIAY, vo_hieu_refresh_cu=True)
    kho.nap_san("200001", "access_0", "refresh_0", T0)
    return kho


def kho_tiktok():
    kho = tokens.KhoToken(tokens.TIKTOK_HAN_ACCESS_GIAY, None, vo_hieu_refresh_cu=False)
    kho.nap_san("CIPHER_A", "access_a", "refresh_a", T0)
    kho.nap_san("CIPHER_B", "access_b", "refresh_b", T0)
    return kho


def ly_do_tu_choi(ham, *tham_so):
    with pytest.raises(tokens.TokenKhongHopLe) as loi:
        ham(*tham_so)
    return loi.value.ly_do


# ---------- access_token ----------

def test_access_token_hop_le_trong_han():
    kho_shopee().kiem_access_token("access_0", "200001", T0 + 4 * 3600 - 1)


def test_access_token_sai_hoac_cua_shop_khac():
    assert ly_do_tu_choi(kho_shopee().kiem_access_token, "khong_co", "200001", T0) == tokens.LY_DO_TOKEN_SAI
    # Shop A không được dùng token để đọc dữ liệu shop B.
    assert ly_do_tu_choi(kho_tiktok().kiem_access_token, "access_a", "CIPHER_B", T0) == tokens.LY_DO_TOKEN_SAI


def test_access_token_het_han_dung_moc_4_gio_va_7_ngay():
    assert (ly_do_tu_choi(kho_shopee().kiem_access_token, "access_0", "200001", T0 + 4 * 3600)
            == tokens.LY_DO_TOKEN_HET_HAN)
    kho = kho_tiktok()
    kho.kiem_access_token("access_a", "CIPHER_A", T0 + 7 * 86400 - 1)
    assert ly_do_tu_choi(kho.kiem_access_token, "access_a", "CIPHER_A", T0 + 7 * 86400) == tokens.LY_DO_TOKEN_HET_HAN


def test_han_song_ngan_qua_tham_so():
    """Hạn đặt qua biến môi trường (MOCK_*_ACCESS_TTL_SECONDS) — đây là cách test token hết hạn."""
    kho = tokens.KhoToken(5, None, vo_hieu_refresh_cu=False)
    kho.nap_san("S", "a", "r", T0)
    kho.kiem_access_token("a", "S", T0 + 4)
    assert ly_do_tu_choi(kho.kiem_access_token, "a", "S", T0 + 5) == tokens.LY_DO_TOKEN_HET_HAN


# ---------- Làm mới ----------

def test_shopee_lam_moi_2_lan_cung_refresh_cu_lan_2_bi_tu_choi():
    kho = kho_shopee()
    access_moi, refresh_moi = kho.lam_moi("refresh_0", "200001", T0 + 100)
    assert ly_do_tu_choi(kho.lam_moi, "refresh_0", "200001", T0 + 200) == tokens.LY_DO_TOKEN_SAI
    # Cặp mới dùng được, hạn tính từ lúc làm mới.
    kho.kiem_access_token(access_moi, "200001", T0 + 100 + 4 * 3600 - 1)
    kho.lam_moi(refresh_moi, "200001", T0 + 300)


def test_shopee_refresh_token_qua_30_ngay():
    assert (ly_do_tu_choi(kho_shopee().lam_moi, "refresh_0", "200001", T0 + 30 * 86400)
            == tokens.LY_DO_TOKEN_HET_HAN)


def test_shopee_access_cu_van_dung_toi_khi_het_han_sau_lam_moi():
    """Tài liệu không nói access_token cũ bị thu hồi khi làm mới → để nó tự hết hạn."""
    kho = kho_shopee()
    kho.lam_moi("refresh_0", "200001", T0 + 100)
    kho.kiem_access_token("access_0", "200001", T0 + 200)


def test_tiktok_refresh_cu_khong_bi_vo_hieu_va_khong_het_han():
    kho = kho_tiktok()
    kho.lam_moi("refresh_a", "CIPHER_A", T0)
    kho.lam_moi("refresh_a", "CIPHER_A", T0 + 100 * 365 * 86400)


def test_lam_moi_bang_refresh_cua_shop_khac_bi_tu_choi():
    assert ly_do_tu_choi(kho_tiktok().lam_moi, "refresh_a", "CIPHER_B", T0) == tokens.LY_DO_TOKEN_SAI


def test_token_moi_khong_trung_nhau():
    kho = kho_tiktok()
    cap_1 = kho.lam_moi("refresh_a", "CIPHER_A", T0)
    cap_2 = kho.lam_moi("refresh_a", "CIPHER_A", T0)
    assert len({*cap_1, *cap_2}) == 4


# ---------- File cấu hình mẫu ----------

def test_env_example_doc_duoc_va_ghi_ro_la_gia():
    duong_dan = Path(config.__file__).parent / ".env.example"
    cau_hinh = config.doc_cau_hinh(duong_dan)
    # Hạn sống bỏ trống trong file mẫu → đúng như sàn thật.
    assert cau_hinh.MOCK_SHOPEE_ACCESS_TTL_SECONDS == 4 * 3600
    assert cau_hinh.MOCK_TIKTOK_ACCESS_TTL_SECONDS == 7 * 86400
    # Mọi khóa / token đều mang chữ GIA — nhìn là biết không phải khóa thật.
    cac_khoa = [cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.TIKTOK_APP_KEY, cau_hinh.TIKTOK_APP_SECRET,
                cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_REFRESH_TOKEN,
                cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN,
                cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN]
    assert all("GIA" in khoa for khoa in cac_khoa)


def test_cau_hinh_thieu_bien_bao_loi(tmp_path):
    file_thieu = tmp_path / ".env"
    file_thieu.write_text("SHOPEE_PARTNER_ID=1\n", encoding="utf-8")
    with pytest.raises(Exception, match="SHOPEE_PARTNER_KEY"):
        config.doc_cau_hinh(file_thieu)
