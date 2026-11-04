"""Kết nối tới PostgreSQL - tạo engine và cấp phiên làm việc (session).

Vì sao cần file này: gom toàn bộ phần "nói chuyện với cơ sở dữ liệu" về một
chỗ. Các module khác (parser, service, API) chỉ xin một phiên làm việc rồi
dùng, không cần biết chuỗi kết nối nằm đâu hay bể kết nối cấu hình thế nào.

Luồng chạy: config.py đọc .env -> file này lấy DATABASE_URL tạo engine ->
engine giữ sẵn bể kết nối -> SessionLocal sinh phiên từ engine đó ->
lay_phien_db() cấp phiên cho nơi cần và đảm bảo đóng lại.

Ngoài ra file này có `Base` — lớp cha chung của mọi model trong app/models/.
Alembic đọc `Base.metadata` để biết CSDL phải có những bảng nào.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# engine giữ sẵn một "bể" kết nối (connection pool) tới PostgreSQL.
#
# Cả ứng dụng dùng CHUNG một engine duy nhất. Tạo nhiều engine thì mỗi cái
# mở một bể riêng, vừa lãng phí vừa dễ chạm giới hạn số kết nối của Postgres
# (mặc định 100) khi có nhiều request cùng lúc.
engine = create_engine(
    settings.DATABASE_URL,
    # echo=True thì SQLAlchemy in ra mọi câu SQL nó sinh ra.
    # Rất đáng bật khi đang học và khi debug: nhìn thấy truy vấn thật thay vì
    # phải đoán ORM dịch ra cái gì. Khi demo thì DEBUG=false nên tự tắt.
    echo=settings.DEBUG,
    # Thử ping kết nối trước khi đem ra dùng, nếu chết thì lặng lẽ thay bằng
    # kết nối mới.
    #
    # Cần thiết vì container Postgres có thể bị tắt/bật giữa buổi làm việc
    # (docker compose down rồi up). Khi đó các kết nối cũ đang nằm trong bể
    # đã chết, nhưng bể không tự biết - truy vấn kế tiếp sẽ lỗi
    # "server closed the connection unexpectedly" ở một chỗ hoàn toàn không
    # liên quan, rất khó lần ra nguyên nhân.
    pool_pre_ping=True,
    # Ép múi giờ phiên là UTC: cột `timestamp` không có múi giờ, nên `now()` và mọi
    # datetime có múi giờ ghi vào đều quy về UTC; lớp API đổi sang giờ VN khi đọc
    # (app/api/sync.py). Không ép thì kết quả phụ thuộc cài đặt của máy chủ PostgreSQL.
    connect_args={"options": "-c timezone=UTC"},
)

# Khuôn để tạo ra các phiên làm việc. Mỗi phiên là một đơn vị công việc với
# DB: mở -> đọc/ghi -> commit hoặc rollback -> đóng.
SessionLocal = sessionmaker(
    bind=engine,
    # autoflush=False: không tự động đẩy thay đổi xuống DB giữa chừng.
    # Nếu để bật, SQLAlchemy có thể tự gửi INSERT/UPDATE vào những thời điểm
    # bất ngờ (ngay trước một câu SELECT chẳng hạn) - thứ tự câu lệnh trở nên
    # khó đoán, và đó đúng là thứ không giải thích được trước hội đồng.
    autoflush=False,
    # Không tự commit: phải gọi commit() rõ ràng thì dữ liệu mới được ghi thật.
    # Quan trọng với nghiệp vụ upload file (SPEC §4): nếu đang nạp dở mà gặp
    # lỗi thì rollback toàn bộ, không để lại trong DB một file nhập nửa chừng.
    autocommit=False,
)


class Base(DeclarativeBase):
    """Lớp cha chung của mọi model (bảng) trong app/models/.

    Mỗi lớp con khai báo một bảng; SQLAlchemy gom tất cả vào `Base.metadata`
    — bản mô tả toàn bộ schema mà Alembic so với CSDL thật để sinh migration.
    Cần đúng MỘT Base cho cả ứng dụng: 2 Base là 2 metadata riêng, Alembic
    chỉ thấy một nửa số bảng.

    Để trống có chủ đích: chưa cần cấu hình chung nào cho mọi bảng.
    """


def lay_phien_db() -> Iterator[Session]:
    """Cấp một phiên làm việc với DB, đảm bảo luôn đóng lại sau khi dùng xong.

    Nhận: không nhận tham số nào.
    Trả: sinh ra (yield) đúng một Session, rồi đóng nó lại khi bên dùng xong.

    Cần hàm này để FastAPI tự lo vòng đời của phiên: mỗi request được cấp một
    phiên riêng, và phiên đó chắc chắn được đóng kể cả khi request ném lỗi
    giữa chừng. Quên đóng phiên thì kết nối không được trả về bể, chạy một lúc
    sẽ cạn kết nối và toàn hệ thống treo.

    Dùng ở tầng API (từ bước 9) theo dạng:
        def doc_kpi(phien: Session = Depends(lay_phien_db)):
            ...
    """
    phien = SessionLocal()
    try:
        yield phien
    finally:
        # Đặt trong finally để dù thân hàm gọi có ném lỗi thì phiên vẫn đóng.
        phien.close()
