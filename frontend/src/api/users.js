import { goiApi } from './client.js';

export function layDanhSachNguoiDung() {
  return goiApi('GET', '/api/users');
}

export function taoNguoiDung({ username, password, role }) {
  return goiApi('POST', '/api/users', { username, password, role });
}

export function doiVaiTro(id, role) {
  return goiApi('PATCH', `/api/users/${id}`, { role });
}

export function datLaiMatKhau(id, password) {
  return goiApi('POST', `/api/users/${id}/reset-password`, { password });
}

export function xoaNguoiDung(id) {
  return goiApi('DELETE', `/api/users/${id}`);
}
