"""Test 3 endpoint TikTok qua tầng HTTP bằng TestClient (SPEC §19.2, §19.3, §19.4).

Như test Shopee: mỗi yêu cầu được ký đúng thuật toán TikTok (đường dẫn + query
sắp xếp + body, bọc app_secret) như một client thật, rồi sửa từng thành phần
để xem máy chủ từ chối đúng mã. Mã 9990xxx là mã quy ước của bản giả lập
(§19.2, §16 mục 7).

Số kỳ vọng tính thẳng từ CSV ẩn danh theo từng shop, cộng các số đã chốt:
7.526 đơn, 7.540 dòng (§17.1), 139 dòng hoàn (§3.2).
"""

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import data_builder
import signature
import tiktok_routes

GIO_VN = timezone(timedelta(hours=7))
# "Bây giờ" của máy chủ: sau toàn bộ dữ liệu mẫu TikTok (01/01–23/08/2026).
T0 = int(datetime(2026, 9, 1, tzinfo=GIO_VN).timestamp())
DAU_NAM = int(datetime(2026, 1, 1, tzinfo=GIO_VN).timestamp())

DUONG_DAN_SEARCH = "/order/202309/orders/search"
DUONG_DAN_REFRESH = "/api/v2/token/refresh"


def duong_dan_finance(ma_don):
    return f"/finance/202501/orders/{ma_don}/statement_transactions"


@pytest.fixture
def dong_ho():
    return {"bay_gio": T0}


@pytest.fixture
def client(tao_client, cau_hinh, dong_ho):
    return tao_client(cau_hinh, dong_ho)


@pytest.fixture(scope="module")
def csv_tiktok():
    return pd.read_csv(data_builder.FILE_TIKTOK, dtype=str)


class KhachTikTok:
    """Client TikTok tối giản trong test: tự ký mọi yêu cầu open-api của một shop."""

    def __init__(self, client, cau_hinh, dong_ho, shop_cipher, access_token):
        self.client = client
        self.cau_hinh = cau_hinh
        self.dong_ho = dong_ho
        self.shop_cipher = shop_cipher
        self.access_token = access_token

    def goi(self, phuong_thuc, duong_dan, tham_so_rieng=None, than=None, sua_sau_khi_ky=None, **sua):
        """Gửi một yêu cầu đã ký, trả JSON.

        `sua`: ghi đè tham số query TRƯỚC khi ký (chữ ký vẫn đúng với giá trị đã sửa).
        `sua_sau_khi_ky`: ghi đè SAU khi ký (để làm chữ ký sai, hoặc xóa tham số khi giá trị là None).
        `than`: dict → serialize MỘT lần, dùng cùng chuỗi đó để ký và để gửi (bẫy §20.1).
        """
        tham_so = {
            "app_key": self.cau_hinh.TIKTOK_APP_KEY,
            "timestamp": str(self.dong_ho["bay_gio"]),
            "shop_cipher": self.shop_cipher,
            **(tham_so_rieng or {}),
            **{khoa: str(gia_tri) for khoa, gia_tri in sua.items()},
        }
        chuoi_than = "" if than is None else (than if isinstance(than, str) else json.dumps(than, separators=(",", ":")))
        tham_so["sign"] = signature.tinh_chu_ky_tiktok(self.cau_hinh.TIKTOK_APP_SECRET, duong_dan, tham_so, chuoi_than)
        for khoa, gia_tri in (sua_sau_khi_ky or {}).items():
            if gia_tri is None:
                tham_so.pop(khoa, None)
            else:
                tham_so[khoa] = gia_tri
        phan_hoi = self.client.request(
            phuong_thuc, duong_dan, params=tham_so, content=chuoi_than,
            headers={"content-type": "application/json", "x-tts-access-token": self.access_token},
        )
        assert phan_hoi.status_code == 200
        return phan_hoi.json()

    def tim_don(self, than=None, sua_sau_khi_ky=None, **sua):
        return self.goi("POST", DUONG_DAN_SEARCH, {"page_size": "100"}, than or {}, sua_sau_khi_ky, **sua)

    def keo_het(self, than, page_size=100, **tham_so):
        """Đi hết page_token, trả danh sách đơn theo đúng thứ tự trả về."""
        cac_don = []
        page_token = ""
        while True:
            phan_hoi = self.goi(
                "POST", DUONG_DAN_SEARCH, {"page_size": str(page_size), "page_token": page_token, **tham_so}, than
            )
            assert phan_hoi["code"] == 0, phan_hoi
            cac_don += phan_hoi["data"]["orders"]
            page_token = phan_hoi["data"]["next_page_token"]
            if page_token == "":
                return cac_don


