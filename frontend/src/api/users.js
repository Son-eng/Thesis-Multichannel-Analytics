import { goiApi } from './client.js';

// Quản lý người dùng, chỉ admin (UC03, SPEC §12.1.4.2). Không có khóa tài khoản.

export function layDanhSachNguoiDung() {
  return goiApi('GET', '/api/users');
}

/** Tạo tài khoản. Trùng tên: 409 username_taken. */
export function taoNguoiDung({ username, password, role }) {
  return goiApi('POST', '/api/users', { username, password, role });
}

export function doiVaiTro(id, role) {
  return goiApi('PATCH', `/api/users/${id}`, { role });
}

export function datLaiMatKhau(id, password) {
  return goiApi('POST', `/api/users/${id}/reset-password`, { password });
}

/** Xóa tài khoản. Không xóa được chính mình: 400 cannot_delete_self. */
export function xoaNguoiDung(id) {
  return goiApi('DELETE', `/api/users/${id}`);
}
