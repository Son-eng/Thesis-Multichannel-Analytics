import { goiApi } from './client.js';

export function dangNhap(tenDangNhap, matKhau) {
  return goiApi('POST', '/api/auth/login', { username: tenDangNhap, password: matKhau });
}

export function layNguoiDungHienTai() {
  return goiApi('GET', '/api/auth/me');
}

export function dangXuat() {
  return goiApi('POST', '/api/auth/logout');
}
