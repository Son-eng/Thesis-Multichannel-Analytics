"""Nhận định bằng LLM: POST /api/insights/generate (UC12, SPEC §10, §12.1.4.3).

Cần đăng nhập (mọi vai trò). Lỗi LLM → 503 `llm_unavailable`; các endpoint khác của dashboard không bị ảnh hưởng.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.services import insight_service, kpi_service

router = APIRouter(prefix="/api/insights", tags=["insights"], dependencies=[Depends(yeu_cau_dang_nhap)])


class YeuCauNhanDinh(BaseModel):
    platform: Literal["shopee", "tiktok"]
    granularity: Literal["day", "month", "quarter", "year"] = "month"
    period: str | None = None


@router.post("/generate")
def sinh_nhan_dinh(yeu_cau: YeuCauNhanDinh, request: Request, phien: Session = Depends(lay_phien_db)):
    try:
        return insight_service.sinh_nhan_dinh(phien, yeu_cau.platform, yeu_cau.granularity, yeu_cau.period,
                                              transport=getattr(request.app.state, "llm_transport", None))
    except kpi_service.KyKhongHopLe as loi:
        raise HTTPException(422, {"code": "invalid_period", "message": str(loi)}) from None
    except insight_service.LoiLLM as loi:
        raise HTTPException(503, {"code": "llm_unavailable", "message": loi.thong_diep}) from None
