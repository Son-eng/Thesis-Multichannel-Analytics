"""Cấu hình ứng dụng - đọc một lần từ file .env lúc khởi động.

Vì sao cần file này: mọi giá trị thay đổi theo môi trường (chuỗi kết nối
DB, ngưỡng cảnh báo, bật/tắt chế độ debug) được gom về một chỗ duy nhất.
Nhờ vậy phần còn lại của chương trình không cần biết biến môi trường tên
là gì, và khi muốn đổi giá trị thì sửa file .env chứ không sửa code.

Đây cũng là chỗ bắt lỗi cấu hình SỚM: sai kiểu hoặc thiếu biến thì chương
trình dừng ngay lúc khởi động với thông báo rõ ràng, thay vì chạy được một
lúc rồi chết giữa chừng ở chỗ không liên quan.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Đường dẫn tuyệt đối tới backend/.env, tính ngược từ vị trí file này
# (backend/app/config.py -> lùi 2 cấp -> backend/).
#
# Vì sao không dùng đường dẫn tương đối ".env": thư mục làm việc lúc chạy
# không cố định - chạy uvicorn từ backend/, chạy pytest từ gốc project,
# chạy lệnh thử từ chỗ khác nữa. Đường dẫn tương đối sẽ trỏ sai tùy lúc,
# và triệu chứng là "thiếu biến môi trường" chứ không phải "không thấy file",
# rất dễ đi tìm nhầm hướng.
DUONG_DAN_FILE_ENV = Path(__file__).resolve().parent.parent / ".env"

# Tiền tố bắt buộc của chuỗi kết nối. Tách thành hằng số để thông báo lỗi
# bên dưới và điều kiện kiểm tra không bao giờ lệch nhau.
TIEN_TO_KET_NOI_BAT_BUOC = "postgresql+psycopg://"


class Settings(BaseSettings):
    """Toàn bộ cấu hình của ứng dụng, đã kiểm tra kiểu và giá trị hợp lệ.

    Nhận: các biến trong backend/.env. Biến môi trường thật của hệ điều hành
    nếu có cùng tên thì được ưu tiên hơn giá trị trong file.
    Trả: một object có thuộc tính rõ kiểu, dùng được ngay mà không phải tự
    ép kiểu hay tự kiểm tra lại.

    Tên thuộc tính viết tiếng Anh in hoa (không theo quy ước tiếng Việt của
    SPEC §0.1) vì chúng BẮT BUỘC trùng khít tên biến trong .env - đây đúng
    là trường hợp ngoại lệ mà SPEC §0.5 đã nêu.
    """

    model_config = SettingsConfigDict(
        env_file=DUONG_DAN_FILE_ENV,
        env_file_encoding="utf-8",
        # Phân biệt hoa/thường để tên trong .env và tên ở đây phải giống hệt.
        # Nếu cho phép lẫn lộn thì một lỗi gõ sai kiểu "Debug=true" vẫn chạy,
        # và sau này người đọc không biết tên chuẩn rốt cuộc là gì.
        case_sensitive=True,
    )

    # Chuỗi kết nối PostgreSQL. Xem hàm kiểm tra bên dưới để biết vì sao
    # phải có tiền tố "+psycopg".
    DATABASE_URL: str

    # Ngưỡng cảnh báo biến động theo SPEC §9.1: doanh thu kỳ này giảm quá
    # bao nhiêu phần trăm so với kỳ trước thì báo động.
    # Ràng buộc 0 < x <= 100: số âm hoặc 0 thì mọi kỳ đều cảnh báo, lớn hơn
    # 100 thì không kỳ nào cảnh báo được - cả hai đều là lỗi gõ nhầm, chặn
    # ngay còn hơn để chạy rồi ngồi thắc mắc sao không có cảnh báo nào.
    ALERT_DROP_THRESHOLD_PCT: float = Field(gt=0, le=100)

    # Bật log chi tiết khi phát triển. Khi demo/nộp bài nên để false.
    DEBUG: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def kiem_tra_tien_to_psycopg(cls, chuoi_ket_noi: str) -> str:
        """Chặn sớm lỗi thiếu '+psycopg' trong chuỗi kết nối.

        Nhận: giá trị DATABASE_URL vừa đọc từ .env.
        Trả: chính chuỗi đó nếu hợp lệ; nếu không thì ném lỗi kèm hướng dẫn sửa.

        Cần kiểm tra này vì dự án dùng psycopg 3. Viết thiếu thành
        "postgresql://" thì SQLAlchemy mặc định đi tìm psycopg2 và báo
        "No module named 'psycopg2'" - thông báo đó khiến người đọc tưởng là
        cài thiếu thư viện và đi cài psycopg2, trong khi nguyên nhân thật nằm
        ở chuỗi kết nối. Bẫy này đã gặp thật, xem QUY_TRINH.md §4.4.
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


# Một object dùng chung cho cả ứng dụng, tạo lúc import module này.
#
# Vì sao tạo sẵn thay vì để mỗi nơi tự gọi Settings(): đọc và kiểm tra file
# .env chỉ cần làm đúng một lần. Các module khác chỉ việc:
#     from app.config import settings
settings = Settings()
