"""Che bí mật (token, khóa, mật khẩu) khỏi MỌI dòng log của tiến trình (chỉ dẫn 022).

Vì sao cần một nơi tập trung: `hide_parameters=True` chỉ che tham số mà SQLAlchemy tự đính vào thông điệp lỗi; nó KHÔNG che
chữ do chính PostgreSQL sinh ra, ví dụ `DETAIL: Failing row contains (..., <access_token>, <refresh_token>, ...)` khi một
lệnh ghi `platform_tokens` vi phạm ràng buộc. Chữ đó đi vào traceback của `logger.exception(...)` ở nhiều nơi. Che ở từng
chỗ ghi log thì sót; che ở bộ lọc thì mọi log (của ứng dụng, uvicorn, sqlalchemy.engine, httpx2) đều qua.

Bộ lọc làm trên MỖI bản ghi trước khi in:
  (a) thông điệp đã định dạng (`record.getMessage()`, tức đã thay `%s` bằng `args`);
  (b) traceback đã định dạng (`exc_info` → `exc_text`) và `stack_info`;
  (c) thay mọi chuỗi khớp `MAU_BI_MAT` (`access_token=...`), mọi GIÁ TRỊ BÍ MẬT ĐÃ ĐĂNG KÝ (`dang_ky_bi_mat`) và phần trong
      ngoặc của `Failing row contains (...)` bằng `***`.
Bản ghi không có gì cần che được giữ NGUYÊN (không đổi `msg`/`args`).

Giới hạn (nói rõ, không phải bảo đảm tuyệt đối): chỉ che được (1) chuỗi khớp mẫu, (2) giá trị ĐÃ ĐĂNG KÝ, (3) dòng
`Failing row`. Một token chưa đăng ký, không nằm trong URL/mẫu và không nằm trong `Failing row` thì không che được.
"""

import logging
import re
import threading

# Mẫu giá trị bí mật có thể lọt vào thông báo lỗi (URL có query, chuỗi lỗi của thư viện). Định nghĩa MỘT lần ở đây;
# `sync/sync_job.py` dùng lại cho `lam_sach_thong_diep`.
MAU_BI_MAT = re.compile(r"(access_token|refresh_token|app_secret|sign|partner_key)=[^&\s'\"]+", re.IGNORECASE)

# Dòng PostgreSQL chép nguyên cả dòng vi phạm ràng buộc: có thể chứa giá trị chưa kịp đăng ký (token mới nhận từ sàn).
MAU_DONG_VI_PHAM = re.compile(r"(Failing row contains )\(.*\)")

DAU_CHE = "***"
# Giá trị bí mật ngắn hơn mức này không đăng ký: che nhầm các chuỗi thường gặp ("true", "shopee"...) còn hại hơn lợi.
DO_DAI_TOI_THIEU_BI_MAT = 8

_cac_bi_mat = set()
_khoa = threading.Lock()


def dang_ky_bi_mat(gia_tri):
    """Đăng ký một giá trị bí mật: từ nay mọi nơi nó xuất hiện trong log đều bị thay bằng `***`.

    Bỏ qua None, không phải chuỗi, hoặc ngắn hơn DO_DAI_TOI_THIEU_BI_MAT. Trả True nếu đã đăng ký.
    Gọi ở nơi nạp/ghi token (`services/token_store.py`, `sync/sync_job.py`) và lúc khởi động cho các khóa trong cấu hình.
    """
    if isinstance(gia_tri, str) and len(gia_tri) >= DO_DAI_TOI_THIEU_BI_MAT:
        with _khoa:
            _cac_bi_mat.add(gia_tri)
        return True
    return False


def cac_bi_mat_da_dang_ky():
    """Bản sao tập giá trị đang đăng ký (cho test)."""
    with _khoa:
        return set(_cac_bi_mat)


def xoa_bi_mat_da_dang_ky(gia_tri=None):
    """Bỏ một giá trị (hoặc tất cả nếu không truyền) khỏi tập đăng ký — chỉ để test dọn dẹp."""
    with _khoa:
        if gia_tri is None:
            _cac_bi_mat.clear()
        else:
            _cac_bi_mat.discard(gia_tri)


