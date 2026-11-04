"""Điểm khởi động backend FastAPI (SPEC §13, §20.4).

Chạy (từ backend/, đã có .env và Docker PostgreSQL):
    .venv\\Scripts\\python -m uvicorn app.main:app --port 8000

Lúc khởi động (lifespan):
  1. dọn các lượt đồng bộ 'running' còn sót (máy chủ tắt giữa lượt);
  2. nạp sẵn token ban đầu từ .env vào platform_tokens (shop nào chưa có);
  3. bật lịch đồng bộ nền (SYNC_SCHEDULER_ENABLED).
Lúc tắt: đặt cờ dừng, đợi vòng lặp lịch kết thúc.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import sync as api_sync
from app.config import settings
from app.database import SessionLocal
from app.services import token_store
from app.sync import scheduler, sync_job


def lay_danh_sach_shop():
    """Mọi (sàn, shop) đang có trong platform_tokens — gọi lại mỗi vòng lịch."""
    with SessionLocal() as phien:
        return sync_job.liet_ke_shop(phien)


def tao_ung_dung(chay_lich=None, khoi_dong_csdl=True, ham_chay_nen=None):
    """Tạo app FastAPI.

    Nhận:
        chay_lich — bật lịch đồng bộ nền; None thì theo SYNC_SCHEDULER_ENABLED.
        khoi_dong_csdl — làm bước 1–2 lúc khởi động; test truyền False để khỏi
            động vào CSDL thật khi mở TestClient.
        ham_chay_nen — hàm chạy các lượt của nút "Đồng bộ ngay"; test truyền
            hàm giả (mặc định: thread thật, api/sync.py).
    Trả: app FastAPI.
    """
    bat_lich = settings.SYNC_SCHEDULER_ENABLED if chay_lich is None else chay_lich

    @asynccontextmanager
    async def lifespan(ung_dung):
        if khoi_dong_csdl:
            with SessionLocal() as phien:
                sync_job.don_dep_luot_treo(phien)
            token_store.nap_san_tu_cau_hinh(settings)
        dung = asyncio.Event()
        tac_vu = None
        if bat_lich:
            tac_vu = asyncio.create_task(scheduler.chay_lich(
                dung, lay_danh_sach_shop, sync_job.dong_bo_mot_shop, settings.SYNC_INTERVAL_MINUTES))
        yield
        dung.set()
        if tac_vu is not None:
            await tac_vu

    ung_dung = FastAPI(title="Hệ thống phân tích dữ liệu bán hàng đa kênh", lifespan=lifespan)
    ung_dung.state.ham_chay_nen = ham_chay_nen or api_sync.chay_nen_mac_dinh
    ung_dung.include_router(api_sync.router)
    return ung_dung


app = tao_ung_dung()
