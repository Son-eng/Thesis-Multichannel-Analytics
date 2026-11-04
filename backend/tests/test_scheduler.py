"""Test lịch đồng bộ nền `app/sync/scheduler.py` (SPEC §20.4) — chỉ cơ chế vòng lặp, hàm đồng bộ là hàm giả.

Việc đồng bộ thật (mock qua socket, CSDL) đã kiểm ở test_sync_job.py; ở đây
chứng minh: lỗi một shop không dừng shop khác, vòng lặp lặp lại theo chu kỳ,
và yêu cầu dừng có hiệu lực ngay (không đợi hết kỳ nghỉ).
"""

import asyncio
import time

from app.sync import scheduler

CAC_SHOP = [("shopee", "Shop C"), ("tiktok", "Shop A"), ("tiktok", "Shop B")]


def test_mot_vong_lan_luot_tung_shop_va_loi_mot_shop_khong_dung_cac_shop_khac():
    da_goi = []

    def dong_bo(san, ten_shop):
        da_goi.append((san, ten_shop))
        if ten_shop == "Shop A":
            raise RuntimeError("loi ngoai du kien")
        return None if ten_shop == "Shop B" else 42               # None = bỏ lượt (đang chạy)

    ket_qua = asyncio.run(scheduler.chay_mot_vong(CAC_SHOP, dong_bo))
    assert da_goi == CAC_SHOP                                       # đủ 3 shop, đúng thứ tự, dù shop giữa lỗi
    assert ket_qua == [("shopee", "Shop C", 42), ("tiktok", "Shop A", "loi"), ("tiktok", "Shop B", None)]


def test_lich_lap_lai_theo_chu_ky_roi_dung_khi_co_yeu_cau():
    so_vong = []

    async def chay():
        dung = asyncio.Event()

        def dong_bo(san, ten_shop):
            if (san, ten_shop) == CAC_SHOP[0]:
                so_vong.append(1)
                if len(so_vong) >= 3:
                    dung.set()
        # 0,001 phút = 0,06 giây giữa 2 vòng.
        await asyncio.wait_for(scheduler.chay_lich(dung, lambda: CAC_SHOP, dong_bo, 0.001), timeout=10)

    asyncio.run(chay())
    assert len(so_vong) == 3


def test_yeu_cau_dung_co_hieu_luc_ngay_khong_doi_het_ky_nghi():
    async def chay():
        dung = asyncio.Event()
        goi = []
        tac_vu = asyncio.create_task(scheduler.chay_lich(dung, lambda: CAC_SHOP, lambda s, t: goi.append(t), 60))
        await asyncio.sleep(0.5)                                    # vòng đầu xong, đang nghỉ 60 phút
        bat_dau = time.monotonic()
        dung.set()
        await asyncio.wait_for(tac_vu, timeout=5)
        return len(goi), time.monotonic() - bat_dau

    so_lan_goi, mat_bao_lau = asyncio.run(chay())
    assert so_lan_goi == 3 and mat_bao_lau < 1                       # dừng trong dưới 1 giây, không phải 60 phút


def test_danh_sach_shop_duoc_lay_lai_moi_vong_va_loi_lay_danh_sach_khong_giet_lich():
    cac_lan_lay = []

    def lay_danh_sach():
        cac_lan_lay.append(1)
        if len(cac_lan_lay) == 1:
            raise RuntimeError("CSDL tam thoi loi")                  # vòng 1 lỗi → vòng 2 vẫn chạy
        return CAC_SHOP[:1]

    da_goi = []

    async def chay():
        dung = asyncio.Event()

        def dong_bo(san, ten_shop):
            da_goi.append(ten_shop)
            dung.set()
        await asyncio.wait_for(scheduler.chay_lich(dung, lay_danh_sach, dong_bo, 0.001), timeout=10)

    asyncio.run(chay())
    assert len(cac_lan_lay) >= 2 and da_goi == ["Shop C"]
