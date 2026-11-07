"""Test nhận định LLM (UC12, SPEC §10, §12.1.4.3). KHÔNG gọi Gemini thật: `httpx2.MockTransport` giả phản hồi.

Dữ liệu mẫu đã nạp trong CSDL thật (chỉ đọc). Điểm cần chứng minh: dữ liệu gửi đi đúng §10 (số tổng hợp, không dữ
liệu dòng), chốt chặn số lạ hoạt động (gọi lại một lần rồi 503), mọi lỗi mạng/khóa/hạn mức → 503 `llm_unavailable`,
khóa không bao giờ ra log hay phản hồi.
"""

import json

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

from app.config import settings
from app.core.deps import yeu_cau_dang_nhap
from app.database import SessionLocal
from app.main import tao_ung_dung
from app.models.user import User
from app.services import insight_service

pytestmark = pytest.mark.db

KHOA_GIA = "KHOA-GIA-DE-TEST-0123456789-ABCDEF"
SO_DONG_MAU = {"orders_shopee": 1774, "orders_tiktok": 7540}
VAN_BAN_TOT = ("Doanh thu Shopee tháng 08/2026 tính đến ngày 16/08 đạt 840.035.154 đ, tăng 34,6% so với cùng kỳ "
               "tháng 07 (624.277.755 đ). Sản phẩm M15 dẫn đầu.")


@pytest.fixture(scope="module")
def du_lieu_mau_da_nap():
    with SessionLocal() as phien:
        for bang, so_dong in SO_DONG_MAU.items():
            if phien.execute(text(f"SELECT count(*) FROM {bang}")).scalar_one() != so_dong:
                pytest.skip(f"{bang} chưa nạp đủ {so_dong} dòng dữ liệu mẫu")


@pytest.fixture
def ung_dung(du_lieu_mau_da_nap, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr(KHOA_GIA))
    monkeypatch.setattr(settings, "GEMINI_MODEL", "mo-hinh-thu")
    app = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    app.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=-1, username="nguoi_thu", role="user")
    return app


def phan_hoi_gemini(van_ban, ly_do="STOP"):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": van_ban}]}, "finishReason": ly_do}]}


class Gia:
    """Máy chủ Gemini giả: ghi lại mọi yêu cầu, trả lần lượt các phản hồi cho sẵn (hoặc ném lỗi)."""

    def __init__(self, *cac_phan_hoi):
        self.cac_phan_hoi = list(cac_phan_hoi)
        self.cac_yeu_cau = []

    def __call__(self, yeu_cau):
        self.cac_yeu_cau.append(yeu_cau)
        muc = self.cac_phan_hoi.pop(0) if len(self.cac_phan_hoi) > 1 else self.cac_phan_hoi[0]
        if isinstance(muc, Exception):
            raise muc
        ma, noi_dung = muc
        return httpx2.Response(ma, json=noi_dung)

    def body(self, chi_so=0):
        return json.loads(self.cac_yeu_cau[chi_so].content)


def goi(ung_dung, gia, **body):
    ung_dung.state.llm_transport = httpx2.MockTransport(gia)
    with TestClient(ung_dung) as client:
        return client.post("/api/insights/generate", json={"platform": "shopee", "granularity": "month",
                                                           "period": "2026-08", **body})


# ---------------------------------------------------------------- đường thành công và dữ liệu gửi đi

def test_phan_hoi_tot_tra_200_dung_khuon(ung_dung):
    gia = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    phan_hoi = goi(ung_dung, gia)
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert set(du_lieu) == {"text", "generated_at", "period_complete", "data_max_date"}
    assert du_lieu["text"] == VAN_BAN_TOT
    assert du_lieu["period_complete"] is False and du_lieu["data_max_date"] == "2026-08-16"
    assert du_lieu["generated_at"].endswith("+07:00")
    assert len(gia.cac_yeu_cau) == 1


