from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import text

from app.core.deps import yeu_cau_dang_nhap
from app.database import SessionLocal
from app.main import tao_ung_dung
from app.models.user import User
from app.services.export_service import trung_hoa_cong_thuc, trung_hoa_toan_bo_o

CONG_THUC = '=HYPERLINK("http://x","y")'


@pytest.mark.parametrize("dau_vao", [CONG_THUC, "=1+1", "+cmd|' /C calc'!A0", "-2+3", "@SUM(A1:A2)", "\t=1", "\r=1", "\n=1"])
def test_chuoi_nguy_hiem_duoc_them_dau_nhay(dau_vao):
    assert trung_hoa_cong_thuc(dau_vao) == "'" + dau_vao


@pytest.mark.parametrize("gia_tri", ["Shop C", "M15", "Hà Nội", "", " =sau dấu cách", "a=b", "Doanh thu (đ)", 840035154, -30.5, 0, 0.0, None, True])
def test_gia_tri_an_toan_va_so_khong_bi_dong_den(gia_tri):
    assert trung_hoa_cong_thuc(gia_tri) is gia_tri or trung_hoa_cong_thuc(gia_tri) == gia_tri


def test_so_am_la_so_khong_phai_chuoi_nen_khong_them_dau_nhay():
    ket_qua = trung_hoa_cong_thuc(-30.5)
    assert ket_qua == -30.5 and not isinstance(ket_qua, str)


def test_o_cong_thuc_cua_openpyxl_duoc_tra_ve_van_ban():
    sổ = Workbook()
    sheet = sổ.active
    sheet["A1"] = CONG_THUC
    sheet["A2"] = "bình thường"
    sheet["A3"] = -5
    assert sheet["A1"].data_type == "f"
    trung_hoa_toan_bo_o(sổ)
    assert sheet["A1"].data_type == "s" and sheet["A1"].value == "'" + CONG_THUC
    assert sheet["A2"].value == "bình thường" and sheet["A3"].value == -5


@pytest.fixture(scope="module")
def client():
    with SessionLocal() as phien:
        for san, so_dong in (("shopee", 1774), ("tiktok", 7540)):
            if phien.execute(text("SELECT count(*) FROM orders WHERE platform = :p"), {"p": san}).scalar_one() != so_dong:
                pytest.skip(f"orders ({san}) chưa nạp đủ dữ liệu mẫu")
    app = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    app.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=-1, username="nguoi_thu", role="user")
    with TestClient(app) as c:
        yield c


def tat_ca_o(sổ):
    return [o for sheet in sổ.worksheets for hang in sheet.iter_rows() for o in hang if o.value is not None]


@pytest.mark.db
def test_ten_gian_hang_la_cong_thuc_thanh_van_ban_va_khong_co_o_cong_thuc_nao(client):
    phan_hoi = client.get("/api/export/tiktok/excel", params={"granularity": "month", "period": "2026-08", "shop_name": CONG_THUC})
    assert phan_hoi.status_code == 200
    sổ = load_workbook(BytesIO(phan_hoi.content))
    o_gian_hang = next(r[1] for r in sổ["Tổng quan"].iter_rows() if r[0].value == "Gian hàng")
    assert o_gian_hang.value == "'" + CONG_THUC
    assert o_gian_hang.data_type == "s"
    assert [o.coordinate for o in tat_ca_o(sổ) if o.data_type == "f"] == []


@pytest.mark.db
def test_ma_san_pham_la_cong_thuc_cung_duoc_che(client):
    phan_hoi = client.get("/api/export/shopee/excel", params={"granularity": "month", "period": "2026-08", "product_code": "=1+1"})
    sổ = load_workbook(BytesIO(phan_hoi.content))
    o = next(r[1] for r in sổ["Tổng quan"].iter_rows() if r[0].value == "Mã sản phẩm")
    assert o.value == "'=1+1" and o.data_type == "s"


@pytest.mark.db
@pytest.mark.parametrize("san, muc, ky", [("shopee", "month", "2026-08"), ("tiktok", "month", "2026-04"), ("tiktok", "year", "2026")])
def test_xuat_binh_thuong_khong_co_o_cong_thuc_va_so_lieu_khong_doi(client, san, muc, ky):
    sổ = load_workbook(BytesIO(client.get(f"/api/export/{san}/excel", params={"granularity": muc, "period": ky}).content))
    assert [o.coordinate for o in tat_ca_o(sổ) if o.data_type == "f"] == []
    hang = next(r for r in sổ["Tổng quan"].iter_rows() if r[0].value == "Doanh thu (đ)")
    chuan = {("shopee", "2026-08"): (840035154, 624277755, 34.6), ("tiktok", "2026-04"): (1014538449, 1459153482, -30.5),
             ("tiktok", "2026"): (7538502584, None, None)}[(san, ky)]
    assert (hang[1].value, hang[2].value, hang[3].value) == chuan
    assert isinstance(hang[3].value, (int, float)) or hang[3].value is None


@pytest.mark.db
def test_khong_o_chuoi_nao_bat_dau_bang_ky_tu_nguy_hiem_ma_thieu_dau_nhay(client):
    phan_hoi = client.get("/api/export/tiktok/excel", params={"granularity": "month", "period": "2026-08", "shop_name": "=A1"})
    sổ = load_workbook(BytesIO(phan_hoi.content))
    for o in tat_ca_o(sổ):
        if isinstance(o.value, str):
            assert not o.value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")), (o.coordinate, o.value)
