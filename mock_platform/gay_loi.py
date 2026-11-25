"""Gây lỗi quá tải có chủ đích để kiểm cơ chế thử lại; gọi đầu tiên ở mọi route nên không chạm vào trạng thái."""

import random


def tao_bo_sinh_ngau_nhien(hat_giong):
    return random.Random(hat_giong)


def nen_gay_loi(trang_thai):
    """Tỷ lệ 0 thì trả False ngay, không rút số, để chuỗi số của lần chạy khác không đổi."""
    ty_le = trang_thai.cau_hinh.MOCK_FAULT_RATE
    if ty_le <= 0:
        return False
    return trang_thai.bo_sinh_ngau_nhien.random() < ty_le
