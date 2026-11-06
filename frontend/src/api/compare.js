import { goiApi } from './client.js';

/**
 * Đối chiếu hai sàn đặt cạnh nhau (§12.1.2). Kết quả chỉ có hai khóa `shopee` và `tiktok`, KHÔNG có tổng.
 * @param {{granularity?: string, period?: string}} tham
 */
export function soSanhHaiSan(tham) {
  return goiApi('GET', '/api/compare/platforms', tham);
}
