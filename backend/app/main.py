"""Điểm khởi động backend FastAPI (SPEC §13, §20.4).

Chạy (từ backend/, đã có .env và Docker PostgreSQL):
    .venv\\Scripts\\python -m uvicorn app.main:app --port 8000

Lúc khởi động (lifespan):
  1. dọn các lượt đồng bộ 'running' còn sót (máy chủ tắt giữa lượt); tạo admin đầu tiên nếu bảng users trống;
  2. nạp sẵn token ban đầu từ .env vào platform_tokens (shop nào chưa có);
  3. bật lịch đồng bộ nền (SYNC_SCHEDULER_ENABLED);
  4. bật quét thư mục data/inbox (WATCHER_ENABLED, §2.4).
Lúc tắt: đặt cờ dừng, đợi vòng lặp lịch kết thúc.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as api_auth
from app.api import dashboard as api_dashboard
from app.api import export as api_export
from app.api import insights as api_insights
from app.api import sync as api_sync
from app.api import upload as api_upload
from app.api import users as api_users
from app.etl import nap_file as bo_nap
from app.config import settings
from app.core import log_filter
from app.database import SessionLocal
from app.services import token_store, user_service
from app.sync import folder_watcher, scheduler, sync_job


# Lắp bộ lọc che bí mật lên MỌI handler của tiến trình (uvicorn dựng handler trước khi nạp ứng dụng nên bộ lọc
# phải được gắn vào cả handler đã có). Gọi ở mức module để cũng có hiệu lực khi chạy `uvicorn app.main:app`.
log_filter.cai_dat_loc(settings)


def lay_danh_sach_shop():
    """Mọi (sàn, shop) đang có trong platform_tokens — gọi lại mỗi vòng lịch."""
    with SessionLocal() as phien:
        return sync_job.liet_ke_shop(phien)


def tao_ung_dung(chay_lich=None, khoi_dong_csdl=True, ham_chay_nen=None,
                 chay_watcher=None, thu_muc_data=None, ham_nap=None):
    """Tạo app FastAPI.

    Nhận:
        chay_lich — bật lịch đồng bộ nền; None thì theo SYNC_SCHEDULER_ENABLED.
        khoi_dong_csdl — làm bước 1–2 lúc khởi động; test truyền False để khỏi
            động vào CSDL thật khi mở TestClient.
        ham_chay_nen — hàm chạy các lượt của nút "Đồng bộ ngay"; test truyền
            hàm giả (mặc định: thread thật, api/sync.py).
        chay_watcher — bật quét thư mục; None thì theo WATCHER_ENABLED.
        thu_muc_data — thư mục `data/` (mặc định ở gốc project); test truyền thư mục tạm.
        ham_nap — hàm nạp file của watcher (mặc định nap_file.nap_file).
    Trả: app FastAPI.
    """
    bat_lich = settings.SYNC_SCHEDULER_ENABLED if chay_lich is None else chay_lich
    bat_watcher = settings.WATCHER_ENABLED if chay_watcher is None else chay_watcher
    trang_thai_quet = folder_watcher.TrangThaiQuet()

    @asynccontextmanager
    async def lifespan(ung_dung):
        if khoi_dong_csdl:
            with SessionLocal() as phien:
                sync_job.don_dep_luot_treo(phien)
                user_service.tao_admin_dau_tien(phien, settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
            token_store.nap_san_tu_cau_hinh(settings)
        dung = asyncio.Event()
        tac_vu = None
        if bat_lich:
            tac_vu = asyncio.create_task(scheduler.chay_lich(
                dung, lay_danh_sach_shop, sync_job.dong_bo_mot_shop, settings.SYNC_INTERVAL_MINUTES))
        tac_vu_quet = None
        if bat_watcher:
            tac_vu_quet = asyncio.create_task(folder_watcher.chay_quet(
                dung, thu_muc_data or folder_watcher.thu_muc_goc_mac_dinh(), settings.WATCHER_INTERVAL_SECONDS,
                ham_nap or bo_nap.nap_file, trang_thai_quet))
        yield
        dung.set()
        for tac in (tac_vu, tac_vu_quet):
            if tac is not None:
                await tac

    ung_dung = FastAPI(title="Hệ thống phân tích dữ liệu bán hàng đa kênh", lifespan=lifespan)
    ung_dung.state.ham_chay_nen = ham_chay_nen or api_sync.chay_nen_mac_dinh
    # CORS: frontend dev (Vite) ở origin khác cổng với backend.
    ung_dung.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOW_ORIGINS,
                            allow_methods=["*"], allow_headers=["*"])
    ung_dung.state.trang_thai_quet = trang_thai_quet
    ung_dung.include_router(api_auth.router)
    ung_dung.include_router(api_users.router)
    ung_dung.include_router(api_sync.router)
    ung_dung.include_router(api_upload.router)
    ung_dung.include_router(api_dashboard.router)
    ung_dung.include_router(api_export.router)
    ung_dung.include_router(api_insights.router)
    return ung_dung


app = tao_ung_dung()
