"""Test bộ lọc che bí mật trong log `app/core/log_filter.py` (chỉ dẫn 022).

Phần thuần (không CSDL) kiểm bộ lọc; phần `db` dựng KỊCH BẢN THẬT: một lệnh ghi `platform_tokens` vi phạm ràng buộc, PostgreSQL
chép cả dòng (kèm token) vào thông điệp lỗi, rồi log qua logger của ứng dụng — có bộ lọc thì token biến mất, không có thì còn
(để chứng minh test có nghĩa).
"""

import asyncio
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import log_filter
from app.core.log_filter import LOC, che_bi_mat, dang_ky_bi_mat
from app.services import token_store
from app.sync import scheduler

TOKEN_GIA = "TOKEN-GIA-DE-KIEM-TRA-777"
TOKEN_REFRESH_GIA = "REFRESH-GIA-DE-KIEM-TRA-888"
CHUA_DANG_KY_1 = "CHUA-DANG-KY-TOKEN-0001"      # đặt ở hằng số: traceback in dòng mã nguồn, không để giá trị nằm trong dòng gọi
CHUA_DANG_KY_2 = "CHUA-DANG-KY-REFRESH-0002"
log = logging.getLogger("app.thu_nghiem")


@pytest.fixture(autouse=True)
def don_dang_ky():
    """Mỗi test bắt đầu với tập bí mật rỗng của test (không đụng bí mật cấu hình đã đăng ký lúc khởi động)."""
    truoc = log_filter.cac_bi_mat_da_dang_ky()
    yield
    for gia_tri in log_filter.cac_bi_mat_da_dang_ky() - truoc:
        log_filter.xoa_bi_mat_da_dang_ky(gia_tri)