def test_yeu_cau_gui_den_gemini_dung_dia_chi_va_khoa_nam_trong_tieu_de(ung_dung):
    gia = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    goi(ung_dung, gia)
    yeu_cau = gia.cac_yeu_cau[0]
    assert yeu_cau.method == "POST"
    assert str(yeu_cau.url) == "https://generativelanguage.googleapis.com/v1beta/models/mo-hinh-thu:generateContent"
    assert yeu_cau.headers["x-goog-api-key"] == KHOA_GIA
    assert KHOA_GIA not in str(yeu_cau.url) and "key=" not in str(yeu_cau.url)         # khóa KHÔNG nằm trong URL


def test_cau_hinh_sinh_van_ban_va_muc_suy_nghi(ung_dung, monkeypatch):
    gia = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    goi(ung_dung, gia)
    cau_hinh = gia.body()["generationConfig"]
    assert cau_hinh == {"maxOutputTokens": 4096, "thinkingConfig": {"thinkingLevel": "LOW"}}
    assert "temperature" not in cau_hinh                       # đã bị bỏ qua ở Gemini 3.6 trở lên
    monkeypatch.setattr(settings, "GEMINI_THINKING_LEVEL", "")   # model cũ không có thinkingLevel
    gia2 = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    goi(ung_dung, gia2)
    assert gia2.body()["generationConfig"] == {"maxOutputTokens": 4096}


def test_du_lieu_gui_di_dung_so_lieu_10_va_khong_co_du_lieu_dong(ung_dung):
    gia = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    goi(ung_dung, gia)
    body = gia.body()
    lenh = body["systemInstruction"]["parts"][0]["text"]
    noi_dung = body["contents"][0]["parts"][0]["text"]
    json_gui = json.loads(noi_dung.split("Số liệu:\n", 1)[1].split("\n\nHãy viết", 1)[0])
    assert json_gui["platform"] == "Shopee" and json_gui["period"] == "2026-08" and json_gui["granularity"] == "month"
    assert json_gui["revenue"] == 840035154 and json_gui["revenue_previous"] == 624277755
    assert json_gui["pct_change"] == 34.6 and json_gui["previous_period"] == "2026-07"
    assert json_gui["period_complete"] is False and json_gui["data_max_date"] == "2026-08-16"
    assert (json_gui["date_from"], json_gui["date_to"]) == ("2026-08-01", "2026-08-16")
    assert (json_gui["previous_date_from"], json_gui["previous_date_to"]) == ("2026-07-01", "2026-07-16")
    assert json_gui["alert_triggered"] is False and json_gui["order_count"] and json_gui["aov"]
    top = json_gui["top_products"]
    assert 1 <= len(top) <= 5 and set(top[0]) == {"product_code", "revenue", "change_pct"}
    assert [m["revenue"] for m in top] == sorted((m["revenue"] for m in top), reverse=True)
    # Không gửi dữ liệu dòng, sku thô, mã đơn, thông tin khách hàng.
    for cam in ("sku", "order_id", "buyer", "phone", "address", "recipient", "customer", "province"):
        assert cam not in noi_dung.lower(), cam
    # Câu lệnh: các quy tắc bắt buộc của SPEC §10.
    for ve in ("KHÔNG tự tính số mới", "KHÔNG suy đoán nguyên nhân", "tính đến ngày", "pct_change", "null", "product_code", "tối đa 5 câu"):
        assert ve in lenh, ve


def test_ky_chua_day_du_va_pct_change_null_duoc_gui_dung(ung_dung):
    gia = Gia((200, phan_hoi_gemini("Doanh thu năm 2026 đạt 1.908.961.059 đ.")))
    phan_hoi = goi(ung_dung, gia, granularity="year", period="2026")
    assert phan_hoi.status_code == 200
    noi_dung = gia.body()["contents"][0]["parts"][0]["text"]
    json_gui = json.loads(noi_dung.split("Số liệu:\n", 1)[1].split("\n\nHãy viết", 1)[0])
    assert json_gui["pct_change"] is None and json_gui["previous_period"] is None and json_gui["revenue"] == 1908961059


