"""Bảng `orders_shopee` — mỗi dòng là 1 dòng sản phẩm của 1 đơn Shopee (SPEC §3.1).

Cách đọc khai báo (dùng chung cho mọi file trong app/models/):
- `Mapped[str]` → cột NOT NULL; `Mapped[str | None]` → cột cho phép NULL.
  SQLAlchemy suy ra NOT NULL từ kiểu, nên không ghi thêm nullable=...
- `server_default` là DEFAULT nằm trong CSDL (ghi vào CREATE TABLE), không phải
  giá trị Python. Cần vậy để INSERT thiếu cột — kể cả INSERT viết tay bằng
  SQL hay upsert ở bước 7 — vẫn nhận đúng giá trị mặc định của §3.
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


class OrderShopee(Base):
    """Một dòng sản phẩm của đơn Shopee, đã chuẩn hóa theo §5.1 / §21.1."""

    __tablename__ = "orders_shopee"
    __table_args__ = (
        # Khóa chống trùng (§4): một đơn có thể nhiều SKU, nên không dùng
        # riêng order_id. Upsert ở bước 7 dựa vào đúng ràng buộc này.
        UniqueConstraint("order_id", "sku", name="uq_shopee_order_sku"),
        # Biết dòng đến từ đường nào; chặn giá trị gõ sai ngay ở CSDL.
        CheckConstraint("data_source IN ('api', 'file')", name="ck_shopee_data_source"),
        Index("idx_shopee_date", "order_date"),
        Index("idx_shopee_status", "order_status"),
        Index("idx_shopee_shop", "shop_name"),
        Index("idx_shopee_sku", "sku"),
        Index("idx_shopee_product", "product_code"),
    )

    # BigInteger khóa chính tự tăng → PostgreSQL tạo BIGSERIAL.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_name: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str] = mapped_column(String(50))
    # SKU thô, khóa chống trùng — NOT NULL bắt buộc (§4.1): NULL không bao giờ
    # "trùng" trong UNIQUE nên nạp lại file sẽ nhân bản dòng.
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
    returned_quantity: Mapped[int] = mapped_column(server_default=text("0"))
    # Các cột tiền đều MỨC DÒNG — SUM() an toàn (§7.4). Numeric(15, 2) là số
    # thập phân chính xác (đúng §3), không dùng số thực: số thực nhị phân
    # không biểu diễn đúng mọi số thập phân, tổng tiền có thể lệch phần lẻ.
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    nmv: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # Cột DUY NHẤT dùng tính doanh thu (§7.1).
    nmv_after_tax: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    # TRUE = NMV tạm tính vì đường API chưa có escrow (§7.5).
    nmv_is_provisional: Mapped[bool] = mapped_column(server_default=text("false"))
    is_affiliate: Mapped[bool] = mapped_column(server_default=text("false"))
    province: Mapped[str | None] = mapped_column(String(100))
    # Giữ bản gốc để truy vết khi bảng tỉnh tra sai (§5.3).
    province_raw: Mapped[str | None] = mapped_column(String(100))
    hour_bucket: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(10))
    # uploaded_at = lần đầu xuất hiện; updated_at = lần upsert gần nhất (§4).
    # DateTime không kèm múi giờ → TIMESTAMP như §3. Lưu ý: NOW() lấy theo
    # múi giờ của phiên CSDL (container đang để UTC), khác order_created_at
    # (giờ VN). Hai cột này chỉ để truy vết, không dùng tính KPI theo ngày.
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Tên file nguồn — chỉ đường file có.
    source_file: Mapped[str | None] = mapped_column(String(255))
