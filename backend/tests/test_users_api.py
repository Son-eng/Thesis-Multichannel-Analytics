import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import lay_phien_db
from app.main import tao_ung_dung
from conftest import tieu_de_dang_nhap

pytestmark = pytest.mark.db

MAU_GIO_VN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$")
KHOA_NGUOI_DUNG = {"id", "username", "role", "created_at"}


@pytest.fixture
def admin(tao_nguoi):
    return tao_nguoi("admin.quan.tri", "admin")


@pytest.fixture
def client(phien_test, admin):
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung, headers=tieu_de_dang_nhap(admin)) as c:
        yield c


def tao(client, ten="nhan.vien.01", mat_khau="mat-khau-moi-1", vai_tro="user"):
    return client.post("/api/users", json={"username": ten, "password": mat_khau, "role": vai_tro})


def test_danh_sach_dung_khuon_khong_co_bam_mat_khau(client, admin, tao_nguoi):
    tao_nguoi("user.hai", "user")
    phan_hoi = client.get("/api/users")
    assert phan_hoi.status_code == 200
    cac_nguoi = phan_hoi.json()
    assert all(set(n) == KHOA_NGUOI_DUNG for n in cac_nguoi)
    assert all(MAU_GIO_VN.match(n["created_at"]) for n in cac_nguoi)
    assert [n["id"] for n in cac_nguoi] == sorted(n["id"] for n in cac_nguoi)
    assert {"admin.quan.tri", "user.hai"} <= {n["username"] for n in cac_nguoi}
    assert "password" not in phan_hoi.text and "$2b$" not in phan_hoi.text


def test_tao_nguoi_dung_201_va_dang_nhap_duoc(client, ket_noi_test):
    phan_hoi = tao(client)
    assert phan_hoi.status_code == 201
    nguoi = phan_hoi.json()
    assert set(nguoi) == KHOA_NGUOI_DUNG and (nguoi["username"], nguoi["role"]) == ("nhan.vien.01", "user")
    assert "mat-khau-moi-1" not in phan_hoi.text and "password" not in phan_hoi.text
    chuoi_bam = ket_noi_test.execute(text("SELECT password_hash FROM users WHERE id = :i"), {"i": nguoi["id"]}).scalar_one()
    assert chuoi_bam.startswith("$2b$") and chuoi_bam != "mat-khau-moi-1"
    dang_nhap = client.post("/api/auth/login", json={"username": "nhan.vien.01", "password": "mat-khau-moi-1"})
    assert dang_nhap.status_code == 200 and dang_nhap.json()["user"]["role"] == "user"


def test_trung_ten_la_409_username_taken(client):
    assert tao(client).status_code == 201
    phan_hoi = tao(client, mat_khau="mat-khau-khac-2")
    assert phan_hoi.status_code == 409 and phan_hoi.json()["detail"]["code"] == "username_taken"
    assert tao(client, ten="  nhan.vien.01 ").status_code == 409


@pytest.mark.parametrize("ten", ["ab", "a" * 51, "co dau cach", "tên-có-dấu", "a@b", ""])
def test_ten_dang_nhap_khong_hop_le_422(client, ten):
    phan_hoi = tao(client, ten=ten)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_username"


@pytest.mark.parametrize("mat_khau", ["", "ngan", "1234567", "a" * 73])
def test_mat_khau_khong_hop_le_422(client, mat_khau):
    phan_hoi = tao(client, mat_khau=mat_khau)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_password"


def test_vai_tro_la_422(client):
    assert tao(client, vai_tro="superuser").status_code == 422
    assert client.post("/api/users", json={"username": "abc", "password": "mat-khau-1"}).status_code == 422


def test_doi_vai_tro(client):
    ma = tao(client).json()["id"]
    phan_hoi = client.patch(f"/api/users/{ma}", json={"role": "admin"})
    assert phan_hoi.status_code == 200 and phan_hoi.json()["role"] == "admin" and set(phan_hoi.json()) == KHOA_NGUOI_DUNG
    assert client.patch(f"/api/users/{ma}", json={"role": "user"}).json()["role"] == "user"
    assert client.patch(f"/api/users/{ma}", json={"role": "x"}).status_code == 422
    assert client.patch("/api/users/999999", json={"role": "user"}).status_code == 404


def test_khong_tu_doi_vai_tro_cua_chinh_minh(client, admin):
    phan_hoi = client.patch(f"/api/users/{admin.id}", json={"role": "user"})
    assert phan_hoi.status_code == 400 and phan_hoi.json()["detail"]["code"] == "cannot_change_own_role"
    assert client.get("/api/users").status_code == 200


def test_dat_lai_mat_khau(client):
    ma = tao(client).json()["id"]
    phan_hoi = client.post(f"/api/users/{ma}/reset-password", json={"password": "mat-khau-moi-9"})
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert client.post("/api/auth/login", json={"username": "nhan.vien.01", "password": "mat-khau-moi-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "nhan.vien.01", "password": "mat-khau-moi-9"}).status_code == 200
    assert client.post(f"/api/users/{ma}/reset-password", json={"password": "ngan"}).status_code == 422
    assert client.post("/api/users/999999/reset-password", json={"password": "mat-khau-moi-9"}).status_code == 404


def test_xoa_nguoi_dung(client):
    ma = tao(client).json()["id"]
    phan_hoi = client.delete(f"/api/users/{ma}")
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""
    assert ma not in [n["id"] for n in client.get("/api/users").json()]
    assert client.post("/api/auth/login", json={"username": "nhan.vien.01", "password": "mat-khau-moi-1"}).status_code == 401
    assert client.delete(f"/api/users/{ma}").status_code == 404


def test_khong_xoa_duoc_chinh_minh(client, admin):
    phan_hoi = client.delete(f"/api/users/{admin.id}")
    assert phan_hoi.status_code == 400 and phan_hoi.json()["detail"]["code"] == "cannot_delete_self"
    assert admin.id in [n["id"] for n in client.get("/api/users").json()]


def test_khong_xoa_nguoi_da_co_lich_su_dong_bo(client, ket_noi_test):
    ma = tao(client).json()["id"]
    ket_noi_test.execute(text("INSERT INTO sync_runs (platform, shop_name, source, status, triggered_by) "
                              "VALUES ('shopee', 'Shop C', 'api', 'success', :i)"), {"i": ma})
    phan_hoi = client.delete(f"/api/users/{ma}")
    assert phan_hoi.status_code == 409 and phan_hoi.json()["detail"]["code"] == "user_has_history"
    assert ma in [n["id"] for n in client.get("/api/users").json()]
