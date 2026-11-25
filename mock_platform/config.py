# Đọc cấu hình từ mock_platform/.env

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import tokens

DUONG_DAN_FILE_ENV = Path(__file__).resolve().parent / ".env"


class CauHinhMock(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", case_sensitive=True)

    SHOPEE_PARTNER_ID: int
    SHOPEE_PARTNER_KEY: str
    SHOPEE_SHOP_ID: int
    SHOPEE_ACCESS_TOKEN: str
    SHOPEE_REFRESH_TOKEN: str

    TIKTOK_APP_KEY: str
    TIKTOK_APP_SECRET: str
    TIKTOK_SHOP_A_ACCESS_TOKEN: str
    TIKTOK_SHOP_A_REFRESH_TOKEN: str
    TIKTOK_SHOP_B_ACCESS_TOKEN: str
    TIKTOK_SHOP_B_REFRESH_TOKEN: str

    # TikTok không nhận redirect ở URL mà chuyển về Redirect URL đã đăng ký của app.
    TIKTOK_SERVICE_ID: str = "mock_service_id_GIA"
    TIKTOK_REDIRECT_URL: str = "http://localhost:8000/api/connections/tiktok/callback"

    # Đặt số nhỏ để test token hết hạn mà không phải chờ 4 giờ hay 7 ngày.
    MOCK_SHOPEE_ACCESS_TTL_SECONDS: int = Field(default=tokens.SHOPEE_HAN_ACCESS_GIAY, gt=0)
    MOCK_TIKTOK_ACCESS_TTL_SECONDS: int = Field(default=tokens.TIKTOK_HAN_ACCESS_GIAY, gt=0)

    # "completed_only" để kiểm nhánh NMV tạm tính của backend.
    MOCK_ESCROW_MODE: Literal["all", "completed_only"] = "all"

    # Tỷ lệ yêu cầu bị trả lỗi quá tải, 0 là tắt; seed cố định để test tái lập được.
    MOCK_FAULT_RATE: float = Field(default=0.0, ge=0, le=1)
    MOCK_FAULT_SEED: int | None = None


def doc_cau_hinh(duong_dan_env=DUONG_DAN_FILE_ENV):
    return CauHinhMock(_env_file=duong_dan_env)
