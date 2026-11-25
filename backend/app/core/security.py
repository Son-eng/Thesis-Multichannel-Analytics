"""Băm mật khẩu bằng bcrypt và JWT; vai trò không nằm trong token mà đọc lại từ CSDL mỗi yêu cầu."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

THUAT_TOAN = "HS256"
# bcrypt chỉ đọc 72 byte đầu, bản 5.x còn ném lỗi nếu dài hơn, nên chặn từ đầu vào.
DO_DAI_TOI_DA_BYTE = 72
DO_DAI_TOI_THIEU = 8

# Băm giả để "sai tên" và "sai mật khẩu" tốn cùng thời gian, tránh bị dò tên có thật.
_BAM_GIA = None


def mat_khau_hop_le(mat_khau):
    if len(mat_khau) < DO_DAI_TOI_THIEU:
        return f"Mật khẩu cần ít nhất {DO_DAI_TOI_THIEU} ký tự"
    if len(mat_khau.encode("utf-8")) > DO_DAI_TOI_DA_BYTE:
        return f"Mật khẩu quá dài (tối đa {DO_DAI_TOI_DA_BYTE} byte)"
    return None


def bam_mat_khau(mat_khau):
    return bcrypt.hashpw(mat_khau.encode("utf-8"), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("ascii")


def kiem_mat_khau(mat_khau, chuoi_bam):
    try:
        return bcrypt.checkpw(mat_khau.encode("utf-8"), chuoi_bam.encode("ascii"))
    except ValueError:
        return False


def kiem_gia_de_dong_deu_thoi_gian(mat_khau):
    global _BAM_GIA
    if _BAM_GIA is None:
        _BAM_GIA = bam_mat_khau("mat-khau-gia-khong-ai-dung-duoc")
    kiem_mat_khau(mat_khau, _BAM_GIA)


def tao_token(ma_nguoi_dung, bay_gio=None):
    bay_gio = bay_gio or datetime.now(timezone.utc)
    noi_dung = {"sub": str(ma_nguoi_dung), "iat": bay_gio,
                "exp": bay_gio + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)}
    return jwt.encode(noi_dung, settings.JWT_SECRET, algorithm=THUAT_TOAN)


def doc_token(token):
    """Trả id người dùng, hoặc None nếu token sai, hết hạn hay bị giả."""
    try:
        noi_dung = jwt.decode(token, settings.JWT_SECRET, algorithms=[THUAT_TOAN], options={"require": ["exp", "sub"]})
        return int(noi_dung["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