@pytest.fixture
def khach_a(client, cau_hinh, dong_ho, du_lieu_tiktok):
    return KhachTikTok(client, cau_hinh, dong_ho, du_lieu_tiktok["Shop A"]["shop_cipher"], cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN)


@pytest.fixture
def khach_b(client, cau_hinh, dong_ho, du_lieu_tiktok):
    return KhachTikTok(client, cau_hinh, dong_ho, du_lieu_tiktok["Shop B"]["shop_cipher"], cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN)


# ---------- Kéo đủ dữ liệu theo từng shop ----------

@pytest.mark.parametrize("ten_shop", ["Shop A", "Shop B"])
def test_keo_du_moi_don_va_finance_theo_shop(ten_shop, request, csv_tiktok):
    khach = request.getfixturevalue("khach_a" if ten_shop == "Shop A" else "khach_b")
    csv_shop = csv_tiktok[csv_tiktok["Shop"] == ten_shop]

    cac_don = khach.keo_het({"create_time_ge": DAU_NAM, "create_time_lt": T0}, sort_order="ASC")
    ma_don = [don["id"] for don in cac_don]
    assert len(ma_don) == len(set(ma_don)) == csv_shop["Order ID"].nunique()
    # Số dòng chuẩn = số cặp (đơn, sku_id) khác nhau; số line item = tổng Quantity.
    so_dong = len({(don["id"], li["sku_id"]) for don in cac_don for li in don["line_items"]})
    assert so_dong == len(csv_shop)
    assert sum(len(don["line_items"]) for don in cac_don) == pd.to_numeric(csv_shop["Quantity"]).sum()

    dong_hoan = []
    for don in cac_don:
        if don["status"] != "COMPLETED":
            continue        # §20.2: chỉ gọi Finance cho đơn COMPLETED
        phan_hoi = khach.goi("GET", duong_dan_finance(don["id"]))
        assert phan_hoi["code"] == 0
        for gd in phan_hoi["data"]["sku_transactions"]:
            if gd["revenue_breakdown"]["refund_subtotal_before_discount_amount"] != "0":
                dong_hoan.append((don["id"], gd["sku_id"]))
    hoan_csv = csv_shop[csv_shop["Cancelation/Return Type"] == "Return/Refund"]
    assert sorted(dong_hoan) == sorted(zip(hoan_csv["Order ID"], hoan_csv["SKU ID"]))


def test_tong_hai_shop_khop_so_da_chot(khach_a, khach_b, csv_tiktok):
    """Cộng 2 shop ra đúng số đã chốt §17.1; tổng dòng hoàn của 2 shop là 139 (test trên kiểm từng dòng)."""
    khoang = {"create_time_ge": DAU_NAM, "create_time_lt": T0}
    cac_don = khach_a.keo_het(khoang) + khach_b.keo_het(khoang)
    assert len(cac_don) == 7526
    assert len({(don["id"], li["sku_id"]) for don in cac_don for li in don["line_items"]}) == 7540
    assert (csv_tiktok["Cancelation/Return Type"] == "Return/Refund").sum() == 139


# ---------- orders/search: lọc, sắp xếp, phân trang ----------

