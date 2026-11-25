import { goiApi } from './client.js';

// Không hàm nào trả giá trị token, chỉ trả hạn.

export function layTrangThaiDongBo() {
  return goiApi('GET', '/api/sync/status');
}

/** 202 trả {run_ids}; 409 nếu sàn đang chạy. */
export function chayDongBo(san) {
  return goiApi('POST', `/api/sync/${san}`);
}

export function layLichSu(tham) {
  return goiApi('GET', '/api/sync/runs', tham);
}
