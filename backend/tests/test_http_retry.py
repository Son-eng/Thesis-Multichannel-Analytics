import hashlib
import hmac
import json
import time

import httpx2
import pytest

from app.connectors import http_retry
from app.config import settings


def tao_client_gia(cac_phan_hoi):
    hang_doi = list(cac_phan_hoi)

    def xu_ly(yeu_cau):
        tiep = hang_doi.pop(0)
        if isinstance(tiep, Exception):
            raise tiep
        return tiep
    return httpx2.Client(transport=httpx2.MockTransport(xu_ly), base_url="http://san")


class DongHoNgu:
    def __init__(self):
        self.cac_lan = []

    def __call__(self, so_giay):
        self.cac_lan.append(so_giay)


def qua_tai_shopee():
    return httpx2.Response(429, json={"error": "error_rate_limit", "message": "", "request_id": "r"})


def thanh_cong_shopee():
    return httpx2.Response(200, json={"error": "", "message": "", "request_id": "r", "response": {"ok": 1}})


def goi(client, phan_loai, ngu, **them):
    return http_retry.goi_co_thu_lai(lambda: client.get("/x"), phan_loai, ham_ngu=ngu, **them)


def test_thanh_cong_ngay_khong_ngu():
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([thanh_cong_shopee()]), http_retry.phan_loai_shopee, ngu)
    assert phan_hoi.json()["response"] == {"ok": 1}
    assert ngu.cac_lan == []


def test_qua_tai_3_lan_roi_thanh_cong_cho_tang_dan():
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([qua_tai_shopee()] * 3 + [thanh_cong_shopee()]), http_retry.phan_loai_shopee, ngu)
    assert phan_hoi.status_code == 200
    assert ngu.cac_lan == [1.0, 2.0, 4.0]


def test_het_so_lan_thi_bo_cuoc():
    ngu = DongHoNgu()
    with pytest.raises(http_retry.LoiHetLanThuLai) as loi:
        goi(tao_client_gia([qua_tai_shopee()] * 5), http_retry.phan_loai_shopee, ngu)
    assert loi.value.so_lan_gui == 5
    assert loi.value.lan_cuoi.status_code == 429
    assert ngu.cac_lan == [1.0, 2.0, 4.0, 8.0]


def test_so_lan_va_thoi_gian_cho_cau_hinh_duoc():
    ngu = DongHoNgu()
    with pytest.raises(http_retry.LoiHetLanThuLai):
        goi(tao_client_gia([qua_tai_shopee()] * 3), http_retry.phan_loai_shopee, ngu,
            so_lan_toi_da=3, cho_co_ban_giay=0.5)
    assert ngu.cac_lan == [0.5, 1.0]


def test_shopee_nhan_dien_qua_tai_bang_body_du_http_200():
    ngu = DongHoNgu()
    qua_tai_200 = httpx2.Response(200, json={"error": "error_rate_limit"})
    goi(tao_client_gia([qua_tai_200, thanh_cong_shopee()]), http_retry.phan_loai_shopee, ngu)
    assert ngu.cac_lan == [1.0]


@pytest.mark.parametrize("ma_loi", ["error_param", "error_sign", "error_auth", "refresh_token_expired"])
def test_shopee_khong_thu_lai_loi_khong_phai_qua_tai(ma_loi):
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([httpx2.Response(200, json={"error": ma_loi})]), http_retry.phan_loai_shopee, ngu)
    assert phan_hoi.json()["error"] == ma_loi
    assert ngu.cac_lan == []


def test_tiktok_36009002_cho_lau_hon_36009003():
    ngu_qua_tai, ngu_noi_bo = DongHoNgu(), DongHoNgu()
    ok = httpx2.Response(200, json={"code": 0, "data": {}})
    goi(tao_client_gia([httpx2.Response(200, json={"code": 36009002})] * 2 + [ok]), http_retry.phan_loai_tiktok, ngu_qua_tai)
    ok = httpx2.Response(200, json={"code": 0, "data": {}})
    goi(tao_client_gia([httpx2.Response(200, json={"code": 36009003})] * 2 + [ok]), http_retry.phan_loai_tiktok, ngu_noi_bo)
    assert ngu_qua_tai.cac_lan == [2.0, 4.0]
    assert ngu_noi_bo.cac_lan == [1.0, 2.0]


@pytest.mark.parametrize("ma", [9990001, 9990003, 9990005, 9990006])
def test_tiktok_khong_thu_lai_ma_khac(ma):
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([httpx2.Response(200, json={"code": ma})]), http_retry.phan_loai_tiktok, ngu)
    assert phan_hoi.json()["code"] == ma and ngu.cac_lan == []


def test_loi_mang_duoc_thu_lai():
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([httpx2.ConnectError("rot mang"), httpx2.ReadError("reset"), thanh_cong_shopee()]),
                   http_retry.phan_loai_shopee, ngu)
    assert phan_hoi.status_code == 200 and ngu.cac_lan == [1.0, 2.0]


def test_loi_mang_mai_thi_bo_cuoc_giu_loi_cuoi():
    with pytest.raises(http_retry.LoiHetLanThuLai) as loi:
        goi(tao_client_gia([httpx2.ConnectError("rot mang")] * 5), http_retry.phan_loai_shopee, DongHoNgu())
    assert isinstance(loi.value.lan_cuoi, httpx2.ConnectError)


def test_body_khong_phai_json_khong_van_loi_khong_thu_lai():
    ngu = DongHoNgu()
    phan_hoi = goi(tao_client_gia([httpx2.Response(502, text="<html>Bad Gateway</html>")]), http_retry.phan_loai_tiktok, ngu)
    assert phan_hoi.status_code == 502 and ngu.cac_lan == []


