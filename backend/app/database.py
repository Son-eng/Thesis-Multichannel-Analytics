# Import thư viện
## Định kiểu dữ liệu của hàm sinh phiên lay_phien_db()
from collections.abc import Iterator
## Declarative: Lớp nền của SQLAlchemy để định nghĩa các bảng dữ liệu bằng Python Class,
## Khai báo một Class Python, SQLAlchemy sẽ hiểu Class đó đại diện cho bảng nào
## các thuộc tính đại diện cho cột nào, và tự động lo hết việc chuyển đổi qua lại giữa CSDL và mã Python -> ORM (kế thừa)
## Còn lại là bộ công cụ quản lý kết nối và phiên làm việc
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
## Đọc chuỗi kết nối DATABASE_URL và cờ DEBUG từ config.py
from app.config import settings

def tao_engine(url, debug):
    return create_engine(
        url,
        # DEBUG=True thì sẽ in hết các câu lệnh SQL lên console
        echo=debug,
        # Ẩn toàn bộ giá trị tham số trong log như access token, refresh, mật khẩu kể cả khi để in ra console
        hide_parameters=True,
        # Khởi động lại container PostgreSQL làm các kết nối trong pool chết mà pool không biết, lúc này sẽ gửi ping 
        # nếu chết thì tạo kết nối mới
        pool_pre_ping=True,
        # Thống nhất giờ về 1 kiểu ở mọi máy chủ
        connect_args={"options": "-c timezone=UTC"},
    )

engine = tao_engine(settings.DATABASE_URL, settings.DEBUG)

# Khuôn tạo các phiên làm việc:
# DB: mở -> đọc/ghi -> commit hoặc rollback -> đóng.
SessionLocal = sessionmaker(
    bind=engine,
    # Kiểm soát được dữ liệu được gửi đi, không cho SQLAlchemy đẩy các thay đổi xuống DB trước khi có lệnh
    autoflush=False,
    # Phải gọi .commit() thì mới lưu dữ liệu vào DB -> tính toàn vẹn ACID
    autocommit=False,
)

class Base(DeclarativeBase):
    """Các model đều kế thừa từ lớp Base này, Base.metadata gom định nghĩa các cột để alembic vào đọc và sinh 
    các file migration"""

# Hàm dạng Generator dùng khóa yield
# Vòng đời:
## Request từ người dùng -> gọi lay_phien_db() -> tạo phiên mới -> "yield phien" trao cho hàm xử lý API truy vấn
## Sau khi hàm API trả về kết quả (dù thành công hay sập lỗi) -> "phien.close()" luôn thực thi để đóng phiên lại
def lay_phien_db() -> Iterator[Session]:
    """"""
    phien = SessionLocal()
    try:
        yield phien
    finally: # finally đảm bảo lệnh close luôn thực thi
        phien.close()
