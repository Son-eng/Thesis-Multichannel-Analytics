import { LoiApi, dungMock, goiApi } from './client.js';

// Kết nối gian hàng bằng ủy quyền (chỉ dẫn 026, SPEC §22). Luồng: bấm nút → lấy địa chỉ trang ủy quyền của sàn từ backend
// → chuyển trình duyệt sang đó → chủ shop bấm Đồng ý → sàn chuyển về backend → backend chuyển về trang Đồng bộ kèm kết quả.
// Giao diện không bao giờ nhìn thấy token, mã ủy quyền hay khóa ứng dụng: chỉ có địa chỉ chuyển trình duyệt.

export const THONG_DIEP_CAN_BACKEND = 'Cần chạy với backend thật (đặt VITE_USE_MOCK=false) để kết nối gian hàng.';

/**
 * Bắt đầu kết nối một gian hàng (admin). Shopee cần tên hiển thị; với "kết nối lại" truyền tên gian hàng đang có.
 * @param {'shopee'|'tiktok'} san
 * @param {string} [tenShop] tên hiển thị (chỉ Shopee)
 * @returns {Promise<string>} địa chỉ trang ủy quyền của sàn
 * @throws {LoiApi} chế độ dữ liệu giả không có luồng này nên báo "cần chạy với backend", không gọi mạng
 */
export async function batDauKetNoi(san, tenShop) {
  if (dungMock()) {
    throw new LoiApi(0, { code: 'mock', message: THONG_DIEP_CAN_BACKEND });
  }
  const kq = await goiApi('POST', `/api/connections/${san}/authorize`, san === 'shopee' ? { shop_name: tenShop } : {});
  return kq.authorize_url;
}

/** Chuyển trình duyệt sang địa chỉ khác. Tách riêng để test thay được (jsdom không thực hiện điều hướng). */
export function chuyenTrinhDuyet(url) {
  window.location.assign(url);
}
