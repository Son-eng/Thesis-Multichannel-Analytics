"""Một lượt đồng bộ API cho MỘT (sàn, shop) — SPEC §18.2, §20.

Luồng (đúng 8 bước §18.2):
    1. giành khóa pg_advisory_lock theo (sàn, shop); đang có lượt chạy → bỏ lượt, không đợi
    2. tạo dòng sync_runs 'running' (commit ngay để trang trạng thái thấy lượt đang chạy)
    3. nạp sẵn token từ .env nếu thiếu; token sắp hết hạn → làm mới và ghi ngay (token_store)
    4. xác định cửa sổ kéo (§20.3)
    5. connector kéo JSON thô (§20.2)
    6. chuẩn hóa thành cột chuẩn (§21) — dùng chung cleaners với đường file
    7. loader.upsert_don_hang + cập nhật sync_runs 'success' trong CÙNG MỘT giao dịch
    8. nhả khóa

Lỗi ở bất kỳ bước nào → dòng sync_runs 'failed' kèm error_message, dữ liệu đơn
hàng không đổi (giao dịch ở bước 7 chưa commit thì rollback). Lỗi của một shop
không ảnh hưởng shop khác: mỗi lượt độc lập, scheduler bắt lỗi từng lượt.

Token KHÔNG BAO GIỜ được ghi ra file hay log: mọi thông báo lỗi đi qua
`lam_sach_thong_diep` trước khi vào sync_runs hoặc logger.
"""

import logging
import re
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

# Token còn dưới ngần này thì làm mới TRƯỚC khi kéo (§18.2 bước 3).
NGUONG_LAM_MOI_TOKEN = timedelta(minutes=5)
SO_LAN_GHI_LAI_TOKEN = 3
CHO_GHI_LAI_TOKEN_GIAY = 1.0
DO_DAI_TOI_DA_LOI = 2000

# classid của khóa advisory — mỗi sàn một giá trị, objid là mã băm tên shop.
CLASSID_KHOA = {token_store.SAN_SHOPEE: 1, token_store.SAN_TIKTOK: 2}

# Mẫu giá trị bí mật có thể lọt vào thông báo lỗi: định nghĩa MỘT lần ở core/log_filter.py (dùng chung với bộ lọc log).


class LoiCanUyQuyenLai(Exception):
    """Quyền truy cập của shop không còn dùng được — người dùng phải ủy quyền lại (§20.1)."""


# ---------------------------------------------------------------- Khóa chống chạy chồng

class KhoaLuot:
    """Khóa advisory của một (sàn, shop), giữ trên MỘT kết nối riêng cho tới khi nhả.

    pg_advisory_lock cấp theo PHIÊN kết nối: kết nối nào giữ khóa thì chỉ kết
    nối đó nhả được, và khóa tự mất nếu tiến trình chết (khác file .sync.lock
    của Pipeline — không bao giờ còn "file khóa cũ nằm lại", §20.4).
    """

    def __init__(self, san, ten_shop):
        self.san = san
        self.ten_shop = ten_shop
        self._ket_noi = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        self._giu = False

    def thu_giu(self):
        """Thử giành khóa, KHÔNG đợi. Trả True nếu giành được."""
        kq = self._ket_noi.execute(
            text("SELECT pg_try_advisory_lock(:a, :b)"),
            {"a": CLASSID_KHOA[self.san], "b": zlib.crc32(self.ten_shop.encode("utf-8")) & 0x7FFFFFFF},
        ).scalar_one()
        self._giu = bool(kq)
        return self._giu

    def nha(self):
        """Nhả khóa (nếu đang giữ) và đóng kết nối. Gọi nhiều lần vẫn an toàn."""
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
    """KhoaLuot đã giành được, hoặc None nếu (sàn, shop) đang có lượt chạy."""
    khoa = KhoaLuot(san, ten_shop)
    if khoa.thu_giu():
        return khoa
    khoa.nha()
    return None


# ---------------------------------------------------------------- Tiện ích

