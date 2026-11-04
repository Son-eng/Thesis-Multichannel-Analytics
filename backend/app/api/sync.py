"""Endpoint đồng bộ API: /api/sync/status, /api/sync/runs, POST /api/sync/{platform} (SPEC §12, §12.1.3.1–§12.1.3.4).

Khuôn JSON đúng hợp đồng §12.1.3. Hai điều BẮT BUỘC:
- Không bao giờ có giá trị token trong phản hồi (chỉ có hạn dùng).
- Mọi thời điểm là ISO 8601 giờ Việt Nam (+07:00). CSDL lưu `timestamp` không
  múi giờ ở UTC (database.py ép phiên UTC), nên đổi ở lớp này, một chỗ duy nhất.
"""

import threading
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import yeu_cau_admin
from app.database import lay_phien_db
from app.models.platform_token import PlatformToken
from app.models.sync_run import SyncRun
from app.models.user import User
from app.sync import sync_job

router = APIRouter(prefix="/api/sync", tags=["sync"])

GIO_VN = timezone(timedelta(hours=7))
TEN_SAN_HIEN_THI = {"shopee": "Shopee", "tiktok": "TikTok Shop"}
COT_CHAT_LUONG = ["rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
                  "rows_province_unmapped", "rows_product_unmapped"]


def gio_vn_iso(thoi_diem):
    """datetime từ CSDL (UTC, không múi giờ) → chuỗi ISO giờ VN, hoặc None."""
    if thoi_diem is None:
        return None
    return sync_job.sang_utc(thoi_diem).astimezone(GIO_VN).isoformat(timespec="seconds")


def tinh_token_status(refresh_expires_at, bay_gio):
    """`ok` / `expiring` / `expired` theo refresh_expires_at (§12.1.3.2).

    NULL → `ok`: refresh_token không hết hạn (TikTok sống tới 2123, access được
    làm mới tự động), người dùng không cần làm gì.
    """
    if refresh_expires_at is None:
        return "ok"
    han = sync_job.sang_utc(refresh_expires_at)
    if han <= bay_gio:
        return "expired"
    if han - bay_gio <= timedelta(days=settings.TOKEN_EXPIRING_DAYS):
        return "expiring"
    return "ok"


def luot_chay_sang_json(dong, nguoi_chay):
    """Một dòng sync_runs → object SyncRun của hợp đồng §12.1.3.1."""
    return {
        "id": dong.id,
        "platform": dong.platform,
        "shop_name": dong.shop_name,
        "source": dong.source,
        "trigger_type": dong.trigger_type,
        "triggered_by": None if nguoi_chay is None else {"id": nguoi_chay.id, "username": nguoi_chay.username},
        "file_name": dong.file_name,
        "window_from": gio_vn_iso(dong.window_from),
        "window_to": gio_vn_iso(dong.window_to),
        "started_at": gio_vn_iso(dong.started_at),
        "finished_at": gio_vn_iso(dong.finished_at),
        "status": dong.status,
        "error_message": dong.error_message,
        "api_calls": dong.api_calls,
        "orders_fetched": dong.orders_fetched,
        "rows_total": dong.rows_total,
        "rows_inserted": dong.rows_inserted,
        "rows_updated": dong.rows_updated,
        "quality": {cot: getattr(dong, cot) for cot in COT_CHAT_LUONG},
    }


@router.get("/status")
def trang_thai_dong_bo(phien: Session = Depends(lay_phien_db)):
    """Mỗi sàn: có lượt đang chạy không. Mỗi (sàn, shop): lần thành công gần nhất, hạn token (KHÔNG có token)."""
    bay_gio = datetime.now(timezone.utc)
    cac_san = {}
    for san in sync_job.SAN_HOP_LE:
        bat_dau = phien.execute(select(func.min(SyncRun.started_at)).where(
            SyncRun.platform == san, SyncRun.source == "api", SyncRun.status == "running")).scalar_one()
        cac_san[san] = {"running": bat_dau is not None, "running_since": gio_vn_iso(bat_dau)}

    cac_shop = []
    for token in phien.execute(select(PlatformToken).order_by(PlatformToken.platform, PlatformToken.shop_name)).scalars():
        thanh_cong_cuoi = phien.execute(select(func.max(SyncRun.finished_at)).where(
            SyncRun.platform == token.platform, SyncRun.shop_name == token.shop_name,
            SyncRun.status == "success")).scalar_one()
        cac_shop.append({
            "platform": token.platform,
            "shop_name": token.shop_name,
            "last_success_at": gio_vn_iso(thanh_cong_cuoi),
            "access_expires_at": gio_vn_iso(token.access_expires_at),
            "refresh_expires_at": gio_vn_iso(token.refresh_expires_at),
            "token_status": tinh_token_status(token.refresh_expires_at, bay_gio),
        })
    return {"interval_minutes": settings.SYNC_INTERVAL_MINUTES, "platforms": cac_san, "shops": cac_shop}


