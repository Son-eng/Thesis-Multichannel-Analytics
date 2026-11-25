# Đăng nhập, lấy thông tin cá nhân, đăng xuất

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

THONG_BAO_SAI_DANG_NHAP = "Tên đăng nhập hoặc mật khẩu không đúng"


class DangNhap(BaseModel):
    username: str
    password: str


def nguoi_dung_sang_json(nguoi):
    return {"id": nguoi.id, "username": nguoi.username, "role": nguoi.role}

# Đăng nhập
@router.post("/login")
def dang_nhap(du_lieu: DangNhap, phien: Session = Depends(lay_phien_db)):
    nguoi = phien.execute(select(User).where(User.username == du_lieu.username.strip())).scalar_one_or_none()
    if nguoi is None:
        security.kiem_gia_de_dong_deu_thoi_gian(du_lieu.password)
        dung = False
    else:
        dung = security.kiem_mat_khau(du_lieu.password, nguoi.password_hash)
    if not dung:
        raise HTTPException(401, detail={"code": "invalid_credentials", "message": THONG_BAO_SAI_DANG_NHAP})
    return {"access_token": security.tao_token(nguoi.id), "token_type": "bearer", "user": nguoi_dung_sang_json(nguoi)}

# Nhận token JWT từ Header xem ai gọi API, trả về id, username, role
@router.get("/me")
def toi_la_ai(nguoi: User = Depends(yeu_cau_dang_nhap)):
    return nguoi_dung_sang_json(nguoi)

# Đăng xuất
@router.post("/logout", status_code=204)
def dang_xuat(_nguoi: User = Depends(yeu_cau_dang_nhap)):
    return Response(status_code=204)