@pytest.fixture
def bat_log(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


# ---------------------------------------------------------------- 1. mẫu khớp MAU_BI_MAT

def test_che_chuoi_khop_mau_access_token_trong_thong_diep_thuong(bat_log):
    log.warning("Gọi https://api.sang/v2/order?partner_id=1&access_token=abc123xyz&sign=deadbeef&timestamp=5 lỗi")
    toan_bo = bat_log.text
    assert "access_token=***" in toan_bo and "sign=***" in toan_bo
    assert "abc123xyz" not in toan_bo and "deadbeef" not in toan_bo
    assert "partner_id=1" in toan_bo and "timestamp=5" in toan_bo       # tham số không nhạy cảm giữ nguyên


@pytest.mark.parametrize("khoa", ["access_token", "refresh_token", "app_secret", "sign", "partner_key", "ACCESS_TOKEN"])
def test_moi_khoa_nhay_cam_deu_bi_che(khoa, bat_log):
    log.error("lỗi %s=GIATRI-BAT-KY-12345 xong", khoa)
    assert "GIATRI-BAT-KY-12345" not in bat_log.text and f"{khoa}=***" in bat_log.text


# ---------------------------------------------------------------- 2. giá trị đã đăng ký: thông điệp, traceback, args

def test_gia_tri_da_dang_ky_bi_che_trong_thong_diep(bat_log):
    assert dang_ky_bi_mat(TOKEN_GIA)
    log.warning(f"Token nhận được là {TOKEN_GIA} đó")
    assert TOKEN_GIA not in bat_log.text and "Token nhận được là *** đó" in bat_log.text


def test_gia_tri_da_dang_ky_bi_che_trong_args_dang_s(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)
    log.warning("Lượt %s dùng token %s, tiếp tục %d", "shopee/Shop C", TOKEN_GIA, 3)
    assert TOKEN_GIA not in bat_log.text
    assert "Lượt shopee/Shop C dùng token ***, tiếp tục 3" in bat_log.text


def test_gia_tri_da_dang_ky_bi_che_trong_traceback_cua_logger_exception(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)
    try:
        raise RuntimeError(f"sàn từ chối token {TOKEN_GIA}")
    except RuntimeError:
        log.exception("Lượt lỗi ngoài dự kiến")
    toan_bo = bat_log.text
    assert TOKEN_GIA not in toan_bo
    assert "RuntimeError: sàn từ chối token ***" in toan_bo            # traceback vẫn còn, chỉ che bí mật
    assert "Traceback (most recent call last)" in toan_bo
    assert all(TOKEN_GIA not in (r.exc_text or "") for r in bat_log.records)


def test_traceback_co_chuoi_nguyen_nhan_long_nhau_cung_bi_che(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)
    try:
        try:
            raise ValueError(f"gốc: {TOKEN_GIA}")
        except ValueError as goc:
            raise RuntimeError("bọc ngoài") from goc
    except RuntimeError:
        log.exception("lỗi")
    assert TOKEN_GIA not in bat_log.text and "gốc: ***" in bat_log.text


def test_bi_mat_dai_chua_bi_mat_ngan_van_che_tron(bat_log):
    dang_ky_bi_mat("ABCDEFGH-12345678")
    dang_ky_bi_mat("12345678")
    log.warning("giá trị ABCDEFGH-12345678 và 12345678")
    assert "12345678" not in bat_log.text.replace("***", "")


# ---------------------------------------------------------------- 3. kịch bản thật với PostgreSQL

CAU_GHI = ("INSERT INTO platform_tokens (platform, shop_name, shop_ref, access_token, refresh_token, access_expires_at) "
           "VALUES ('shopee', 'ZZ_TEST_LOC', NULL, :acc, :ref, now())")           # shop_ref NOT NULL ← NULL


class GomBanGhiKhongLoc(logging.Handler):
    """Handler cố ý GỠ bộ lọc: bằng chứng rằng nếu không có bộ lọc thì token lọt vào log."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.removeFilter(LOC)
        self.dong = []

    def emit(self, record):
        self.dong.append(self.format(record))


@pytest.mark.db
def test_kich_ban_that_failing_row_chua_token_khong_con_trong_log_sau_bo_loc(ket_noi_test, caplog):
    dang_ky_bi_mat(TOKEN_GIA)
    dang_ky_bi_mat(TOKEN_REFRESH_GIA)
    khong_loc = GomBanGhiKhongLoc()
    # Chèn ĐẦU danh sách handler: bộ lọc sửa bản ghi DÙNG CHUNG tại chỗ, nên handler không lọc phải in trước khi handler của
    # caplog (có lọc) kịp che bản ghi.
    logging.getLogger().handlers.insert(0, khong_loc)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="sqlalchemy.engine")
    try:
        ket_noi_test.execute(text("SAVEPOINT s1"))
        try:
            ket_noi_test.execute(text(CAU_GHI), {"acc": TOKEN_GIA, "ref": TOKEN_REFRESH_GIA})
        except IntegrityError:
            log.exception("Ghi token lỗi")            # đúng kiểu nơi gọi trong ứng dụng: logger.exception khi có lỗi CSDL
    finally:
        logging.getLogger().removeHandler(khong_loc)

    # Chứng minh lỗi gốc CÓ chứa token (nếu PostgreSQL không in `Failing row` thì test này vô nghĩa → dừng, không giả lập).
    ban_ghi_goc = "\n".join(khong_loc.dong)
    assert "Failing row contains" in ban_ghi_goc, "PostgreSQL môi trường này không in 'Failing row': báo lại, đừng giả lập"
    assert TOKEN_GIA in ban_ghi_goc, "Không bộ lọc: token phải lọt vào log (đây là lỗi gốc cần che)"

    # Qua bộ lọc (handler của caplog): không còn token ở BẤT KỲ bản ghi nào, vẫn còn tên loại lỗi.
    sau_loc = caplog.text + "\n".join(r.getMessage() + (r.exc_text or "") for r in caplog.records)
    assert TOKEN_GIA not in sau_loc and TOKEN_REFRESH_GIA not in sau_loc
    assert "IntegrityError" in sau_loc and "Failing row contains (***)" in sau_loc
    assert "Ghi token lỗi" in sau_loc


@pytest.mark.db
def test_failing_row_chua_dang_ky_van_bi_che_nho_mau_failing_row(engine_test, caplog):
    """Token VỪA nhận từ sàn, chưa kịp đăng ký: phần trong ngoặc của `Failing row` vẫn bị che. Dùng engine DỰNG BẰNG
    `tao_engine` (có hide_parameters như ứng dụng) để chỉ còn đường duy nhất là chữ do PostgreSQL sinh ra."""
    from app import database
    from app.config import settings
    caplog.set_level(logging.DEBUG)
    engine = database.tao_engine(settings.DATABASE_URL, False)
    try:
        with engine.connect() as ket_noi:
            giao_dich = ket_noi.begin()
            try:
                ket_noi.execute(text(CAU_GHI), {"acc": CHUA_DANG_KY_1, "ref": CHUA_DANG_KY_2})
            except IntegrityError:
                log.exception("Ghi token lỗi")
            giao_dich.rollback()
    finally:
        engine.dispose()
    assert CHUA_DANG_KY_1 not in caplog.text and CHUA_DANG_KY_2 not in caplog.text
    assert "Failing row contains (***)" in caplog.text and "IntegrityError" in caplog.text


def test_mau_failing_row_chi_thay_phan_trong_ngoac(bat_log):
    log.error("DETAIL:  Failing row contains (1, shopee, a, SECRET-XYZ, 2026-11-11). Hết.")
    assert "Failing row contains (***)" in bat_log.text and "SECRET-XYZ" not in bat_log.text and "Hết." in bat_log.text


# ---------------------------------------------------------------- 4. không che nhầm, log thường không đổi

@pytest.mark.parametrize("gia_tri", ["", None, "short", "1234567", "true", "shopee", 12345678, b"abcdefghij"])
def test_gia_tri_rong_ngan_hoac_sai_kieu_khong_duoc_dang_ky(gia_tri):
    truoc = log_filter.cac_bi_mat_da_dang_ky()
    assert dang_ky_bi_mat(gia_tri) is False
    assert log_filter.cac_bi_mat_da_dang_ky() == truoc


def test_gia_tri_dung_8_ky_tu_duoc_dang_ky():
    assert dang_ky_bi_mat("12345abc") is True


def test_log_binh_thuong_khong_doi_noi_dung_va_khong_dung_vao_msg_args(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)
    log.info("Bỏ lượt %s/%s: đang có lượt chạy", "shopee", "Shop C")
    ban_ghi = bat_log.records[-1]
    assert ban_ghi.getMessage() == "Bỏ lượt shopee/Shop C: đang có lượt chạy"
    assert ban_ghi.msg == "Bỏ lượt %s/%s: đang có lượt chạy" and ban_ghi.args == ("shopee", "Shop C")   # nguyên vẹn, chưa bị thay


def test_che_bi_mat_tren_chuoi_thuong_tra_nguyen_chuoi():
    assert che_bi_mat("Tỷ lệ hủy 39,7% — không có gì nhạy cảm") == "Tỷ lệ hủy 39,7% — không có gì nhạy cảm"
    assert che_bi_mat("") == "" and che_bi_mat(None) is None


# ---------------------------------------------------------------- 5. an toàn với % và Unicode

def test_thong_diep_co_phan_tram_va_tieng_viet_khong_lam_hong_log(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)
    log.warning("Doanh thu giảm 30%% — Đơn hàng Hà Nội, Đà Nẵng, Thành phố Hồ Chí Minh; token %s", TOKEN_GIA)
    log.warning("Chuỗi có dấu % lẻ loi và token " + TOKEN_GIA)
    log.warning("Số 100%% đúng: %s", "Ư Ơ Â Ê Ô ă đ")
    toan_bo = bat_log.text
    assert TOKEN_GIA not in toan_bo
    assert "Doanh thu giảm 30% — Đơn hàng Hà Nội, Đà Nẵng, Thành phố Hồ Chí Minh; token ***" in toan_bo
    assert "Số 100% đúng: Ư Ơ Â Ê Ô ă đ" in toan_bo
    assert "dấu % lẻ loi" in toan_bo


def test_bo_loc_loi_khong_lam_mat_dong_log(bat_log, monkeypatch):
    def hong(chuoi):
        raise RuntimeError("bộ lọc hỏng")
    monkeypatch.setattr(log_filter, "che_bi_mat", hong)
    log.warning("vẫn phải ra dòng này")
    assert "vẫn phải ra dòng này" in bat_log.text


# ---------------------------------------------------------------- 6. tiến trình nền (scheduler)

def test_scheduler_ghi_log_loi_ngoai_du_kien_qua_bo_loc_va_co_ten_loai_loi(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)

    def ham_dong_bo_hong(san, ten_shop):
        raise RuntimeError(f"không ghi được token {TOKEN_GIA} (access_token=raw999888)")

    ket_qua = asyncio.run(scheduler.chay_mot_vong([("shopee", "Shop C")], ham_dong_bo_hong))
    assert ket_qua == [("shopee", "Shop C", "loi")]
    toan_bo = bat_log.text
    assert TOKEN_GIA not in toan_bo and "raw999888" not in toan_bo
    assert "Lượt đồng bộ shopee/Shop C lỗi ngoài dự kiến (RuntimeError)" in toan_bo      # tên loại lỗi ở đầu dòng
    assert "Traceback (most recent call last)" in toan_bo                                 # vẫn giữ traceback để gỡ lỗi


def test_scheduler_loi_lay_danh_sach_shop_cung_qua_bo_loc(bat_log):
    dang_ky_bi_mat(TOKEN_GIA)

    def lay_hong():
        raise ConnectionError(f"mất kết nối, mật khẩu {TOKEN_GIA}")

    async def chay():
        dung_truoc = asyncio.Event()
        tac_vu = asyncio.create_task(scheduler.chay_lich(dung_truoc, lay_hong, lambda s, t: None, 0.001))
        await asyncio.sleep(0.3)
        dung_truoc.set()
        await asyncio.wait_for(tac_vu, timeout=5)
    asyncio.run(chay())
    assert TOKEN_GIA not in bat_log.text
    assert "Không lấy được danh sách shop để đồng bộ (ConnectionError)" in bat_log.text


# ---------------------------------------------------------------- lắp đặt và đăng ký ở nơi nạp token

def test_handler_tao_sau_khi_cai_dat_tu_co_bo_loc():
    handler = logging.StreamHandler()
    assert LOC in handler.filters


def test_handler_da_ton_tai_truoc_khi_cai_dat_duoc_gan_bo_loc_khi_cai_dat():
    """uvicorn dựng handler TRƯỚC khi nạp ứng dụng: cai_dat_loc phải gắn bộ lọc cả vào handler đã có."""
    handler = logging.StreamHandler()
    handler.removeFilter(LOC)                        # giả lập handler có từ trước
    assert LOC not in handler.filters
    log_filter.cai_dat_loc()
    assert LOC in handler.filters


def test_cai_dat_loc_dang_ky_cac_khoa_trong_cau_hinh():
    from app.config import settings
    cac_bi_mat = log_filter.cac_bi_mat_da_dang_ky()
    assert settings.JWT_SECRET in cac_bi_mat
    assert settings.SHOPEE_PARTNER_KEY in cac_bi_mat and settings.TIKTOK_APP_SECRET in cac_bi_mat
    if settings.GEMINI_API_KEY is not None and len(settings.GEMINI_API_KEY.get_secret_value()) >= 8:
        assert settings.GEMINI_API_KEY.get_secret_value() in cac_bi_mat
    from sqlalchemy.engine import make_url
    mat_khau_csdl = make_url(settings.DATABASE_URL).password
    assert mat_khau_csdl in cac_bi_mat


@pytest.mark.db
def test_doc_token_va_ghi_token_dang_ky_token_vao_bo_loc(tao_phien_test, ket_noi_test, monkeypatch):
    from app.config import settings
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    log_filter.xoa_bi_mat_da_dang_ky(settings.SHOPEE_ACCESS_TOKEN)
    log_filter.xoa_bi_mat_da_dang_ky(settings.SHOPEE_REFRESH_TOKEN)
    dong = token_store.doc_token("shopee", settings.SHOPEE_SHOP_NAME)
    assert dong.access_token in log_filter.cac_bi_mat_da_dang_ky()            # đọc token → đã đăng ký
    assert dong.refresh_token in log_filter.cac_bi_mat_da_dang_ky()
    token_store.ghi_token("shopee", settings.SHOPEE_SHOP_NAME, {
        "access_token": TOKEN_GIA, "refresh_token": TOKEN_REFRESH_GIA, "access_expires_at": dong.access_expires_at,
        "refresh_expires_at": dong.refresh_expires_at})
    assert TOKEN_GIA in log_filter.cac_bi_mat_da_dang_ky() and TOKEN_REFRESH_GIA in log_filter.cac_bi_mat_da_dang_ky()


@pytest.mark.db
def test_lam_moi_va_ghi_dang_ky_token_moi_truoc_khi_ghi(tao_phien_test, ket_noi_test, monkeypatch):
    from app.config import settings
    ket_noi_test.execute(text("DELETE FROM platform_tokens"))
    monkeypatch.setattr(token_store, "SessionLocal", tao_phien_test)
    token_store.nap_san_tu_cau_hinh(settings)
    token_moi = {}

    def ham_lam_moi(refresh_token, shop_ref):
        token_moi["da_dang_ky_luc_goi"] = TOKEN_GIA in log_filter.cac_bi_mat_da_dang_ky()
        return {"access_token": TOKEN_GIA, "refresh_token": TOKEN_REFRESH_GIA, "expire_in": 14400}

    token_store.lam_moi_va_ghi("shopee", settings.SHOPEE_SHOP_NAME, ham_lam_moi)
    assert token_moi["da_dang_ky_luc_goi"] is False                          # trước khi sàn trả lời thì chưa biết
    assert TOKEN_GIA in log_filter.cac_bi_mat_da_dang_ky() and TOKEN_REFRESH_GIA in log_filter.cac_bi_mat_da_dang_ky()
