"""Bảng orders dùng chung cho mọi sàn; mỗi dòng là một dòng sản phẩm của một đơn."""

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


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Một đơn có nhiều SKU và mã đơn hai sàn khác hệ nên khóa chống trùng gồm cả sàn; upsert dựa vào ràng buộc này.
        UniqueConstraint("platform", "order_id", "sku", name="uq_orders_platform_order_sku"),
        CheckConstraint("platform IN ('shopee', 'tiktok')", name="ck_orders_platform"),
        CheckConstraint("data_source IN ('api', 'file')", name="ck_orders_data_source"),
        # Mọi truy vấn dashboard đều lọc theo sàn nên platform đứng đầu mọi chỉ mục.
        Index("idx_orders_platform_date", "platform", "order_date"),
        Index("idx_orders_platform_status", "platform", "order_status"),
        Index("idx_orders_platform_shop", "platform", "shop_name"),
        Index("idx_orders_platform_sku", "platform", "sku"),
        Index("idx_orders_platform_product", "platform", "product_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    platform: Mapped[str] = mapped_column(String(10))
    shop_name: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str] = mapped_column(String(50))
    # SKU phải NOT NULL: NULL không bao giờ trùng trong UNIQUE nên nạp lại file sẽ nhân bản dòng.
    sku: Mapped[str] = mapped_column(String(100))
    # NULL nghĩa là SKU lạ, không tra được mã sản phẩm.
    product_code: Mapped[str | None] = mapped_column(String(50))
    order_date: Mapped[date] = mapped_column(Date)
    # Giờ Việt Nam; đường file Shopee để NULL vì file chỉ có ngày.
    order_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    order_status_raw: Mapped[str | None] = mapped_column(Text)
    order_status: Mapped[str] = mapped_column(String(20))
    is_returned: Mapped[bool] = mapped_column(server_default=text("false"))
    product_name: Mapped[str | None] = mapped_column(Text)
    variation: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # Không dùng để tính tỷ lệ hoàn của TikTok vì sàn điền cột này cho cả đơn hủy.
    returned_quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # Tiền là mức dòng nên SUM được, trừ order_amount; dùng Numeric để tổng không lệch phần lẻ.
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    sku_subtotal_after_discount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    nmv: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Cột duy nhất dùng tính doanh thu.
    nmv_after_tax: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Mức đơn, lặp lại trên mọi dòng của đơn nên không được SUM theo dòng.
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # true là NMV tạm tính vì đường API Shopee chưa có escrow; TikTok luôn false.
    nmv_is_provisional: Mapped[bool] = mapped_column(server_default=text("false"))
    is_affiliate: Mapped[bool] = mapped_column(server_default=text("false"))
    province: Mapped[str | None] = mapped_column(String(100))
    province_raw: Mapped[str | None] = mapped_column(String(100))
    hour_bucket: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(10))
    # Lưu UTC, chỉ để truy vết, không dùng tính KPI theo ngày.
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    source_file: Mapped[str | None] = mapped_column(String(255))
