"""Quét thư mục nạp file tự động; tệp Shopee phải nằm trong ngăn của đúng gian hàng, sai chỗ thì chuyển sang failed."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CAC_SAN = ("shopee", "tiktok")

# Ký tự không được có trong tên thư mục trên Windows.
KY_TU_CAM_TRONG_TEN_NGAN = '/\\:*?"<>|'


class TrangThaiQuet:
    def __init__(self):
        self.last_scan_at = None
        self.pending_files = 0


def thu_muc_goc_mac_dinh():
    return Path(__file__).resolve().parents[3] / "data"


def ten_ngan_hop_le(ten_shop):
    return (bool(ten_shop) and ten_shop == ten_shop.strip() and not ten_shop.startswith(".")
            and not any(k in ten_shop for k in KY_TU_CAM_TRONG_TEN_NGAN))


def tao_ngan_shopee(thu_muc_goc, cac_shop_shopee):
    for ten_shop in cac_shop_shopee:
        if ten_ngan_hop_le(ten_shop):
            (Path(thu_muc_goc) / "inbox" / "shopee" / ten_shop).mkdir(parents=True, exist_ok=True)


def _csv_trong(thu_muc):
    return [f for f in thu_muc.iterdir()
            if f.is_file() and f.suffix.lower() == ".csv" and not f.name.startswith(".")]


def liet_ke_file(thu_muc_goc, san):
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
    """TikTok có cột Shop nên không cần ngăn; Shopee lấy tên shop từ ngăn chứa file."""
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
    """Thêm mốc thời gian để hai file cùng tên không đè nhau."""
    moc = datetime.now().strftime("%Y%m%d_%H%M%S")
    thu_muc = Path(thu_muc_goc) / nhom / san
    if ten_shop:
        thu_muc = thu_muc / ten_shop
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"{file.stem}__{moc}{file.suffix}"
    dem = 1
    while dich.exists():
        dich = thu_muc / f"{file.stem}__{moc}_{dem}{file.suffix}"
        dem += 1
    return dich


def chuyen_file_thanh_cong(thu_muc_goc, san, file, ten_shop=None):
    dich = _dich_den(thu_muc_goc, "processed", san, file, ten_shop)
    file.replace(dich)
    return dich


def chuyen_file_that_bai(thu_muc_goc, san, file, loi, ten_shop=None):
    """Chuyển sang failed kèm file .log ghi nguyên nhân, không chứa dữ liệu đơn hàng."""
    dich = _dich_den(thu_muc_goc, "failed", san, file, ten_shop)
    file.replace(dich)
    dich.with_suffix(".log").write_text(
        f"Thời điểm: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"File gốc: {file.name}\nNguyên nhân: {type(loi).__name__}: {loi}\n", encoding="utf-8")
    return dich


def quet_mot_lan(thu_muc_goc, kich_thuoc_truoc, ham_nap, trang_thai=None, cac_shop_shopee=(), ham_ghi_loi=None):
    """File chỉ được nạp khi kích thước không đổi qua hai lần quét, để tránh file đang chép dở."""
    kich_thuoc_nay = {}
    ket_qua = []
    cac_shop_shopee = tuple(cac_shop_shopee)
    tao_ngan_shopee(thu_muc_goc, cac_shop_shopee)
    for san in CAC_SAN:
        for file in liet_ke_file(thu_muc_goc, san):
            try:
                kich_thuoc = file.stat().st_size
            except OSError:                   # file vừa bị chuyển hoặc xóa giữa lúc liệt kê và đọc
                continue
            kich_thuoc_nay[file] = kich_thuoc
            if kich_thuoc_truoc.get(file) != kich_thuoc:
                ket_qua.append((san, file.name, "cho"))
                continue
            ten_shop, loi_vi_tri = ten_shop_cua_file(thu_muc_goc, san, file, cac_shop_shopee)
            try:
                if loi_vi_tri is not None:
                    # Từ chối trước khi nạp nhưng vẫn để lại dấu vết trong sync_runs.
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
            kich_thuoc_nay.pop(file, None)
    if trang_thai is not None:
        # Gán số file chờ trước mốc quét vì endpoint trạng thái đọc từ thread khác.
        trang_thai.pending_files = sum(len(liet_ke_file(thu_muc_goc, san)) for san in CAC_SAN)
        trang_thai.last_scan_at = datetime.now(timezone.utc)
    return kich_thuoc_nay, ket_qua


async def chay_quet(dung, thu_muc_goc, so_giay, ham_nap, trang_thai, lay_shop_shopee=None, ham_ghi_loi=None):
    """Lỗi đọc CSDL thì bỏ cả vòng; quét với danh sách shop rỗng sẽ chuyển nhầm mọi tệp Shopee sang failed."""
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
