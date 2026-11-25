# Nạp một file CSV vào CSDL trong một giao dịch; lỗi thì rollback và ghi riêng một lượt failed
## Điều phối quy trình nạp
## Quản lý giao dịch an toàn
import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from sqlalchemy import func
from sqlalchemy.exc import DataError, IntegrityError

from app.config import settings
from app.core import log_filter
from app.database import SessionLocal
from app.etl import shopee_parser, tiktok_parser
from app.etl.loader import upsert_don_hang
from app.models.sync_run import SyncRun

logger = logging.getLogger(__name__)


# Các lỗi do nội dung tệp, chỉ những lỗi này mới thành 422; lỗi hạ tầng phải ra 500.
LOI_NOI_DUNG_TEP = (ValueError, KeyError, ParserError, EmptyDataError, UnicodeDecodeError, DataError, IntegrityError)


def mo_ta_loi_gon(loi):
    """Mô tả lỗi gọn, không chứa giá trị ô, vì error_message hiện cho mọi người dùng."""
    ten_loi = type(loi).__name__
    if isinstance(loi, ThieuCotBatBuoc):
        return f"Tệp thiếu cột bắt buộc: {', '.join(loi.cac_cot)}"
    if isinstance(loi, ParserError):
        khop = re.search(r"line (\d+)", str(loi))
        return f"Lỗi đọc tệp ({ten_loi}) ở dòng {khop.group(1)}" if khop else f"Lỗi đọc tệp ({ten_loi})"
    if isinstance(loi, EmptyDataError):
        return f"Tệp rỗng hoặc không có dòng tiêu đề ({ten_loi})"
    if isinstance(loi, UnicodeDecodeError):
        return f"Tệp sai mã hóa ký tự ({ten_loi}) ở byte {loi.start}"
    if isinstance(loi, ValueError):
        thong_diep = str(loi)
        if thong_diep.startswith("DataFrame không đúng cột chuẩn"):
            return thong_diep
        khop_lap = re.match(r"Có (\d+) cặp \(order_id, sku\) lặp lại", thong_diep)
        if khop_lap:
            return f"Có {khop_lap.group(1)} cặp (order_id, sku) lặp lại trong tệp ({ten_loi})"
        khop_vi_tri = re.search(r"at position (\d+)", thong_diep)
        if khop_vi_tri:
            return f"Giá trị không đọc được ({ten_loi}) ở dòng dữ liệu thứ {int(khop_vi_tri.group(1)) + 1}"
        return f"Giá trị trong tệp không hợp lệ ({ten_loi})"
    if isinstance(loi, KeyError):
        return f"Tệp thiếu cột hoặc sai tên cột ({ten_loi})"
    if isinstance(loi, (DataError, IntegrityError)):
        # Tên cột vi phạm do PostgreSQL báo, không phải giá trị, nên an toàn.
        cot = getattr(getattr(getattr(loi, "orig", None), "diag", None), "column_name", None)
        mo_ta = ("Giá trị trong tệp không vừa kiểu dữ liệu của CSDL" if isinstance(loi, DataError)
                 else "Dòng trong tệp vi phạm ràng buộc của CSDL")
        return f"{mo_ta} ({ten_loi})" + (f" ở cột {cot}" if cot else "")
    return f"Lỗi hệ thống khi nạp tệp ({ten_loi})"


class ThieuCotBatBuoc(ValueError):
    def __init__(self, cac_cot):
        self.cac_cot = list(cac_cot)
        super().__init__(f"File thiếu cột bắt buộc: {self.cac_cot}")


def kiem_cot_bat_buoc(san, duong_dan):
    cot_can_doc = shopee_parser.COT_CAN_DOC if san == "shopee" else tiktok_parser.COT_CAN_DOC
    cot_co = set(pd.read_csv(duong_dan, nrows=0, dtype=str, encoding="utf-8-sig").columns)
    cot_thieu = [cot for cot in cot_can_doc if cot not in cot_co]
    if cot_thieu:
        raise ThieuCotBatBuoc(cot_thieu)


def chay_parser(san, duong_dan, ten_shop):
    if san == "shopee":
        return shopee_parser.chuan_hoa_file_shopee(duong_dan, ten_shop)
    return tiktok_parser.chuan_hoa_file_tiktok(duong_dan)


def tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay=None):
    if nguon == "file_manual":
        kieu_kich_hoat = "manual"
    else:
        kieu_kich_hoat = "schedule"
    return SyncRun(
        platform=san,
        # File TikTok chứa nhiều shop nên để NULL.
        shop_name=ten_shop,
        source=nguon,
        trigger_type=kieu_kich_hoat,
        file_name=Path(duong_dan).name,
        triggered_by=nguoi_chay,
    )


