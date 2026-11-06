import { goiApi } from './client.js';

// Đồng bộ dữ liệu (SPEC §12.1.3). Không hàm nào trả giá trị token, chỉ trả hạn.

/** Trạng thái đồng bộ: chu kỳ, sàn nào đang chạy, hạn quyền truy cập từng gian hàng (§12.1.3.2). */
export function layTrangThaiDongBo() {
  return goiApi('GET', '/api/sync/status');
}

/** "Đồng bộ ngay" một sàn (admin). 202 -> {run_ids}; 409 nếu sàn đang chạy (§12.1.3.3). */
export function chayDongBo(san) {
  return goiApi('POST', `/api/sync/${san}`);
}

/** Lịch sử mọi lượt đưa dữ liệu vào, có lọc và phân trang (§12.1.3.4). */
export function layLichSu(tham) {
  return goiApi('GET', '/api/sync/runs', tham);
}

/** Trạng thái tác vụ quét thư mục (§12.1.3.6). */
export function layTrangThaiThuMuc() {
  return goiApi('GET', '/api/watcher/status');
}
