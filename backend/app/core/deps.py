"""Phụ thuộc (dependency) dùng chung của router: đăng nhập và phân quyền (SPEC §11, §12.1.4).

- `yeu_cau_dang_nhap`: có token hợp lệ của một người dùng CÒN TỒN TẠI → trả User; không thì 401.
- `yeu_cau_admin`: như trên và vai trò phải là admin → không thì 403.
Router chỉ khai báo `Depends(...)`; mọi logic kiểm quyền nằm ở đây, một chỗ.
Mọi 401 dùng cùng một mã `not_authenticated` (thiếu, sai, hết hạn đều giống nhau) để không lộ thêm thông tin.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.database import lay_phien_db
from app.models.user import User

_BEARER = HTTPBearer(auto_error=False)   # tự xử lý thiếu token để trả đúng khuôn lỗi §12.1.0


def _chua_dang_nhap():
    return HTTPException(401, detail={"code": "not_authenticated", "message": "Cần đăng nhập"},
                         headers={"WWW-Authenticate": "Bearer"})


def yeu_cau_dang_nhap(
    thong_tin: HTTPAuthorizationCredentials | None = Depends(_BEARER),
    phien: Session = Depends(lay_phien_db),
):
    """Người dùng đang đăng nhập (mọi vai trò). Thiếu/sai/hết hạn token hoặc người dùng đã bị xóa → 401."""
    if thong_tin is None:
        raise _chua_dang_nhap()
    ma = security.doc_token(thong_tin.credentials)
    nguoi = phien.get(User, ma) if ma is not None else None
    if nguoi is None:
        raise _chua_dang_nhap()
    return nguoi


def yeu_cau_admin(nguoi: User = Depends(yeu_cau_dang_nhap)):
    """Chỉ admin; vai trò khác → 403. Trả User để ghi `triggered_by`."""
    if nguoi.role != "admin":
        raise HTTPException(403, detail={"code": "forbidden", "message": "Chức năng này chỉ dành cho quản trị viên"})
    return nguoi