def lam_sach_thong_diep(thong_diep, cac_gia_tri_bi_mat=()):
    """Che mọi giá trị bí mật trong thông báo lỗi trước khi ghi vào sync_runs / log.

    Nhận: chuỗi; các giá trị token đang biết (che nguyên văn dù không có mẫu `khóa=`).
    Trả: chuỗi đã che, cắt tối đa DO_DAI_TOI_DA_LOI ký tự.
    """
    thong_diep = MAU_BI_MAT.sub(lambda m: f"{m.group(1)}=***", str(thong_diep))
    for gia_tri in cac_gia_tri_bi_mat:
        if gia_tri:
            thong_diep = thong_diep.replace(gia_tri, "***")
    return thong_diep[:DO_DAI_TOI_DA_LOI]


def sang_utc(thoi_diem):
    """Cột timestamp của CSDL không có múi giờ và phiên chạy UTC (database.py) → gắn UTC khi đọc."""
    return thoi_diem if thoi_diem.tzinfo else thoi_diem.replace(tzinfo=timezone.utc)


def tinh_cua_so(phien, san, ten_shop, bay_gio):
    """Cửa sổ kéo của lượt này (§20.3).

    Nhận: phiên CSDL; sàn; tên shop; bay_gio — datetime có múi giờ.
    Trả: dict {tu, den (datetime có múi giờ), truong ("create_time" | "update_time"), loai}.
    - Chưa có lượt 'success' đường API nào cho (sàn, shop) → backfill: từ
      SYNC_BACKFILL_FROM (0h giờ VN) đến bây giờ, lọc theo create_time.
    - Đã có: định kỳ — từ bây giờ − SYNC_LOOKBACK_DAYS, lọc theo update_time
      (đơn đổi trạng thái gần đây đều được kéo lại rồi upsert cập nhật).
    - Lượt thành công gần nhất cũ hơn SYNC_LOOKBACK_DAYS (bị gián đoạn) →
      cửa sổ tự mở rộng về mốc đó (window_to của lượt đó) để không sót dữ liệu.
    """
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
    """Tên các shop có trong platform_tokens (thứ tự ổn định), có thể lọc theo sàn."""
    cau_hoi = select(PlatformToken.platform, PlatformToken.shop_name).order_by(
        PlatformToken.platform, PlatformToken.shop_name)
    if san is not None:
        cau_hoi = cau_hoi.where(PlatformToken.platform == san)
    return [tuple(dong) for dong in phien.execute(cau_hoi).all()]


# ---------------------------------------------------------------- sync_runs

def tao_luot_chay(phien, san, ten_shop, trigger_type="schedule", triggered_by=None):
    """Ghi dòng sync_runs 'running' và COMMIT ngay. Trả id.

    Commit ngay (không đợi hết lượt) để GET /api/sync/status thấy lượt đang
    chạy; nếu lượt hỏng giữa chừng thì dòng này còn đó để chuyển sang 'failed'.
    """
    dong = SyncRun(platform=san, shop_name=ten_shop, source="api", trigger_type=trigger_type,
                   triggered_by=triggered_by)
    phien.add(dong)
    phien.commit()
    return dong.id


def ghi_that_bai(run_id, loi, cac_gia_tri_bi_mat, thong_ke):
    """Chuyển dòng sync_runs sang 'failed' trong phiên RIÊNG (giao dịch chính đã rollback)."""
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
        # CSDL hỏng đúng lúc ghi lỗi: không còn cách nào ghi nhận, chỉ để lại log (đã che bí mật).
        logger.exception("Không ghi được trạng thái 'failed' cho sync_runs %s (%s)", run_id, type(loi_ghi).__name__)


# ---------------------------------------------------------------- Token

def tao_client(san, dong_token):
    """Connector của một shop từ dòng platform_tokens (đoạn nối mẫu §20.1)."""
    if san == token_store.SAN_SHOPEE:
        return ShopeeClient(settings.SHOPEE_BASE_URL, settings.SHOPEE_PARTNER_ID, settings.SHOPEE_PARTNER_KEY,
                            int(dong_token.shop_ref), dong_token.access_token)
    return TikTokClient(settings.TIKTOK_BASE_URL, settings.TIKTOK_AUTH_BASE_URL, settings.TIKTOK_APP_KEY,
                        settings.TIKTOK_APP_SECRET, dong_token.shop_ref, dong_token.access_token)


