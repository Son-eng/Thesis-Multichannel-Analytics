"""Đăng nhập: POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout (SPEC §11, §12.1.4.1).

Sai tên đăng nhập và sai mật khẩu cho CÙNG một phản hồi (cùng thông báo, cùng thời gian xử lý).
Đăng xuất phía máy chủ chỉ trả 204: token không lưu trạng thái nên không có gì để thu hồi; giao diện xóa token.
"""

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


@router.get("/me")
def toi_la_ai(nguoi: User = Depends(yeu_cau_dang_nhap)):
    return nguoi_dung_sang_json(nguoi)


@router.post("/logout", status_code=204)
def dang_xuat(_nguoi: User = Depends(yeu_cau_dang_nhap)):
    return Response(status_code=204)