def test_ge_lay_moc_lt_khong_lay_moc(khach_a, du_lieu_tiktok):
    """Tài liệu: `_ge` = "on or after", `_lt` = "before"."""
    don = next(iter(du_lieu_tiktok["Shop A"]["don_hang"].values()))
    moc = don["create_time"]
    co = [d["id"] for d in khach_a.keo_het({"create_time_ge": moc, "create_time_lt": moc + 1})]
    assert don["id"] in co
    khong = [d["id"] for d in khach_a.keo_het({"create_time_ge": moc - 100, "create_time_lt": moc})]
    assert don["id"] not in khong


def test_loc_update_time_va_trang_thai(khach_a):
    khoang = {"update_time_ge": DAU_NAM, "update_time_lt": DAU_NAM + 30 * 86400, "order_status": "CANCELLED"}
    cac_don = khach_a.keo_het(khoang)
    assert cac_don
    assert all(d["status"] == "CANCELLED" and DAU_NAM <= d["update_time"] < DAU_NAM + 30 * 86400 for d in cac_don)


def test_chi_co_ge_thi_lt_mac_dinh_la_bay_gio(khach_a, dong_ho):
    dong_ho["bay_gio"] = DAU_NAM + 10 * 86400
    cac_don = khach_a.keo_het({"create_time_ge": DAU_NAM})
    assert cac_don and all(d["create_time"] < DAU_NAM + 10 * 86400 for d in cac_don)


def test_sap_xep_mac_dinh_moi_nhat_truoc_va_phan_trang_on_dinh(khach_a):
    khoang = {"create_time_ge": DAU_NAM, "create_time_lt": DAU_NAM + 20 * 86400}
    ca_trang = khach_a.keo_het(khoang)
    tung_trang = khach_a.keo_het(khoang, page_size=7)
    assert [d["id"] for d in tung_trang] == [d["id"] for d in ca_trang]
    thoi_gian = [d["create_time"] for d in ca_trang]
    assert thoi_gian == sorted(thoi_gian, reverse=True)       # mặc định DESC theo create_time


def test_total_count_va_trang_cuoi(khach_a):
    phan_hoi = khach_a.tim_don({"create_time_ge": DAU_NAM, "create_time_lt": DAU_NAM + 86400})
    du_lieu = phan_hoi["data"]
    assert du_lieu["total_count"] == len(du_lieu["orders"]) < 100
    assert du_lieu["next_page_token"] == ""


def test_don_tra_ve_du_khuon_21_2(khach_a):
    don = khach_a.tim_don({"create_time_ge": DAU_NAM, "create_time_lt": T0})["data"]["orders"][0]
    assert set(don) >= {"id", "status", "create_time", "update_time", "payment", "recipient_address", "line_items"}
    assert set(don["line_items"][0]) >= {"sku_id", "seller_sku", "original_price", "sale_price", "seller_discount"}


# ---------- Finance ----------

def test_finance_don_chua_completed_tra_rong(khach_a, du_lieu_tiktok):
    """Phương án (a), §16 mục 5: code 0, sku_transactions rỗng, total_count 0."""
    don = next(d for d in du_lieu_tiktok["Shop A"]["don_hang"].values() if d["status"] != "COMPLETED")
    phan_hoi = khach_a.goi("GET", duong_dan_finance(don["id"]))
    assert phan_hoi["code"] == 0
    assert phan_hoi["data"]["sku_transactions"] == []
    assert phan_hoi["data"]["total_count"] == 0


def test_finance_don_completed(khach_a, du_lieu_tiktok):
    ma_don, giao_dich = next(iter(du_lieu_tiktok["Shop A"]["finance"].items()))
    du_lieu = khach_a.goi("GET", duong_dan_finance(ma_don))["data"]
    assert du_lieu["order_id"] == ma_don
    assert du_lieu["sku_transactions"] == giao_dich
    assert du_lieu["total_count"] == len(giao_dich)