def ghi_lan_nap_that_bai(san, duong_dan, ten_shop, nguon, loi, thoi_diem_bat_dau, nguoi_chay=None):
    """Ghi lượt failed trong giao dịch riêng vì giao dịch chính đã rollback."""
    with SessionLocal() as phien:
        dong_sync = tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay)
        # Gán tay started_at, để now() thì thành giờ lúc đã hỏng xong.
        dong_sync.started_at = thoi_diem_bat_dau
        dong_sync.status = "failed"
        dong_sync.error_message = mo_ta_loi_gon(loi)
        # Chi tiết đầy đủ chỉ ở log máy chủ.
        logger.error("Nạp tệp %s (%s) thất bại: %s: %s", Path(duong_dan).name, san, type(loi).__name__, loi)
        dong_sync.finished_at = func.clock_timestamp()
        phien.add(dong_sync)
        phien.commit()
        return dong_sync.id


def nap_file(san, duong_dan, ten_shop, nguon, nguoi_chay=None):
    """Lỗi thì rollback toàn bộ, ghi sync_runs failed rồi ném lại lỗi gốc."""
    # Ghi ở phía Python vì nếu lỗi thì giao dịch chính rollback, mất started_at.
    thoi_diem_bat_dau = datetime.now().astimezone()
    try:
        with SessionLocal() as phien:
            dong_sync = tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay)
            phien.add(dong_sync)
            phien.flush()

            kiem_cot_bat_buoc(san, duong_dan)
            bang_chuan, bo_dem = chay_parser(san, duong_dan, ten_shop)
            so_dong_moi, so_dong_cap_nhat = upsert_don_hang(
                phien, san, bang_chuan, Path(duong_dan).name
            )

            dong_sync.rows_total = len(bang_chuan)
            dong_sync.rows_inserted = so_dong_moi
            dong_sync.rows_updated = so_dong_cap_nhat
            for ten_cot, gia_tri in bo_dem.items():
                setattr(dong_sync, ten_cot, gia_tri)
            dong_sync.status = "success"
            dong_sync.finished_at = func.clock_timestamp()

            # Commit một lần ở cuối để dữ liệu và nhật ký cùng thành công hoặc cùng mất.
            phien.commit()
            return {
                "sync_run_id": dong_sync.id,
                "rows_total": len(bang_chuan),
                "rows_inserted": so_dong_moi,
                "rows_updated": so_dong_cap_nhat,
                **bo_dem,
            }
    except Exception as loi:
        # Bắt mọi lỗi để lỗi nào cũng để lại dấu vết trong sync_runs, rồi ném lại.
        ghi_lan_nap_that_bai(san, duong_dan, ten_shop, nguon, loi, thoi_diem_bat_dau, nguoi_chay)
        raise


def doc_tham_so_dong_lenh(danh_sach_tham_so):
    bo_doc = argparse.ArgumentParser(description="Nạp một file CSV đơn hàng vào CSDL.")
    bo_doc.add_argument("san", choices=["shopee", "tiktok"])
    bo_doc.add_argument("duong_dan", help="đường dẫn file CSV")
    bo_doc.add_argument("--shop", help="tên gian hàng — BẮT BUỘC với Shopee (tệp Shopee không có cột shop), không dùng với TikTok")
    tham_so = bo_doc.parse_args(danh_sach_tham_so)

    if tham_so.san == "tiktok" and tham_so.shop is not None:
        bo_doc.error("file TikTok có cột Shop, không nhận --shop")
    if tham_so.san == "shopee" and not (tham_so.shop and tham_so.shop.strip()):
        # Không có mặc định: đoán sai shop là cộng nhầm doanh thu sang shop khác.
        bo_doc.error('tệp Shopee không có cột shop, phải chỉ rõ gian hàng bằng --shop "<tên gian hàng>"')
    return tham_so


def main():
    log_filter.cai_dat_loc(settings)
    tham_so = doc_tham_so_dong_lenh(sys.argv[1:])
    try:
        ket_qua = nap_file(tham_so.san, tham_so.duong_dan, tham_so.shop, "file_manual")
    except Exception as loi:
        print(f"NẠP THẤT BẠI — đã rollback, đã ghi sync_runs 'failed'. Lỗi: {type(loi).__name__}: {loi}")
        sys.exit(1)

    print(f"Nạp xong {tham_so.san} — {Path(tham_so.duong_dan).name}")
    for ten, gia_tri in ket_qua.items():
        print(f"  {ten}: {gia_tri}")


if __name__ == "__main__":
    main()
