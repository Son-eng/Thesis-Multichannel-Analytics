"""Gói mã nguồn của backend.

Để trống có chủ đích: file này chỉ để Python nhận `app` là một package,
nhờ đó các module viết được `from app.config import settings`.
Không đặt code khởi tạo ở đây - đặt vào đây thì mọi lần import bất kỳ
module con nào cũng kéo theo, rất khó lần ra nguyên nhân khi có lỗi.
"""
