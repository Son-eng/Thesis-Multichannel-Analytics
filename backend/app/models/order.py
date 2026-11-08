"""Bảng `orders` — MỘT bảng cho mọi sàn; mỗi dòng là 1 dòng sản phẩm của 1 đơn (SPEC §3.1).

Gộp từ `orders_shopee` và `orders_tiktok` (chốt 08/11/2026 theo yêu cầu GVHD): cột `platform` phân biệt sàn, cột chung
giữ nguyên tên và kiểu, cột riêng của một sàn để cho phép NULL. Thêm sàn mới = thêm một giá trị `platform` cùng
parser/connector của sàn đó, KHÔNG thêm bảng.

Cách đọc khai báo (dùng chung cho mọi file trong app/models/):
- `Mapped[str]` → cột NOT NULL; `Mapped[str | None]` → cột cho phép NULL.
  SQLAlchemy suy ra NOT NULL từ kiểu, nên không ghi thêm nullable=...
- `server_default` là DEFAULT nằm trong CSDL (ghi vào CREATE TABLE), không phải
  giá trị Python. Cần vậy để INSERT thiếu cột — kể cả INSERT viết tay bằng
  SQL hay upsert — vẫn nhận đúng giá trị mặc định của §3.
- Tên ràng buộc và index đặt tường minh, giống SPEC §3.1, để thông báo lỗi
  của PostgreSQL chỉ thẳng tới quy tắc bị vi phạm.
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


class Order(Base):
    """Một dòng sản phẩm của một đơn, đã chuẩn hóa theo §5 / §21.1; `platform` cho biết sàn."""

    __tablename__ = "orders"
    __table_args__ = (
        # Khóa chống trùng (§4): một đơn có thể nhiều SKU, và order_id của hai sàn thuộc hai hệ mã khác nhau nên
        # khóa gồm cả sàn. Upsert dựa vào đúng ràng buộc này.
        UniqueConstraint("platform", "order_id", "sku", name="uq_orders_platform_order_sku"),
        CheckConstraint("platform IN ('shopee', 'tiktok')", name="ck_orders_platform"),
        # Biết dòng đến từ đường nào; chặn giá trị gõ sai ngay ở CSDL.
        CheckConstraint("data_source IN ('api', 'file')", name="ck_orders_data_source"),
        # Mọi truy vấn dashboard đều lọc theo một sàn, nên `platform` đứng đầu mọi chỉ mục.
        Index("idx_orders_platform_date", "platform", "order_date"),
        Index("idx_orders_platform_status", "platform", "order_status"),
        Index("idx_orders_platform_shop", "platform", "shop_name"),
        Index("idx_orders_platform_sku", "platform", "sku"),
        Index("idx_orders_platform_product", "platform", "product_code"),
    )

    # BigInteger khóa chính tự tăng → PostgreSQL tạo BIGSERIAL.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Sàn: 'shopee' | 'tiktok' (mở rộng sàn mới = thêm giá trị vào CHECK và một parser/connector).
    platform: Mapped[str] = mapped_column(String(10))
    shop_name: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str] = mapped_column(String(50))
    # SKU đã làm sạch (Shopee §5.1; TikTok bỏ dấu nháy hai đầu §5.2), khóa chống trùng — NOT NULL bắt buộc (§4.1):
    # NULL không bao giờ "trùng" trong UNIQUE nên nạp lại file sẽ nhân bản dòng.
    sku: Mapped[str] = mapped_column(String(100))
    # Mã sản phẩm chuẩn hóa, dùng cho mọi báo cáo; NULL = SKU lạ (§5.4).
    product_code: Mapped[str | None] = mapped_column(String(50))
    order_date: Mapped[date] = mapped_column(Date)
    # Giờ VN; NULL ở đường file Shopee vì file chỉ có ngày.
    order_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    order_status_raw: Mapped[str | None] = mapped_column(Text)
    order_status: Mapped[str] = mapped_column(String(20))
    is_returned: Mapped[bool] = mapped_column(server_default=text("false"))
    product_name: Mapped[str | None] = mapped_column(Text)
    variation: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # CẤM dùng tính tỷ lệ hoàn của TikTok: sàn này điền cột cho cả đơn hủy (§3.2).
    returned_quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # Các cột tiền đều MỨC DÒNG — SUM() an toàn (§7.4), trừ `order_amount`. Numeric(15, 2) là số thập phân chính xác,
    # không dùng số thực: số thực nhị phân không biểu diễn đúng mọi số thập phân, tổng tiền có thể lệch phần lẻ.
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Chỉ TikTok; Shopee để NULL.
    sku_subtotal_after_discount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    nmv: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Cột DUY NHẤT dùng tính doanh thu (§7.1).
    nmv_after_tax: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # MỨC ĐƠN — lặp lại trên mọi dòng của cùng đơn, CẤM SUM theo dòng (§7.4). Chỉ TikTok; Shopee để NULL.
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # TRUE = NMV tạm tính vì đường API Shopee chưa có escrow (§7.5). NOT NULL DEFAULT false: TikTok luôn false
    # (không có khái niệm NMV tạm tính) — chọn cột chung thay vì nullable để mọi `WHERE nmv_is_provisional` đơn giản.
    nmv_is_provisional: Mapped[bool] = mapped_column(server_default=text("false"))
    is_affiliate: Mapped[bool] = mapped_column(server_default=text("false"))
    province: Mapped[str | None] = mapped_column(String(100))
    # Giữ bản gốc để truy vết khi bảng tỉnh tra sai (§5.3).
    province_raw: Mapped[str | None] = mapped_column(String(100))
    hour_bucket: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(10))
    # uploaded_at = lần đầu xuất hiện; updated_at = lần upsert gần nhất (§4). DateTime không múi giờ → TIMESTAMP,
    # lưu UTC vì phiên CSDL ép timezone=UTC (database.py). Chỉ để truy vết, không dùng tính KPI theo ngày.
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Tên file nguồn — chỉ đường file có.
    source_file: Mapped[str | None] = mapped_column(String(255))
