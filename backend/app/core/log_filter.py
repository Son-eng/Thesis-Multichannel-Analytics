"""Che token, khóa, mật khẩu khỏi mọi dòng log, kể cả dòng "Failing row contains" do PostgreSQL sinh ra."""

import logging
import re
import threading

# Mẫu bí mật có thể lọt vào thông báo lỗi; sync_job dùng lại mẫu này.
MAU_BI_MAT = re.compile(r"(access_token|refresh_token|app_secret|sign|partner_key)=[^&\s'\"]+", re.IGNORECASE)

# PostgreSQL chép nguyên dòng vi phạm ràng buộc, có thể chứa token chưa kịp đăng ký.
MAU_DONG_VI_PHAM = re.compile(r"(Failing row contains )\(.*\)")

DAU_CHE = "***"
# Chuỗi quá ngắn không đăng ký, vì che nhầm chữ thường gặp còn hại hơn.
DO_DAI_TOI_THIEU_BI_MAT = 8

_cac_bi_mat = set()
_khoa = threading.Lock()


def dang_ky_bi_mat(gia_tri):
    """Từ nay giá trị này xuất hiện ở đâu trong log cũng bị thay bằng ***."""
    if isinstance(gia_tri, str) and len(gia_tri) >= DO_DAI_TOI_THIEU_BI_MAT:
        with _khoa:
            _cac_bi_mat.add(gia_tri)
        return True
    return False


def cac_bi_mat_da_dang_ky():
    with _khoa:
        return set(_cac_bi_mat)


def xoa_bi_mat_da_dang_ky(gia_tri=None):
    with _khoa:
        if gia_tri is None:
            _cac_bi_mat.clear()
        else:
            _cac_bi_mat.discard(gia_tri)


def che_bi_mat(chuoi):
    if not chuoi:
        return chuoi
    chuoi = MAU_BI_MAT.sub(lambda m: f"{m.group(1)}={DAU_CHE}", chuoi)
    chuoi = MAU_DONG_VI_PHAM.sub(lambda m: f"{m.group(1)}({DAU_CHE})", chuoi)
    with _khoa:
        cac_gia_tri = sorted(_cac_bi_mat, key=len, reverse=True)      # dài trước để bí mật chứa bí mật khác vẫn được che trọn
    for gia_tri in cac_gia_tri:
        if gia_tri in chuoi:
            chuoi = chuoi.replace(gia_tri, DAU_CHE)
    return chuoi


class LocBiMat(logging.Filter):
    """Không loại bản ghi nào, chỉ che chữ nhạy cảm trong bản ghi."""

    def filter(self, record):
        try:
            thong_diep = record.getMessage()
            da_che = che_bi_mat(thong_diep)
            if da_che != thong_diep:
                record.msg, record.args = da_che, None          # đã định dạng xong, không để % thay lại lần nữa
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


LOC = LocBiMat()
_da_cai_dat = False


def cai_dat_loc(cau_hinh=None):
    """Lắp bộ lọc lên mọi handler, cả handler tạo sau, vì bộ lọc ở logger không áp cho logger con."""
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
    from sqlalchemy.engine import make_url

    gia_tri = [cau_hinh.JWT_SECRET, cau_hinh.ADMIN_PASSWORD, cau_hinh.SHOPEE_PARTNER_KEY, cau_hinh.TIKTOK_APP_SECRET,
               cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_REFRESH_TOKEN,
               cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN,
               cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN]
    if cau_hinh.GEMINI_API_KEY is not None:
        gia_tri.append(cau_hinh.GEMINI_API_KEY.get_secret_value())
    try:
        gia_tri.append(make_url(cau_hinh.DATABASE_URL).password)
    except Exception:
        pass
    for mot_gia_tri in gia_tri:
        dang_ky_bi_mat(mot_gia_tri)
