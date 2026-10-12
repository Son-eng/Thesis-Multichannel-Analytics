"""Bảng `orders_tiktok` — mỗi dòng là 1 dòng sản phẩm của 1 đơn TikTok (SPEC §3.2).

Cách đọc khai báo: xem docstring đầu file order_shopee.py.

Khác bảng Shopee: có `sku_subtotal_after_discount` (mức dòng) và
`order_amount` (MỨC ĐƠN — CẤM SUM theo dòng, §7.4); không có
`nmv_is_provisional` vì TikTok trả đủ tiền ngay trong đơn.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrderTiktok(Base):
    """Một dòng sản phẩm của đơn TikTok, đã chuẩn hóa theo §5.2 / §21.2."""

    __tablename__ = "orders_tiktok"
    __table_args__ = (
        UniqueConstraint("order_id", "sku", name="uq_tiktok_order_sku"),
        CheckConstraint("data_source IN ('api', 'file')", name="ck_tiktok_data_source"),
        Index("idx_tiktok_date", "order_date"),
        Index("idx_tiktok_status", "order_status"),
        Index("idx_tiktok_shop", "shop_name"),
        Index("idx_tiktok_sku", "sku"),
        Index("idx_tiktok_product", "product_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_name: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str] = mapped_column(String(50))
    # SKU đã bỏ dấu nháy hai đầu (§5.2), khóa chống trùng, NOT NULL (§4.1).
    sku: Mapped[str] = mapped_column(String(100))
    product_code: Mapped[str | None] = mapped_column(String(50))
    order_date: Mapped[date] = mapped_column(Date)
    order_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    order_status_raw: Mapped[str | None] = mapped_column(Text)
    order_status: Mapped[str] = mapped_column(String(20))
    is_returned: Mapped[bool] = mapped_column(server_default=text("false"))
    product_name: Mapped[str | None] = mapped_column(Text)
    variation: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # CẤM dùng tính tỷ lệ hoàn: TikTok điền cột này cả cho đơn hủy (§3.2).
    returned_quantity: Mapped[int] = mapped_column(server_default=text("0"))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    sku_subtotal_after_discount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    nmv: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Cột DUY NHẤT dùng tính doanh thu (§7.1).
    nmv_after_tax: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # MỨC ĐƠN — lặp lại trên mọi dòng của cùng đơn, CẤM SUM theo dòng (§7.4).
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    is_affiliate: Mapped[bool] = mapped_column(server_default=text("false"))
    province: Mapped[str | None] = mapped_column(String(100))
    province_raw: Mapped[str | None] = mapped_column(String(100))
    hour_bucket: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(10))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    source_file: Mapped[str | None] = mapped_column(String(255))
