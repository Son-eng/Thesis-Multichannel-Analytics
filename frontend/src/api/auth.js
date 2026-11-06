import { goiApi } from './client.js';

// Đăng nhập (SPEC §12.1.4.1). Hoãn ở backend: khi demo chạy bằng mock.

/** Trả {access_token, token_type, user}. Sai thông tin: 401 invalid_credentials. */
export function dangNhap(tenDangNhap, matKhau) {
  return goiApi('POST', '/api/auth/login', { username: tenDangNhap, password: matKhau });
}

/** Thông tin người dùng hiện tại: {id, username, role}. */
export function layNguoiDungHienTai() {
  return goiApi('GET', '/api/auth/me');
}

export function dangXuat() {
  return goiApi('POST', '/api/auth/logout');
}
