import { goiApi } from './client.js';

/** Đối chiếu hai sàn: kết quả chỉ có hai khóa shopee và tiktok, không có tổng. */
export function soSanhHaiSan(tham) {
  return goiApi('GET', '/api/compare/platforms', tham);
}
