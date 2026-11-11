"""Nhận định bằng LLM: POST /api/insights/generate (UC12, SPEC §10, §12.1.4.3).

Cần đăng nhập (mọi vai trò). Lỗi LLM → 503 `llm_unavailable`; các endpoint khác của dashboard không bị ảnh hưởng.

Giới hạn tần suất (chốt 11/11/2026, chỉ dẫn 021 C.1): mỗi người dùng cách nhau tối thiểu KHOANG_NGHI_TOI_THIEU_GIAY giây
giữa hai lần gọi; gọi sớm hơn → 429 `too_many_requests` kèm `retry_after_seconds` và header `Retry-After`. Đây là bộ đếm
TRONG BỘ NHỚ MỘT TIẾN TRÌNH — đủ cho demo một máy chủ, KHÔNG phải giải pháp phân tán (nhiều tiến trình/máy chủ mỗi nơi
đếm riêng, khởi động lại thì xóa). Lần thử lại nội bộ của chốt chặn số liệu (insight_service) không tính là gọi thêm.
"""

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

# Khoảng nghỉ tối thiểu giữa hai lần gọi của CÙNG một người dùng (giây). 0 = tắt giới hạn (test đặt 0).
KHOANG_NGHI_TOI_THIEU_GIAY = 10

# Đồng hồ đơn điệu, tách thành biến để test giả lập thời gian mà không phải ngủ thật.
dong_ho = time.monotonic

# {id người dùng: thời điểm gọi gần nhất}. Khóa để kiểm-rồi-ghi là một bước nguyên tử khi nhiều luồng cùng gọi.
_lan_goi_cuoi = {}
_khoa = threading.Lock()


def kiem_tan_suat(ma_nguoi_dung):
    """Cho phép hay chưa. Trả 0 nếu được gọi (và ghi nhận lần gọi này), hoặc số giây còn phải chờ (làm tròn lên)."""
    if KHOANG_NGHI_TOI_THIEU_GIAY <= 0:
        return 0
    bay_gio = dong_ho()
    with _khoa:
        lan_truoc = _lan_goi_cuoi.get(ma_nguoi_dung)
        if lan_truoc is not None and bay_gio - lan_truoc < KHOANG_NGHI_TOI_THIEU_GIAY:
            return max(1, math.ceil(KHOANG_NGHI_TOI_THIEU_GIAY - (bay_gio - lan_truoc)))
        _lan_goi_cuoi[ma_nguoi_dung] = bay_gio
        # Dọn các mục đã quá hạn để từ điển không phình dần theo số người dùng.
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
