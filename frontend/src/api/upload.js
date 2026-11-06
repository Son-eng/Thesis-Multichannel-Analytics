import { goiApi } from './client.js';

/**
 * Nạp tệp CSV dự phòng (admin) (SPEC §12.1.3.5). Trả một SyncRun với source = "file_manual".
 * Lỗi: 400 shop_required; 422 invalid_file; 422 missing_columns.
 * @param {'shopee'|'tiktok'} san
 * @param {File} tep
 * @param {string} [tenGianHang] bắt buộc với Shopee; TikTok bỏ qua vì tệp đã có cột gian hàng
 */
export function napTep(san, tep, tenGianHang) {
  const form = new FormData();
  form.append('file', tep);
  if (tenGianHang) {
    form.append('shop_name', tenGianHang);
  }
  return goiApi('POST', `/api/upload/${san}`, form);
}
