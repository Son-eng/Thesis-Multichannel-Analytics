"""Endpoint nạp file dự phòng: POST /api/upload/{platform}, GET /api/watcher/status."""

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.sync import gio_vn_iso, luot_chay_sang_json
from app.config import settings
from app.core.deps import yeu_cau_admin, yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.etl import nap_file as bo_nap
from app.models.sync_run import SyncRun

router = APIRouter(tags=["upload"])

# Giới hạn 50 MB chỉ chặn việc chép ra đĩa và nạp; framework đã nhận hết thân yêu cầu từ trước.
GIOI_HAN_TAI_FILE_BYTE = 50 * 1024 * 1024
KHOI_DOC_BYTE = 1024 * 1024


def _loi(ma, thong_diep, **them):
    return {"code": ma, "message": thong_diep, **them}


@router.post("/api/upload/{platform}")
def tai_file_len(
    platform: Literal["shopee", "tiktok"],
    file: UploadFile = File(...),
    shop_name: str | None = Form(default=None),
    phien: Session = Depends(lay_phien_db),
    admin=Depends(yeu_cau_admin),
):
    if platform == "shopee" and not (shop_name and shop_name.strip()):
        raise HTTPException(400, _loi("shop_required", "Tệp Shopee cần chọn gian hàng"))
    ten_shop = shop_name.strip() if platform == "shopee" else None

    # Thư mục tạm tự xóa khi ra khỏi with, kể cả khi ném 413.
    with tempfile.TemporaryDirectory() as thu_muc_tam:
        ten_goc = Path(file.filename or "upload.csv").name
        duong_dan = Path(thu_muc_tam) / ten_goc
        da_doc = 0
        with open(duong_dan, "wb") as dau_ra:
            while khoi := file.file.read(KHOI_DOC_BYTE):
                da_doc += len(khoi)
                if da_doc > GIOI_HAN_TAI_FILE_BYTE:
                    raise HTTPException(413, _loi(
                        "file_too_large", f"Tệp vượt quá {GIOI_HAN_TAI_FILE_BYTE / (1024 * 1024):g} MB",
                        max_bytes=GIOI_HAN_TAI_FILE_BYTE))
                dau_ra.write(khoi)
        try:
            ket_qua = bo_nap.nap_file(platform, str(duong_dan), ten_shop, "file_manual", admin.id)
        except bo_nap.ThieuCotBatBuoc as loi:
            raise HTTPException(422, _loi("missing_columns", "Tệp thiếu cột bắt buộc, không dòng nào được ghi",
                                          missing_columns=loi.cac_cot))
        except bo_nap.LOI_NOI_DUNG_TEP as loi:
            # Chỉ lỗi do nội dung tệp mới trả 422; lỗi hạ tầng để ra 500.
            raise HTTPException(422, _loi("invalid_file", "Tệp không đọc được, không dòng nào được ghi")) from loi

    dong = phien.get(SyncRun, ket_qua["sync_run_id"])
    return luot_chay_sang_json(dong, admin)


@router.get("/api/watcher/status", dependencies=[Depends(yeu_cau_dang_nhap)])
def trang_thai_watcher(request: Request):
    trang_thai = request.app.state.trang_thai_quet
    return {
        "interval_seconds": settings.WATCHER_INTERVAL_SECONDS,
        "last_scan_at": gio_vn_iso(trang_thai.last_scan_at),
        "pending_files": trang_thai.pending_files,
    }