def lam_moi_va_xu_ly_loi_ghi(san, ten_shop, client, ham_ngu=time.sleep):
    """Làm mới token + ghi CSDL; xử lý `LoiGhiTokenSauLamMoi` theo §20.1.

    Trả: access_token MỚI.
    Sàn đã cấp token mới mà commit lỗi → thử ghi lại token mới vài lần, mỗi lần
    trong phiên CSDL MỚI, có chờ giữa các lần. Vẫn không được → đánh dấu hết
    quyền (token_status = "expired") và ném LoiCanUyQuyenLai. Token không bao
    giờ ra file hay log.
    """
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
    """refresh_token hết hạn → không còn cách tự làm mới: báo ủy quyền lại, không gọi sàn vô ích."""
    if dong_token.refresh_expires_at is not None and sang_utc(dong_token.refresh_expires_at) <= bay_gio:
        raise LoiCanUyQuyenLai(
            f"Cần ủy quyền lại {dong_token.platform}/{dong_token.shop_name}: refresh_token đã hết hạn.")


# ---------------------------------------------------------------- Một lượt

def chuan_hoa(san, ket_qua_keo, ten_shop):
    """Chuẩn hóa kết quả kéo của đúng sàn → (DataFrame cột chuẩn, 5 bộ đếm)."""
    if san == token_store.SAN_SHOPEE:
        return shopee_api_transform.chuan_hoa_api_shopee(ket_qua_keo, ten_shop)
    return tiktok_api_transform.chuan_hoa_api_tiktok(ket_qua_keo, ten_shop)


def thuc_hien_luot(run_id, san, ten_shop, cua_so=None, bay_gio=None, ham_ngu=time.sleep):
    """Phần việc của một lượt (bước 3–7); lỗi gì cũng được ghi vào dòng sync_runs `run_id`.

    Nhận: cua_so — dict {tu, den, truong} để ép cửa sổ (test, chạy lại tay);
    None thì tính theo §20.3.
    Không ném lỗi ra ngoài: mọi lỗi thành dòng 'failed'.
    """
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

        # Bước 7: upsert + cập nhật sync_runs 'success' trong MỘT giao dịch — dữ
        # liệu đơn hàng và nhật ký cùng thành công hoặc cùng mất (§18.2).
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
    """Một lượt đồng bộ cho một (sàn, shop). Trả run_id, hoặc None nếu lượt bị bỏ.

    Nhận:
        trigger_type — "schedule" (lịch) hoặc "manual" (nút "Đồng bộ ngay").
        khoa, run_id — nơi gọi (endpoint POST) đã giành khóa và tạo dòng
            sync_runs sẵn (để trả run_ids ngay); None thì tự làm.
    Bỏ lượt (None) khi (sàn, shop) đang có lượt chạy: không đợi, không chạy chồng.
    Khóa luôn được nhả, kể cả khi lỗi.
    """
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
    """Có lượt đang chạy cho (sàn, shop) không (thăm dò khóa rồi nhả ngay)."""
    khoa = thu_giu_khoa(san, ten_shop)
    if khoa is None:
        return True
    khoa.nha()
    return False


def don_dep_luot_treo(phien):
    """Chuyển các dòng 'running' đường API còn sót (máy chủ tắt giữa lượt) sang 'failed'.

    Gọi lúc khởi động ứng dụng: lúc đó chắc chắn chưa có lượt nào đang chạy.
    Trả: số dòng đã dọn.
    """
    luot_treo = phien.execute(
        select(SyncRun).where(SyncRun.source == "api", SyncRun.status == "running")).scalars().all()
    for dong in luot_treo:
        dong.status = "failed"
        dong.error_message = "Lượt bị gián đoạn: máy chủ dừng khi đang đồng bộ"
        dong.finished_at = func.now()
    phien.commit()
    return len(luot_treo)
