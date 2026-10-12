"""Bảng `users` — tài khoản đăng nhập (SPEC §3.3, §11).

Đăng nhập/phân quyền đã hoãn sau demo, nhưng bảng vẫn phải có ngay từ
migration đầu: `sync_runs.triggered_by` tham chiếu tới `users(id)`. Thiếu bảng
này thì khóa ngoại không tạo được.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """Một tài khoản; role chỉ có 2 giá trị admin / user (§11)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
    )

    # Integer khóa chính tự tăng → SERIAL (§3.3 ghi SERIAL, không phải BIGSERIAL).
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    # Chỉ lưu chuỗi băm mật khẩu, không bao giờ lưu mật khẩu gốc.
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