def test_moi_lan_thu_goi_lai_ham_gui():
    so_lan_goi = []
    client = tao_client_gia([qua_tai_shopee(), thanh_cong_shopee()])

    def gui():
        so_lan_goi.append(1)
        return client.get("/x")
    http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_shopee, ham_ngu=DongHoNgu())
    assert len(so_lan_goi) == 2


DUONG_DAN_DETAIL = "/api/v2/order/get_order_detail"
DUONG_DAN_SEARCH = "/order/202309/orders/search"


def gui_shopee_da_ky(client, duong_dan, tham_so_rieng):
    timestamp = int(time.time())
    chuoi = f"{settings.SHOPEE_PARTNER_ID}{duong_dan}{timestamp}{settings.SHOPEE_ACCESS_TOKEN}{settings.SHOPEE_SHOP_ID}"
    chu_ky = hmac.new(settings.SHOPEE_PARTNER_KEY.encode(), chuoi.encode(), hashlib.sha256).hexdigest()
    return client.get(duong_dan, params={
        "partner_id": settings.SHOPEE_PARTNER_ID, "timestamp": timestamp, "sign": chu_ky,
        "access_token": settings.SHOPEE_ACCESS_TOKEN, "shop_id": settings.SHOPEE_SHOP_ID, **tham_so_rieng,
    })


def gui_tiktok_da_ky(client):
    than = json.dumps({}, separators=(",", ":"))
    tham_so = {"app_key": settings.TIKTOK_APP_KEY, "timestamp": str(int(time.time())),
               "shop_cipher": settings.TIKTOK_SHOP_A_CIPHER, "page_size": "1"}
    chuoi = DUONG_DAN_SEARCH + "".join(f"{k}{tham_so[k]}" for k in sorted(tham_so)) + than
    bao = settings.TIKTOK_APP_SECRET + chuoi + settings.TIKTOK_APP_SECRET
    tham_so["sign"] = hmac.new(settings.TIKTOK_APP_SECRET.encode(), bao.encode(), hashlib.sha256).hexdigest()
    return client.post(DUONG_DAN_SEARCH, params=tham_so, content=than, headers={
        "content-type": "application/json", "x-tts-access-token": settings.TIKTOK_SHOP_A_ACCESS_TOKEN,
    })


def dem_lan_gui(ham_gui):
    so_lan = []

    def gui():
        so_lan.append(1)
        return ham_gui()
    return gui, so_lan


def test_socket_that_khong_loi(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with httpx2.Client(base_url=may_chu.url) as client:
        phan_hoi = http_retry.goi_co_thu_lai(
            lambda: gui_shopee_da_ky(client, DUONG_DAN_DETAIL, {"order_sn_list": "X"}), http_retry.phan_loai_shopee)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["error"] == ""


def test_socket_that_co_qua_tai_van_lay_duoc_ket_qua(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_FAULT_RATE=0.5, MOCK_FAULT_SEED=2026)
    tong_lan_shopee, tong_lan_tiktok = 0, 0
    with httpx2.Client(base_url=may_chu.url) as client:
        for _ in range(20):
            gui, so_lan = dem_lan_gui(lambda: gui_shopee_da_ky(client, DUONG_DAN_DETAIL, {"order_sn_list": "X"}))
            phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_shopee, so_lan_toi_da=10, ham_ngu=DongHoNgu())
            assert phan_hoi.status_code == 200 and phan_hoi.json()["error"] == ""
            tong_lan_shopee += len(so_lan)

            gui, so_lan = dem_lan_gui(lambda: gui_tiktok_da_ky(client))
            phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_tiktok, so_lan_toi_da=10, ham_ngu=DongHoNgu())
            assert phan_hoi.json()["code"] == 0
            tong_lan_tiktok += len(so_lan)
    assert tong_lan_shopee > 20 and tong_lan_tiktok > 20


def test_socket_that_qua_tai_mai_thi_bo_cuoc(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap(MOCK_FAULT_RATE=1)
    with httpx2.Client(base_url=may_chu.url) as client:
        with pytest.raises(http_retry.LoiHetLanThuLai) as loi:
            http_retry.goi_co_thu_lai(lambda: gui_shopee_da_ky(client, DUONG_DAN_DETAIL, {"order_sn_list": "X"}),
                                      http_retry.phan_loai_shopee, ham_ngu=DongHoNgu())
        assert loi.value.lan_cuoi.status_code == 429
        with pytest.raises(http_retry.LoiHetLanThuLai) as loi:
            http_retry.goi_co_thu_lai(lambda: gui_tiktok_da_ky(client), http_retry.phan_loai_tiktok, ham_ngu=DongHoNgu())
        assert loi.value.lan_cuoi.json()["code"] == 36009002


def test_socket_that_sai_chu_ky_khong_thu_lai(bat_may_chu_gia_lap):
    may_chu = bat_may_chu_gia_lap()
    with httpx2.Client(base_url=may_chu.url) as client:
        gui, so_lan = dem_lan_gui(lambda: client.get(DUONG_DAN_DETAIL, params={
            "partner_id": settings.SHOPEE_PARTNER_ID, "timestamp": int(time.time()), "sign": "sai",
            "access_token": settings.SHOPEE_ACCESS_TOKEN, "shop_id": settings.SHOPEE_SHOP_ID, "order_sn_list": "X"}))
        phan_hoi = http_retry.goi_co_thu_lai(gui, http_retry.phan_loai_shopee, ham_ngu=DongHoNgu())
    assert phan_hoi.json()["error"] == "error_sign" and len(so_lan) == 1
