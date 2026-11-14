"""Test luồng KẾT NỐI GIAN HÀNG bằng ủy quyền (chỉ dẫn 026, giai đoạn 3): `/api/connections/*`.

Chạy trọn vòng với MÁY CHỦ GIẢ LẬP THẬT trên socket (fixture `bat_may_chu_gia_lap`) và CSDL thật trong giao dịch rollback:
    POST authorize (admin) → mở trang ủy quyền của sàn → bấm Đồng ý/Từ chối → sàn chuyển về callback → backend đổi mã.
Phần "trình duyệt" do hàm `nguoi_dung_ben_trang_san` đóng vai: đọc biểu mẫu HTML của trang ủy quyền và gửi quyết định.

Phần logic thuần của `state` (hết hạn, dùng một lần, khác sàn) test không cần CSDL ở đầu file.
"""

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.database import lay_phien_db
from app.main import tao_ung_dung
from app.services import ket_noi_gian_hang, token_store
from app.services.ket_noi_gian_hang import KhoYeuCau, xu_ly_callback

BAY_GIO = datetime(2026, 11, 14, 9, 0, 0).astimezone()


# =====================================================================
# 1. Kho `state` — logic thuần (không CSDL)
# =====================================================================

def test_state_dung_mot_lan():
    kho = KhoYeuCau()
    state = kho.tao("shopee", 7, "Shop D", BAY_GIO, timedelta(minutes=10))
    yeu_cau = kho.lay_mot_lan(state, "shopee", BAY_GIO)
    assert yeu_cau.nguoi_id == 7 and yeu_cau.ten_shop == "Shop D"
    assert kho.lay_mot_lan(state, "shopee", BAY_GIO) is None


def test_state_het_han_sau_muoi_phut():
    kho = KhoYeuCau()
    state = kho.tao("tiktok", 1, None, BAY_GIO, timedelta(minutes=10))
    assert kho.lay_mot_lan(state, "tiktok", BAY_GIO + timedelta(minutes=10, seconds=1)) is None
    state2 = kho.tao("tiktok", 1, None, BAY_GIO, timedelta(minutes=10))
    assert kho.lay_mot_lan(state2, "tiktok", BAY_GIO + timedelta(minutes=9, seconds=59)) is not None


def test_state_cua_san_nay_khong_dung_cho_san_kia_va_bi_huy_luon():
    kho = KhoYeuCau()
    state = kho.tao("shopee", 1, "Shop D", BAY_GIO, timedelta(minutes=10))
    assert kho.lay_mot_lan(state, "tiktok", BAY_GIO) is None
    assert kho.lay_mot_lan(state, "shopee", BAY_GIO) is None          # đã bị hủy: không thử lại được


def test_state_gia_mao_hoac_rong_khong_hop_le():
    kho = KhoYeuCau()
    kho.tao("shopee", 1, "Shop D", BAY_GIO, timedelta(minutes=10))
    assert kho.lay_mot_lan("doan-bua", "shopee", BAY_GIO) is None
    assert kho.lay_mot_lan("", "shopee", BAY_GIO) is None
    assert kho.lay_mot_lan(None, "shopee", BAY_GIO) is None


def test_callback_state_khong_hop_le_khong_goi_ra_ngoai_va_tra_loi_state():
    """Không có state hợp lệ thì KHÔNG đổi mã (không gọi sàn): dùng cấu hình trỏ vào cổng không ai nghe — nếu có gọi sẽ ra lỗi khác."""
    kho = KhoYeuCau()
    ket_qua = xu_ly_callback("shopee", {"code": "abc", "shop_id": "1", "state": "gia"}, kho=kho)
    assert not ket_qua.thanh_cong and ket_qua.ly_do == ket_noi_gian_hang.LY_DO_STATE