def che_bi_mat(chuoi):
    """Thay mọi bí mật trong `chuoi` bằng `***`: mẫu `khóa=giá_trị`, giá trị đã đăng ký, dòng `Failing row`."""
    if not chuoi:
        return chuoi
    chuoi = MAU_BI_MAT.sub(lambda m: f"{m.group(1)}={DAU_CHE}", chuoi)
    chuoi = MAU_DONG_VI_PHAM.sub(lambda m: f"{m.group(1)}({DAU_CHE})", chuoi)
    with _khoa:
        cac_gia_tri = sorted(_cac_bi_mat, key=len, reverse=True)      # dài trước: bí mật chứa bí mật khác vẫn che trọn
    for gia_tri in cac_gia_tri:
        if gia_tri in chuoi:
            chuoi = chuoi.replace(gia_tri, DAU_CHE)
    return chuoi


class LocBiMat(logging.Filter):
    """Bộ lọc không bao giờ loại bản ghi (luôn trả True), chỉ che chữ nhạy cảm ngay trong bản ghi."""

    def filter(self, record):
        try:
            thong_diep = record.getMessage()
            da_che = che_bi_mat(thong_diep)
            if da_che != thong_diep:
                record.msg, record.args = da_che, None          # đã định dạng xong: không để `%` tự thay lại
            if record.exc_info:
                if not record.exc_text:
                    record.exc_text = logging.Formatter().formatException(record.exc_info)
                record.exc_text = che_bi_mat(record.exc_text)
            elif record.exc_text:
                record.exc_text = che_bi_mat(record.exc_text)
            if record.stack_info:
                record.stack_info = che_bi_mat(record.stack_info)
        except Exception:                                       # bộ lọc hỏng không được làm mất dòng log
            pass
        return True


# Một thể hiện dùng chung: `addFilter` không thêm trùng cùng một đối tượng.
LOC = LocBiMat()
_da_cai_dat = False


def cai_dat_loc(cau_hinh=None):
    """Lắp bộ lọc lên MỌI handler (đang có và sẽ tạo sau), rồi đăng ký các bí mật trong cấu hình. Gọi lại nhiều lần vẫn an toàn.

    Vì sao lắp lên handler chứ không lên root logger: bộ lọc của một logger chỉ áp cho bản ghi do CHÍNH logger đó phát ra,
    không áp cho logger con. Handler thì nhận mọi bản ghi đi qua, nên lắp ở handler mới phủ hết (ứng dụng, uvicorn,
    sqlalchemy.engine, httpx2, handler của pytest `caplog`).
    - Handler đã tồn tại (uvicorn dựng sẵn trước khi nạp ứng dụng): lấy từ danh sách nội bộ `logging._handlerList`.
    - Handler tạo sau (echo của SQLAlchemy, caplog): bọc `logging.Handler.__init__` để tự gắn bộ lọc.
    """
    global _da_cai_dat
    if not _da_cai_dat:
        goc_init = logging.Handler.__init__

        def init_co_loc(self, *tham_so, **tu_khoa):
            goc_init(self, *tham_so, **tu_khoa)
            self.addFilter(LOC)
        logging.Handler.__init__ = init_co_loc
        _da_cai_dat = True
    for tham_chieu in list(logging._handlerList):                # noqa: SLF001 — danh sách yếu của mọi handler
        handler = tham_chieu()
        if handler is not None:
            handler.addFilter(LOC)
    if cau_hinh is not None:
        dang_ky_bi_mat_cau_hinh(cau_hinh)


def dang_ky_bi_mat_cau_hinh(cau_hinh):
    """Đăng ký các bí mật có trong cấu hình: khóa Gemini, khóa JWT, mật khẩu admin và CSDL, khóa sàn, token ban đầu."""
    from sqlalchemy.engine import make_url

    gia_tri = [cau_hinh.JWT_SECRET, cau_hinh.ADMIN_PASSWORD, cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.TIKTOK_APP_SECRET,
               cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_REFRESH_TOKEN,
               cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN,
               cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN]
    if cau_hinh.GEMINI_API_KEY is not None:
        gia_tri.append(cau_hinh.GEMINI_API_KEY.get_secret_value())
    try:
        gia_tri.append(make_url(cau_hinh.DATABASE_URL).password)
    except Exception:                                           # chuỗi kết nối sai đã bị config.py chặn từ trước
        pass
    for mot_gia_tri in gia_tri:
        dang_ky_bi_mat(mot_gia_tri)
