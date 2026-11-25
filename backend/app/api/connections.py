# Kết nối gian hàng bằng ủy quyền

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import yeu_cau_admin
from app.database import lay_phien_db
from app.services import ket_noi_gian_hang
from app.sync import sync_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connections", tags=["connections"])


class YeuCauBatDau(BaseModel):
    shop_name: str | None = None


@router.post("/{platform}/authorize")
def bat_dau_ket_noi(platform: Literal["shopee", "tiktok"], than: YeuCauBatDau | None = None, admin=Depends(yeu_cau_admin)):
    try:
        url = ket_noi_gian_hang.bat_dau_ket_noi(platform, admin.id, than.shop_name if than else None)
    except ket_noi_gian_hang.LoiYeuCauKetNoi as loi:
        raise HTTPException(422, detail={"code": loi.ma, "message": loi.thong_diep}) from None
    return {"authorize_url": url}


def kich_hoat_dong_bo_shop(request, phien, san, ten_shop, nguoi_id):
    """Đồng bộ ngay shop vừa kết nối; lỗi ở đây chỉ ghi log, không làm hỏng kết nối."""
    khoa = sync_job.thu_giu_khoa(san, ten_shop)
    if khoa is None:
        return
    try:
        run_id = sync_job.tao_luot_chay(phien, san, ten_shop, "manual", nguoi_id)
        request.app.state.ham_chay_nen([(san, ten_shop)], [khoa], [run_id])
    except BaseException:
        khoa.nha()
        raise


@router.get("/{platform}/callback")
def nhan_ket_qua(platform: Literal["shopee", "tiktok"], request: Request, phien: Session = Depends(lay_phien_db)):
    ket_qua = ket_noi_gian_hang.xu_ly_callback(platform, dict(request.query_params))
    if ket_qua.thanh_cong:
        for ten_shop in ket_qua.cac_shop:
            try:
                kich_hoat_dong_bo_shop(request, phien, platform, ten_shop, ket_qua.nguoi_id)
            except Exception as loi:
                logger.warning("Không kích hoạt được đồng bộ ngay cho %s/%s: %s", platform, ten_shop, type(loi).__name__)
    return RedirectResponse(ket_noi_gian_hang.url_ve_giao_dien(ket_qua), status_code=303)
