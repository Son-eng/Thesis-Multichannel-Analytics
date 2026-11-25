"""Lịch đồng bộ chạy nền; chống chạy chồng nằm ở khóa advisory trong sync_job, không ở đây."""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def chay_mot_vong(cac_shop, ham_dong_bo):
    ket_qua = []
    for san, ten_shop in cac_shop:
        try:
            ket_qua.append((san, ten_shop, await asyncio.to_thread(ham_dong_bo, san, ten_shop)))
        except Exception as loi:
            # Lớp bảo vệ cuối cho lỗi ngoài dự kiến; traceback vẫn đi qua bộ lọc che bí mật.
            logger.exception("Lượt đồng bộ %s/%s lỗi ngoài dự kiến (%s)", san, ten_shop, type(loi).__name__)
            ket_qua.append((san, ten_shop, "loi"))
    return ket_qua


async def chay_lich(dung, lay_danh_sach_shop, ham_dong_bo, so_phut):
    """Nghỉ bằng wait_for để yêu cầu dừng có hiệu lực ngay."""
    while not dung.is_set():
        try:
            await chay_mot_vong(await asyncio.to_thread(lay_danh_sach_shop), ham_dong_bo)
        except Exception as loi:
            logger.exception("Không lấy được danh sách shop để đồng bộ (%s)", type(loi).__name__)
        try:
            await asyncio.wait_for(dung.wait(), timeout=so_phut * 60)
        except asyncio.TimeoutError:
            pass
