"""Lịch đồng bộ chạy nền trong `lifespan` của FastAPI (SPEC §20.4).

Vòng lặp: đồng bộ lần lượt từng (sàn, shop) → ngủ SYNC_INTERVAL_MINUTES → lặp lại.

Tách riêng với tác vụ quét thư mục (§2.4, chu kỳ 30 giây): hai chu kỳ khác
nhau, gộp thì phải thêm logic đếm vòng — khó giải thích hơn.

Chống chạy chồng KHÔNG nằm ở đây mà ở khóa advisory trong sync_job: lượt do
nút "Đồng bộ ngay" đang chạy thì lượt của lịch tự bỏ qua (dong_bo_mot_shop trả None).

Code đồng bộ (HTTP, CSDL) chạy trong thread (`asyncio.to_thread`) để không
chặn vòng lặp sự kiện của FastAPI.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def chay_mot_vong(cac_shop, ham_dong_bo):
    """Đồng bộ lần lượt từng (sàn, shop). Lỗi một shop không dừng shop khác.

    Nhận: cac_shop — list (sàn, tên shop); ham_dong_bo(san, ten_shop) — hàm
    đồng bộ (thật là sync_job.dong_bo_mot_shop, test truyền hàm giả).
    Trả: list (sàn, shop, kết quả) — kết quả là run_id / None (bỏ lượt) / "loi".
    """
    ket_qua = []
    for san, ten_shop in cac_shop:
        try:
            ket_qua.append((san, ten_shop, await asyncio.to_thread(ham_dong_bo, san, ten_shop)))
        except Exception as loi:
            # dong_bo_mot_shop tự ghi lỗi vào sync_runs; đây là lớp bảo vệ cuối
            # (lỗi ngoài dự kiến, ví dụ không mở được kết nối khóa). Traceback đầy đủ vẫn được ghi (để gỡ lỗi) và đi qua
            # bộ lọc che bí mật (core/log_filter.py); tên loại lỗi đưa lên đầu dòng cho dễ đọc.
            logger.exception("Lượt đồng bộ %s/%s lỗi ngoài dự kiến (%s)", san, ten_shop, type(loi).__name__)
            ket_qua.append((san, ten_shop, "loi"))
    return ket_qua


async def chay_lich(dung, lay_danh_sach_shop, ham_dong_bo, so_phut):
    """Vòng lặp lịch cho tới khi `dung` (asyncio.Event) được đặt.

    Nhận: lay_danh_sach_shop() — trả list (sàn, shop), gọi lại MỖI vòng để shop
    mới thêm vào platform_tokens được nhận ngay; so_phut — nghỉ giữa 2 vòng.
    Nghỉ bằng wait_for(dung.wait()) thay vì sleep: yêu cầu dừng có hiệu lực
    ngay, không phải đợi hết kỳ nghỉ (tắt máy chủ không bị treo).
    """
    while not dung.is_set():
        try:
            await chay_mot_vong(await asyncio.to_thread(lay_danh_sach_shop), ham_dong_bo)
        except Exception as loi:
            logger.exception("Không lấy được danh sách shop để đồng bộ (%s)", type(loi).__name__)
        try:
            await asyncio.wait_for(dung.wait(), timeout=so_phut * 60)
        except asyncio.TimeoutError:
            pass
