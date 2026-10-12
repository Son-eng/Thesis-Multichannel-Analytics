"""Bảng `platform_tokens` — token truy cập API của từng gian hàng (SPEC §3.3, §20.1).

Vì sao lưu token trong CSDL chứ không lưu file JSON như Pipeline cũ: refresh
token Shopee chỉ dùng được 1 lần. Ghi token mới trong cùng một giao dịch CSDL
thì hoặc ghi được hết, hoặc không có gì thay đổi — không bao giờ mất token
giữa chừng. Ở môi trường giả lập, token là giá trị giả do mock_platform cấp.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformToken(Base):
    """Token của một gian hàng trên một sàn — mỗi (sàn, shop) đúng một dòng."""

    __tablename__ = "platform_tokens"
    __table_args__ = (
        CheckConstraint("platform IN ('shopee', 'tiktok')", name="ck_platform_tokens_platform"),
        # Mỗi gian hàng chỉ một bộ token; làm mới token là UPDATE dòng đó.
        UniqueConstraint("platform", "shop_name", name="uq_token_shop"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))
    shop_name: Mapped[str] = mapped_column(String(50))
    # Shopee: shop_id · TikTok: shop_cipher.
    shop_ref: Mapped[str] = mapped_column(String(100))
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