def test_ten_shop_shopee_kiem_tra():
    assert ket_noi_gian_hang.kiem_tra_ten_shop("  Shop D ") == "Shop D"
    for sai in ["", "   ", None, "a/b", "a\\b", ".an", "x" * 51, 'a"b']:
        with pytest.raises(ket_noi_gian_hang.LoiYeuCauKetNoi):
            ket_noi_gian_hang.kiem_tra_ten_shop(sai)


def test_url_ve_giao_dien_khong_co_ma_hay_state():
    from app.services.ket_noi_gian_hang import KetQuaKetNoi, url_ve_giao_dien
    url = url_ve_giao_dien(KetQuaKetNoi(True, cac_shop=["Shop D"], ket_noi_lai=False))
    truy_van = parse_qs(urlparse(url).query)
    assert truy_van == {"ket_noi": ["thanh_cong"], "shop": ["Shop D"], "lai": ["0"]}
    loi = parse_qs(urlparse(url_ve_giao_dien(KetQuaKetNoi(False, "chu_shop_tu_choi"))).query)
    assert loi == {"ket_noi": ["loi"], "ly_do": ["chu_shop_tu_choi"]}


# =====================================================================
# 2. Trọn vòng với máy chủ giả lập thật + CSDL thật
# =====================================================================

class Moi:
    """Môi trường một test: app, máy chủ giả lập, danh sách lời gọi chạy nền, các hàm đóng vai trình duyệt."""

    def __init__(self, client, tieu_de_admin, may_chu, cac_lan_chay, ket_noi):
        self.client = client
        self.tieu_de_admin = tieu_de_admin
        self.may_chu = may_chu
        self.cac_lan_chay = cac_lan_chay
        self.ket_noi = ket_noi

    def bat_dau(self, san, ten_shop=None, tieu_de=None):
        than = {"shop_name": ten_shop} if ten_shop is not None else {}
        return self.client.post(f"/api/connections/{san}/authorize", json=than,
                                headers=self.tieu_de_admin if tieu_de is None else tieu_de)

    def nguoi_dung_ben_trang_san(self, authorize_url, quyet_dinh="dong_y", chon=None):
        """Mở trang ủy quyền của sàn rồi bấm nút; trả truy vấn (dict) của địa chỉ sàn chuyển trình duyệt về."""
        trang = httpx2.get(authorize_url)
        assert trang.status_code == 200, trang.text
        phien = re.search(r'name="phien" value="([^"]+)"', trang.text).group(1)
        hanh_dong = re.search(r'<form method="post" action="([^"]+)"', trang.text).group(1)
        ten_o = re.search(r'type="radio" name="([^"]+)"', trang.text).group(1)
        du_lieu = {"phien": phien, "quyet_dinh": quyet_dinh}
        if chon is not None:
            du_lieu[ten_o] = chon
        chuyen = httpx2.post(self.may_chu.url + hanh_dong, data=du_lieu, follow_redirects=False)
        assert chuyen.status_code in (302, 303), chuyen.text
        return {k: v[0] for k, v in parse_qs(urlparse(chuyen.headers["location"]).query).items()}

    def callback(self, san, truy_van):
        """Sàn chuyển trình duyệt về backend: KHÔNG có JWT."""
        return self.client.get(f"/api/connections/{san}/callback", params=truy_van, follow_redirects=False)

    def ket_noi_hoan_chinh(self, san, chon, ten_shop=None, quyet_dinh="dong_y"):
        url = self.bat_dau(san, ten_shop).json()["authorize_url"]
        truy_van = self.nguoi_dung_ben_trang_san(url, quyet_dinh, chon)
        return self.callback(san, truy_van), truy_van

    def dong_token(self, san):
        return self.ket_noi.execute(text(
            "SELECT shop_name, shop_ref, access_token, refresh_token FROM platform_tokens WHERE platform = :p ORDER BY shop_name"),
            {"p": san}).all()


