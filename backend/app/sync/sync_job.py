"""Một lượt đồng bộ API cho một (sàn, shop); token không bao giờ được ghi ra file hay log."""

import logging
import time
import zlib
from datetime import datetime, time as gio_trong_ngay, timedelta, timezone

from sqlalchemy import func, select, text

from app.config import settings
from app.connectors.shopee_client import ShopeeClient
from app.connectors.tiktok_client import TikTokClient
from app.core.log_filter import MAU_BI_MAT, dang_ky_bi_mat
from app.database import SessionLocal, engine
from app.etl import loader, shopee_api_transform, tiktok_api_transform
from app.models.platform_token import PlatformToken
from app.models.sync_run import SyncRun
from app.services import token_store

logger = logging.getLogger(__name__)

GIO_VN = timezone(timedelta(hours=7))
SAN_HOP_LE = (token_store.SAN_SHOPEE, token_store.SAN_TIKTOK)

# Token còn ít hơn ngần này thì làm mới trước khi kéo.
NGUONG_LAM_MOI_TOKEN = timedelta(minutes=5)
SO_LAN_GHI_LAI_TOKEN = 3
CHO_GHI_LAI_TOKEN_GIAY = 1.0
DO_DAI_TOI_DA_LOI = 2000

# classid của khóa advisory, mỗi sàn một giá trị; objid là mã băm tên shop.
CLASSID_KHOA = {token_store.SAN_SHOPEE: 1, token_store.SAN_TIKTOK: 2}


class LoiCanUyQuyenLai(Exception):
    """Quyền truy cập của shop không còn dùng được, người dùng phải ủy quyền lại."""


class KhoaLuot:
    """Khóa advisory theo phiên kết nối: tự mất nếu tiến trình chết, không để lại khóa cũ."""

    def __init__(self, san, ten_shop):
        self.san = san
        self.ten_shop = ten_shop
        self._ket_noi = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        self._giu = False

    def thu_giu(self):
        kq = self._ket_noi.execute(
            text("SELECT pg_try_advisory_lock(:a, :b)"),
            {"a": CLASSID_KHOA[self.san], "b": zlib.crc32(self.ten_shop.encode("utf-8")) & 0x7FFFFFFF},
        ).scalar_one()
        self._giu = bool(kq)
        return self._giu

    def nha(self):
        if self._ket_noi.closed:
            return
        try:
            if self._giu:
                self._ket_noi.execute(
                    text("SELECT pg_advisory_unlock(:a, :b)"),
                    {"a": CLASSID_KHOA[self.san], "b": zlib.crc32(self.ten_shop.encode("utf-8")) & 0x7FFFFFFF},
                )
        finally:
            self._giu = False
            self._ket_noi.close()


def thu_giu_khoa(san, ten_shop):
    khoa = KhoaLuot(san, ten_shop)
    if khoa.thu_giu():
        return khoa
    khoa.nha()
    return None


def lam_sach_thong_diep(thong_diep, cac_gia_tri_bi_mat=()):
    """Che mọi giá trị bí mật trong thông báo lỗi trước khi ghi vào sync_runs hay log."""
    thong_diep = MAU_BI_MAT.sub(lambda m: f"{m.group(1)}=***", str(thong_diep))
    for gia_tri in cac_gia_tri_bi_mat:
        if gia_tri:
            thong_diep = thong_diep.replace(gia_tri, "***")
    return thong_diep[:DO_DAI_TOI_DA_LOI]


def sang_utc(thoi_diem):
    """Cột timestamp không có múi giờ và phiên chạy UTC nên gắn UTC khi đọc."""
    return thoi_diem if thoi_diem.tzinfo else thoi_diem.replace(tzinfo=timezone.utc)


def tinh_cua_so(phien, san, ten_shop, bay_gio):
    """Lần đầu thì backfill theo create_time; các lần sau kéo lại vài ngày gần nhất theo update_time, bị gián đoạn lâu thì tự mở rộng để không sót."""
    luot_cuoi = phien.execute(
        select(func.max(SyncRun.window_to)).where(
            SyncRun.platform == san, SyncRun.shop_name == ten_shop,
            SyncRun.source == "api", SyncRun.status == "success",
        )
    ).scalar_one()
    if luot_cuoi is None:
        tu = datetime.combine(settings.SYNC_BACKFILL_FROM, gio_trong_ngay.min, tzinfo=GIO_VN)
        return {"tu": tu, "den": bay_gio, "truong": "create_time", "loai": "backfill"}
    moc_dinh_ky = bay_gio - timedelta(days=settings.SYNC_LOOKBACK_DAYS)
    moc_cuoi = sang_utc(luot_cuoi)
    if moc_cuoi < moc_dinh_ky:
        return {"tu": moc_cuoi, "den": bay_gio, "truong": "update_time", "loai": "gian_doan"}
    return {"tu": moc_dinh_ky, "den": bay_gio, "truong": "update_time", "loai": "dinh_ky"}


