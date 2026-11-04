"""Endpoint nạp file dự phòng: POST /api/upload/{platform}, GET /api/watcher/status (SPEC §12.1.3.5–§12.1.3.6).

Chưa có đăng nhập (hoãn sau demo): dependency `yeu_cau_admin` là chỗ giữ sẵn; `triggered_by = NULL`.
"""

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.sync import gio_vn_iso, luot_chay_sang_json
from app.config import settings
from app.core.deps import yeu_cau_admin
from app.database import lay_phien_db
from app.etl import nap_file as bo_nap
from app.models.sync_run import SyncRun

router = APIRouter(tags=["upload"])


def _loi(ma, thong_diep, **them):
    return {"code": ma, "message": thong_diep, **them}


@router.post("/api/upload/{platform}")
def tai_file_len(
    platform: Literal["shopee", "tiktok"],
    file: UploadFile = File(...),
    shop_name: str | None = Form(default=None),
    phien: Session = Depends(lay_phien_db),
    _admin=Depends(yeu_cau_admin),
):
    """Nạp một file CSV; trả một SyncRun `file_manual` (§12.1.3.1)."""
    if platform == "shopee" and not (shop_name and shop_name.strip()):
        raise HTTPException(400, _loi("shop_required", "Tệp Shopee cần chọn gian hàng"))
    ten_shop = shop_name.strip() if platform == "shopee" else None

    # Lưu ra file tạm (đúng đuôi .csv, tên thật của file giữ trong sync_runs.file_name).
    with tempfile.TemporaryDirectory() as thu_muc_tam:
        ten_goc = Path(file.filename or "upload.csv").name
        duong_dan = Path(thu_muc_tam) / ten_goc
        with open(duong_dan, "wb") as dau_ra:
            while khoi := file.file.read(1024 * 1024):
                dau_ra.write(khoi)
        try:
            ket_qua = bo_nap.nap_file(platform, str(duong_dan), ten_shop, "file_manual")
        except bo_nap.ThieuCotBatBuoc as loi:
            raise HTTPException(422, _loi("missing_columns", "Tệp thiếu cột bắt buộc, không dòng nào được ghi",
                                          missing_columns=loi.cac_cot))
        except Exception as loi:
            # File không đọc được (không phải CSV, sai giá trị số…): nap_file đã rollback và ghi sync_runs 'failed'.
            raise HTTPException(422, _loi("invalid_file", "Tệp không đọc được, không dòng nào được ghi")) from loi

    dong = phien.get(SyncRun, ket_qua["sync_run_id"])
    return luot_chay_sang_json(dong, None)


@router.get("/api/watcher/status")
def trang_thai_watcher(request: Request):
    """Thời điểm quét gần nhất và số file đang chờ trong inbox (§12.1.3.6)."""
    trang_thai = request.app.state.trang_thai_quet
    return {
        "interval_seconds": settings.WATCHER_INTERVAL_SECONDS,
        "last_scan_at": gio_vn_iso(trang_thai.last_scan_at),
        "pending_files": trang_thai.pending_files,
    }
