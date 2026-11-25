# File quản lý cấu hình của toàn bộ Backend
# Fail-Fast: nếu thiếu biến, sai kiểu dữ liệu hoặc chuỗi kết nối sai định dạng, hệ thống dừng ngay từ lúc khởi động
from datetime import date
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Đảm bảo luôn trỏ vào đúng file backend/.env
# Vì khi chạy dự án, mỗi lúc mình ở 1 chỗ nên nếu dùng đường dẫn tương đối ".env" thì Python sẽ tìm sai chỗ và báo "thiếu biến môi trường"
DUONG_DAN_FILE_ENV = Path(__file__).resolve().parent.parent / ".env"

# Tiền tố bắt buộc của chuỗi kết nối
# Tách thành hằng số để thông báo lỗi bên dưới và điều kiện kiểm tra không bao giờ lệch nhau.
TIEN_TO_KET_NOI_BAT_BUOC = "postgresql+psycopg://"


class Settings(BaseSettings):  # Kế thừa từ Pydantic - đọc biến môi trường -> tự ép kiểu
    """
    """
    model_config = SettingsConfigDict(
        env_file=DUONG_DAN_FILE_ENV,
        env_file_encoding="utf-8",
        # Phân biệt hoa/thường
        case_sensitive=True,
    )

    # Kết nối CSDL & ngưỡng cảnh báo
    DATABASE_URL: str

    # Ngưỡng cảnh báo doanh thu sụt giảm, điền <0 or >100 thì từ chối
    ALERT_DROP_THRESHOLD_PCT: float = Field(gt=0, le=100)

    # Xác thực & phân quyền
    # Chuỗi phải dài >32 kí tự
    JWT_SECRET: str = Field(min_length=32)
    # Token hết hạn sau 8 tiếng
    JWT_EXPIRE_MINUTES: int = Field(default=480, gt=0)
    # Độ khó của hàm băm 2^12 (chạy test có thể hạ xuống)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=15)
    # Tài khoản admin đầu tiên
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None

    # Nhận định AI
    # Khi in key ra màn hình hay ghi log thì chỉ hiện ***
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_MODEL: str = "gemini-3.6-flash"
    # Effort
    GEMINI_THINKING_LEVEL: str | None = "LOW"

    # Bật log chi tiết khi phát triển. Khi demo/nộp bài nên để false.
    DEBUG: bool = False

    # Kết nối sàn (mặc định trỏ về cổng 8001 - máy chủ giả lập)
    SHOPEE_BASE_URL: str = "http://127.0.0.1:8001"
    TIKTOK_BASE_URL: str = "http://127.0.0.1:8001"
    TIKTOK_AUTH_BASE_URL: str = "http://127.0.0.1:8001"

    SHOPEE_AUTH_PAGE_BASE_URL: str = "http://localhost:8001"
    TIKTOK_AUTH_PAGE_BASE_URL: str = "http://localhost:8001"
    # `service_id` của app TikTok (gắn vào link ủy quyền, lấy ở Partner Center)
    TIKTOK_SERVICE_ID: str = "mock_service_id_GIA"

    # Dùng cho luồng kết nối gian hàng mới
    PUBLIC_BACKEND_URL: str = "http://localhost:8000"
    # Sau khi kết nối xong, chuyển trình duyệt về giao diện ở địa chỉ này.
    FRONTEND_URL: str = "http://localhost:5173"
    # Yêu cầu bắt đầu kết nối hết hạn sau N phút (mã ủy quyền của sàn sống 10 phút Shopee / 30 phút TikTok).
    CONNECT_STATE_MINUTES: int = Field(default=10, gt=0)

    # Khóa ứng dụng — tên biến TRÙNG với mock_platform/.env
    # Bắt buộc, thiếu khóa thì dừng ngay lúc khởi động.
    SHOPEE_PARTNER_ID: int
    SHOPEE_PARTNER_KEY: str
    SHOPEE_SHOP_ID: int
    TIKTOK_APP_KEY: str
    TIKTOK_APP_SECRET: str

    # Gian hàng và token ban đầu. Sau lần nạp đầu, token sống trong CSDL, sửa các biến này không ghi đè token đang dùng.
    SHOPEE_SHOP_NAME: str = "Shop C"
    SHOPEE_ACCESS_TOKEN: str
    SHOPEE_REFRESH_TOKEN: str
    TIKTOK_SHOP_A_NAME: str = "Shop A"
    TIKTOK_SHOP_A_CIPHER: str
    TIKTOK_SHOP_A_ACCESS_TOKEN: str
    TIKTOK_SHOP_A_REFRESH_TOKEN: str
    TIKTOK_SHOP_B_NAME: str = "Shop B"
    TIKTOK_SHOP_B_CIPHER: str
    TIKTOK_SHOP_B_ACCESS_TOKEN: str
    TIKTOK_SHOP_B_REFRESH_TOKEN: str

    # Các origin của frontend được phép gọi API (CORS)
    CORS_ALLOW_ORIGINS: list[str] = ["http://localhost:5173"]

    # Tham số tác vụ ngầm
    SYNC_INTERVAL_MINUTES: int = Field(default=10, gt=0)  # chu kỳ kéo API 10p
    SYNC_LOOKBACK_DAYS: int = Field(default=3, gt=0)  # Kéo 3 ngày gần nhất
    SYNC_BACKFILL_FROM: date = date(2026, 1, 1)
    # Còn ≤ N ngày đến refresh_expires_at thì token_status = "expiring"
    TOKEN_EXPIRING_DAYS: int = Field(default=7, gt=0)
    # Bật lịch đồng bộ nền khi chạy `uvicorn app.main:app`, test tắt bằng tham số của tao_ung_dung()
    SYNC_SCHEDULER_ENABLED: bool = True
    # Quét thư mục: 30s
    WATCHER_INTERVAL_SECONDS: int = Field(default=30, gt=0)
    # Bật quét thư mục khi chạy `uvicorn app.main:app`, test tắt bằng tham số của tao_ung_dung().
    WATCHER_ENABLED: bool = True

    # Kiểm tra driver CSDL
    @field_validator("DATABASE_URL")
    @classmethod
    def kiem_tra_tien_to_psycopg(cls, chuoi_ket_noi: str) -> str:
        """
        """
        if not chuoi_ket_noi.startswith(TIEN_TO_KET_NOI_BAT_BUOC):
            phan_dau_chuoi = chuoi_ket_noi[:30]
            raise ValueError(
                f"DATABASE_URL phải bắt đầu bằng '{TIEN_TO_KET_NOI_BAT_BUOC}' "
                f"nhưng đang là '{phan_dau_chuoi}...'. "
                "Dự án dùng psycopg 3; thiếu '+psycopg' sẽ gây lỗi khó hiểu "
                "'No module named psycopg2'."
            )
        return chuoi_ket_noi


# Khởi động Singleton bằng settings
settings = Settings()
