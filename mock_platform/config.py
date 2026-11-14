"""Cấu hình của máy chủ giả lập — đọc từ mock_platform/.env (SPEC §19.4).

Mọi khóa và token ở đây là GIẢ. Backend dùng cùng các giá trị đó trong .env
của nó, như một app đã đăng ký với "sàn" giả lập này.

Không tạo đối tượng cấu hình ngay khi import (khác backend/app/config.py): test
chữ ký, token, data_builder không cần .env, nên import module nào cũng không
được đòi .env. Chỉ main.py gọi doc_cau_hinh() lúc khởi động.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import tokens

# Tính từ vị trí file này để chạy uvicorn/pytest ở thư mục nào cũng đúng.
DUONG_DAN_FILE_ENV = Path(__file__).resolve().parent / ".env"


class CauHinhMock(BaseSettings):
    """Cấu hình đã kiểm kiểu. Tên thuộc tính in hoa tiếng Anh vì phải trùng tên biến trong .env (§0.5)."""

    model_config = SettingsConfigDict(env_file_encoding="utf-8", case_sensitive=True)

    # --- Shopee: thông tin app và shop (GIẢ) ---
    SHOPEE_PARTNER_ID: int
    SHOPEE_PARTNER_KEY: str
    SHOPEE_SHOP_ID: int
    SHOPEE_ACCESS_TOKEN: str
    SHOPEE_REFRESH_TOKEN: str

    # --- TikTok: thông tin app và token từng shop (GIẢ) ---
    TIKTOK_APP_KEY: str
    TIKTOK_APP_SECRET: str
    TIKTOK_SHOP_A_ACCESS_TOKEN: str
    TIKTOK_SHOP_A_REFRESH_TOKEN: str
    TIKTOK_SHOP_B_ACCESS_TOKEN: str
    TIKTOK_SHOP_B_REFRESH_TOKEN: str

    # --- Ủy quyền gian hàng (chỉ dẫn 026) ---
    # TikTok: `service_id` của app (gắn vào link ủy quyền) và Redirect URL ĐÃ ĐĂNG KÝ — TikTok không nhận
    # `redirect` ở URL mà chuyển về địa chỉ đã khai ở Partner Center (Pipeline/Tiktok/tiktok_auth.py).
    # Có mặc định để .env cũ vẫn chạy; đổi nếu backend chạy ở địa chỉ khác.
    TIKTOK_SERVICE_ID: str = "mock_service_id_GIA"
    TIKTOK_REDIRECT_URL: str = "http://localhost:8000/api/connections/tiktok/callback"

    # --- Hạn sống access_token (giây) ---
    # Mặc định đúng như sàn thật. Đặt số nhỏ (ví dụ 5) để test "token hết hạn"
    # mà không phải chờ 4 giờ / 7 ngày.
    MOCK_SHOPEE_ACCESS_TTL_SECONDS: int = Field(default=tokens.SHOPEE_HAN_ACCESS_GIAY, gt=0)
    MOCK_TIKTOK_ACCESS_TTL_SECONDS: int = Field(default=tokens.TIKTOK_HAN_ACCESS_GIAY, gt=0)

    # Escrow Shopee (§19.2): "all" = trả cho mọi đơn (mặc định, để số liệu đường
    # API khớp §17.2); "completed_only" = đơn khác COMPLETED bị báo lỗi, để
    # kiểm nhánh NMV tạm tính của backend (§7.5).
    MOCK_ESCROW_MODE: Literal["all", "completed_only"] = "all"

    # Gây lỗi quá tải có chủ đích (§19.3 mục 5): tỷ lệ yêu cầu bị trả lỗi,
    # 0 = tắt. Seed cố định chuỗi lỗi để test tái lập được; bỏ trống = ngẫu nhiên.
    MOCK_FAULT_RATE: float = Field(default=0.0, ge=0, le=1)
    MOCK_FAULT_SEED: int | None = None


def doc_cau_hinh(duong_dan_env=DUONG_DAN_FILE_ENV):
    """Đọc và kiểm cấu hình. Thiếu biến hoặc sai kiểu → lỗi ngay lúc khởi động.

    Nhận: đường dẫn file .env (test truyền .env.example để kiểm file mẫu).
    Trả: CauHinhMock.
    """
    return CauHinhMock(_env_file=duong_dan_env)
