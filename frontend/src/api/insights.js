import { goiApi } from './client.js';

/**
 * Nhận định tự động (SPEC §12.1.4.3). Chỉ gọi khi người dùng bấm nút.
 * Lỗi 503 llm_unavailable chỉ được thẻ nhận định hiển thị, các khối khác không bị ảnh hưởng.
 * @param {{platform: string, granularity: string, period: string}} thamSo
 */
export function sinhNhanDinh(thamSo) {
  return goiApi('POST', '/api/insights/generate', thamSo);
}