def test_finance_ky_theo_duong_dan_co_order_id(khach_a, du_lieu_tiktok):
    """Ký bằng đường dẫn của đơn khác → sai chữ ký: order_id nằm trong chuỗi ký."""
    ma_1, ma_2 = list(du_lieu_tiktok["Shop A"]["finance"])[:2]
    tham_so = {
        "app_key": khach_a.cau_hinh.TIKTOK_APP_KEY, "timestamp": str(T0), "shop_cipher": khach_a.shop_cipher,
    }
    tham_so["sign"] = signature.tinh_chu_ky_tiktok(khach_a.cau_hinh.TIKTOK_APP_SECRET, duong_dan_finance(ma_1), tham_so)
    phan_hoi = khach_a.client.get(
        duong_dan_finance(ma_2), params=tham_so, headers={"x-tts-access-token": khach_a.access_token}
    ).json()
    assert phan_hoi["code"] == tiktok_routes.MA_SAI_CHU_KY


# ---------- Xác thực và giới hạn tham số ----------

@pytest.mark.parametrize("page_size", ["101", "0", "muoi"])
def test_page_size_ngoai_khoang(khach_a, page_size):
    assert khach_a.goi("POST", DUONG_DAN_SEARCH, {"page_size": page_size}, {})["code"] == tiktok_routes.MA_THAM_SO_SAI


def test_page_size_100_hop_le(khach_a):
    assert khach_a.goi("POST", DUONG_DAN_SEARCH, {"page_size": "100"}, {})["code"] == 0


@pytest.mark.parametrize("tham_so", [{"sort_field": "pay_time"}, {"sort_order": "UP"}, {"page_token": "abc"}])
def test_tham_so_sap_xep_va_page_token_la(khach_a, tham_so):
    assert khach_a.tim_don({}, **tham_so)["code"] == tiktok_routes.MA_THAM_SO_SAI


@pytest.mark.parametrize("than", ["khong phai json", "[1,2]", {"create_time_ge": "hom nay"}])
def test_body_sai(khach_a, than):
    assert khach_a.goi("POST", DUONG_DAN_SEARCH, {"page_size": "10"}, than)["code"] == tiktok_routes.MA_THAM_SO_SAI


def test_sai_chu_ky(khach_a):
    assert khach_a.tim_don({}, sua_sau_khi_ky={"sign": "0" * 64})["code"] == tiktok_routes.MA_SAI_CHU_KY


def test_body_serialize_lai_la_sai_chu_ky(khach_a):
    """Ký trên '{"a":1}' nhưng gửi '{"a": 1}' → sai chữ ký (bẫy §20.1)."""
    tham_so = {"app_key": khach_a.cau_hinh.TIKTOK_APP_KEY, "timestamp": str(T0),
               "shop_cipher": khach_a.shop_cipher, "page_size": "10"}
    tham_so["sign"] = signature.tinh_chu_ky_tiktok(
        khach_a.cau_hinh.TIKTOK_APP_SECRET, DUONG_DAN_SEARCH, tham_so, '{"order_status":"COMPLETED"}'
    )
    phan_hoi = khach_a.client.post(
        DUONG_DAN_SEARCH, params=tham_so, content='{"order_status": "COMPLETED"}',
        headers={"content-type": "application/json", "x-tts-access-token": khach_a.access_token},
    ).json()
    assert phan_hoi["code"] == tiktok_routes.MA_SAI_CHU_KY


def test_timestamp_lech(khach_a):
    assert khach_a.tim_don({}, timestamp=T0 - 301)["code"] == tiktok_routes.MA_LECH_THOI_GIAN
    assert khach_a.tim_don({}, timestamp=T0 - 300)["code"] == 0


def test_thieu_tham_so_chung_hoac_app_key_sai(khach_a):
    assert khach_a.tim_don({}, sua_sau_khi_ky={"shop_cipher": None})["code"] == tiktok_routes.MA_THAM_SO_SAI
    assert khach_a.tim_don({}, app_key="khac")["code"] == tiktok_routes.MA_THAM_SO_SAI


def test_token_sai_va_token_cua_shop_khac(khach_a, cau_hinh):
    khach_a.access_token = "token_bia"
    assert khach_a.tim_don({})["code"] == tiktok_routes.MA_TOKEN_SAI
    # Token của Shop B gửi kèm shop_cipher của Shop A.
    khach_a.access_token = cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN
    assert khach_a.tim_don({})["code"] == tiktok_routes.MA_TOKEN_SAI