def test_ky_khong_co_du_lieu_khong_goi_llm(ung_dung):
    gia = Gia((200, phan_hoi_gemini("không được gọi")))
    phan_hoi = goi(ung_dung, gia, period="2026-03")
    assert phan_hoi.status_code == 200 and "chưa có dữ liệu" in phan_hoi.json()["text"]
    assert gia.cac_yeu_cau == []


# ---------------------------------------------------------------- chốt chặn số lạ

def test_so_la_thi_goi_lai_mot_lan_roi_503(ung_dung, caplog):
    gia = Gia((200, phan_hoi_gemini("Doanh thu đạt 850 triệu, tăng 40%.")))
    with caplog.at_level("WARNING"):
        phan_hoi = goi(ung_dung, gia)
    assert phan_hoi.status_code == 503
    assert phan_hoi.json() == {"detail": {"code": "llm_unavailable", "message": "Nhận định chứa số không có trong dữ liệu"}}
    assert len(gia.cac_yeu_cau) == 2                                                  # đúng một lần gọi lại
    lan_hai = gia.body(1)["contents"][0]["parts"][0]["text"]
    assert "850" in lan_hai and "KHÔNG có trong số liệu" in lan_hai                   # báo cho model biết số nào lạ
    assert caplog.text.count("bị chặn vì số không có trong dữ liệu") == 2             # ghi số lần bị chặn vào log


def test_lan_dau_so_la_lan_hai_tot_thi_200(ung_dung, caplog):
    gia = Gia((200, phan_hoi_gemini("Tăng 99,9% so với kỳ trước.")), (200, phan_hoi_gemini(VAN_BAN_TOT)))
    with caplog.at_level("WARNING"):
        phan_hoi = goi(ung_dung, gia)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["text"] == VAN_BAN_TOT
    assert len(gia.cac_yeu_cau) == 2 and "sau 1 lần bị chặn" in caplog.text


def test_tu_tinh_chenh_lech_cung_bi_chan(ung_dung):
    """840.035.154 − 624.277.755 = 215.757.399: model tự tính số mới → bị chặn dù phép tính đúng."""
    gia = Gia((200, phan_hoi_gemini("Doanh thu tăng 215.757.399 đ so với kỳ trước.")))
    assert goi(ung_dung, gia).status_code == 503


@pytest.mark.parametrize("van_ban", [
    "Doanh thu đạt 840 triệu đồng.",                                    # làm tròn theo triệu
    "Doanh thu đạt 0,84 tỷ đồng, tăng 34,6%.",                          # làm tròn theo tỷ + phần trăm
    "Doanh thu tăng khoảng 35% so với kỳ trước.",                       # làm tròn phần trăm về số nguyên
    "Doanh thu tăng 34.6% so với kỳ trước.",                            # dấu chấm thập phân
    "Tính đến ngày 16/08/2026, doanh thu tháng 8 so với tháng 7.",      # ngày, tháng, năm
    "Kỳ 2026-08 so với 2026-07; sản phẩm M15 và BU01.",                 # mã kỳ, mã sản phẩm
    "Doanh thu đạt 840.035.154 đ.",                                     # số đầy đủ kiểu Việt
])
def test_cach_viet_lam_tron_hop_ly_duoc_chap_nhan(ung_dung, van_ban):
    gia = Gia((200, phan_hoi_gemini(van_ban)))
    phan_hoi = goi(ung_dung, gia)
    assert phan_hoi.status_code == 200, van_ban
    assert len(gia.cac_yeu_cau) == 1


