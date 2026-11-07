"""Nạp một file CSV vào CSDL — lõi chung của đường file (SPEC §2.4, bước 7).

Chạy tay (từ backend/, đã kích hoạt .venv):
    python -m app.etl.nap_file shopee <đường_dẫn_csv> --shop "Shop C"
    python -m app.etl.nap_file tiktok <đường_dẫn_csv>

Hàm nap_file() là "hàm xử lý chung" mà §2.4 nói tới: thư mục quét tự động và
nút tải file (bước 12) chỉ việc gọi lại hàm này, không viết lại.

Luồng một lần nạp — tất cả trong MỘT giao dịch:
    tạo dòng sync_runs (running) → parser đọc file → loader upsert
    → cập nhật sync_runs (số dòng, 5 bộ đếm, success) → COMMIT
Lỗi ở bất kỳ bước nào → ROLLBACK cả giao dịch (không còn dòng đơn hàng nào
của lần nạp dở), rồi ghi RIÊNG một dòng sync_runs 'failed' kèm thông báo lỗi.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import func

from app.database import SessionLocal
from app.etl import shopee_parser, tiktok_parser
from app.etl.loader import upsert_don_hang
from app.models.sync_run import SyncRun

# Tên gian hàng Shopee mặc định khi nạp file (SPEC §5.1): file Shopee không
# có cột shop nên phải được truyền vào.
SHOP_SHOPEE_MAC_DINH = "Shop C"


class ThieuCotBatBuoc(ValueError):
    """File thiếu cột bắt buộc; `cac_cot` là danh sách tên cột thiếu (SPEC §12.1.3.5, mã 422)."""

    def __init__(self, cac_cot):
        self.cac_cot = list(cac_cot)
        super().__init__(f"File thiếu cột bắt buộc: {self.cac_cot}")


def kiem_cot_bat_buoc(san, duong_dan):
    """Đọc DÒNG TIÊU ĐỀ của file và báo cột nào của sàn bị thiếu, trước khi đọc dữ liệu.

    Nhận: sàn, đường dẫn file.
    Trả: không trả gì; thiếu cột thì ném ThieuCotBatBuoc (đủ tên cột thiếu, theo thứ tự chuẩn).
    Cần hàm này vì `usecols` của pandas chỉ báo lỗi chung chung, còn endpoint nạp file
    phải trả đúng danh sách cột thiếu để người dùng biết file nào đã xuất sai.
    """
    cot_can_doc = shopee_parser.COT_CAN_DOC if san == "shopee" else tiktok_parser.COT_CAN_DOC
    cot_co = set(pd.read_csv(duong_dan, nrows=0, dtype=str, encoding="utf-8-sig").columns)
    cot_thieu = [cot for cot in cot_can_doc if cot not in cot_co]
    if cot_thieu:
        raise ThieuCotBatBuoc(cot_thieu)


def chay_parser(san, duong_dan, ten_shop):
    """Gọi đúng parser của sàn.

    Nhận: san — "shopee" / "tiktok"; đường dẫn file; tên shop (chỉ Shopee dùng).
    Trả: tuple (DataFrame cột chuẩn, dict 5 bộ đếm §3.3) như parser trả.
    Cần hàm này vì 2 parser nhận tham số khác nhau (TikTok lấy shop từ cột
    `Shop` trong file), nơi gọi không phải tự rẽ nhánh.
    """
    if san == "shopee":
        return shopee_parser.chuan_hoa_file_shopee(duong_dan, ten_shop)
    return tiktok_parser.chuan_hoa_file_tiktok(duong_dan)


def tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay=None):
    """Tạo đối tượng SyncRun cho một lần nạp file, chưa ghi xuống CSDL.

    Nhận: sàn, đường dẫn file, tên shop (None với TikTok), nguon —
    "file_manual" (chạy tay / nút tải file) hoặc "file_auto" (thư mục quét).
    Trả: SyncRun mới; status, started_at do CSDL tự đặt mặc định khi ghi.
    Cần hàm này vì cả nhánh thành công lẫn nhánh lỗi đều ghi một dòng
    sync_runs với cùng các thông tin nhận diện lần nạp.
    """
    # trigger_type (§3.3): người bấm/chạy lệnh → "manual"; thư mục quét tự
    # động chạy theo chu kỳ → "schedule".
    if nguon == "file_manual":
        kieu_kich_hoat = "manual"
    else:
        kieu_kich_hoat = "schedule"
    return SyncRun(
        platform=san,
        # File TikTok chứa nhiều shop → để NULL (§3.3).
        shop_name=ten_shop,
        source=nguon,
        trigger_type=kieu_kich_hoat,
        file_name=Path(duong_dan).name,
        triggered_by=nguoi_chay,
    )


def ghi_lan_nap_that_bai(san, duong_dan, ten_shop, nguon, loi, thoi_diem_bat_dau, nguoi_chay=None):
    """Ghi một dòng sync_runs status='failed' trong giao dịch RIÊNG.

    Nhận: thông tin lần nạp như tao_dong_sync_run; loi — exception đã xảy ra;
    thoi_diem_bat_dau — datetime có múi giờ, lấy lúc vào nap_file().
    Trả: id của dòng sync_runs vừa ghi.
    Cần hàm này vì giao dịch chính đã rollback — dòng sync_runs 'running' tạo
    lúc đầu cũng mất theo. Phải mở giao dịch mới thì lịch sử đồng bộ mới thấy
    được lần nạp hỏng này và lý do.
    """
    with SessionLocal() as phien:
        dong_sync = tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay)
        # Phải gán tay: để mặc định now() thì started_at là giờ của giao dịch
        # RIÊNG này, tức lúc đã hỏng xong, không phải lúc lần nạp bắt đầu.
        # Cột kiểu timestamp không múi giờ; PostgreSQL tự đổi giá trị có múi
        # giờ về múi giờ phiên — cùng quy ước với now() của dòng thành công.
        dong_sync.started_at = thoi_diem_bat_dau
        dong_sync.status = "failed"
        dong_sync.error_message = f"{type(loi).__name__}: {loi}"
        # clock_timestamp() là giờ thực lúc chạy câu lệnh; now() là giờ BẮT
        # ĐẦU giao dịch. Cả hai theo múi giờ phiên CSDL, cùng múi với started_at.
        dong_sync.finished_at = func.clock_timestamp()
        phien.add(dong_sync)
        phien.commit()
        return dong_sync.id


def nap_file(san, duong_dan, ten_shop, nguon, nguoi_chay=None):
    """Nạp một file CSV vào bảng orders_* và ghi nhật ký vào sync_runs.

    Nhận: san — "shopee"/"tiktok"; duong_dan — file CSV; ten_shop — tên gian
    hàng (Shopee) hoặc None (TikTok); nguon — "file_manual" hoặc "file_auto";
    nguoi_chay — id người dùng tải file lên (nút tải file), None với thư mục quét và lệnh chạy tay.
    Trả: dict kết quả (id sync_runs, số dòng, số thêm mới, số cập nhật, 5 bộ đếm).
    Lỗi: rollback toàn bộ, ghi sync_runs 'failed', rồi raise lại lỗi gốc để
    nơi gọi biết (lệnh chạy tay thoát mã 1; thư mục quét chuyển file sang failed/).
    Cần hàm này để mọi đường nạp file dùng chung một quy trình có giao dịch.
    """
    # Ghi nhận ở phía Python vì nếu lỗi thì giao dịch chính rollback, mất luôn
    # started_at mà CSDL đã cấp. astimezone() gắn múi giờ máy để CSDL đổi đúng.
    thoi_diem_bat_dau = datetime.now().astimezone()
    try:
        # `with` đảm bảo phiên luôn đóng; thoát khối bằng exception mà chưa
        # commit thì SQLAlchemy tự rollback giao dịch.
        with SessionLocal() as phien:
            dong_sync = tao_dong_sync_run(san, duong_dan, ten_shop, nguon, nguoi_chay)
            phien.add(dong_sync)
            # flush: gửi INSERT ngay (vẫn trong giao dịch, chưa commit) để CSDL
            # cấp id và started_at.
            phien.flush()

            kiem_cot_bat_buoc(san, duong_dan)
            bang_chuan, bo_dem = chay_parser(san, duong_dan, ten_shop)
            so_dong_moi, so_dong_cap_nhat = upsert_don_hang(
                phien, san, bang_chuan, Path(duong_dan).name
            )

            dong_sync.rows_total = len(bang_chuan)
            dong_sync.rows_inserted = so_dong_moi
            dong_sync.rows_updated = so_dong_cap_nhat
            # Khóa của bo_dem trùng tên cột sync_runs (§3.3) nên gán thẳng.
            for ten_cot, gia_tri in bo_dem.items():
                setattr(dong_sync, ten_cot, gia_tri)
            dong_sync.status = "success"
            dong_sync.finished_at = func.clock_timestamp()

            # Commit một lần ở cuối: dữ liệu đơn hàng và nhật ký cùng thành
            # công hoặc cùng mất, không bao giờ có file nạp dở trong CSDL.
            phien.commit()
            return {
                "sync_run_id": dong_sync.id,
                "rows_total": len(bang_chuan),
                "rows_inserted": so_dong_moi,
                "rows_updated": so_dong_cap_nhat,
                **bo_dem,
            }
    except Exception as loi:
        # Bắt mọi loại lỗi (đọc file, parser, CSDL) vì lỗi nào cũng phải để
        # lại dấu vết trong sync_runs. Không nuốt lỗi: raise lại ngay sau đó.
        ghi_lan_nap_that_bai(san, duong_dan, ten_shop, nguon, loi, thoi_diem_bat_dau, nguoi_chay)
        raise


def doc_tham_so_dong_lenh(danh_sach_tham_so):
    """Đọc tham số dòng lệnh.

    Nhận: list chuỗi tham số (thường là sys.argv[1:]).
    Trả: argparse.Namespace có san, duong_dan, shop.
    Cần hàm này để tách phần đọc tham số khỏi phần nạp, test được riêng.
    """
    bo_doc = argparse.ArgumentParser(description="Nạp một file CSV đơn hàng vào CSDL.")
    bo_doc.add_argument("san", choices=["shopee", "tiktok"])
    bo_doc.add_argument("duong_dan", help="đường dẫn file CSV")
    bo_doc.add_argument("--shop", help=f'tên gian hàng — chỉ dùng cho Shopee, mặc định "{SHOP_SHOPEE_MAC_DINH}"')
    tham_so = bo_doc.parse_args(danh_sach_tham_so)

    if tham_so.san == "tiktok" and tham_so.shop is not None:
        # Báo lỗi thay vì lặng lẽ bỏ qua: người chạy tưởng đã đặt tên shop.
        bo_doc.error("file TikTok có cột Shop, không nhận --shop")
    if tham_so.san == "shopee" and tham_so.shop is None:
        tham_so.shop = SHOP_SHOPEE_MAC_DINH
    return tham_so


def main():
    """Điểm vào của lệnh chạy tay. Thành công thoát mã 0, lỗi thoát mã 1."""
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
