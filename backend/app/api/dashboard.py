"""Endpoint dashboard một sàn và đối chiếu hai sàn (SPEC §12.1.0–§12.1.2).

Router mỏng: đọc tham số, gọi `services/kpi_service.py`, trả JSON đúng hợp đồng. Không logic nghiệp vụ ở đây.
Chưa có đăng nhập (hoãn sau demo): endpoint đọc, mở cho mọi người dùng nội bộ.
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.services import alert_service, kpi_service

# Mọi endpoint đọc dữ liệu cần đăng nhập (mọi vai trò) — SPEC §11.
router = APIRouter(tags=["dashboard"], dependencies=[Depends(yeu_cau_dang_nhap)])

San = Literal["shopee", "tiktok"]
Muc = Literal["day", "month", "quarter", "year"]


def _goi(ham, *tham_so, **tu_khoa):
    """Gọi hàm của kpi_service; mã kỳ sai định dạng → 422 `invalid_period` (khuôn lỗi §12.1.0)."""
    try:
        return ham(*tham_so, **tu_khoa)
    except kpi_service.KyKhongHopLe as loi:
        raise HTTPException(422, {"code": "invalid_period", "message": str(loi)}) from None


@router.get("/api/compare/platforms")
def doi_chieu_hai_san(granularity: Muc = "month", period: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.so_sanh_hai_san, phien, granularity, period)


@router.get("/api/{platform}/filters")
def bo_loc(platform: San, phien: Session = Depends(lay_phien_db)):
    return kpi_service.danh_sach_loc(phien, platform)


@router.get("/api/{platform}/kpi")
def kpi(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
        product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.kpi, phien, platform, granularity, period, shop_name, product_code)


@router.get("/api/{platform}/revenue-trend")
def xu_huong_doanh_thu(platform: San, granularity: Muc = "month", date_from: date | None = None,
                       date_to: date | None = None, shop_name: str | None = None, product_code: str | None = None,
                       phien: Session = Depends(lay_phien_db)):
    return kpi_service.revenue_trend(phien, platform, granularity, date_from, date_to, shop_name, product_code)


@router.get("/api/{platform}/top-products")
def san_pham_ban_chay(platform: San, granularity: Muc = "month", period: str | None = None,
                      shop_name: str | None = None, product_code: str | None = None,
                      limit: int = Query(default=10, ge=1, le=100),
                      sort_by: Literal["revenue", "quantity"] = "revenue", phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.top_products, phien, platform, granularity, period, limit, sort_by, shop_name, product_code)


@router.get("/api/{platform}/by-affiliate")
def theo_affiliate(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
                   product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_affiliate, phien, platform, granularity, period, shop_name, product_code)


@router.get("/api/{platform}/by-province")
def theo_tinh(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
              product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_province, phien, platform, granularity, period, shop_name, product_code)


@router.get("/api/{platform}/by-hour")
def theo_gio(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
             product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_hour, phien, platform, granularity, period, shop_name, product_code)


@router.get("/api/{platform}/alerts")
def canh_bao(platform: San, granularity: Muc = "month", shop_name: str | None = None,
             product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    """Mọi kỳ bị cảnh báo theo mức đang chọn trên toàn bộ dữ liệu của sàn (§12.1.1.8). Không nhận `period`."""
    return alert_service.liet_ke_canh_bao(phien, platform, granularity, shop_name, product_code)
