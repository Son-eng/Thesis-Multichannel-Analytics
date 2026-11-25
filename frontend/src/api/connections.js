import { LoiApi, dungMock, goiApi } from './client.js';

// Kết nối gian hàng bằng ủy quyền; giao diện không bao giờ thấy token, mã ủy quyền hay khóa ứng dụng.

export const THONG_DIEP_CAN_BACKEND = 'Cần chạy với backend thật (đặt VITE_USE_MOCK=false) để kết nối gian hàng.';

/** Shopee cần tên hiển thị; kết nối lại thì truyền tên gian hàng đang có. */
export async function batDauKetNoi(san, tenShop) {
  if (dungMock()) {
    throw new LoiApi(0, { code: 'mock', message: THONG_DIEP_CAN_BACKEND });
  }
  const kq = await goiApi('POST', `/api/connections/${san}/authorize`, san === 'shopee' ? { shop_name: tenShop } : {});
  return kq.authorize_url;
}

/** Tách riêng để test thay được, jsdom không điều hướng thật. */
export function chuyenTrinhDuyet(url) {
  window.location.assign(url);
}
