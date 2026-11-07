"""Test đăng nhập, phân quyền và quản lý người dùng (SPEC §11, §12.1.4.1–§12.1.4.2).

CSDL thật trong giao dịch rollback (người dùng tạo trong test tự biến mất). Token là JWT thật; bcrypt hạ còn 4 vòng
(conftest). Điểm cần chứng minh: sai tên và sai mật khẩu giống hệt nhau, mọi endpoint đòi token, endpoint quản trị
đòi admin, mật khẩu chỉ lưu dạng băm và không bao giờ trả ra.
"""

import re
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.core import security
from app.database import lay_phien_db
from app.main import tao_ung_dung
from app.models.user import User
from app.services import token_store, user_service
from conftest import tieu_de_dang_nhap

pytestmark = pytest.mark.db

MAU_GIO_VN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$")
THONG_BAO_SAI = {"code": "invalid_credentials", "message": "Tên đăng nhập hoặc mật khẩu không đúng"}


@pytest.fixture
def client(phien_test, ket_noi_test, tao_phien_test, monkeypatch):
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    # Hàm chạy nền giả PHẢI nhả khóa advisory mà POST /api/sync đã giành, nếu không khóa treo đến hết phiên
    # pytest và làm hỏng các test đồng bộ chạy sau (đã gặp ở lần chạy đủ đầu tiên của chỉ dẫn 017).
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False,
                            ham_chay_nen=lambda cac_shop, cac_khoa, cac_run_id: [k.nha() for k in cac_khoa])
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung) as c:
        yield c


def dang_nhap(client, ten, mat_khau):
    return client.post("/api/auth/login", json={"username": ten, "password": mat_khau})


# ---------------------------------------------------------------- đăng nhập

def test_dang_nhap_dung_tra_token_va_thong_tin_khong_co_bam(client, tao_nguoi):
    nguoi = tao_nguoi("nguyen.van.a", "user", "mat-khau-dung-1")
    phan_hoi = dang_nhap(client, "nguyen.van.a", "mat-khau-dung-1")
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert set(du_lieu) == {"access_token", "token_type", "user"} and du_lieu["token_type"] == "bearer"
    assert du_lieu["user"] == {"id": nguoi.id, "username": "nguyen.van.a", "role": "user"}
    assert security.doc_token(du_lieu["access_token"]) == nguoi.id
    assert "password" not in phan_hoi.text and "$2b$" not in phan_hoi.text


def test_sai_mat_khau_va_sai_ten_dang_nhap_cung_mot_phan_hoi(client, tao_nguoi):
    tao_nguoi("co_that", "user", "mat-khau-dung-1")
    sai_mat_khau = dang_nhap(client, "co_that", "mat-khau-sai-99")
    sai_ten = dang_nhap(client, "khong_ton_tai", "mat-khau-dung-1")
    assert sai_mat_khau.status_code == sai_ten.status_code == 401
    assert sai_mat_khau.json() == sai_ten.json() == {"detail": THONG_BAO_SAI}


def test_ten_khong_ton_tai_van_ton_mot_lan_kiem_bcrypt(client, monkeypatch):
    """Chống dò tên: nhánh "không có người dùng" vẫn chạy một lần kiểm bcrypt như nhánh có người dùng."""
    da_goi = []
    monkeypatch.setattr(security, "kiem_gia_de_dong_deu_thoi_gian", lambda mk: da_goi.append(mk))
    dang_nhap(client, "ten_khong_co", "abc12345")
    assert da_goi == ["abc12345"]


def test_ten_dang_nhap_phan_biet_va_bo_khoang_trang_hai_dau(client, tao_nguoi):
    tao_nguoi("ten.chuan", "user", "mat-khau-dung-1")
    assert dang_nhap(client, "  ten.chuan  ", "mat-khau-dung-1").status_code == 200
    assert dang_nhap(client, "TEN.CHUAN", "mat-khau-dung-1").status_code == 401


def test_thieu_truong_tra_422(client):
    assert client.post("/api/auth/login", json={"username": "x"}).status_code == 422


def test_me_va_logout(client, tao_nguoi):
    nguoi = tao_nguoi("nguoi.dung", "user")
    tieu_de = tieu_de_dang_nhap(nguoi)
    assert client.get("/api/auth/me", headers=tieu_de).json() == {"id": nguoi.id, "username": "nguoi.dung", "role": "user"}
    phan_hoi = client.post("/api/auth/logout", headers=tieu_de)
    assert phan_hoi.status_code == 204 and phan_hoi.content == b""


