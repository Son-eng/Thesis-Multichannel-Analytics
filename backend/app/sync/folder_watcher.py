"""Quét thư mục nạp file tự động — đường DỰ PHÒNG (SPEC §2.4).

Cấu trúc (gốc `data/`): inbox/<sàn>/ → processed/<sàn>/ hoặc failed/<sàn>/.
Mỗi `WATCHER_INTERVAL_SECONDS` (30 giây) quét một lần. Quy tắc "file đã lưu xong":
chỉ xử lý khi kích thước KHÔNG ĐỔI qua hai lần quét liên tiếp (file đang copy dở
thì kích thước còn tăng). Tên file do nhân viên đặt nên sàn được xác định bằng
thư mục chứa file, không đoán từ tên.

Mỗi file đi qua `nap_file(san, đường_dẫn, tên_shop, "file_auto")` — cùng hàm với
đường chạy tay và nút tải file, nên giao dịch, `sync_runs` và chống trùng giống hệt.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

CAC_SAN = ("shopee", "tiktok")


class TrangThaiQuet:
    """Trạng thái cho GET /api/watcher/status: lần quét gần nhất và số file đang chờ."""

    def __init__(self):
        self.last_scan_at = None      # datetime có múi giờ, None nếu chưa quét lần nào
        self.pending_files = 0


def thu_muc_goc_mac_dinh():
    """`data/` ở gốc project (backend/app/sync/folder_watcher.py → lùi 4 cấp)."""
    return Path(__file__).resolve().parents[3] / "data"


def liet_ke_file(thu_muc_goc, san):
    """Các file `.csv` đang nằm trong inbox/<sàn>/ (bỏ file ẩn như .gitkeep), sắp theo tên."""
    thu_muc = Path(thu_muc_goc) / "inbox" / san
    if not thu_muc.is_dir():
        return []
    return sorted(f for f in thu_muc.iterdir()
                  if f.is_file() and f.suffix.lower() == ".csv" and not f.name.startswith("."))


def ten_shop_cua_san(san):
    """Shopee: file không có cột shop → dùng tên shop cấu hình; TikTok: lấy từ cột `Shop` trong file."""
    return settings.SHOPEE_SHOP_NAME if san == "shopee" else None


def _dich_den(thu_muc_goc, nhom, san, file):
    """processed/<sàn>/<tên>__YYYYmmdd_HHMMSS.csv — thêm mốc để hai file cùng tên không đè nhau."""
    moc = datetime.now().strftime("%Y%m%d_%H%M%S")
    thu_muc = Path(thu_muc_goc) / nhom / san
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"{file.stem}__{moc}{file.suffix}"
    dem = 1
    while dich.exists():                     # hai file cùng tên xử lý trong cùng một giây
        dich = thu_muc / f"{file.stem}__{moc}_{dem}{file.suffix}"
        dem += 1
    return dich


def chuyen_file_thanh_cong(thu_muc_goc, san, file):
    dich = _dich_den(thu_muc_goc, "processed", san, file)
    file.replace(dich)
    return dich


def chuyen_file_that_bai(thu_muc_goc, san, file, loi):
    """Chuyển sang failed/<sàn>/ kèm file `.log` cùng tên ghi nguyên nhân (không chứa dữ liệu đơn hàng)."""
    dich = _dich_den(thu_muc_goc, "failed", san, file)
    file.replace(dich)
    dich.with_suffix(".log").write_text(
        f"Thời điểm: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"File gốc: {file.name}\nNguyên nhân: {type(loi).__name__}: {loi}\n", encoding="utf-8")
    return dich


def quet_mot_lan(thu_muc_goc, kich_thuoc_truoc, ham_nap, trang_thai=None):
    """Một lần quét cả 2 sàn.

    Nhận:
        thu_muc_goc — thư mục `data/`.
        kich_thuoc_truoc — dict {đường dẫn file: kích thước lần quét trước}.
        ham_nap — `nap_file(san, duong_dan, ten_shop, nguon)`; test truyền hàm giả.
        trang_thai — TrangThaiQuet để cập nhật (có thể None).
    Trả: (kích thước lần này {file: size}, danh sách (sàn, tên file, "processed"/"failed"/"cho")).
    File mới thấy lần đầu hoặc kích thước vừa đổi → chờ lần quét sau. File nạp lỗi không làm dừng
    các file khác; lỗi nạp đã được `nap_file` ghi vào `sync_runs`.
    """
    kich_thuoc_nay = {}
    ket_qua = []
    for san in CAC_SAN:
        for file in liet_ke_file(thu_muc_goc, san):
            try:
                kich_thuoc = file.stat().st_size
            except OSError:                   # file vừa bị chuyển/xóa giữa lúc liệt kê và đọc
                continue
            kich_thuoc_nay[file] = kich_thuoc
            if kich_thuoc_truoc.get(file) != kich_thuoc:
                ket_qua.append((san, file.name, "cho"))
                continue
            try:
                ham_nap(san, str(file), ten_shop_cua_san(san), "file_auto")
            except Exception as loi:
                try:
                    chuyen_file_that_bai(thu_muc_goc, san, file, loi)
                except OSError:
                    logger.exception("Không chuyển được file lỗi %s sang failed/", file.name)
                ket_qua.append((san, file.name, "failed"))
                logger.warning("Nạp file %s thất bại: %s", file.name, type(loi).__name__)
            else:
                try:
                    chuyen_file_thanh_cong(thu_muc_goc, san, file)
                except OSError:
                    logger.exception("Nạp xong nhưng không chuyển được %s sang processed/", file.name)
                ket_qua.append((san, file.name, "processed"))
            kich_thuoc_nay.pop(file, None)    # đã xử lý xong, quên kích thước
    if trang_thai is not None:
        trang_thai.last_scan_at = datetime.now(timezone.utc)
        trang_thai.pending_files = sum(len(liet_ke_file(thu_muc_goc, san)) for san in CAC_SAN)
    return kich_thuoc_nay, ket_qua


async def chay_quet(dung, thu_muc_goc, so_giay, ham_nap, trang_thai):
    """Vòng lặp nền: quét → ngủ `so_giay` → lặp lại; dừng ngay khi `dung` được đặt."""
    kich_thuoc = {}
    while not dung.is_set():
        try:
            kich_thuoc, _ = await asyncio.to_thread(quet_mot_lan, thu_muc_goc, kich_thuoc, ham_nap, trang_thai)
        except Exception:
            logger.exception("Lần quét thư mục lỗi; vòng sau quét lại")
        try:
            await asyncio.wait_for(dung.wait(), timeout=so_giay)
        except asyncio.TimeoutError:
            pass
