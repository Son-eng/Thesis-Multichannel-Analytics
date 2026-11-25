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
# Khởi tạo thư viện và module
## Quản lý các tác vụ ngầm bất đồng bộ và kiểm soát vòng ứng dụng
import asyncio
from contextlib import asynccontextmanager
## Khởi tạo máy chủ web và cấu hình chia sẻ tài nguyên giữa các domain
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
## Import các router API
from app.api import auth as api_auth
from app.api import connections as api_connections
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


# Che các thông tin nhạy cảm, quét toàn bộ nội dung in ra console/file; nếu xuất hiện access/ refresh token
# hay mật khẩu thì tự động che bằng ***
log_filter.cai_dat_loc(settings)

# Hai hàm truy vấn danh sách gian hàng
# Cả 2 đều dùng with SessionLocal() as phien là để dùng xong sẽ đóng phiên lại ngay và trả về pool
def lay_danh_sach_shop(): # Cung cấp shop và gian hàng trong CSDL để bộ lập lịch biết cần kéo shop nào
    """Mọi (sàn, shop) đang có trong platform_tokens — gọi lại mỗi vòng lịch."""
    with SessionLocal() as phien:
        return sync_job.liet_ke_shop(phien)


def lay_shop_shopee(): # Lấy riêng tên các shop Shopee vì trong tệp csv không có cột tên shop
    """Tên các shop Shopee đang có trong platform_tokens — watcher đọc lại mỗi vòng để tạo ngăn thư mục và gán tệp đúng shop."""
    with SessionLocal() as phien:
        return [ten for _, ten in sync_job.liet_ke_shop(phien, "shopee")]

# Hàm Factory: cho phép các bài test có thể truyền vào các tham số giả lập (khoi_dong_csdl=False, chay_lich=False)
# để test nhanh mà không chạm vào CSDL
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
        # Chạy khi máy chủ khởi động
        if khoi_dong_csdl:
            with SessionLocal() as phien:
                # Tìm các lượt đồng bộ còn đang bị treo và chuyển về "failed" để giải phóng hệ thống
                sync_job.don_dep_luot_treo(phien)
                # Nếu chưa có người dùng thì tạo admin đầu tiên từ biến môi trường
                user_service.tao_admin_dau_tien(phien, settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
            # Nạp token có sẵn trong .env cho shop nào chưa có
            token_store.nap_san_tu_cau_hinh(settings)
        dung = asyncio.Event()
        tac_vu = None
        if bat_lich:
            # Kích hoạt 2 tác vụ chạy ngầm
            ## scheduler.chay_lich: Cứ 10p đồng bộ API một lần
            tac_vu = asyncio.create_task(scheduler.chay_lich(
                dung, lay_danh_sach_shop, sync_job.dong_bo_mot_shop, settings.SYNC_INTERVAL_MINUTES))
        tac_vu_quet = None
        if bat_watcher:
            ## folder_watcher.chay_quet: Cứ 30s quét data/inbox một lần
            tac_vu_quet = asyncio.create_task(folder_watcher.chay_quet(
                dung, thu_muc_data or folder_watcher.thu_muc_goc_mac_dinh(), settings.WATCHER_INTERVAL_SECONDS,
                ham_nap or bo_nap.nap_file, trang_thai_quet, lay_shop_shopee, bo_nap.ghi_lan_nap_that_bai))
        # Tắt máy chủ
        yield
        dung.set() # Báo 2 tác vụ ngầm dừng lại
        for tac in (tac_vu, tac_vu_quet):
            if tac is not None:
                await tac # Chờ tác vụ xử lý xong trước khi tắt hẳn

    ung_dung = FastAPI(title="Hệ thống phân tích dữ liệu bán hàng đa kênh", lifespan=lifespan)
    ung_dung.state.ham_chay_nen = ham_chay_nen or api_sync.chay_nen_mac_dinh
    # Cấu hình CORS
    ## CORSMiddleware: cho phép frontend gửi request tới backend mà không bị chặn
    ung_dung.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOW_ORIGINS,
                            allow_methods=["*"], allow_headers=["*"])
    # Gắn 8 router chức năng
    ## Lưu trữ trạng thái của FastAPI, truyền các đối tượng dùng chung mà không cần dùng biến toàn cục
    ung_dung.state.trang_thai_quet = trang_thai_quet 
    ## include_router: gom các endpoint từ các file con vào ứng dụng -> hệ thống RESTful API
    ung_dung.include_router(api_auth.router)
    ung_dung.include_router(api_users.router)
    ung_dung.include_router(api_sync.router)
    ung_dung.include_router(api_connections.router)
    ung_dung.include_router(api_upload.router)
    ung_dung.include_router(api_dashboard.router)
    ung_dung.include_router(api_export.router)
    ung_dung.include_router(api_insights.router)
    return ung_dung

# Khởi tạo biến thực thi app (Gọi hàm Factory để tạo app)
app = tao_ung_dung()