@pytest.mark.parametrize("van_ban", [
    "Doanh thu đạt 850 triệu đồng.",       # lệch quá nửa triệu
    "Doanh thu đạt 840.035.155 đ.",        # lệch 1 đồng ở số viết đủ
    "Doanh thu tăng 34,7%.",               # lệch 0,1 điểm
    "Doanh thu tăng 36%.",                 # làm tròn sai
    "Có 7 sản phẩm bán chạy nhất 99 ngày.",
])
def test_so_sai_bi_chan(ung_dung, van_ban):
    gia = Gia((200, phan_hoi_gemini(van_ban)))
    assert goi(ung_dung, gia).status_code == 503, van_ban


# ---------------------------------------------------------------- lỗi Gemini → 503 llm_unavailable

@pytest.mark.parametrize("phan_hoi_loi, thong_diep", [
    ((429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}}), "Đã hết hạn mức gọi Gemini, thử lại sau"),
    ((400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "API key not valid"}}), "Khóa Gemini không hợp lệ hoặc chưa được cấp quyền"),
    ((403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "x"}}), "Khóa Gemini không hợp lệ hoặc chưa được cấp quyền"),
    ((500, {"error": {"code": 500, "message": "boom"}}), "Gemini đang gặp sự cố, thử lại sau"),
    ((503, {"error": {"code": 503, "message": "overloaded"}}), "Gemini đang gặp sự cố, thử lại sau"),
])
def test_loi_http_cua_gemini_la_503(ung_dung, phan_hoi_loi, thong_diep):
    phan_hoi = goi(ung_dung, Gia(phan_hoi_loi))
    assert phan_hoi.status_code == 503
    assert phan_hoi.json() == {"detail": {"code": "llm_unavailable", "message": thong_diep}}
    assert "quota" not in phan_hoi.text and "boom" not in phan_hoi.text                # không lộ nội dung lỗi của bên thứ ba


@pytest.mark.parametrize("loi", [httpx2.ConnectError("mạng đứt"), httpx2.ReadTimeout("quá hạn")])
def test_loi_mang_la_503(ung_dung, loi):
    phan_hoi = goi(ung_dung, Gia(loi))
    assert phan_hoi.status_code == 503 and phan_hoi.json()["detail"]["message"] == "Không kết nối được Gemini"


@pytest.mark.parametrize("noi_dung", [
    (200, {"khong": "co candidates"}), (200, {"candidates": []}), (200, {"candidates": [{"content": {}}]}),
    (200, phan_hoi_gemini("", "STOP")), (200, phan_hoi_gemini("đang viết dở", "MAX_TOKENS")),
    (200, phan_hoi_gemini("bị chặn", "SAFETY")),
])
def test_phan_hoi_khong_dung_khuon_hoac_cat_giua_chung_la_503(ung_dung, noi_dung):
    assert goi(ung_dung, Gia(noi_dung)).status_code == 503


def test_phan_hoi_khong_phai_json_la_503(ung_dung):
    ung_dung.state.llm_transport = httpx2.MockTransport(lambda yc: httpx2.Response(200, content=b"<html>"))
    with TestClient(ung_dung) as client:
        phan_hoi = client.post("/api/insights/generate", json={"platform": "shopee", "granularity": "month", "period": "2026-08"})
    assert phan_hoi.status_code == 503


def test_chua_cau_hinh_khoa_la_503_va_khong_goi_mang(ung_dung, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    gia = Gia((200, phan_hoi_gemini(VAN_BAN_TOT)))
    phan_hoi = goi(ung_dung, gia)
    assert phan_hoi.status_code == 503 and phan_hoi.json()["detail"]["message"] == "Chưa cấu hình GEMINI_API_KEY"
    assert gia.cac_yeu_cau == []
    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr(""))
    assert goi(ung_dung, gia).status_code == 503 and gia.cac_yeu_cau == []