def liet_ke_shop(phien, san=None):
    cau_hoi = select(PlatformToken.platform, PlatformToken.shop_name).order_by(
        PlatformToken.platform, PlatformToken.shop_name)
    if san is not None:
        cau_hoi = cau_hoi.where(PlatformToken.platform == san)
    return [tuple(dong) for dong in phien.execute(cau_hoi).all()]


def tao_luot_chay(phien, san, ten_shop, trigger_type="schedule", triggered_by=None):
    dong = SyncRun(platform=san, shop_name=ten_shop, source="api", trigger_type=trigger_type,
                   triggered_by=triggered_by)
    phien.add(dong)
    phien.commit()
    return dong.id


def ghi_that_bai(run_id, loi, cac_gia_tri_bi_mat, thong_ke):
    """Chuyển dòng sync_runs sang 'failed' trong phiên riêng (giao dịch chính đã rollback)."""
    thong_diep = lam_sach_thong_diep(f"{type(loi).__name__}: {loi}", cac_gia_tri_bi_mat)
    logger.error("Lượt đồng bộ %s thất bại: %s", run_id, thong_diep)
    try:
        with SessionLocal() as phien:
            dong = phien.get(SyncRun, run_id)
            dong.status = "failed"
            dong.error_message = thong_diep
            dong.api_calls = thong_ke.get("api_calls", 0)
            dong.finished_at = func.clock_timestamp()
            phien.commit()
    except Exception as loi_ghi:
        # CSDL hỏng đúng lúc ghi lỗi thì chỉ còn log.
        logger.exception("Không ghi được trạng thái 'failed' cho sync_runs %s (%s)", run_id, type(loi_ghi).__name__)


def tao_client(san, dong_token):
    if san == token_store.SAN_SHOPEE:
        return ShopeeClient(settings.SHOPEE_BASE_URL, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                            int(dong_token.shop_ref), dong_token.access_token)
    return TikTokClient(settings.TIKTOK_BASE_URL, settings.TIKTOK_AUTH_BASE_URL, settings.TIKTOK_APP_KEY,
                        settings.TIKTOK_APP_SECRET, dong_token.shop_ref, dong_token.access_token)


def lam_moi_va_xu_ly_loi_ghi(san, ten_shop, client, ham_ngu=time.sleep):
    """Commit token mới lỗi thì thử ghi lại vài lần; vẫn không được thì đánh dấu hết quyền."""
    try:
        return token_store.lam_moi_va_ghi(san, ten_shop, client.goi_lam_moi_token)["access_token"]
    except token_store.LoiGhiTokenSauLamMoi as loi:
        token_moi = loi.token_moi
    for lan in range(SO_LAN_GHI_LAI_TOKEN):
        try:
            token_store.ghi_token(san, ten_shop, token_moi)
            logger.warning("Đã ghi lại token %s/%s sau lần lỗi (thử %d)", san, ten_shop, lan + 1)
            return token_moi["access_token"]
        except Exception:
            ham_ngu(CHO_GHI_LAI_TOKEN_GIAY * (lan + 1))
    token_store.danh_dau_het_quyen(san, ten_shop)
    raise LoiCanUyQuyenLai(
        f"Cần ủy quyền lại {san}/{ten_shop}: sàn đã cấp token mới nhưng không ghi được vào CSDL "
        "(refresh_token cũ đã bị vô hiệu)."
    )


def kiem_con_quyen(dong_token, bay_gio):
    """refresh_token hết hạn thì báo ủy quyền lại, không gọi sàn vô ích."""
    if dong_token.refresh_expires_at is not None and sang_utc(dong_token.refresh_expires_at) <= bay_gio:
        raise LoiCanUyQuyenLai(
            f"Cần ủy quyền lại {dong_token.platform}/{dong_token.shop_name}: refresh_token đã hết hạn.")


