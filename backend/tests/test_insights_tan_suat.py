"""Test giới hạn tần suất `POST /api/insights/generate` (chỉ dẫn 021, C.1): tối thiểu 10 giây giữa hai lần gọi của MỘT người dùng.

Đồng hồ được giả lập (`insights.dong_ho`) nên test không phải ngủ thật. Gemini được giả bằng `httpx2.MockTransport`.
"""

import threading

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

from app.api import insights as api_insights
from app.config import settings
from app.core.deps import yeu_cau_dang_nhap
from app.database import SessionLocal
from app.main import tao_ung_dung
from app.models.user import User

pytestmark = pytest.mark.db

VAN_BAN_TOT = "Doanh thu Shopee tháng 08/2026 tính đến ngày 16/08 đạt 840.035.154 đ, tăng 34,6% so với 624.277.755 đ."
BODY = {"platform": "shopee", "granularity": "month", "period": "2026-08"}


class DongHoGia:
    """Đồng hồ giả: tiến thời gian bằng tay."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class GeminiGia:
    def __init__(self, *cac_van_ban):
        self.cac_van_ban = list(cac_van_ban)
        self.so_lan_goi = 0

    def __call__(self, yeu_cau):
        self.so_lan_goi += 1
        van_ban = self.cac_van_ban.pop(0) if len(self.cac_van_ban) > 1 else self.cac_van_ban[0]
        return httpx2.Response(200, json={"candidates": [{"content": {"parts": [{"text": van_ban}]}, "finishReason": "STOP"}]})


@pytest.fixture(scope="module")
def du_lieu_mau_da_nap():
    with SessionLocal() as phien:
        if phien.execute(text("SELECT count(*) FROM orders WHERE platform = 'shopee'")).scalar_one() != 1774:
            pytest.skip("orders (shopee) chưa nạp đủ dữ liệu mẫu")


@pytest.fixture
def dong_ho(monkeypatch):
    gia = DongHoGia()
    monkeypatch.setattr(api_insights, "dong_ho", gia)
    monkeypatch.setattr(api_insights, "KHOANG_NGHI_TOI_THIEU_GIAY", 10)
    api_insights._lan_goi_cuoi.clear()
    yield gia
    api_insights._lan_goi_cuoi.clear()


@pytest.fixture
def goi(du_lieu_mau_da_nap, dong_ho, monkeypatch):
    """goi(nguoi_id, gemini) → phản hồi; mỗi lần gọi tạo một app mới với người dùng giả có id cho trước."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("KHOA-GIA-0123456789"))

    def _goi(ma_nguoi, gemini):
        app = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
        app.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=ma_nguoi, username=f"u{ma_nguoi}", role="user")
        app.state.llm_transport = httpx2.MockTransport(gemini)
        with TestClient(app) as client:
            return client.post("/api/insights/generate", json=BODY)
    return _goi


def test_hai_lan_lien_tiep_cua_mot_nguoi_lan_hai_la_429_dung_khuon(goi):
    gemini = GeminiGia(VAN_BAN_TOT)
    assert goi(1, gemini).status_code == 200
    phan_hoi = goi(1, gemini)
    assert phan_hoi.status_code == 429
    assert phan_hoi.json()["detail"] == {"code": "too_many_requests", "message": "Vui lòng đợi vài giây rồi thử lại",
                                         "retry_after_seconds": 10}
    assert phan_hoi.headers["Retry-After"] == "10"
    assert gemini.so_lan_goi == 1                                  # lần bị chặn KHÔNG gọi Gemini


def test_so_giay_cho_giam_dan_theo_thoi_gian_va_lam_tron_len(goi, dong_ho):
    gemini = GeminiGia(VAN_BAN_TOT)
    goi(1, gemini)
    dong_ho.t += 3.2
    phan_hoi = goi(1, gemini)
    assert phan_hoi.status_code == 429 and phan_hoi.json()["detail"]["retry_after_seconds"] == 7    # ceil(10 − 3,2)
    assert phan_hoi.headers["Retry-After"] == "7"