def test_loi_llm_khong_lam_hong_khoi_khac_cua_dashboard(ung_dung):
    ung_dung.state.llm_transport = httpx2.MockTransport(Gia((500, {})))
    with TestClient(ung_dung) as client:
        assert client.post("/api/insights/generate", json={"platform": "shopee", "period": "2026-08"}).status_code == 503
        assert client.get("/api/shopee/kpi", params={"period": "2026-08"}).status_code == 200


# ---------------------------------------------------------------- khóa không bao giờ lộ

@pytest.mark.parametrize("cach", ["tot", "so_la", "loi_mang", "loi_429", "dinh_dang"])
def test_khoa_khong_xuat_hien_trong_log_va_phan_hoi(ung_dung, caplog, cach):
    gia = {"tot": Gia((200, phan_hoi_gemini(VAN_BAN_TOT))),
           "so_la": Gia((200, phan_hoi_gemini("Tăng 77,7%."))),
           "loi_mang": Gia(httpx2.ConnectError(f"không nối được tới ...?key={KHOA_GIA}")),
           "loi_429": Gia((429, {"error": {"message": f"quota cho khóa {KHOA_GIA}"}})),
           "dinh_dang": Gia((200, {"candidates": [{"content": {"parts": [{"text": f"{KHOA_GIA}"}]}, "finishReason": "SAFETY"}]}))}[cach]
    with caplog.at_level("DEBUG"):
        phan_hoi = goi(ung_dung, gia)
    assert KHOA_GIA not in phan_hoi.text
    assert KHOA_GIA not in caplog.text
    assert KHOA_GIA not in repr(settings) and KHOA_GIA not in str(settings)           # SecretStr che khóa
    assert KHOA_GIA not in json.dumps(phan_hoi.json(), ensure_ascii=False)


# ---------------------------------------------------------------- quyền, tham số

def test_phai_dang_nhap(du_lieu_mau_da_nap):
    with TestClient(tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)) as client:
        phan_hoi = client.post("/api/insights/generate", json={"platform": "shopee"})
        assert phan_hoi.status_code == 401 and phan_hoi.json()["detail"]["code"] == "not_authenticated"


@pytest.mark.parametrize("body, ma", [({"platform": "lazada"}, 422), ({"platform": "shopee", "granularity": "week"}, 422),
                                      ({}, 422), ({"platform": "shopee", "granularity": "month", "period": "2026-Q3"}, 422)])
def test_tham_so_sai_422(ung_dung, body, ma):
    ung_dung.state.llm_transport = httpx2.MockTransport(Gia((200, phan_hoi_gemini(VAN_BAN_TOT))))
    with TestClient(ung_dung) as client:
        assert client.post("/api/insights/generate", json=body).status_code == ma


# ---------------------------------------------------------------- hàm thuần

def test_doc_so_cac_cach_viet():
    assert insight_service.doc_so("840.035.154") == (840035154.0, 0)
    assert insight_service.doc_so("34,6") == (34.6, 1)
    assert insight_service.doc_so("34.6") == (34.6, 1)
    assert insight_service.doc_so("1.234") == (1234.0, 0)
    assert insight_service.doc_so("1.234,5") == (1234.5, 1)
    assert insight_service.doc_so("2026") == (2026.0, 0)


def test_tim_so_la_thuan():
    du_lieu = {"revenue": 840035154, "pct_change": -21.4, "period": "2026-08", "top_products": [{"product_code": "M3 Plus", "revenue": 5}]}
    f = insight_service.tim_so_la
    assert f("Doanh thu 840 triệu giảm 21,4% so với kỳ trước.", du_lieu) == []                # dấu âm không cần có trong văn bản
    assert f("Tháng 8/2026, M3 Plus đứng thứ 1.", du_lieu) == []                               # kỳ, mã sản phẩm, thứ hạng
    assert f("Doanh thu 900 triệu.", du_lieu) == ["900"]
    assert f("Giảm 22%.", du_lieu) == ["22"]
    assert f("", du_lieu) == []
