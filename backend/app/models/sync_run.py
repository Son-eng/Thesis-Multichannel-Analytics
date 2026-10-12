"""Bảng `sync_runs` — nhật ký MỌI lượt đưa dữ liệu vào, cả 3 đường (SPEC §3.3).

Ba đường: đồng bộ API, thư mục quét tự động, nút tải file. Thay cho bảng
`upload_logs` cũ. Trang lịch sử đồng bộ đọc bảng này.
"""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncRun(Base):
    """Một lượt nạp dữ liệu của 1 sàn: nguồn, số dòng, 5 bộ đếm chất lượng, kết quả."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("platform IN ('shopee', 'tiktok')", name="ck_sync_runs_platform"),
        CheckConstraint("source IN ('api', 'file_auto', 'file_manual')", name="ck_sync_runs_source"),
        CheckConstraint("trigger_type IN ('schedule', 'manual')", name="ck_sync_runs_trigger_type"),
        CheckConstraint("status IN ('running', 'success', 'failed')", name="ck_sync_runs_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))
    # NULL khi một file chứa nhiều shop (file TikTok).
    shop_name: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(15))
    trigger_type: Mapped[str] = mapped_column(String(10), server_default=text("'schedule'"))
    # Chỉ đường API: khoảng thời gian đã kéo.
    window_from: Mapped[datetime | None] = mapped_column(DateTime)
    window_to: Mapped[datetime | None] = mapped_column(DateTime)
    # Chỉ đường file.
    file_name: Mapped[str | None] = mapped_column(String(255))
    api_calls: Mapped[int] = mapped_column(server_default=text("0"))
    orders_fetched: Mapped[int] = mapped_column(server_default=text("0"))
    rows_total: Mapped[int] = mapped_column(server_default=text("0"))
    rows_inserted: Mapped[int] = mapped_column(server_default=text("0"))
    # Thay rows_skipped cũ: upsert cập nhật dòng đã có, không bỏ qua (§4).
    rows_updated: Mapped[int] = mapped_column(server_default=text("0"))

    # 5 bộ đếm chất lượng (§3.3) — tên trùng khóa của dict bộ đếm mà 2 parser
    # trả về, để bước nạp ghi thẳng vào đây.
    rows_sku_fallback: Mapped[int] = mapped_column(server_default=text("0"))
    rows_sku_unknown: Mapped[int] = mapped_column(server_default=text("0"))
    rows_status_unknown: Mapped[int] = mapped_column(server_default=text("0"))
    rows_province_unmapped: Mapped[int] = mapped_column(server_default=text("0"))
    rows_product_unmapped: Mapped[int] = mapped_column(server_default=text("0"))

    # NULL khi do lịch tự chạy.
    triggered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(10), server_default=text("'running'"))
    error_message: Mapped[str | None] = mapped_column(Text)