def test_nguoi_dung_khac_khong_bi_anh_huong(goi):
    gemini = GeminiGia(VAN_BAN_TOT)
    assert goi(1, gemini).status_code == 200
    assert goi(2, gemini).status_code == 200                       # người khác vẫn gọi được ngay
    assert goi(1, gemini).status_code == 429                       # người 1 vẫn đang chờ
    assert gemini.so_lan_goi == 2


def test_sau_khi_qua_thoi_gian_cho_goi_lai_duoc(goi, dong_ho):
    gemini = GeminiGia(VAN_BAN_TOT)
    goi(1, gemini)
    dong_ho.t += 9.9
    assert goi(1, gemini).status_code == 429
    dong_ho.t += 0.2                                               # tổng 10,1 giây kể từ lần gọi đầu
    assert goi(1, gemini).status_code == 200
    assert gemini.so_lan_goi == 2


def test_dung_bang_muoi_giay_thi_duoc_goi(goi, dong_ho):
    gemini = GeminiGia(VAN_BAN_TOT)
    goi(1, gemini)
    dong_ho.t += 10.0
    assert goi(1, gemini).status_code == 200


def test_lan_goi_that_bai_cung_tinh_vao_gioi_han(goi, dong_ho, monkeypatch):
    """Giới hạn đếm mọi lần gọi tới được Gemini kể cả khi Gemini lỗi (để không thể dội liên tục khi dịch vụ đang hỏng)."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    gemini = GeminiGia(VAN_BAN_TOT)
    assert goi(1, gemini).status_code == 503                       # chưa có khóa → 503
    assert goi(1, gemini).status_code == 429


def test_thu_lai_noi_bo_cua_chot_chan_so_la_khong_tinh_la_hai_lan_goi(goi):
    """Gemini trả số bịa ở lần đầu, đúng ở lần hai: bên trong gọi Gemini 2 lần nhưng với người dùng đó là MỘT lần gọi API."""
    gemini = GeminiGia("Tăng 99,9% so với kỳ trước.", VAN_BAN_TOT)
    phan_hoi = goi(1, gemini)
    assert phan_hoi.status_code == 200 and gemini.so_lan_goi == 2   # không bị 429 giữa hai lần thử nội bộ
    assert goi(1, gemini).status_code == 429                       # nhưng lần gọi API kế tiếp thì bị chờ


def test_loi_422_do_pydantic_khong_tinh_vao_gioi_han(du_lieu_mau_da_nap, dong_ho):
    app = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    app.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=1, username="u1", role="user")
    with TestClient(app) as client:
        assert client.post("/api/insights/generate", json={"platform": "lazada"}).status_code == 422
        assert 1 not in api_insights._lan_goi_cuoi


def test_khoang_nghi_bang_0_tat_gioi_han(goi, monkeypatch):
    monkeypatch.setattr(api_insights, "KHOANG_NGHI_TOI_THIEU_GIAY", 0)
    gemini = GeminiGia(VAN_BAN_TOT)
    assert goi(1, gemini).status_code == 200 and goi(1, gemini).status_code == 200


def test_nhieu_luong_cung_luc_chi_mot_luong_duoc_qua(dong_ho):
    """Kiểm-rồi-ghi là nguyên tử: 20 luồng cùng gọi một lúc chỉ đúng MỘT luồng nhận 0 (được gọi), 19 luồng còn lại phải chờ."""
    ket_qua = []
    rao = threading.Barrier(20)

    def chay():
        rao.wait()
        ket_qua.append(api_insights.kiem_tan_suat(77))
    cac_luong = [threading.Thread(target=chay) for _ in range(20)]
    for luong in cac_luong:
        luong.start()
    for luong in cac_luong:
        luong.join()
    assert ket_qua.count(0) == 1 and len(ket_qua) == 20


def test_dong_ho_that_khong_bi_thay_trong_ung_dung():
    assert api_insights.KHOANG_NGHI_TOI_THIEU_GIAY == 10