def test_mat_khau_luu_dang_bam_khong_phai_ban_ro(client, tao_nguoi, ket_noi_test):
    tao_nguoi("co_bam", "user", "mat-khau-ro-123")
    chuoi_bam = ket_noi_test.execute(text("SELECT password_hash FROM users WHERE username = 'co_bam'")).scalar_one()
    assert chuoi_bam != "mat-khau-ro-123" and chuoi_bam.startswith("$2b$") and "mat-khau-ro-123" not in chuoi_bam
    assert security.kiem_mat_khau("mat-khau-ro-123", chuoi_bam) and not security.kiem_mat_khau("mat-khau-khac-1", chuoi_bam)


# ---------------------------------------------------------------- token

def test_token_dung_khoa_khac_het_han_va_gia_deu_bi_tu_choi(client, tao_nguoi):
    nguoi = tao_nguoi("nguoi.dung", "user")
    bay_gio = datetime.now(timezone.utc)
    het_han = security.tao_token(nguoi.id, bay_gio=bay_gio - timedelta(minutes=settings.JWT_EXPIRE_MINUTES + 5))
    khoa_khac = jwt.encode({"sub": str(nguoi.id), "exp": bay_gio + timedelta(hours=1)},
                           "khoa-khac-hoan-toan-dai-hon-32-ky-tu-abcdef", algorithm="HS256")
    khong_ky = jwt.encode({"sub": str(nguoi.id), "exp": bay_gio + timedelta(hours=1)}, key=None, algorithm="none")
    khong_co_han = jwt.encode({"sub": str(nguoi.id)}, settings.JWT_SECRET, algorithm="HS256")
    sub_la = jwt.encode({"sub": "khong-phai-so", "exp": bay_gio + timedelta(hours=1)}, settings.JWT_SECRET, algorithm="HS256")
    for token in (het_han, khoa_khac, khong_ky, khong_co_han, sub_la, "rac.rac.rac", ""):
        phan_hoi = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert phan_hoi.status_code == 401, token[:30]
        assert phan_hoi.json()["detail"]["code"] == "not_authenticated"


def test_token_cua_nguoi_da_bi_xoa_khong_con_dung_duoc(client, tao_nguoi, tieu_de_admin, phien_test):
    nguoi = tao_nguoi("sap.bi.xoa", "user")
    tieu_de = tieu_de_dang_nhap(nguoi)
    assert client.get("/api/auth/me", headers=tieu_de).status_code == 200
    assert client.delete(f"/api/users/{nguoi.id}", headers=tieu_de_admin).status_code == 204
    assert client.get("/api/auth/me", headers=tieu_de).status_code == 401


def test_doi_vai_tro_co_hieu_luc_ngay_voi_token_dang_dung(client, tao_nguoi, phien_test):
    nguoi = tao_nguoi("dang.la.admin", "admin")
    tieu_de = tieu_de_dang_nhap(nguoi)
    assert client.get("/api/users", headers=tieu_de).status_code == 200
    nguoi.role = "user"
    phien_test.flush()
    assert client.get("/api/users", headers=tieu_de).status_code == 403          # token cũ, vai trò mới


def test_khong_co_token_hoac_sai_kieu_bearer_la_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Basic YWJjOmRlZg=="}).status_code == 401


# ---------------------------------------------------------------- mọi endpoint đòi đăng nhập / quản trị đòi admin

DOC = [("GET", "/api/shopee/filters"), ("GET", "/api/tiktok/kpi"), ("GET", "/api/shopee/revenue-trend"),
       ("GET", "/api/tiktok/top-products"), ("GET", "/api/shopee/by-affiliate"), ("GET", "/api/tiktok/by-province"),
       ("GET", "/api/shopee/by-hour"), ("GET", "/api/tiktok/alerts"), ("GET", "/api/compare/platforms"),
       ("GET", "/api/sync/status"), ("GET", "/api/sync/runs"), ("GET", "/api/watcher/status"),
       ("GET", "/api/auth/me"), ("POST", "/api/auth/logout")]
QUAN_TRI = [("POST", "/api/sync/shopee"), ("POST", "/api/upload/tiktok"), ("GET", "/api/users"),
            ("POST", "/api/users"), ("PATCH", "/api/users/1"), ("POST", "/api/users/1/reset-password"),
            ("DELETE", "/api/users/1")]


@pytest.mark.parametrize("phuong_thuc, duong_dan", DOC + QUAN_TRI)
def test_khong_token_la_401_moi_endpoint(client, phuong_thuc, duong_dan):
    phan_hoi = client.request(phuong_thuc, duong_dan)
    assert phan_hoi.status_code == 401, (phuong_thuc, duong_dan)
    assert phan_hoi.json()["detail"]["code"] == "not_authenticated"


