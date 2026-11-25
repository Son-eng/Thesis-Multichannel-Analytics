"""Quản lý người dùng, chỉ admin."""

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.sync import gio_vn_iso
from app.core import security
from app.core.deps import yeu_cau_admin
from app.database import lay_phien_db
from app.models.sync_run import SyncRun
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["users"])

MAU_TEN_DANG_NHAP = re.compile(r"^[A-Za-z0-9._-]{3,50}$")


class TaoNguoiDung(BaseModel):
    username: str
    password: str
    role: Literal["admin", "user"]


class DoiVaiTro(BaseModel):
    role: Literal["admin", "user"]


class DoiMatKhau(BaseModel):
    password: str


def sang_json(nguoi):
    return {"id": nguoi.id, "username": nguoi.username, "role": nguoi.role, "created_at": gio_vn_iso(nguoi.created_at)}


def _loi(ma_http, ma, thong_diep):
    return HTTPException(ma_http, detail={"code": ma, "message": thong_diep})


def _kiem_mat_khau(mat_khau):
    ly_do = security.mat_khau_hop_le(mat_khau)
    if ly_do:
        raise _loi(422, "invalid_password", ly_do)


def _lay_hoac_404(phien, ma):
    nguoi = phien.get(User, ma)
    if nguoi is None:
        raise _loi(404, "user_not_found", "Không tìm thấy người dùng")
    return nguoi


@router.get("")
def danh_sach(phien: Session = Depends(lay_phien_db), _admin: User = Depends(yeu_cau_admin)):
    return [sang_json(n) for n in phien.execute(select(User).order_by(User.id)).scalars()]


@router.post("", status_code=201)
def tao(du_lieu: TaoNguoiDung, phien: Session = Depends(lay_phien_db), _admin: User = Depends(yeu_cau_admin)):
    ten = du_lieu.username.strip()
    if not MAU_TEN_DANG_NHAP.match(ten):
        raise _loi(422, "invalid_username", "Tên đăng nhập gồm 3–50 ký tự: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang")
    _kiem_mat_khau(du_lieu.password)
    if phien.execute(select(User.id).where(User.username == ten)).first() is not None:
        raise _loi(409, "username_taken", "Tên đăng nhập đã tồn tại")
    nguoi = User(username=ten, password_hash=security.bam_mat_khau(du_lieu.password), role=du_lieu.role)
    phien.add(nguoi)
    try:
        phien.commit()
    except IntegrityError:                       # hai yêu cầu cùng tạo một tên thì ràng buộc UNIQUE chặn
        phien.rollback()
        raise _loi(409, "username_taken", "Tên đăng nhập đã tồn tại") from None
    phien.refresh(nguoi)
    return sang_json(nguoi)


@router.patch("/{ma}")
def doi_vai_tro(ma: int, du_lieu: DoiVaiTro, phien: Session = Depends(lay_phien_db), admin: User = Depends(yeu_cau_admin)):
    nguoi = _lay_hoac_404(phien, ma)
    if nguoi.id == admin.id:
        # Không cho tự hạ quyền để luôn còn ít nhất một admin.
        raise _loi(400, "cannot_change_own_role", "Không đổi được vai trò của chính mình")
    nguoi.role = du_lieu.role
    phien.commit()
    phien.refresh(nguoi)
    return sang_json(nguoi)


@router.post("/{ma}/reset-password", status_code=204)
def dat_lai_mat_khau(ma: int, du_lieu: DoiMatKhau, phien: Session = Depends(lay_phien_db),
                     _admin: User = Depends(yeu_cau_admin)):
    nguoi = _lay_hoac_404(phien, ma)
    _kiem_mat_khau(du_lieu.password)
    nguoi.password_hash = security.bam_mat_khau(du_lieu.password)
    phien.commit()
    return Response(status_code=204)


@router.delete("/{ma}", status_code=204)
def xoa(ma: int, phien: Session = Depends(lay_phien_db), admin: User = Depends(yeu_cau_admin)):
    if ma == admin.id:
        raise _loi(400, "cannot_delete_self", "Không xóa được chính mình")
    nguoi = _lay_hoac_404(phien, ma)
    if phien.execute(select(SyncRun.id).where(SyncRun.triggered_by == nguoi.id).limit(1)).first() is not None:
        # Xóa sẽ làm lịch sử đồng bộ mất người chạy hoặc hiện sai thành "Tự động".
        raise _loi(409, "user_has_history", "Người dùng này đã chạy đồng bộ hoặc nạp tệp nên không xóa được")
    phien.delete(nguoi)
    phien.commit()
    return Response(status_code=204)
