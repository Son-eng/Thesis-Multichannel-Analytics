"""Bảng platform_tokens: lưu token trong CSDL vì refresh token Shopee chỉ dùng được một lần, ghi trong giao dịch thì không mất giữa chừng."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformToken(Base):
    __tablename__ = "platform_tokens"
    __table_args__ = (
        CheckConstraint("platform IN ('shopee', 'tiktok')", name="ck_platform_tokens_platform"),
        UniqueConstraint("platform", "shop_name", name="uq_token_shop"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))
    shop_name: Mapped[str] = mapped_column(String(50))
    shop_ref: Mapped[str] = mapped_column(String(100))
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
