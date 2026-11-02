"""Fixture dùng chung cho test endpoint của máy chủ giả lập.

Dữ liệu từ CSV dựng MỘT lần cho cả phiên test (mất vài giây mỗi lần dựng);
app thì tạo mới cho từng test để bảng token luôn sạch.
"""

from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
import data_builder
import main


@pytest.fixture(scope="session")
def du_lieu_shopee():
    return data_builder.dung_du_lieu_shopee()


@pytest.fixture(scope="session")
def du_lieu_tiktok():
    return data_builder.dung_du_lieu_tiktok()


@pytest.fixture(scope="session")
def cau_hinh():
    """Cấu hình đọc từ chính file mẫu .env.example (toàn giá trị giả)."""
    return config.doc_cau_hinh(Path(config.__file__).parent / ".env.example")


@pytest.fixture
def tao_client(du_lieu_shopee, du_lieu_tiktok):
    """Hàm tạo TestClient cho một app mới, với cấu hình và đồng hồ giả cho trước.

    dong_ho là dict {"bay_gio": epoch}: test đổi giá trị này để "tua" thời gian.
    Client được mở trong ngữ cảnh `with` (ExitStack đóng lại khi hết test):
    không có `with`, TestClient dựng một vòng lặp sự kiện MỚI cho mỗi yêu cầu,
    nên test gọi hàng nghìn lần (Finance) chậm hơn nhiều lần.
    """
    with ExitStack() as ngan_xep:
        def tao(cau_hinh, dong_ho):
            ung_dung = main.tao_ung_dung(
                cau_hinh, dong_ho=lambda: dong_ho["bay_gio"],
                du_lieu_shopee=du_lieu_shopee, du_lieu_tiktok=du_lieu_tiktok,
            )
            return ngan_xep.enter_context(TestClient(ung_dung))
        yield tao
