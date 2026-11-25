# Sinh nhận định bằng AI

import math
import threading
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.models.user import User
from app.services import insight_service, kpi_service

router = APIRouter(prefix="/api/insights", tags=["insights"], dependencies=[Depends(yeu_cau_dang_nhap)])

# Khoảng nghỉ tối thiểu giữa hai lần gọi của một người dùng (giây), 0 là tắt.
KHOANG_NGHI_TOI_THIEU_GIAY = 10

# Tách ra biến để test giả lập thời gian.
dong_ho = time.monotonic

# Khóa để bước kiểm rồi ghi là nguyên tử khi nhiều luồng cùng gọi.
_lan_goi_cuoi = {}
_khoa = threading.Lock()


def kiem_tan_suat(ma_nguoi_dung):
    if KHOANG_NGHI_TOI_THIEU_GIAY <= 0:
        return 0
    bay_gio = dong_ho()
    with _khoa:
        lan_truoc = _lan_goi_cuoi.get(ma_nguoi_dung)
        if lan_truoc is not None and bay_gio - lan_truoc < KHOANG_NGHI_TOI_THIEU_GIAY:
            return max(1, math.ceil(KHOANG_NGHI_TOI_THIEU_GIAY - (bay_gio - lan_truoc)))
        _lan_goi_cuoi[ma_nguoi_dung] = bay_gio
        # Dọn mục quá hạn để từ điển không phình theo số người dùng.
        for ma, thoi_diem in list(_lan_goi_cuoi.items()):
            if bay_gio - thoi_diem >= KHOANG_NGHI_TOI_THIEU_GIAY:
                del _lan_goi_cuoi[ma]
        _lan_goi_cuoi[ma_nguoi_dung] = bay_gio
        return 0


class YeuCauNhanDinh(BaseModel):
    platform: Literal["shopee", "tiktok"]
    granularity: Literal["day", "month", "quarter", "year"] = "month"
    period: str | None = None


@router.post("/generate")
def sinh_nhan_dinh(yeu_cau: YeuCauNhanDinh, request: Request, phien: Session = Depends(lay_phien_db),
                   nguoi: User = Depends(yeu_cau_dang_nhap)):
    cho_them = kiem_tan_suat(nguoi.id)
    if cho_them:
        raise HTTPException(429, {"code": "too_many_requests", "message": "Vui lòng đợi vài giây rồi thử lại",
                                  "retry_after_seconds": cho_them}, headers={"Retry-After": str(cho_them)})
    try:
        return insight_service.sinh_nhan_dinh(phien, yeu_cau.platform, yeu_cau.granularity, yeu_cau.period,
                                              transport=getattr(request.app.state, "llm_transport", None))
    except kpi_service.KyKhongHopLe as loi:
        raise HTTPException(422, {"code": "invalid_period", "message": str(loi)}) from None
    except insight_service.LoiLLM as loi:
        raise HTTPException(503, {"code": "llm_unavailable", "message": loi.thong_diep}) from None
