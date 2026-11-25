"""Cấu hình Alembic chạy migration (SPEC §3, bước 6).

Luồng: Alembic gọi file này mỗi lần chạy lệnh (`upgrade`, `downgrade`,
`revision --autogenerate`). File này cho Alembic biết 2 thứ:
1. Kết nối tới CSDL nào — lấy từ app.config.settings (đọc backend/.env),
   không chép chuỗi kết nối vào alembic.ini.
2. Schema mong muốn là gì — `Base.metadata`, chứa mọi bảng khai báo trong
   app/models/. Khi autogenerate, Alembic so metadata này với CSDL thật để
   sinh ra các lệnh tạo/sửa bảng.

Chạy từ thư mục backend/ (alembic.ini có prepend_sys_path = . nên import
được gói app):
    .venv\\Scripts\\python -m alembic upgrade head
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.config import settings
from app.database import Base

# Phải import các model để autogenerate không sinh lệnh xóa bảng.
from app.models import order, platform_token, sync_run, user  # noqa: F401

config = context.config

# Cấu hình log theo mục [loggers] trong alembic.ini (in ra các bước migration).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata # cho alembic biết cấu trúc mong muốn là gì


def chay_migration_offline() -> None: # Kiểm tra, xuất file .sql nộp/bàn giao
    """Không kết nối CSDL, chỉ đọc file migration, dịch lệnh SQL thuần túy và in ra màn hình.    """
    context.configure(
        url=settings.DATABASE_URL, # cho alembic biết kết nối CSDL nào
        target_metadata=target_metadata,
        # Ghi thẳng giá trị vào câu SQL thay vì dùng tham số, để SQL in ra
        # đọc được và chạy lại được.
        literal_binds=True, # không để các tham số dạng ẩn, ghi thẳng giá trị vào câu lệnh SQL 
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def chay_migration_online() -> None: # Nạp cấu trúc bảng khi cài đặt hệ thống
    """Kết nối CSDL thật và chạy migration: kiểm tra bảng alembic_version -> chạy lệnh thật.
    """
    engine_migration = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool) # Mở 1 kết nối duy nhất, chạy xong là đóng, không tạo pool gây lãng phí
    with engine_migration.connect() as ket_noi:
        context.configure(connection=ket_noi, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode(): # Chạy offline hay online theo lệnh mình
    chay_migration_offline()
else:
    chay_migration_online()
