"""Điểm khởi động máy chủ giả lập API sàn (SPEC §19). Cổng 8001.

Chạy (từ mock_platform/, đã có .env):
    ..\\backend\\.venv\\Scripts\\python -m uvicorn main:tao_ung_dung_tu_env --factory --port 8001

Dùng chế độ --factory (uvicorn gọi hàm để lấy app) thay vì biến `app` tạo
sẵn lúc import: tạo app cần .env, mà test chỉ muốn import hàm tao_ung_dung()
rồi truyền cấu hình mẫu và đồng hồ giả vào — không được đòi .env thật.

Lúc khởi động: dựng dữ liệu từ CSV (data_builder) và nạp token ban đầu từ
.env vào bảng token. Mọi trạng thái giữ trong `app.state`, mất khi tắt máy
chủ — đúng ý: mỗi lần chạy là một "sàn" sạch.
"""

import time

from fastapi import FastAPI

import config
import data_builder
import shopee_routes
import tokens


def tao_ung_dung(cau_hinh, dong_ho=time.time, du_lieu_shopee=None):
    """Tạo app FastAPI của máy chủ giả lập.

    Nhận: cau_hinh — CauHinhMock; dong_ho — hàm trả epoch giây hiện tại
    (test truyền đồng hồ giả để "tua" thời gian khi kiểm token hết hạn);
    du_lieu_shopee — dữ liệu đã dựng sẵn (test truyền vào để khỏi đọc CSV
    lại cho mỗi test), None thì tự dựng.
    Trả: app FastAPI.
    """
    ung_dung = FastAPI(title="Máy chủ giả lập API sàn (bản demo khóa luận)")
    ung_dung.state.cau_hinh = cau_hinh
    ung_dung.state.dong_ho = dong_ho
    ung_dung.state.du_lieu_shopee = du_lieu_shopee or data_builder.dung_du_lieu_shopee()

    kho_shopee = tokens.KhoToken(
        cau_hinh.MOCK_SHOPEE_ACCESS_TTL_SECONDS, tokens.SHOPEE_HAN_REFRESH_GIAY, vo_hieu_refresh_cu=True
    )
    # Token gắn với shop_id dạng chuỗi — đúng như giá trị đọc từ query.
    kho_shopee.nap_san(
        str(cau_hinh.SHOPEE_SHOP_ID), cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_REFRESH_TOKEN, int(dong_ho())
    )
    ung_dung.state.kho_token_shopee = kho_shopee

    ung_dung.include_router(shopee_routes.router)
    ung_dung.add_exception_handler(shopee_routes.LoiShopee, shopee_routes.xu_ly_loi_shopee)
    return ung_dung


def tao_ung_dung_tu_env():
    """Hàm uvicorn gọi (--factory): đọc mock_platform/.env rồi tạo app."""
    return tao_ung_dung(config.doc_cau_hinh())
