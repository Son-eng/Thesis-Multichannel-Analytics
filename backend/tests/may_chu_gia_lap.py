"""Bật máy chủ giả lập (mock_platform) trên SOCKET THẬT ngay trong tiến trình test (chỉ dẫn 009).

Vì sao không dùng TestClient: TestClient không có socket, nên không bắt được
lỗi chỉ có trên mạng thật — đã gặp ở bước 8 C-e (máy chủ trả lỗi trước khi
đọc hết body POST → client bị "connection reset"; TestClient vẫn pass).
Connector là HTTP client thật, nên test connector (bước 9) và test khứ hồi
(bước 10) gọi máy chủ thật.

Vì sao chạy trong một THREAD của tiến trình test, không bật tiến trình ngoài
bằng PowerShell: tắt tiến trình ngoài khó dọn (bước 8 C-c để lại 3 tiến trình
mồ côi) và phụ thuộc hệ điều hành. Thread thì hết phiên test là dừng theo.

Cách dùng (fixture `bat_may_chu_gia_lap` trong conftest.py):
    may_chu = bat_may_chu_gia_lap(MOCK_FAULT_RATE=0.3, MOCK_FAULT_SEED=1)
    httpx2.get(may_chu.url + "/api/v2/...")
"""

import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

THU_MUC_MOCK = Path(__file__).resolve().parents[2] / "mock_platform"


def nap_module_mock():
    """Import code của mock_platform (main, config, data_builder) từ thư mục bên cạnh.

    Chỉ TEST của backend import mock — code chạy thật của backend thì không,
    và mock không bao giờ import backend (§13). Tên module của mock (`main`,
    `config`…) không trùng tên nào của backend (backend chỉ có gói `app`).
    """
    if str(THU_MUC_MOCK) not in sys.path:
        sys.path.insert(0, str(THU_MUC_MOCK))
    import config as config_mock
    import data_builder
    import main as main_mock
    return config_mock, data_builder, main_mock


class MayChuGiaLap:
    """Một máy chủ giả lập đang chạy trong thread nền, cổng ngẫu nhiên còn trống."""

    def __init__(self, ung_dung):
        self.ung_dung = ung_dung
        # Mở socket ở cổng 0 → hệ điều hành chọn một cổng còn trống. Đưa
        # thẳng socket này cho uvicorn nên không có khoảng hở "chọn cổng rồi
        # mới mở" mà tiến trình khác chen vào được.
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self._socket.getsockname()[1]}"
        self._server = uvicorn.Server(uvicorn.Config(ung_dung, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, kwargs={"sockets": [self._socket]}, daemon=True)

    def bat(self):
        self._thread.start()
        han_cho = time.monotonic() + 15
        while not self._server.started:
            if time.monotonic() > han_cho or not self._thread.is_alive():
                raise RuntimeError("Máy chủ giả lập không khởi động được trong 15 giây")
            time.sleep(0.05)
        return self

    def tat(self):
        # should_exit: uvicorn tự dừng vòng lặp, đóng kết nối, rồi thread kết thúc.
        self._server.should_exit = True
        self._thread.join(timeout=15)
        self._socket.close()
