# Dữ liệu của toàn bộ giao diện phân tích (màn hình từng sàn, màn hình so sánh 2 sàn)

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_dang_nhap
from app.database import lay_phien_db
from app.services import alert_service, kpi_service

# Phân quyền và xác thực tham số đầu vào
## Cho toàn bộ users
router = APIRouter(tags=["dashboard"], dependencies=[Depends(yeu_cau_dang_nhap)])

San = Literal["shopee", "tiktok"]
Muc = Literal["day", "month", "quarter", "year"]

# Hàm bọc xử lý lỗi
def _goi(ham, *tham_so, **tu_khoa):
    try:
        return ham(*tham_so, **tu_khoa)
    except kpi_service.KyKhongHopLe as loi:
        raise HTTPException(422, {"code": "invalid_period", "message": str(loi)}) from None

# 9 endpoint cho các khối giao diện 
## Đối chiếu 2 sàn
@router.get("/api/compare/platforms")
def doi_chieu_hai_san(granularity: Muc = "month", period: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.so_sanh_hai_san, phien, granularity, period)

## Bộ lọc
@router.get("/api/{platform}/filters")
def bo_loc(platform: San, phien: Session = Depends(lay_phien_db)):
    return kpi_service.danh_sach_loc(phien, platform)

## Dữ liệu cho 4 thẻ KPI đầu trang
@router.get("/api/{platform}/kpi")
def kpi(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
        product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.kpi, phien, platform, granularity, period, shop_name, product_code)

## Cung cấp dữ liệu vẽ biểu đồ theo thời gian
@router.get("/api/{platform}/revenue-trend")
def xu_huong_doanh_thu(platform: San, granularity: Muc = "month", date_from: date | None = None,
                       date_to: date | None = None, shop_name: str | None = None, product_code: str | None = None,
                       phien: Session = Depends(lay_phien_db)):
    return kpi_service.revenue_trend(phien, platform, granularity, date_from, date_to, shop_name, product_code)

## Danh sách sản phẩm bán chạy nhất
@router.get("/api/{platform}/top-products")
def san_pham_ban_chay(platform: San, granularity: Muc = "month", period: str | None = None,
                      shop_name: str | None = None, product_code: str | None = None,
                      limit: int = Query(default=10, ge=1, le=100),
                      sort_by: Literal["revenue", "quantity"] = "revenue", phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.top_products, phien, platform, granularity, period, limit, sort_by, shop_name, product_code)

## Tỉ trọng doanh thu giữa Affiliate và Inhouse
@router.get("/api/{platform}/by-affiliate")
def theo_affiliate(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
                   product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_affiliate, phien, platform, granularity, period, shop_name, product_code)

## Xếp hạng doanh thu và đơn hàng theo tỉnh thành VN
@router.get("/api/{platform}/by-province")
def theo_tinh(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
              product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_province, phien, platform, granularity, period, shop_name, product_code)

## Khung giờ ra đơn
@router.get("/api/{platform}/by-hour")
def theo_gio(platform: San, granularity: Muc = "month", period: str | None = None, shop_name: str | None = None,
             product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return _goi(kpi_service.by_hour, phien, platform, granularity, period, shop_name, product_code)

## Danh sách các kỳ sụt giảm quá ngưỡng
@router.get("/api/{platform}/alerts")
def canh_bao(platform: San, granularity: Muc = "month", shop_name: str | None = None,
             product_code: str | None = None, phien: Session = Depends(lay_phien_db)):
    return alert_service.liet_ke_canh_bao(phien, platform, granularity, shop_name, product_code)

### Chia endpoint để tăng hiệu năng tải trang và tái sử dụng linh hoạt