import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

THU_MUC_MOCK = Path(__file__).resolve().parents[2] / "mock_platform"


def nap_module_mock():
    if str(THU_MUC_MOCK) not in sys.path:
        sys.path.insert(0, str(THU_MUC_MOCK))
    import config as config_mock
    import data_builder
    import main as main_mock
    return config_mock, data_builder, main_mock


class MayChuGiaLap:
    def __init__(self, ung_dung):
        self.ung_dung = ung_dung
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
        self._server.should_exit = True
        self._thread.join(timeout=15)
        self._socket.close()