def chuan_hoa(san, ket_qua_keo, ten_shop):
    if san == token_store.SAN_SHOPEE:
        return shopee_api_transform.chuan_hoa_api_shopee(ket_qua_keo, ten_shop)
    return tiktok_api_transform.chuan_hoa_api_tiktok(ket_qua_keo, ten_shop)


def thuc_hien_luot(run_id, san, ten_shop, cua_so=None, bay_gio=None, ham_ngu=time.sleep):
    """Phần việc của một lượt; lỗi gì cũng được ghi vào dòng sync_runs `run_id`."""
    bay_gio = bay_gio or datetime.now(timezone.utc)
    thong_ke = {"api_calls": 0}
    cac_bi_mat = []
    try:
        token_store.nap_san_tu_cau_hinh(settings)
        dong_token = token_store.doc_token(san, ten_shop)
        if dong_token is None:
            raise LookupError(f"Chưa có token của {san}/{ten_shop} trong platform_tokens")
        cac_bi_mat += [dong_token.access_token, dong_token.refresh_token]
        dang_ky_bi_mat(dong_token.access_token)
        dang_ky_bi_mat(dong_token.refresh_token)
        kiem_con_quyen(dong_token, bay_gio)

        if cua_so is None:
            with SessionLocal() as phien:
                cua_so = tinh_cua_so(phien, san, ten_shop, bay_gio)
        with tao_client(san, dong_token) as client:
            client.khi_can_lam_moi = lambda: lam_moi_va_xu_ly_loi_ghi(san, ten_shop, client, ham_ngu)
            if sang_utc(dong_token.access_expires_at) - bay_gio < NGUONG_LAM_MOI_TOKEN:
                client.access_token = client.khi_can_lam_moi()
            try:
                ket_qua = client.keo_don(int(cua_so["tu"].timestamp()), int(cua_so["den"].timestamp()), cua_so["truong"])
            finally:
                thong_ke["api_calls"] = client.so_lan_goi
                cac_bi_mat.append(client.access_token)
                dang_ky_bi_mat(client.access_token)

        bang_chuan, bo_dem = chuan_hoa(san, ket_qua, ten_shop)

        # Upsert và cập nhật sync_runs trong một giao dịch để cùng thành công hoặc cùng mất.
        with SessionLocal() as phien:
            so_dong_moi, so_dong_cap_nhat = loader.upsert_don_hang(phien, san, bang_chuan, None)
            dong = phien.get(SyncRun, run_id)
            dong.window_from, dong.window_to = cua_so["tu"], cua_so["den"]
            dong.api_calls = thong_ke["api_calls"]
            dong.orders_fetched = len(ket_qua["don_hang"])
            dong.rows_total = len(bang_chuan)
            dong.rows_inserted, dong.rows_updated = so_dong_moi, so_dong_cap_nhat
            for ten_cot, gia_tri in bo_dem.items():
                setattr(dong, ten_cot, gia_tri)
            dong.status = "success"
            dong.finished_at = func.clock_timestamp()
            phien.commit()
    except Exception as loi:
        ghi_that_bai(run_id, loi, cac_bi_mat, thong_ke)


def dong_bo_mot_shop(san, ten_shop, trigger_type="schedule", triggered_by=None, cua_so=None,
                     khoa=None, run_id=None, bay_gio=None, ham_ngu=time.sleep):
    if san not in SAN_HOP_LE:
        raise ValueError(f"Sàn không hợp lệ: {san!r}")
    if khoa is None:
        khoa = thu_giu_khoa(san, ten_shop)
        if khoa is None:
            logger.info("Bỏ lượt %s/%s: đang có lượt chạy", san, ten_shop)
            return None
    try:
        if run_id is None:
            with SessionLocal() as phien:
                run_id = tao_luot_chay(phien, san, ten_shop, trigger_type, triggered_by)
        thuc_hien_luot(run_id, san, ten_shop, cua_so, bay_gio, ham_ngu)
        return run_id
    finally:
        khoa.nha()


def dang_chay(san, ten_shop):
    khoa = thu_giu_khoa(san, ten_shop)
    if khoa is None:
        return True
    khoa.nha()
    return False


def don_dep_luot_treo(phien):
    luot_treo = phien.execute(
        select(SyncRun).where(SyncRun.source == "api", SyncRun.status == "running")).scalars().all()
    for dong in luot_treo:
        dong.status = "failed"
        dong.error_message = "Lượt bị gián đoạn: máy chủ dừng khi đang đồng bộ"
        dong.finished_at = func.now()
    phien.commit()
    return len(luot_treo)