@pytest.fixture
def moi(phien_test, ket_noi_test, tao_phien_test, monkeypatch, tieu_de_admin, bat_may_chu_gia_lap):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    ket_noi_test.execute(text("DELETE FROM sync_runs"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    may_chu = bat_may_chu_gia_lap()
    for ten in ["SHOPEE_BASE_URL", "TIKTOK_BASE_URL", "TIKTOK_AUTH_BASE_URL", "SHOPEE_AUTH_PAGE_BASE_URL", "TIKTOK_AUTH_PAGE_BASE_URL"]:
        monkeypatch.setattr(settings, ten, may_chu.url)
    ket_noi_gian_hang.KHO_YEU_CAU.xoa_het()
    cac_lan_chay = []

    def chay_nen_gia(cac_shop, cac_khoa, cac_run_id):
        cac_lan_chay.append({"shops": list(cac_shop), "khoa": list(cac_khoa), "run_ids": list(cac_run_id)})

    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False, ham_chay_nen=chay_nen_gia)
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung) as client:
        yield Moi(client, tieu_de_admin, may_chu, cac_lan_chay, ket_noi_test)
    for lan in cac_lan_chay:
        for khoa in lan["khoa"]:
            khoa.nha()
    ket_noi_gian_hang.KHO_YEU_CAU.xoa_het()


def duong_dan_ve_giao_dien(phan_hoi):
    dich = urlparse(phan_hoi.headers["location"])
    return f"{dich.scheme}://{dich.netloc}{dich.path}", {k: v[0] for k, v in parse_qs(dich.query).items()}


@pytest.mark.db
def test_chi_admin_moi_bat_dau_duoc_ket_noi(moi, tieu_de_user):
    assert moi.client.post("/api/connections/shopee/authorize", json={"shop_name": "Shop D"}).status_code == 401
    assert moi.bat_dau("shopee", "Shop D", tieu_de_user).status_code == 403
    assert moi.bat_dau("tiktok", None, tieu_de_user).status_code == 403
    assert moi.dong_token("shopee")[0][0] == "Shop C" and len(moi.dong_token("tiktok")) == 2     # chưa đổi gì


@pytest.mark.db
def test_shopee_bat_buoc_ten_hien_thi_va_ten_hop_le(moi):
    phan_hoi = moi.bat_dau("shopee")
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "shop_name_required"
    assert moi.bat_dau("shopee", "a/b").json()["detail"]["code"] == "shop_name_invalid"
    assert moi.bat_dau("shopee", "x" * 51).json()["detail"]["code"] == "shop_name_too_long"
    assert moi.bat_dau("tiktok").status_code == 200                       # TikTok không cần tên


@pytest.mark.db
def test_dia_chi_uy_quyen_khong_chua_khoa_ung_dung_hay_token(moi):
    url_shopee = moi.bat_dau("shopee", "Shop D").json()["authorize_url"]
    url_tiktok = moi.bat_dau("tiktok").json()["authorize_url"]
    truy_van = parse_qs(urlparse(url_shopee).query)
    assert set(truy_van) == {"partner_id", "timestamp", "sign", "redirect"}        # đúng thứ sàn yêu cầu công khai
    assert truy_van["redirect"][0].startswith(f"{settings.PUBLIC_BACKEND_URL}/api/connections/shopee/callback?state=")
    assert set(parse_qs(urlparse(url_tiktok).query)) == {"service_id", "state"}
    bi_mat = [settings.SHOPEE_PARTNER_KEY, settings.TIKTOK_APP_SECRET, settings.SHOPEE_ACCESS_TOKEN,
              settings.SHOPEE_REFRESH_TOKEN, settings.TIKTOK_SHOP_A_ACCESS_TOKEN]
    for chuoi in [url_shopee, url_tiktok]:
        assert all(b not in chuoi for b in bi_mat)


