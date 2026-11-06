// MỘT cửa duy nhất gọi API. Trang và hook KHÔNG BAO GIỜ gọi fetch trực tiếp.
// Cờ VITE_USE_MOCK chọn nguồn dữ liệu: bật -> src/api/mock/, tắt -> fetch tới VITE_API_BASE_URL.
// Nhờ vậy khi backend xong, chỉ cần tắt cờ, không phải sửa trang nào (SPEC §14 điểm 4).

const KHOA_TOKEN = 'dak_token';
export const SU_KIEN_HET_PHIEN = 'dak-het-phien';

/** Lỗi API thống nhất: status HTTP và `detail` đúng dạng FastAPI (SPEC §12.1.0). */
export class LoiApi extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : (detail && detail.message) || 'Lỗi không xác định');
    this.name = 'LoiApi';
    this.status = status;
    this.detail = detail;
  }
}

/** Đọc token từ localStorage. Bọc try/catch vì trình duyệt có thể chặn localStorage. */
export function layToken() {
  try {
    return window.localStorage.getItem(KHOA_TOKEN);
  } catch (loi) {
    return null;
  }
}

export function datToken(token) {
  try {
    window.localStorage.setItem(KHOA_TOKEN, token);
  } catch (loi) {
    // Không lưu được thì phiên chỉ sống đến khi tải lại trang; không phải lỗi nghiêm trọng.
  }
}

export function xoaToken() {
  try {
    window.localStorage.removeItem(KHOA_TOKEN);
  } catch (loi) {
    // Như trên.
  }
}

/** Mock được bật trừ khi VITE_USE_MOCK được đặt rõ là "false". */
export function dungMock() {
  return import.meta.env.VITE_USE_MOCK !== 'false';
}

function dungChuoiTruyVan(thamSo) {
  const p = new URLSearchParams();
  Object.keys(thamSo || {}).forEach((khoa) => {
    const v = thamSo[khoa];
    if (v !== null && v !== undefined && v !== '') {
      p.append(khoa, String(v));
    }
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}

/**
 * Gom mọi dạng lỗi về một hàm đọc: {code, message, extra}.
 * Vì sao cần: lỗi có thể là {"detail": "chuỗi"}, {"detail": {code, message, ...}}, hoặc mảng 422 của FastAPI;
 * giao diện chỉ cần một chỗ để lấy thông báo.
 */
export function docLoi(loi) {
  if (!loi) {
    return { code: 'unknown', message: 'Lỗi không xác định', extra: {} };
  }
  const detail = loi.detail !== undefined ? loi.detail : null;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const { code, message, ...extra } = detail;
    return { code: code || 'error', message: message || loi.message || 'Lỗi không xác định', extra };
  }
  if (typeof detail === 'string') {
    return { code: 'error', message: detail, extra: {} };
  }
  if (Array.isArray(detail)) {
    return { code: 'validation', message: 'Dữ liệu gửi lên không hợp lệ', extra: { chiTiet: detail } };
  }
  return { code: 'error', message: loi.message || 'Lỗi không xác định', extra: {} };
}

function cho(ms) {
  return new Promise((xong) => {
    setTimeout(xong, ms);
  });
}

async function goiMock(phuongThuc, duongDan, thamSo) {
  const mock = await import('./mock/handlers.js');
  const engine = await import('./mock/engine.js');
  await cho(mock.cauHinhMock.doTre);
  try {
    return await mock.xuLyMock(phuongThuc, duongDan, thamSo, { token: layToken() });
  } catch (loi) {
    if (loi instanceof engine.LoiMock) {
      throw new LoiApi(loi.status, loi.detail);
    }
    throw loi;
  }
}

async function goiHttp(phuongThuc, duongDan, thamSo) {
  const goc = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const coThan = phuongThuc !== 'GET' && phuongThuc !== 'DELETE';
  const headers = {};
  const token = layToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let body;
  if (coThan && thamSo) {
    if (typeof FormData !== 'undefined' && thamSo instanceof FormData) {
      body = thamSo;
    } else {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(thamSo);
    }
  }
  const url = goc + duongDan + (coThan ? '' : dungChuoiTruyVan(thamSo));
  let phanHoi;
  try {
    phanHoi = await fetch(url, { method: phuongThuc, headers, body });
  } catch (loi) {
    throw new LoiApi(0, { code: 'network', message: 'Không kết nối được máy chủ' });
  }
  if (phanHoi.status === 204) {
    return null;
  }
  let noiDung = null;
  try {
    noiDung = await phanHoi.json();
  } catch (loi) {
    noiDung = null;
  }
  if (!phanHoi.ok) {
    throw new LoiApi(phanHoi.status, noiDung && noiDung.detail !== undefined ? noiDung.detail : 'Lỗi máy chủ');
  }
  return noiDung;
}

/**
 * Gọi một endpoint.
 * @param {'GET'|'POST'|'PATCH'|'DELETE'} phuongThuc
 * @param {string} duongDan ví dụ "/api/shopee/kpi"
 * @param {object|FormData} [thamSo] GET/DELETE: tham số truy vấn; POST/PATCH: nội dung gửi lên
 * @returns {Promise<object|null>} JSON theo hợp đồng SPEC §12.1, hoặc null với phản hồi 204
 * @throws {LoiApi}
 */
export async function goiApi(phuongThuc, duongDan, thamSo) {
  try {
    if (dungMock()) {
      return await goiMock(phuongThuc, duongDan, thamSo);
    }
    return await goiHttp(phuongThuc, duongDan, thamSo);
  } catch (loi) {
    // Hết phiên: báo cho AuthContext đưa người dùng về trang đăng nhập (trừ chính lời gọi đăng nhập).
    if (loi instanceof LoiApi && loi.status === 401 && duongDan !== '/api/auth/login') {
      xoaToken();
      window.dispatchEvent(new Event(SU_KIEN_HET_PHIEN));
    }
    throw loi;
  }
}
