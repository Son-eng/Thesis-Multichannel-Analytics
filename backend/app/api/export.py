"""Xuất báo cáo: GET /api/export/{platform}/excel, GET /api/export/{platform}/pdf."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.services import export_service, kpi_service

router = APIRouter(prefix="/api/export", tags=["export"], dependencies=[Depends(yeu_cau_dang_nhap)])

KIEU_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/{platform}/excel")
def xuat_excel(platform: Literal["shopee", "tiktok"], granularity: Literal["day", "month", "quarter", "year"] = "month",
               period: str | None = None, shop_name: str | None = None, product_code: str | None = None,
               phien: Session = Depends(lay_phien_db)):
    try:
        noi_dung, ky = export_service.tao_bao_cao_excel(phien, platform, granularity, period, shop_name, product_code)
    except kpi_service.KyKhongHopLe as loi:
        raise HTTPException(422, {"code": "invalid_period", "message": str(loi)}) from None
    ten_tep = f"bao-cao-{platform}-{ky}.xlsx"
    return Response(content=noi_dung, media_type=KIEU_EXCEL,
                    headers={"Content-Disposition": f'attachment; filename="{ten_tep}"'})


@router.get("/{platform}/pdf")
def xuat_pdf(platform: Literal["shopee", "tiktok"]):
    raise HTTPException(501, {"code": "not_supported", "message": "Chưa hỗ trợ trong bản demo"})