@pytest.mark.db
def test_shopee_ket_noi_shop_moi_tao_dong_token_va_kich_hoat_dong_bo(moi):
    truoc = moi.dong_token("shopee")
    phan_hoi, truy_van = moi.ket_noi_hoan_chinh("shopee", "200004", "Shop D")
    assert phan_hoi.status_code == 303
    goc, tham_so = duong_dan_ve_giao_dien(phan_hoi)
    assert goc == f"{settings.FRONTEND_URL}/admin/sync"
    assert tham_so == {"ket_noi": "thanh_cong", "shop": "Shop D", "lai": "0"}
    sau = moi.dong_token("shopee")
    assert [d[0] for d in sau] == ["Shop C", "Shop D"] and len(sau) == len(truoc) + 1
    shop_d = next(d for d in sau if d[0] == "Shop D")
    assert shop_d[1] == "200004" and shop_d[2] and shop_d[3]
    # Không có token / mã / state nào trong địa chỉ chuyển về giao diện.
    chuoi_ve = phan_hoi.headers["location"]
    for gia_tri in [shop_d[2], shop_d[3], truy_van["code"], truy_van["state"]]:
        assert gia_tri not in chuoi_ve
    # Kích hoạt MỘT lượt đồng bộ cho đúng shop vừa kết nối.
    assert [lan["shops"] for lan in moi.cac_lan_chay] == [[("shopee", "Shop D")]]
    dong_run = moi.ket_noi.execute(text("SELECT platform, shop_name, trigger_type, status FROM sync_runs")).all()
    assert dong_run == [("shopee", "Shop D", "manual", "running")]


@pytest.mark.db
def test_shopee_ket_noi_lai_shop_cu_cap_nhat_dung_dong_khong_tao_dong_trung_va_giu_ten(moi):
    truoc = {d[0]: d for d in moi.dong_token("shopee")}
    # Admin gõ tên khác, nhưng sàn trả đúng shop_id đang có → là KẾT NỐI LẠI: giữ tên cũ.
    phan_hoi, _ = moi.ket_noi_hoan_chinh("shopee", str(settings.SHOPEE_SHOP_ID), "Tên gõ khác")
    _, tham_so = duong_dan_ve_giao_dien(phan_hoi)
    assert tham_so == {"ket_noi": "thanh_cong", "shop": "Shop C", "lai": "1"}
    sau = moi.dong_token("shopee")
    assert len(sau) == 1 and sau[0][0] == "Shop C"                          # không thêm dòng, không đổi tên
    assert sau[0][2] != truoc["Shop C"][2] and sau[0][3] != truoc["Shop C"][3]   # token được thay
    assert moi.cac_lan_chay[0]["shops"] == [("shopee", "Shop C")]


@pytest.mark.db
def test_shopee_ten_trung_voi_shop_khac_bi_tu_choi_va_khong_dong_den_shop_do(moi):
    truoc = moi.dong_token("shopee")
    phan_hoi, _ = moi.ket_noi_hoan_chinh("shopee", "200004", "Shop C")    # shop D nhưng đặt tên "Shop C" đang là shop khác
    _, tham_so = duong_dan_ve_giao_dien(phan_hoi)
    assert tham_so == {"ket_noi": "loi", "ly_do": "ten_trung"}
    assert moi.dong_token("shopee") == truoc                               # token Shop C nguyên vẹn
    assert moi.cac_lan_chay == []


@pytest.mark.db
def test_chu_shop_tu_choi_khong_thay_doi_gi(moi):
    truoc = moi.dong_token("shopee") + moi.dong_token("tiktok")
    phan_hoi, truy_van = moi.ket_noi_hoan_chinh("shopee", None, "Shop D", quyet_dinh="tu_choi")
    assert "code" not in truy_van and truy_van["error"] == "access_denied"
    _, tham_so = duong_dan_ve_giao_dien(phan_hoi)
    assert tham_so == {"ket_noi": "loi", "ly_do": "chu_shop_tu_choi"}
    phan_hoi2, _ = moi.ket_noi_hoan_chinh("tiktok", None, quyet_dinh="tu_choi")
    assert duong_dan_ve_giao_dien(phan_hoi2)[1] == {"ket_noi": "loi", "ly_do": "chu_shop_tu_choi"}
    assert moi.dong_token("shopee") + moi.dong_token("tiktok") == truoc and moi.cac_lan_chay == []