def test_token_het_han_sau_7_ngay(khach_a, dong_ho):
    dong_ho["bay_gio"] = T0 + 7 * 86400 - 1
    assert khach_a.tim_don({})["code"] == 0
    dong_ho["bay_gio"] = T0 + 7 * 86400
    assert khach_a.tim_don({})["code"] == tiktok_routes.MA_TOKEN_HET_HAN


def test_phan_hoi_dung_khuon(khach_a):
    thanh_cong = khach_a.tim_don({})
    assert set(thanh_cong) == {"code", "message", "request_id", "data"}
    loi = khach_a.tim_don({}, sua_sau_khi_ky={"sign": "sai"})
    assert set(loi) == {"code", "message", "request_id"} and loi["request_id"]


# ---------- token/refresh ----------

def lam_moi(client, cau_hinh, refresh_token, **sua):
    tham_so = {"app_key": cau_hinh.TIKTOK_APP_KEY, "app_secret": cau_hinh.TIKTOK_APP_SECRET,
               "refresh_token": refresh_token, "grant_type": "refresh_token", **sua}
    phan_hoi = client.get(DUONG_DAN_REFRESH, params=tham_so)
    assert phan_hoi.status_code == 200
    return phan_hoi.json()


def test_lam_moi_cap_token_moi_dung_duoc(khach_a, cau_hinh):
    phan_hoi = lam_moi(khach_a.client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)
    assert phan_hoi["code"] == 0
    assert set(phan_hoi["data"]) == {"access_token", "refresh_token"}     # đúng như SDK thể hiện
    khach_a.access_token = phan_hoi["data"]["access_token"]
    assert khach_a.tim_don({})["code"] == 0


def test_lam_moi_dung_shop_cua_refresh_token(khach_b, cau_hinh):
    """Refresh của Shop A cấp token cho Shop A — dùng với shop_cipher Shop B bị từ chối."""
    khach_b.access_token = lam_moi(khach_b.client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)["data"]["access_token"]
    assert khach_b.tim_don({})["code"] == tiktok_routes.MA_TOKEN_SAI


def test_refresh_cu_van_dung_lai_duoc(client, cau_hinh, dong_ho):
    """TikTok: tài liệu không nói refresh cũ bị vô hiệu, refresh sống tới 2123 (§19.3 mục 3)."""
    assert lam_moi(client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)["code"] == 0
    dong_ho["bay_gio"] = T0 + 10 * 365 * 86400
    assert lam_moi(client, cau_hinh, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN)["code"] == 0


@pytest.mark.parametrize("sua, ma", [
    ({"refresh_token": "bia"}, tiktok_routes.MA_REFRESH_SAI),
    ({"app_secret": "sai"}, tiktok_routes.MA_REFRESH_SAI),
    ({"app_key": "sai"}, tiktok_routes.MA_REFRESH_SAI),
    ({"grant_type": "authorized_code"}, tiktok_routes.MA_THAM_SO_SAI),
    ({"refresh_token": ""}, tiktok_routes.MA_THAM_SO_SAI),
])
def test_lam_moi_bi_tu_choi(client, cau_hinh, sua, ma):
    tham_so = {"refresh_token": cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN, **sua}
    assert lam_moi(client, cau_hinh, **tham_so)["code"] == ma


def test_ma_quy_uoc_khong_trung_ma_that():
    cac_ma = [tiktok_routes.MA_SAI_CHU_KY, tiktok_routes.MA_LECH_THOI_GIAN, tiktok_routes.MA_TOKEN_SAI,
              tiktok_routes.MA_TOKEN_HET_HAN, tiktok_routes.MA_THAM_SO_SAI, tiktok_routes.MA_REFRESH_SAI]
    assert len(set(cac_ma)) == 6
    assert not {36009002, 36009003} & set(cac_ma)
    assert all(str(ma).startswith("9990") for ma in cac_ma)
    assert Counter(len(str(ma)) for ma in cac_ma) == {7: 6}


# ---------- affiliate_seller/orders/search ----------

