import { goiApi } from './client.js';

// Các endpoint của dashboard một sàn (SPEC §12.1.1). Mỗi hàm một endpoint, trang chỉ import từ đây.

/** Danh sách gian hàng, mã sản phẩm, khoảng dữ liệu của sàn (§12.1.1.1). */
export function layBoLoc(san) {
  return goiApi('GET', `/api/${san}/filters`);
}

/** KPI tổng quan của một kỳ (§12.1.1.2). tham: {granularity, period, shop_name, product_code}. */
export function layKpi(san, tham) {
  return goiApi('GET', `/api/${san}/kpi`, tham);
}

/** Chuỗi doanh thu theo kỳ, tách theo mã sản phẩm (§12.1.1.3). tham: {granularity, date_from, date_to, shop_name, product_code}. */
export function layXuHuong(san, tham) {
  return goiApi('GET', `/api/${san}/revenue-trend`, tham);
}

/** Sản phẩm bán chạy theo product_code (§12.1.1.4). */
export function layTopSanPham(san, tham) {
  return goiApi('GET', `/api/${san}/top-products`, tham);
}

/** Doanh thu tiếp thị liên kết / shop tự bán (§12.1.1.5). */
export function layKenhBan(san, tham) {
  return goiApi('GET', `/api/${san}/by-affiliate`, tham);
}

/** Doanh thu theo tỉnh/thành (§12.1.1.6). */
export function layTheoTinh(san, tham) {
  return goiApi('GET', `/api/${san}/by-province`, tham);
}

/** Đơn hàng theo 24 khung giờ (§12.1.1.7). */
export function layTheoGio(san, tham) {
  return goiApi('GET', `/api/${san}/by-hour`, tham);
}

/** Mọi kỳ vượt ngưỡng cảnh báo (§12.1.1.8). */
export function layCanhBao(san, tham) {
  return goiApi('GET', `/api/${san}/alerts`, tham);
}
