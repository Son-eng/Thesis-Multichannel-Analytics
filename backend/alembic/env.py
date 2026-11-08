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

# Import từng module model chỉ để các lớp model được khai báo, nhờ đó bảng của
# chúng có mặt trong Base.metadata. Thiếu một dòng ở đây thì autogenerate
# tưởng bảng đó không còn cần và sinh lệnh XÓA bảng.
from app.models import order, platform_token, sync_run, user  # noqa: F401

config = context.config

# Cấu hình log theo mục [loggers] trong alembic.ini (in ra các bước migration).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def chay_migration_offline() -> None:
    """Sinh câu SQL ra màn hình thay vì chạy vào CSDL (`alembic upgrade --sql`).

    Nhận/trả: không. Cần hàm này để xem trước SQL sẽ chạy — hữu ích khi đối
    chiếu migration với CREATE TABLE ở SPEC §3 mà không đụng vào CSDL.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        # Ghi thẳng giá trị vào câu SQL thay vì dùng tham số, để SQL in ra
        # đọc được và chạy lại được.
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def chay_migration_online() -> None:
    """Kết nối CSDL thật và chạy migration.

    Nhận/trả: không. Tạo engine riêng thay vì dùng engine của app/database.py:
    engine đó bật echo theo DEBUG và giữ bể kết nối; một lượt migration chỉ
    cần một kết nối dùng xong là đóng (NullPool).
    """
    engine_migration = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    with engine_migration.connect() as ket_noi:
        context.configure(connection=ket_noi, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    chay_migration_offline()
else:
    chay_migration_online()
