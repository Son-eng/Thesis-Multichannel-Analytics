"""Phụ thuộc (dependency) dùng chung của router — hiện CHỈ có chỗ gắn phân quyền.

Đăng nhập và phân quyền đang HOÃN đến sau demo (SPEC §11, §12.1.4). Khi làm
(JWT, bcrypt, bảng users), sửa DUY NHẤT hàm `yeu_cau_admin` dưới đây: giải mã
token, trả về người dùng, ném 401/403 nếu không đúng. Router không phải đổi.
"""


def yeu_cau_admin():
    """Chỗ để kiểm quyền admin cho các endpoint ghi (POST /api/sync, /api/upload).

    HIỆN TẠI KHÔNG KIỂM GÌ: ai gọi cũng được. Chấp nhận được ở bản demo chạy
    trên máy cá nhân; KHÔNG được mở cổng này ra ngoài mạng nội bộ trước khi
    gắn kiểm quyền thật.
    Trả: người dùng gọi API — None vì chưa có đăng nhập, nên `triggered_by`
    của sync_runs là NULL (hợp đồng §12.1.3.1: "Tự động" khi null).
    """
    return None
