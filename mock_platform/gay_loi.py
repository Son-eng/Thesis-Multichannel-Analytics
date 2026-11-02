"""Gây lỗi quá tải có chủ đích (SPEC §19.3 mục 5) — để kiểm cơ chế thử lại của connector.

Mỗi route gọi `nen_gay_loi()` ở dòng ĐẦU TIÊN, trước mọi bước kiểm khác. Nhờ
vậy một yêu cầu bị gây lỗi không chạm vào trạng thái: không tiêu refresh_token,
không đổi dữ liệu — y như sàn thật từ chối vì quá tải trước khi xử lý.

Mỗi sàn tự trả lỗi theo khuôn của mình (route quyết định):
    Shopee: HTTP 429 + error_rate_limit   (§16 mục 8)
    TikTok: HTTP 200 + code 36009002      (§16 mục 9)
"""

import random


def tao_bo_sinh_ngau_nhien(hat_giong):
    """Bộ sinh số ngẫu nhiên RIÊNG của máy chủ giả lập.

    Nhận: hạt giống (MOCK_FAULT_SEED) hoặc None.
    Trả: random.Random. Có hạt giống thì chuỗi lỗi lặp lại y hệt giữa các
    lần chạy (test tái lập được); None thì mỗi lần chạy một khác.
    Dùng đối tượng riêng thay cho hàm random.random() chung: code khác (hay
    thư viện) có rút số ngẫu nhiên cũng không làm lệch chuỗi lỗi.
    """
    return random.Random(hat_giong)


def nen_gay_loi(trang_thai):
    """Yêu cầu hiện tại có bị trả lỗi quá tải không.

    Nhận: app.state (có cau_hinh.MOCK_FAULT_RATE và bo_sinh_ngau_nhien).
    Trả: True với xác suất MOCK_FAULT_RATE.
    Tỷ lệ 0 thì trả False ngay, KHÔNG rút số: bật/tắt gây lỗi không làm đổi
    chuỗi số của những lần chạy khác.
    """
    ty_le = trang_thai.cau_hinh.MOCK_FAULT_RATE
    if ty_le <= 0:
        return False
    # random() trả số trong [0, 1) nên tỷ lệ 1 luôn ra True.
    return trang_thai.bo_sinh_ngau_nhien.random() < ty_le
