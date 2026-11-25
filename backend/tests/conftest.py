import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core import log_filter
from may_chu_gia_lap import THU_MUC_MOCK, MayChuGiaLap, nap_module_mock

# Mọi test chạy với bộ lọc che bí mật đã lắp, như khi chạy thật.
log_filter.cai_dat_loc(settings)


@pytest.fixture(scope="session")
def engine_test():
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
    ket_noi = engine_test.connect()
    giao_dich_ngoai = ket_noi.begin()
    ket_noi.execute(text("DELETE FROM orders"))
    ket_noi.execute(text("DELETE FROM sync_runs"))
    yield ket_noi
    giao_dich_ngoai.rollback()
    ket_noi.close()


@pytest.fixture
def tao_phien_test(ket_noi_test):
    return sessionmaker(bind=ket_noi_test, join_transaction_mode="create_savepoint")


@pytest.fixture
def phien_test(tao_phien_test):
    phien: Session = tao_phien_test()
    yield phien
    phien.close()


@pytest.fixture(scope="session")
def bat_may_chu_gia_lap():
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


@pytest.fixture(autouse=True)
def bcrypt_nhanh(monkeypatch):
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 4)


@pytest.fixture
def tao_nguoi(phien_test):
    from app.core import security
    from app.models.user import User

    def _tao(ten, vai_tro="admin", mat_khau="mat-khau-thu-1"):
        nguoi = User(username=ten, password_hash=security.bam_mat_khau(mat_khau), role=vai_tro)
        phien_test.add(nguoi)
        phien_test.flush()
        return nguoi
    return _tao


def tieu_de_dang_nhap(nguoi):
    from app.core import security
    return {"Authorization": f"Bearer {security.tao_token(nguoi.id)}"}


@pytest.fixture
def tieu_de_admin(tao_nguoi):
    return tieu_de_dang_nhap(tao_nguoi("admin_thu", "admin"))


@pytest.fixture
def tieu_de_user(tao_nguoi):
    return tieu_de_dang_nhap(tao_nguoi("user_thu", "user"))


@pytest.fixture
def gia_dang_nhap():
    from app.core.deps import yeu_cau_dang_nhap
    from app.models.user import User

    def _gan(ung_dung, vai_tro="user"):
        ung_dung.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=-1, username="nguoi_thu", role=vai_tro)
    return _gan
