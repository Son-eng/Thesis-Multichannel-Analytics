"""Chạy tay: gọi Gemini thật để thử sinh nhận định, tốn hạn mức của khóa.
Dùng (từ backend/): .venv\\Scripts\\python scripts\\thu_nhan_dinh.py [sàn mức kỳ], ví dụ: tiktok month 2026-04.
Chỉ gửi số liệu tổng hợp, không có dữ liệu cá nhân; không bao giờ in khóa.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import insight_service  # noqa: E402


def main():
    san = sys.argv[1] if len(sys.argv) > 1 else "shopee"
    muc = sys.argv[2] if len(sys.argv) > 2 else "month"
    ky = sys.argv[3] if len(sys.argv) > 3 else "2026-08"
    if settings.GEMINI_API_KEY is None or not settings.GEMINI_API_KEY.get_secret_value():
        print("chưa có khóa: đặt GEMINI_API_KEY trong backend/.env rồi chạy lại.")
        return 0
    print(f"Model: {settings.GEMINI_MODEL} · {san} {muc} {ky}")
    with SessionLocal() as phien:
        du_lieu, _ = insight_service.dung_du_lieu_gui(phien, san, muc, ky)
        print("--- Dữ liệu gửi đi ---")
        print(json.dumps(du_lieu, ensure_ascii=False, indent=2))
        try:
            ket_qua = insight_service.sinh_nhan_dinh(phien, san, muc, ky)
        except insight_service.LoiLLM as loi:
            print(f"--- LỖI: {loi.thong_diep}")
            return 1
    print("--- Nhận định nhận được ---")
    print(ket_qua["text"])
    print(f"--- Số lạ theo chốt chặn: {insight_service.tim_so_la(ket_qua['text'], du_lieu) or 'không có'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
