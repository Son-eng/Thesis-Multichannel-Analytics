"""Fixture dùng chung cho các test cần PostgreSQL thật (marker `db`).

Cách test tự dọn dữ liệu — không xóa gì thật sự:
- Mỗi test mở MỘT kết nối và một giao dịch bao ngoài.
- Mọi Session trong test gắn vào kết nối đó với join_transaction_mode=
  "create_savepoint": khi code gọi commit(), SQLAlchemy chỉ chốt một SAVEPOINT
  bên trong, không chốt giao dịch ngoài.
- Hết test → rollback giao dịch ngoài → CSDL trở về đúng như trước test, kể
  cả dữ liệu đã nạp tay bằng lệnh nap_file.
Nhờ vậy test chạy lại bao nhiêu lần cũng ra cùng kết quả và không làm mất dữ
liệu sinh viên đang dùng để xem dashboard.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from may_chu_gia_lap import THU_MUC_MOCK, MayChuGiaLap, nap_module_mock


@pytest.fixture(scope="session")
def engine_test():
    """Engine tới CSDL dự án; không kết nối được thì skip mọi test dùng nó."""
    # connect_timeout: Docker tắt thì báo lỗi sau tối đa 3 giây thay vì treo.
    engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as ket_noi:
            ket_noi.execute(text("SELECT 1"))
    except OperationalError:
        engine.dispose()
        pytest.skip("Không kết nối được PostgreSQL (Docker chưa chạy?) — bỏ qua test marker db")
    yield engine
    engine.dispose()


@pytest.fixture
def ket_noi_test(engine_test):
    """Một kết nối với giao dịch bao ngoài, luôn rollback khi hết test.

    Xóa sạch 3 bảng NGAY TRONG giao dịch này để test bắt đầu từ bảng rỗng
    (đếm "1.774 dòng thêm mới" mới có nghĩa). Lệnh xóa cũng bị rollback ở cuối,
    nên dữ liệu thật vẫn còn nguyên.
    """
    ket_noi = engine_test.connect()
    giao_dich_ngoai = ket_noi.begin()
    ket_noi.execute(text("DELETE FROM orders_shopee"))
    ket_noi.execute(text("DELETE FROM orders_tiktok"))
    ket_noi.execute(text("DELETE FROM sync_runs"))
    yield ket_noi
    giao_dich_ngoai.rollback()
    ket_noi.close()


@pytest.fixture
def tao_phien_test(ket_noi_test):
    """Khuôn tạo Session gắn vào kết nối test; commit() chỉ chốt SAVEPOINT."""
    return sessionmaker(bind=ket_noi_test, join_transaction_mode="create_savepoint")


@pytest.fixture
def phien_test(tao_phien_test):
    """Một Session gắn vào kết nối test."""
    phien: Session = tao_phien_test()
    yield phien
    phien.close()


# ---------------- Máy chủ giả lập trên socket thật (bước 9, chỉ dẫn 009) ----------------

@pytest.fixture(scope="session")
def bat_may_chu_gia_lap():
    """Hàm bật một máy chủ giả lập mới trên socket thật; mọi máy chủ đã bật tắt khi hết phiên test.

    bat_may_chu_gia_lap(**ghi_de) — ghi_de là biến cấu hình của mock
    (MOCK_FAULT_RATE, MOCK_ESCROW_MODE, MOCK_*_TTL_SECONDS…) đè lên
    mock_platform/.env.example (toàn khóa giả, trùng giá trị backend/.env).
    Mỗi lần gọi là một máy chủ mới với bảng token sạch. Dữ liệu CSV chỉ dựng
    một lần cho cả phiên (mất vài giây mỗi lần dựng).
    """
    config_mock, data_builder, main_mock = nap_module_mock()
    cau_hinh_mau = config_mock.doc_cau_hinh(THU_MUC_MOCK / ".env.example")
    du_lieu_shopee = data_builder.dung_du_lieu_shopee()
    du_lieu_tiktok = data_builder.dung_du_lieu_tiktok()
    cac_may_chu = []

    def bat(**ghi_de):
        ung_dung = main_mock.tao_ung_dung(
            cau_hinh_mau.model_copy(update=ghi_de),
            du_lieu_shopee=du_lieu_shopee, du_lieu_tiktok=du_lieu_tiktok,
        )
        may_chu = MayChuGiaLap(ung_dung).bat()
        cac_may_chu.append(may_chu)
        return may_chu

    yield bat
    for may_chu in cac_may_chu:
        may_chu.tat()
