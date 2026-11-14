"""Quét thư mục nạp file tự động — đường DỰ PHÒNG (SPEC §2.4).

Cấu trúc (gốc `data/`): inbox/<sàn>/ → processed/<sàn>/ hoặc failed/<sàn>/.
Riêng Shopee (chỉ dẫn 026): tệp không có cột shop nên PHẢI nằm trong ngăn của gian hàng,
`inbox/shopee/<tên shop>/` (tên ngăn trùng `shop_name` trong `platform_tokens`); kết quả vào
`processed/shopee/<tên shop>/` hoặc `failed/shopee/<tên shop>/`. Tệp đặt thẳng ở `inbox/shopee/` hoặc trong
ngăn không khớp shop nào KHÔNG được nạp (tránh cộng nhầm doanh thu sang shop khác): chuyển sang `failed/`
kèm lý do, và ghi một dòng `sync_runs` 'failed'.

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

logger = logging.getLogger(__name__)

CAC_SAN = ("shopee", "tiktok")

# Ký tự không được có trong tên thư mục của shop (Windows + dấu phân cách đường dẫn).
KY_TU_CAM_TRONG_TEN_NGAN = '/\\:*?"<>|'


class TrangThaiQuet:
    """Trạng thái cho GET /api/watcher/status: lần quét gần nhất và số file đang chờ."""

    def __init__(self):
        self.last_scan_at = None      # datetime có múi giờ, None nếu chưa quét lần nào
        self.pending_files = 0


def thu_muc_goc_mac_dinh():
    """`data/` ở gốc project (backend/app/sync/folder_watcher.py → lùi 4 cấp)."""
    return Path(__file__).resolve().parents[3] / "data"


def ten_ngan_hop_le(ten_shop):
    """Tên shop có dùng làm tên thư mục được không: không rỗng, không thừa khoảng trắng, không bắt đầu bằng "."
    (file ẩn), không chứa dấu phân cách đường dẫn hay ký tự cấm của Windows."""
    return (bool(ten_shop) and ten_shop == ten_shop.strip() and not ten_shop.startswith(".")
            and not any(k in ten_shop for k in KY_TU_CAM_TRONG_TEN_NGAN))


def tao_ngan_shopee(thu_muc_goc, cac_shop_shopee):
    """Tạo `inbox/shopee/<tên shop>/` cho mọi shop Shopee, để nhân viên thấy ngăn của shop mới.

    Tên không dùng làm thư mục được thì bỏ qua (shop đó phải nạp bằng nút tải file hoặc lệnh `--shop`)."""
    for ten_shop in cac_shop_shopee:
        if ten_ngan_hop_le(ten_shop):
            (Path(thu_muc_goc) / "inbox" / "shopee" / ten_shop).mkdir(parents=True, exist_ok=True)


def _csv_trong(thu_muc):
    return [f for f in thu_muc.iterdir()
            if f.is_file() and f.suffix.lower() == ".csv" and not f.name.startswith(".")]


def liet_ke_file(thu_muc_goc, san):
    """Các file `.csv` đang chờ trong inbox/<sàn>/ (bỏ file ẩn như .gitkeep), sắp theo tên.

    Shopee: gồm cả file ở gốc `inbox/shopee/` lẫn file trong các ngăn con. File ở gốc sẽ bị đưa sang failed/,
    nhưng vẫn là file "đang chờ" nên được đếm cho `GET /api/watcher/status`.
    """
    thu_muc = Path(thu_muc_goc) / "inbox" / san
    if not thu_muc.is_dir():
        return []
    cac_file = _csv_trong(thu_muc)
    if san == "shopee":
        for ngan in thu_muc.iterdir():
            if ngan.is_dir() and not ngan.name.startswith("."):
                cac_file += _csv_trong(ngan)
    return sorted(cac_file)


def ten_shop_cua_file(thu_muc_goc, san, file, cac_shop_shopee):
    """Tên shop và lý do lỗi (nếu có) của một file trong inbox.

    Nhận: gốc `data/`, sàn, file, danh sách tên shop Shopee hiện có trong `platform_tokens`.
    Trả: (tên shop hoặc None, thông điệp lỗi hoặc None). TikTok: (None, None) vì tệp có cột `Shop`.
    Shopee: tên shop = tên ngăn chứa file; file ở gốc `inbox/shopee/` hoặc ngăn không khớp shop nào → có lỗi.
    """
    if san != "shopee":
        return None, None
    ngan = file.parent
    cac_ngan = ", ".join(f'"{t}"' for t in cac_shop_shopee if ten_ngan_hop_le(t)) or "(chưa có gian hàng Shopee nào)"
    if ngan == Path(thu_muc_goc) / "inbox" / "shopee":
        return None, ("Tệp Shopee phải đặt trong thư mục của gian hàng (inbox/shopee/<tên gian hàng>/). "
                      f"Các thư mục hợp lệ: {cac_ngan}")
    if ngan.name in cac_shop_shopee:
        return ngan.name, None
    return None, (f'Tệp Shopee phải đặt trong thư mục của gian hàng: thư mục "{ngan.name}" không khớp gian hàng '
                  f"Shopee nào. Các thư mục hợp lệ: {cac_ngan}")


def _dich_den(thu_muc_goc, nhom, san, file, ten_shop=None):
    """processed/<sàn>[/<shop>]/<tên>__YYYYmmdd_HHMMSS.csv — thêm mốc để hai file cùng tên không đè nhau.

    Shopee có thêm cấp shop (cùng cấu trúc với inbox): hai shop hay xuất tệp trùng tên, tách theo shop thì
    truy vết được tệp nào của shop nào. Tệp lỗi chưa xác định được shop thì nằm thẳng ở `failed/shopee/`."""
    moc = datetime.now().strftime("%Y%m%d_%H%M%S")
    thu_muc = Path(thu_muc_goc) / nhom / san
    if ten_shop:
        thu_muc = thu_muc / ten_shop
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"{file.stem}__{moc}{file.suffix}"
    dem = 1
    while dich.exists():                     # hai file cùng tên xử lý trong cùng một giây
        dich = thu_muc / f"{file.stem}__{moc}_{dem}{file.suffix}"
        dem += 1
    return dich


def chuyen_file_thanh_cong(thu_muc_goc, san, file, ten_shop=None):
    dich = _dich_den(thu_muc_goc, "processed", san, file, ten_shop)
    file.replace(dich)
    return dich


def chuyen_file_that_bai(thu_muc_goc, san, file, loi, ten_shop=None):
    """Chuyển sang failed/<sàn>[/<shop>]/ kèm file `.log` cùng tên ghi nguyên nhân (không chứa dữ liệu đơn hàng)."""
    dich = _dich_den(thu_muc_goc, "failed", san, file, ten_shop)
    file.replace(dich)
    dich.with_suffix(".log").write_text(
        f"Thời điểm: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"File gốc: {file.name}\nNguyên nhân: {type(loi).__name__}: {loi}\n", encoding="utf-8")
    return dich


def quet_mot_lan(thu_muc_goc, kich_thuoc_truoc, ham_nap, trang_thai=None, cac_shop_shopee=(), ham_ghi_loi=None):
    """Một lần quét cả 2 sàn.

    Nhận:
        thu_muc_goc — thư mục `data/`.
        kich_thuoc_truoc — dict {đường dẫn file: kích thước lần quét trước}.
        ham_nap — `nap_file(san, duong_dan, ten_shop, nguon)`; test truyền hàm giả.
        trang_thai — TrangThaiQuet để cập nhật (có thể None).
        cac_shop_shopee — tên các shop Shopee trong `platform_tokens` (production đọc lại CSDL mỗi vòng).
        ham_ghi_loi — `ghi_lan_nap_that_bai(san, đường_dẫn, tên_shop, nguồn, lỗi, thời_điểm)`: ghi `sync_runs`
            'failed' cho tệp bị từ chối TRƯỚC khi vào `nap_file` (đặt sai ngăn); lỗi khi nạp thì `nap_file`
            tự ghi. None thì không ghi.
    Trả: (kích thước lần này {file: size}, danh sách (sàn, tên file, "processed"/"failed"/"cho")).
    File mới thấy lần đầu hoặc kích thước vừa đổi → chờ lần quét sau. File nạp lỗi không làm dừng
    các file khác; lỗi nạp đã được `nap_file` ghi vào `sync_runs`.
    """
    kich_thuoc_nay = {}
    ket_qua = []
    cac_shop_shopee = tuple(cac_shop_shopee)
    tao_ngan_shopee(thu_muc_goc, cac_shop_shopee)
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
            ten_shop, loi_vi_tri = ten_shop_cua_file(thu_muc_goc, san, file, cac_shop_shopee)
            try:
                if loi_vi_tri is not None:
                    # Từ chối TRƯỚC khi nạp: không dòng nào vào orders, nhưng vẫn để lại dấu vết trong sync_runs.
                    loi = ValueError(loi_vi_tri)
                    if ham_ghi_loi is not None:
                        ham_ghi_loi(san, str(file), None, "file_auto", loi, datetime.now().astimezone())
                    raise loi
                ham_nap(san, str(file), ten_shop, "file_auto")
            except Exception as loi:
                try:
                    chuyen_file_that_bai(thu_muc_goc, san, file, loi, ten_shop)
                except OSError:
                    logger.exception("Không chuyển được file lỗi %s sang failed/", file.name)
                ket_qua.append((san, file.name, "failed"))
                logger.warning("Nạp file %s thất bại: %s", file.name, type(loi).__name__)
            else:
                try:
                    chuyen_file_thanh_cong(thu_muc_goc, san, file, ten_shop)
                except OSError:
                    logger.exception("Nạp xong nhưng không chuyển được %s sang processed/", file.name)
                ket_qua.append((san, file.name, "processed"))
            kich_thuoc_nay.pop(file, None)    # đã xử lý xong, quên kích thước
    if trang_thai is not None:
        # Gán số file chờ TRƯỚC mốc quét: GET /api/watcher/status chạy ở thread khác, thấy mốc quét mới
        # thì số file chờ phải đã là của lần quét đó (không được thấy mốc mới kèm số cũ).
        trang_thai.pending_files = sum(len(liet_ke_file(thu_muc_goc, san)) for san in CAC_SAN)
        trang_thai.last_scan_at = datetime.now(timezone.utc)
    return kich_thuoc_nay, ket_qua


async def chay_quet(dung, thu_muc_goc, so_giay, ham_nap, trang_thai, lay_shop_shopee=None, ham_ghi_loi=None):
    """Vòng lặp nền: quét → ngủ `so_giay` → lặp lại; dừng ngay khi `dung` được đặt.

    `lay_shop_shopee()` trả tên các shop Shopee hiện có; đọc lại CSDL MỖI vòng nên shop mới kết nối xong có
    ngăn thư mục ở vòng sau. Lỗi đọc CSDL làm hỏng cả vòng đó (ghi log, vòng sau quét lại): KHÔNG quét với danh
    sách rỗng, vì như vậy mọi tệp Shopee sẽ bị chuyển sang failed/ nhầm."""
    kich_thuoc = {}
    while not dung.is_set():
        try:
            cac_shop = tuple(await asyncio.to_thread(lay_shop_shopee)) if lay_shop_shopee is not None else ()
            kich_thuoc, _ = await asyncio.to_thread(
                quet_mot_lan, thu_muc_goc, kich_thuoc, ham_nap, trang_thai, cac_shop, ham_ghi_loi)
        except Exception as loi:
            logger.exception("Lần quét thư mục lỗi (%s); vòng sau quét lại", type(loi).__name__)
        try:
            await asyncio.wait_for(dung.wait(), timeout=so_giay)
        except asyncio.TimeoutError:
            pass