DUONG_DAN_AFFILIATE = "/affiliate_seller/202410/orders/search"


def keo_het_affiliate(khach, than, page_size=100):
    cac_don, page_token = [], ""
    while True:
        phan_hoi = khach.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": str(page_size), "page_token": page_token}, than)
        assert phan_hoi["code"] == 0, phan_hoi
        cac_don += phan_hoi["data"]["orders"]
        page_token = phan_hoi["data"]["next_page_token"]
        if page_token == "":
            return cac_don


@pytest.mark.parametrize("ten_shop, so_dong", [("Shop A", 2763), ("Shop B", 1534)])
def test_affiliate_keo_du_theo_shop(request, du_lieu_tiktok, ten_shop, so_dong):
    khach = request.getfixturevalue("khach_a" if ten_shop == "Shop A" else "khach_b")
    # 3 tháng/yêu cầu (tài liệu) → chia cửa sổ 90 ngày [ge, lt) nối tiếp như connector sẽ làm.
    cac_don, ge = [], DAU_NAM
    while ge < T0:
        lt = min(ge + 90 * 86400, T0)
        cac_don += keo_het_affiliate(khach, {"create_time_ge": ge, "create_time_lt": lt})
        ge = lt
    ma_don = [d["id"] for d in cac_don]
    assert len(ma_don) == len(set(ma_don))
    cap = {(d["id"], s["sku_id"]) for d in cac_don for s in d["skus"]}
    mong_doi = {(ma, sku_id) for ma, muc in du_lieu_tiktok[ten_shop]["affiliate"].items() for sku_id in muc["skus"]}
    assert len(cap) == so_dong and cap == mong_doi


def test_affiliate_vuot_3_thang_bi_tu_choi(khach_a):
    qua = {"create_time_ge": DAU_NAM, "create_time_lt": DAU_NAM + 94 * 86400}
    assert khach_a.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": "10"}, qua)["code"] == tiktok_routes.MA_THAM_SO_SAI
    dung = {"create_time_ge": DAU_NAM, "create_time_lt": DAU_NAM + 93 * 86400}
    assert khach_a.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": "10"}, dung)["code"] == 0


def test_affiliate_ranh_gioi_ge_lt(khach_a, du_lieu_tiktok):
    ma_x, muc = next((m, v) for m, v in du_lieu_tiktok["Shop A"]["affiliate"].items()
                     if v["create_time"] > DAU_NAM + 30 * 86400)
    moc = muc["create_time"]

    def ma(than):
        return [d["id"] for d in keo_het_affiliate(khach_a, than)]
    assert ma_x in ma({"create_time_ge": moc, "create_time_lt": moc + 1})
    assert ma_x not in ma({"create_time_ge": moc - 100, "create_time_lt": moc})        # _lt không lấy mốc


def test_affiliate_mac_dinh_ba_thang_gan_nhat_va_khong_lo_pii(khach_a, dong_ho):
    dong_ho["bay_gio"] = DAU_NAM + 30 * 86400
    cac_don = keo_het_affiliate(khach_a, {})
    assert cac_don
    assert all(dong_ho["bay_gio"] - 93 * 86400 <= d["create_time"] < dong_ho["bay_gio"] for d in cac_don)
    assert "creator_username" not in json.dumps(cac_don)


@pytest.mark.parametrize("page_size", ["101", "0", "muoi"])
def test_affiliate_page_size_ngoai_khoang(khach_a, page_size):
    assert khach_a.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": page_size}, {})["code"] == tiktok_routes.MA_THAM_SO_SAI


def test_affiliate_van_kiem_chu_ky_va_token(khach_a):
    ket_qua = khach_a.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": "10"}, {}, sua_sau_khi_ky={"sign": "0" * 64})
    assert ket_qua["code"] == tiktok_routes.MA_SAI_CHU_KY
    khach_a.access_token = "bia"
    assert khach_a.goi("POST", DUONG_DAN_AFFILIATE, {"page_size": "10"}, {})["code"] == tiktok_routes.MA_TOKEN_SAI