@pytest.mark.db
def test_state_gia_mao_het_han_dung_lai_bi_tu_choi_khong_doi_ma(moi):
    url = moi.bat_dau("shopee", "Shop D").json()["authorize_url"]
    truy_van = moi.nguoi_dung_ben_trang_san(url, "dong_y", "200004")
    truoc = moi.dong_token("shopee")
    # (a) state giả
    gia = {**truy_van, "state": "doan-bua"}
    assert duong_dan_ve_giao_dien(moi.callback("shopee", gia))[1] == {"ket_noi": "loi", "ly_do": "state_khong_hop_le"}
    # (b) thiếu state
    thieu = {k: v for k, v in truy_van.items() if k != "state"}
    assert duong_dan_ve_giao_dien(moi.callback("shopee", thieu))[1]["ly_do"] == "state_khong_hop_le"
    assert moi.dong_token("shopee") == truoc
    # (c) state thật dùng được MỘT lần
    assert duong_dan_ve_giao_dien(moi.callback("shopee", truy_van))[1]["ket_noi"] == "thanh_cong"
    assert duong_dan_ve_giao_dien(moi.callback("shopee", truy_van))[1]["ly_do"] == "state_khong_hop_le"
    # (d) hết hạn: lùi hạn của yêu cầu về quá khứ
    url2 = moi.bat_dau("tiktok").json()["authorize_url"]
    truy_van2 = moi.nguoi_dung_ben_trang_san(url2, "dong_y", "Shop E")
    for yeu_cau in ket_noi_gian_hang.KHO_YEU_CAU._yeu_cau.values():
        yeu_cau.het_han = datetime.now().astimezone() - timedelta(seconds=1)
    assert duong_dan_ve_giao_dien(moi.callback("tiktok", truy_van2))[1]["ly_do"] == "state_khong_hop_le"
    assert all(d[0] != "Shop E" for d in moi.dong_token("tiktok"))


@pytest.mark.db
def test_state_cua_shopee_khong_dung_duoc_cho_callback_tiktok(moi):
    url = moi.bat_dau("shopee", "Shop D").json()["authorize_url"]
    truy_van = moi.nguoi_dung_ben_trang_san(url, "dong_y", "200004")
    assert duong_dan_ve_giao_dien(moi.callback("tiktok", truy_van))[1]["ly_do"] == "state_khong_hop_le"
    assert all(d[0] != "Shop D" for d in moi.dong_token("shopee"))


@pytest.mark.db
def test_ma_uy_quyen_het_han_o_san_thi_bao_loi_san_va_khong_ghi(moi):
    url = moi.bat_dau("shopee", "Shop D").json()["authorize_url"]
    truy_van = moi.nguoi_dung_ben_trang_san(url, "dong_y", "200004")
    truy_van["code"] = "ma-sai-khong-ton-tai"                              # sàn sẽ từ chối đổi (invalid_code)
    truoc = moi.dong_token("shopee")
    assert duong_dan_ve_giao_dien(moi.callback("shopee", truy_van))[1] == {"ket_noi": "loi", "ly_do": "loi_san"}
    assert moi.dong_token("shopee") == truoc and moi.cac_lan_chay == []


@pytest.mark.db
def test_tiktok_ket_noi_shop_moi_lay_ten_va_cipher_tu_san(moi):
    phan_hoi, _ = moi.ket_noi_hoan_chinh("tiktok", "Shop E")
    _, tham_so = duong_dan_ve_giao_dien(phan_hoi)
    assert tham_so == {"ket_noi": "thanh_cong", "shop": "Shop E", "lai": "0"}
    cac_dong = {d[0]: d for d in moi.dong_token("tiktok")}
    assert set(cac_dong) == {"Shop A", "Shop B", "Shop E"} and cac_dong["Shop E"][1] == "MOCK_CIPHER_SHOP_E"
    assert moi.cac_lan_chay[0]["shops"] == [("tiktok", "Shop E")]


