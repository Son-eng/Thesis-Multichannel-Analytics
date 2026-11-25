import { goiApi } from './client.js';

/** Chỉ gọi khi người dùng bấm nút; lỗi 503 chỉ hiện ở thẻ nhận định. */
export function sinhNhanDinh(thamSo) {
  return goiApi('POST', '/api/insights/generate', thamSo);
}