@router.get("/runs")
def lich_su_dong_bo(
    platform: Literal["shopee", "tiktok"] | None = None,
    source: Literal["api", "file_auto", "file_manual"] | None = None,
    status: Literal["running", "success", "failed"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    phien: Session = Depends(lay_phien_db),
):
    """Lịch sử MỌI lượt đưa dữ liệu vào (api + file), mới nhất trước, có phân trang."""
    dieu_kien = []
    if platform is not None:
        dieu_kien.append(SyncRun.platform == platform)
    if source is not None:
        dieu_kien.append(SyncRun.source == source)
    if status is not None:
        dieu_kien.append(SyncRun.status == status)

    tong = phien.execute(select(func.count()).select_from(SyncRun).where(*dieu_kien)).scalar_one()
    cac_dong = phien.execute(
        select(SyncRun).where(*dieu_kien)
        .order_by(SyncRun.started_at.desc(), SyncRun.id.desc())   # id phá thế hòa khi trùng thời điểm
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    ma_nguoi_chay = {dong.triggered_by for dong in cac_dong if dong.triggered_by is not None}
    nguoi_chay = {u.id: u for u in phien.execute(select(User).where(User.id.in_(ma_nguoi_chay))).scalars()} if ma_nguoi_chay else {}
    return {
        "total": tong, "page": page, "page_size": page_size,
        "items": [luot_chay_sang_json(dong, nguoi_chay.get(dong.triggered_by)) for dong in cac_dong],
    }


def chay_nen_mac_dinh(cac_shop, cac_khoa, cac_run_id):
    """Chạy các lượt trong MỘT thread nền riêng, lần lượt từng shop.

    Dùng threading.Thread thay vì BackgroundTasks của FastAPI: BackgroundTasks
    chạy sau khi gửi phản hồi nhưng TestClient đợi nó xong mới trả về, nên không
    kiểm được "trả 202 ngay, lượt vẫn chạy" và 409 khi đang chạy.
    daemon=True: tắt máy chủ không bị treo chờ lượt (dòng 'running' sót lại sẽ
    được don_dep_luot_treo dọn lúc khởi động lần sau).
    """
    def chay():
        try:
            for (san, ten_shop), khoa, run_id in zip(cac_shop, cac_khoa, cac_run_id):
                # dong_bo_mot_shop tự nhả khoa của shop đó và nuốt mọi lỗi của lượt.
                sync_job.dong_bo_mot_shop(san, ten_shop, "manual", None, khoa=khoa, run_id=run_id)
        finally:
            for khoa in cac_khoa:
                khoa.nha()                      # nhả nốt khóa của shop chưa kịp chạy (nhả nhiều lần vẫn an toàn)
    threading.Thread(target=chay, name="dong-bo-ngay", daemon=True).start()


@router.post("/{platform}", status_code=202)
def dong_bo_ngay(
    platform: Literal["shopee", "tiktok"],
    request: Request,
    phien: Session = Depends(lay_phien_db),
    nguoi_dung=Depends(yeu_cau_admin),
):
    """Nút "Đồng bộ ngay": một lượt cho MỖI gian hàng của sàn, chạy nền, trả `run_ids` ngay.

    Đang có lượt chạy của bất kỳ shop nào của sàn → 409, không chạy chồng (§20.4).
    Giành khóa của MỌI shop trước rồi mới tạo dòng sync_runs: lượt bị từ chối
    không để lại dòng 'running' mồ côi.
    """
    cac_shop = sync_job.liet_ke_shop(phien, platform)
    if not cac_shop:
        raise HTTPException(404, detail={"code": "no_shop", "message": f"Chưa có gian hàng nào của {TEN_SAN_HIEN_THI[platform]}"})

    cac_khoa = []
    try:
        for san, ten_shop in cac_shop:
            khoa = sync_job.thu_giu_khoa(san, ten_shop)
            if khoa is None:
                raise HTTPException(409, detail={
                    "code": "sync_running", "message": f"{TEN_SAN_HIEN_THI[platform]} đang có lượt đồng bộ chạy"})
            cac_khoa.append(khoa)
        trigger_by = None if nguoi_dung is None else nguoi_dung.id
        cac_run_id = [sync_job.tao_luot_chay(phien, san, ten_shop, "manual", trigger_by) for san, ten_shop in cac_shop]
    except BaseException:
        for khoa in cac_khoa:
            khoa.nha()
        raise
    request.app.state.ham_chay_nen(cac_shop, cac_khoa, cac_run_id)
    return {"run_ids": cac_run_id}
