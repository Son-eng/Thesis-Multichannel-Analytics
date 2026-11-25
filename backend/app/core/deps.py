"""Phụ thuộc dùng chung cho router: đăng nhập và phân quyền; mọi 401 dùng chung mã not_authenticated."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.database import lay_phien_db
from app.models.user import User

_BEARER = HTTPBearer(auto_error=False)   # tự xử lý khi thiếu token để trả đúng khuôn lỗi chung


def _chua_dang_nhap():
    return HTTPException(401, detail={"code": "not_authenticated", "message": "Cần đăng nhập"},
                         headers={"WWW-Authenticate": "Bearer"})


def yeu_cau_dang_nhap(
    thong_tin: HTTPAuthorizationCredentials | None = Depends(_BEARER),
    phien: Session = Depends(lay_phien_db),
):
    """Người dùng đang đăng nhập; token sai, hết hạn hoặc người dùng đã bị xóa đều trả 401."""
    if thong_tin is None:
        raise _chua_dang_nhap()
    ma = security.doc_token(thong_tin.credentials)
    nguoi = phien.get(User, ma) if ma is not None else None
    if nguoi is None:
        raise _chua_dang_nhap()
    return nguoi


def yeu_cau_admin(nguoi: User = Depends(yeu_cau_dang_nhap)):
    if nguoi.role != "admin":
        raise HTTPException(403, detail={"code": "forbidden", "message": "Chức năng này chỉ dành cho quản trị viên"})
    return nguoi