@pytest.mark.db
def test_tiktok_ket_noi_lai_shop_a_thay_token_khong_tao_dong_trung(moi):
    truoc = {d[0]: d for d in moi.dong_token("tiktok")}
    phan_hoi, _ = moi.ket_noi_hoan_chinh("tiktok", "Shop A")
    assert duong_dan_ve_giao_dien(phan_hoi)[1] == {"ket_noi": "thanh_cong", "shop": "Shop A", "lai": "1"}
    sau = {d[0]: d for d in moi.dong_token("tiktok")}
    assert set(sau) == {"Shop A", "Shop B"}
    assert sau["Shop A"][2] != truoc["Shop A"][2] and sau["Shop B"] == truoc["Shop B"]       # chỉ Shop A đổi


@pytest.mark.db
def test_token_va_ma_khong_xuat_hien_trong_phan_hoi_hay_log(moi, caplog):
    caplog.set_level(logging.DEBUG)
    url = moi.bat_dau("shopee", "Shop D").json()["authorize_url"]
    truy_van = moi.nguoi_dung_ben_trang_san(url, "dong_y", "200004")
    # Từ đây chỉ xét log do BACKEND ghi: bước "trình duyệt" ở trên là do test đóng vai (thư viện HTTP của test ghi cả
    # địa chỉ chuyển về ở mức DEBUG), không phải mã của ứng dụng.
    caplog.clear()
    phan_hoi = moi.callback("shopee", truy_van)
    shop_d = next(d for d in moi.dong_token("shopee") if d[0] == "Shop D")
    bi_mat = [shop_d[2], shop_d[3], truy_van["code"], truy_van["state"], settings.SHOPEE_PARTNER_KEY]
    assert caplog.records, "phải có log của lần xử lý callback thì kiểm tra này mới có nghĩa"
    for gia_tri in bi_mat:
        assert gia_tri not in caplog.text, "bí mật lọt vào log"
        assert gia_tri not in phan_hoi.text and gia_tri not in phan_hoi.headers["location"]
    # Hai lần thất bại (state sai, sàn từ chối mã) cũng không làm lộ mã trong log.
    truy_van2 = moi.nguoi_dung_ben_trang_san(moi.bat_dau("shopee", "Shop X").json()["authorize_url"], "dong_y", "200004")
    ma_that = truy_van2["code"]
    truy_van2["code"] = "ma-sai-" + ma_that
    caplog.clear()
    moi.callback("shopee", truy_van2)
    moi.callback("shopee", {**truy_van2, "state": "state-gia-" + truy_van2["state"]})
    for gia_tri in [ma_that, truy_van2["code"], truy_van2["state"]]:
        assert gia_tri not in caplog.text


@pytest.mark.db
def test_shop_moi_duoc_lich_dong_bo_va_watcher_thay_o_vong_sau(moi, phien_test, tmp_path):
    """Shop vừa kết nối nằm trong platform_tokens nên: scheduler (đọc lại danh sách mỗi vòng) và watcher (tạo ngăn) đều thấy."""
    from app.sync import folder_watcher, sync_job

    moi.ket_noi_hoan_chinh("shopee", "200004", "Shop D")
    assert ("shopee", "Shop D") in sync_job.liet_ke_shop(phien_test)          # danh sách mà scheduler đọc lại mỗi vòng
    ten_shopee = [ten for _, ten in sync_job.liet_ke_shop(phien_test, "shopee")]
    folder_watcher.quet_mot_lan(tmp_path, {}, lambda *t: None, None, ten_shopee)
    assert (tmp_path / "inbox" / "shopee" / "Shop D").is_dir()