@pytest.mark.parametrize("phuong_thuc, duong_dan", QUAN_TRI)
def test_user_thuong_goi_endpoint_quan_tri_la_403(client, tieu_de_user, phuong_thuc, duong_dan):
    phan_hoi = client.request(phuong_thuc, duong_dan, headers=tieu_de_user)
    assert phan_hoi.status_code == 403, (phuong_thuc, duong_dan)
    assert phan_hoi.json()["detail"]["code"] == "forbidden"


@pytest.mark.parametrize("duong_dan", ["/api/sync/status", "/api/sync/runs", "/api/watcher/status"])
def test_user_thuong_doc_duoc_du_lieu(client, tieu_de_user, duong_dan):
    assert client.get(duong_dan, headers=tieu_de_user).status_code == 200


def test_user_thuong_doc_dashboard_va_admin_cung_duoc(client, tieu_de_user, tieu_de_admin):
    assert client.get("/api/shopee/filters", headers=tieu_de_user).status_code == 200
    assert client.get("/api/compare/platforms", headers=tieu_de_admin).status_code == 200


def test_admin_bam_nut_dong_bo_ghi_triggered_by(client, tao_nguoi, ket_noi_test):
    admin = tao_nguoi("admin.bam.nut", "admin")
    assert client.post("/api/sync/tiktok", headers=tieu_de_dang_nhap(admin)).status_code == 202
    cac_nguoi = ket_noi_test.execute(text("SELECT DISTINCT triggered_by FROM sync_runs")).scalars().all()
    assert cac_nguoi == [admin.id]


# ---------------------------------------------------------------- admin đầu tiên từ .env

def test_tao_admin_dau_tien_chi_khi_bang_trong(phien_test, ket_noi_test):
    ket_noi_test.execute(text("DELETE FROM users"))
    assert user_service.tao_admin_dau_tien(phien_test, "admin.dau", "mat-khau-admin-1") is True
    dong = ket_noi_test.execute(text("SELECT username, role, password_hash FROM users")).one()
    assert dong[:2] == ("admin.dau", "admin") and dong[2].startswith("$2b$") and "mat-khau-admin-1" not in dong[2]
    assert user_service.tao_admin_dau_tien(phien_test, "admin.hai", "mat-khau-admin-2") is False      # đã có người dùng
    assert ket_noi_test.execute(text("SELECT count(*) FROM users")).scalar_one() == 1


def test_khong_dat_bien_moi_truong_thi_khong_tao_admin(phien_test, ket_noi_test):
    ket_noi_test.execute(text("DELETE FROM users"))
    assert user_service.tao_admin_dau_tien(phien_test, None, "mat-khau-admin-1") is False
    assert user_service.tao_admin_dau_tien(phien_test, "admin", None) is False
    assert ket_noi_test.execute(text("SELECT count(*) FROM users")).scalar_one() == 0


def test_mat_khau_admin_qua_ngan_dung_som_va_khong_vao_log(phien_test, ket_noi_test, caplog):
    ket_noi_test.execute(text("DELETE FROM users"))
    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        user_service.tao_admin_dau_tien(phien_test, "admin", "ngan")
    user_service.tao_admin_dau_tien(phien_test, "admin", "mat-khau-bi-mat-123")
    assert "mat-khau-bi-mat-123" not in caplog.text


# ---------------------------------------------------------------- hàm bảo mật thuần

def test_mat_khau_hop_le_va_qua_dai_khong_lam_bcrypt_ne_loi():
    assert security.mat_khau_hop_le("1234567") is not None and security.mat_khau_hop_le("12345678") is None
    assert security.mat_khau_hop_le("a" * 72) is None and security.mat_khau_hop_le("a" * 73) is not None
    assert security.mat_khau_hop_le("ư" * 37) is not None                        # 74 byte UTF-8 dù chỉ 37 ký tự
    assert security.kiem_mat_khau("a" * 100, security.bam_mat_khau("a" * 20)) is False   # không ném ValueError
    assert security.kiem_mat_khau("x", "khong-phai-chuoi-bam") is False


def test_jwt_secret_ngan_bi_tu_choi_luc_khoi_dong():
    from pydantic import ValidationError
    from app.config import Settings
    with pytest.raises(ValidationError) as loi:
        Settings(_env_file=None, JWT_SECRET="ngan", DATABASE_URL="postgresql+psycopg://x", ALERT_DROP_THRESHOLD_PCT=30)
    assert any(chi_tiet["loc"] == ("JWT_SECRET",) and chi_tiet["type"] == "string_too_short" for chi_tiet in loi.value.errors())
