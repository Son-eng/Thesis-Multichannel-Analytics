import { goiApi } from './client.js';

/** Nạp tệp CSV dự phòng; tên gian hàng bắt buộc với Shopee, TikTok bỏ qua vì tệp đã có cột gian hàng. */
export function napTep(san, tep, tenGianHang) {
  const form = new FormData();
  form.append('file', tep);
  if (tenGianHang) {
    form.append('shop_name', tenGianHang);
  }
  return goiApi('POST', `/api/upload/${san}`, form);
}
