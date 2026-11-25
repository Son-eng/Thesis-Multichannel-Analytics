import logging

from sqlalchemy import func, select

from app.core import security
from app.models.user import User

logger = logging.getLogger(__name__)


def tao_admin_dau_tien(phien, ten_dang_nhap, mat_khau):
    """Tạo admin nếu bảng users trống; mật khẩu không hợp lệ thì dừng ngay lúc khởi động."""
    if not ten_dang_nhap or not mat_khau:
        return False
    if phien.execute(select(func.count()).select_from(User)).scalar_one() > 0:
        return False
    ly_do = security.mat_khau_hop_le(mat_khau)
    if ly_do:
        raise ValueError(f"ADMIN_PASSWORD không hợp lệ: {ly_do}")
    phien.add(User(username=ten_dang_nhap.strip(), password_hash=security.bam_mat_khau(mat_khau), role="admin"))
    phien.commit()
    logger.info("Đã tạo tài khoản admin đầu tiên '%s'", ten_dang_nhap)
    return True
