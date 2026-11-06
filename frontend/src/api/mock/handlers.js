// Bộ định tuyến của mock: nhận (phương thức, đường dẫn, tham số) như API thật và trả JSON theo hợp đồng SPEC §12.1.
// Phần nào tính từ số liệu thì gọi engine.js; phần nào là trạng thái (đồng bộ, người dùng, lịch sử) thì giữ ở đây.
//
// Tài khoản mock là tài khoản GIẢ: admin.vh (admin) và quanly.kd (user), mật khẩu giả `demo123`.

import { TAI_KHOAN_GIA, CHAT_LUONG_TEP_MAU, GIAN_HANG } from './realFigures.js';
import { TOKEN_GIA, CHU_KY_DONG_BO_PHUT, THOI_DIEM_HIEN_TAI } from './illustrativeFigures.js';
import * as engine from './engine.js';
import { LoiMock, loiCoMa, kiemTraSan } from './engine.js';
import { dinhDangNgay, rutGonTien, dinhDangTien, dinhDangPhanTram } from '../../utils/format.js';

/**
 * Cấu hình mock. Test và cờ gỡ lỗi chỉnh ở đây, không có nút nào trên giao diện.
 * - doTre: độ trễ giả (ms) để thấy trạng thái đang tải.
 * - thoiGianDongBo: một lượt "Đồng bộ ngay" chạy bao lâu (ms).
 * - llmLoi: true thì /api/insights/generate trả 503.
 */
export const cauHinhMock = {
  doTre: 300,
  thoiGianDongBo: 5000,
  llmLoi: false,
};

export function datCauHinhMock(thayDoi) {
  Object.assign(cauHinhMock, thayDoi);
}

// ----- Trạng thái trong bộ nhớ -----

let nguoiDung = TAI_KHOAN_GIA.map((t) => ({ ...t }));
let idNguoiDungKeTiep = 3;
let dangChay = { shopee: null, tiktok: null }; // thời điểm bắt đầu (ISO) hoặc null
let lichSu = [];
let idLuotKeTiep = 1000;
let hanhDongHen = [];

function taoLichSuMau() {
  // 137 lượt minh họa, mới nhất trước (đúng con số ví dụ §12.1.3.4: total 137).
  const ds = [];
  const cacShop = [
    { platform: 'shopee', shop: 'Shop C' },
    { platform: 'tiktok', shop: 'Shop A' },
    { platform: 'tiktok', shop: 'Shop B' },
  ];
  const baGio = new Date('2026-08-23T16:40:00+07:00').getTime();
  for (let i = 0; i < 137; i += 1) {
    const ca = cacShop[i % 3];
    const thoiDiem = new Date(baGio - Math.floor(i / 3) * 10 * 60000 - (i % 3) * 3000);
    const batDau = chuyenGioVN(thoiDiem);
    const xong = chuyenGioVN(new Date(thoiDiem.getTime() + 7000));
    const huBo = i === 41 || i === 96;
    ds.push({
      id: 137 - i,
      platform: ca.platform,
      shop_name: ca.shop,
      source: 'api',
      trigger_type: i === 20 ? 'manual' : 'schedule',
      triggered_by: i === 20 ? { id: 1, username: 'admin.vh' } : null,
      file_name: null,
      window_from: chuyenGioVN(new Date(thoiDiem.getTime() - 10 * 60000)),
      window_to: batDau,
      started_at: batDau,
      finished_at: xong,
      status: huBo ? 'failed' : 'success',
      error_message: huBo ? 'Máy chủ sàn quá tải, thử lại ở lượt sau' : null,
      api_calls: 3,
      orders_fetched: 4 + (i % 7),
      rows_total: 4 + (i % 7),
      rows_inserted: i % 4,
      rows_updated: 4 + (i % 7) - (i % 4),
      quality: { rows_sku_fallback: 0, rows_sku_unknown: 0, rows_status_unknown: 0, rows_province_unmapped: 0, rows_product_unmapped: 0 },
    });
  }
  // Hai lượt nạp tệp mẫu với bộ đếm THẬT (SPEC §3.3): Shopee 6 / 19, TikTok toàn 0.
  ds[60] = {
    ...ds[60],
    platform: 'shopee',
    shop_name: 'Shop C',
    source: 'file_manual',
    trigger_type: 'manual',
    triggered_by: { id: 1, username: 'admin.vh' },
    file_name: 'shopee_mau.csv',
    window_from: null,
    window_to: null,
    api_calls: 0,
    orders_fetched: 0,
    rows_total: 1774,
    rows_inserted: 1774,
    rows_updated: 0,
    quality: { ...CHAT_LUONG_TEP_MAU.shopee },
  };
  ds[61] = {
    ...ds[61],
    platform: 'tiktok',
    shop_name: null, // tệp TikTok chứa nhiều gian hàng (§12.1.3.1)
    source: 'file_auto',
    trigger_type: 'schedule',
    triggered_by: null,
    file_name: 'tiktok_mau.csv',
    window_from: null,
    window_to: null,
    api_calls: 0,
    orders_fetched: 0,
    rows_total: 7540,
    rows_inserted: 7540,
    rows_updated: 0,
    quality: { ...CHAT_LUONG_TEP_MAU.tiktok },
  };
  return ds;
}

/** Đổi Date sang chuỗi ISO giờ Việt Nam (+07:00) như backend trả ra. */
function chuyenGioVN(d) {
  const bu = new Date(d.getTime() + 7 * 3600000);
  return bu.toISOString().slice(0, 19) + '+07:00';
}

/** Đặt lại toàn bộ trạng thái mock về ban đầu. Test gọi trước mỗi ca. */
export function datLaiMock() {
  nguoiDung = TAI_KHOAN_GIA.map((t) => ({ ...t }));
  idNguoiDungKeTiep = 3;
  dangChay = { shopee: null, tiktok: null };
  hanhDongHen.forEach((h) => clearTimeout(h));
  hanhDongHen = [];
  lichSu = taoLichSuMau();
  idLuotKeTiep = 1000;
  cauHinhMock.llmLoi = false;
}
datLaiMock();

// ----- Phiên đăng nhập giả -----

function tokenCua(u) {
  return `mock-token-${u.username}`;
}

function nguoiTuToken(token) {
  if (!token || !token.startsWith('mock-token-')) {
    return null;
  }
  const ten = token.slice('mock-token-'.length);
  return nguoiDung.find((u) => u.username === ten) || null;
}

function boMatKhau(u) {
  const { password, ...an } = u;
  return an;
}

function canAdmin(nguCanh) {
  const u = nguoiTuToken(nguCanh.token);
  if (!u) {
    throw new LoiMock(401, 'Chưa đăng nhập');
  }
  if (u.role !== 'admin') {
    throw loiCoMa(403, 'forbidden', 'Chỉ quản trị viên được thực hiện thao tác này');
  }
  return u;
}

// ----- Đồng bộ -----

function trangThaiDongBo() {
  const gianHang = TOKEN_GIA.map((t) => ({ ...t }));
  return {
    interval_minutes: CHU_KY_DONG_BO_PHUT,
    platforms: {
      shopee: { running: dangChay.shopee !== null, running_since: dangChay.shopee },
      tiktok: { running: dangChay.tiktok !== null, running_since: dangChay.tiktok },
    },
    shops: gianHang,
  };
}

const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };

function batDauDongBo(san, ngDung, nguCanh) {
  if (dangChay[san] !== null) {
    throw loiCoMa(409, 'sync_running', `${TEN_SAN[san]} đang có lượt đồng bộ chạy`);
  }
  dangChay[san] = THOI_DIEM_HIEN_TAI;
  const dsShop = GIAN_HANG[san];
  const idLuot = dsShop.map(() => {
    idLuotKeTiep += 1;
    return idLuotKeTiep;
  });
  const hen = setTimeout(() => {
    dangChay[san] = null;
    dsShop.forEach((shop, i) => {
      lichSu.unshift({
        id: idLuot[i],
        platform: san,
        shop_name: shop,
        source: 'api',
        trigger_type: 'manual',
        triggered_by: { id: ngDung.id, username: ngDung.username },
        file_name: null,
        window_from: '2026-08-23T16:40:00+07:00',
        window_to: THOI_DIEM_HIEN_TAI,
        started_at: THOI_DIEM_HIEN_TAI,
        finished_at: '2026-08-23T16:50:05+07:00',
        status: 'success',
        error_message: null,
        api_calls: 3,
        orders_fetched: 6,
        rows_total: 6,
        rows_inserted: 2,
        rows_updated: 4,
        quality: { rows_sku_fallback: 0, rows_sku_unknown: 0, rows_status_unknown: 0, rows_province_unmapped: 0, rows_product_unmapped: 0 },
      });
    });
  }, cauHinhMock.thoiGianDongBo);
  hanhDongHen.push(hen);
  return { run_ids: idLuot };
}

function danhSachLuot(q) {
  let ds = lichSu;
  if (q.platform) {
    ds = ds.filter((m) => m.platform === q.platform);
  }
  if (q.source) {
    ds = ds.filter((m) => m.source === q.source);
  }
  if (q.status) {
    ds = ds.filter((m) => m.status === q.status);
  }
  const trang = Number(q.page || 1);
  const co = Number(q.page_size || 20);
  return { total: ds.length, page: trang, page_size: co, items: ds.slice((trang - 1) * co, trang * co) };
}

// ----- Nạp tệp -----

function napTep(san, thamSo, ngDung) {
  const tep = thamSo.get ? thamSo.get('file') : thamSo.file;
  const shop = thamSo.get ? thamSo.get('shop_name') : thamSo.shop_name;
  const tenTep = tep && tep.name ? tep.name : '';
  if (san === 'shopee' && !shop) {
    throw loiCoMa(400, 'shop_required', 'Tệp Shopee cần chọn gian hàng');
  }
  // Chỉ dẫn 06/11/2026: tên tệp có "khong-doc-duoc" -> 422 invalid_file; khác với missing_columns ở chỗ không có danh sách cột.
  if (tenTep.includes('khong-doc-duoc')) {
    throw loiCoMa(422, 'invalid_file', 'Tệp không đọc được, không dòng nào được ghi');
  }
  if (tenTep.includes('thieu-cot')) {
    throw loiCoMa(422, 'missing_columns', 'Tệp thiếu cột bắt buộc, không dòng nào được ghi', {
      missing_columns: ['Mã đơn hàng'],
    });
  }
  idLuotKeTiep += 1;
  const luot = {
    id: idLuotKeTiep,
    platform: san,
    shop_name: san === 'shopee' ? shop : null,
    source: 'file_manual',
    trigger_type: 'manual',
    triggered_by: { id: ngDung.id, username: ngDung.username },
    file_name: tenTep,
    window_from: null,
    window_to: null,
    started_at: THOI_DIEM_HIEN_TAI,
    finished_at: '2026-08-23T16:50:03+07:00',
    status: 'success',
    error_message: null,
    api_calls: 0,
    orders_fetched: 0,
    rows_total: san === 'shopee' ? 1774 : 7540,
    rows_inserted: 0,
    rows_updated: san === 'shopee' ? 1774 : 7540, // nạp lại tệp mẫu: upsert cập nhật, không thêm dòng mới (§4)
    quality: { ...CHAT_LUONG_TEP_MAU[san] },
  };
  lichSu.unshift(luot);
  return luot;
}

// ----- Người dùng -----

function xuLyNguoiDung(phuongThuc, doan, thamSo, nguCanh) {
  const nguoiGoi = canAdmin(nguCanh);
  if (doan.length === 0) {
    if (phuongThuc === 'GET') {
      return nguoiDung.map(boMatKhau);
    }
    if (phuongThuc === 'POST') {
      if (nguoiDung.some((u) => u.username === thamSo.username)) {
        throw loiCoMa(409, 'username_taken', 'Tên đăng nhập đã tồn tại');
      }
      const moi = {
        id: idNguoiDungKeTiep,
        username: thamSo.username,
        role: thamSo.role || 'user',
        password: thamSo.password,
        created_at: THOI_DIEM_HIEN_TAI,
      };
      idNguoiDungKeTiep += 1;
      nguoiDung.push(moi);
      return boMatKhau(moi);
    }
  }
  const id = Number(doan[0]);
  const u = nguoiDung.find((x) => x.id === id);
  if (!u) {
    throw new LoiMock(404, 'Không tìm thấy người dùng');
  }
  if (doan.length === 1 && phuongThuc === 'PATCH') {
    u.role = thamSo.role;
    return boMatKhau(u);
  }
  if (doan.length === 1 && phuongThuc === 'DELETE') {
    if (u.id === nguoiGoi.id) {
      throw loiCoMa(400, 'cannot_delete_self', 'Không thể xóa chính tài khoản đang đăng nhập');
    }
    nguoiDung = nguoiDung.filter((x) => x.id !== id);
    return null;
  }
  if (doan[1] === 'reset-password' && phuongThuc === 'POST') {
    u.password = thamSo.password;
    return null;
  }
  throw new LoiMock(404, 'Không tìm thấy');
}

// ----- Nhận định (LLM giả) -----

/**
 * Sinh nhận định từ chính số mock, đúng nguyên tắc SPEC §10: chỉ diễn giải số đã tính, không tự tính thêm.
 * Đây là văn bản giả lập, không gọi mô hình ngôn ngữ nào.
 */
function sinhNhanDinh(thamSo) {
  if (cauHinhMock.llmLoi) {
    throw loiCoMa(503, 'llm_unavailable', 'Dịch vụ nhận định tự động tạm thời không dùng được');
  }
  const san = thamSo.platform;
  kiemTraSan(san);
  const k = engine.kpi(san, { granularity: thamSo.granularity, period: thamSo.period });
  const top = engine.topProducts(san, { granularity: thamSo.granularity, period: thamSo.period, limit: 3 });
  const doanhThu = k.metrics.revenue;
  const cau = [];
  const mocThoiGian = k.period_complete
    ? `Doanh thu kỳ ${k.period}`
    : `Tính đến ${dinhDangNgay(k.current.date_to)}, doanh thu kỳ ${k.period}`;
  if (k.status === 'no_data') {
    cau.push(`Kỳ ${k.period} không có dữ liệu nên không có nhận định.`);
  } else if (doanhThu.previous_zero || doanhThu.pct_change === null) {
    cau.push(`${mocThoiGian} đạt ${dinhDangTien(doanhThu.value)}. Chưa có kỳ trước để so sánh nên không nhận xét xu hướng.`);
  } else {
    const huong = doanhThu.pct_change >= 0 ? 'tăng' : 'giảm';
    cau.push(
      `${mocThoiGian} đạt ${dinhDangTien(doanhThu.value)}, ${huong} ${dinhDangPhanTram(Math.abs(doanhThu.pct_change))} so với kỳ trước cùng số ngày.`,
    );
  }
  if (top.items.length > 0) {
    cau.push(`Mã ${top.items[0].product_code} dẫn đầu doanh thu với ${dinhDangTien(top.items[0].revenue)} (${rutGonTien(top.items[0].revenue)}).`);
  }
  if (k.alert.triggered) {
    cau.push('Kỳ này vượt ngưỡng cảnh báo giảm doanh thu.');
  }
  return {
    text: cau.join(' '),
    generated_at: THOI_DIEM_HIEN_TAI,
    period_complete: k.period_complete,
    data_max_date: k.data_max_date,
  };
}

// ----- Bộ định tuyến -----

/**
 * Xử lý một lời gọi mock.
 * @param {string} phuongThuc GET | POST | PATCH | DELETE
 * @param {string} duongDan ví dụ "/api/shopee/kpi"
 * @param {object|FormData} thamSo query (GET, DELETE) hoặc body (POST, PATCH)
 * @param {{token: string|null}} nguCanh
 * @returns {Promise<object|null>} dữ liệu JSON, hoặc null với phản hồi 204
 */
export async function xuLyMock(phuongThuc, duongDan, thamSo = {}, nguCanh = { token: null }) {
  const doan = duongDan.replace(/^\/api\//, '').split('/').filter(Boolean);
  const [dau, hai, ba] = doan;
  const goc = thamSo || {};

  if (dau === 'auth') {
    if (hai === 'login' && phuongThuc === 'POST') {
      const u = nguoiDung.find((x) => x.username === goc.username && x.password === goc.password);
      if (!u) {
        throw loiCoMa(401, 'invalid_credentials', 'Tên đăng nhập hoặc mật khẩu không đúng');
      }
      return { access_token: tokenCua(u), token_type: 'bearer', user: { id: u.id, username: u.username, role: u.role } };
    }
    if (hai === 'me' && phuongThuc === 'GET') {
      const u = nguoiTuToken(nguCanh.token);
      if (!u) {
        throw new LoiMock(401, 'Chưa đăng nhập');
      }
      return { id: u.id, username: u.username, role: u.role };
    }
    if (hai === 'logout' && phuongThuc === 'POST') {
      return null;
    }
  }

  if (dau === 'users') {
    return xuLyNguoiDung(phuongThuc, doan.slice(1), goc, nguCanh);
  }

  if (dau === 'sync') {
    if (hai === 'status' && phuongThuc === 'GET') {
      return trangThaiDongBo();
    }
    if (hai === 'runs' && phuongThuc === 'GET') {
      return danhSachLuot(goc);
    }
    if ((hai === 'shopee' || hai === 'tiktok') && phuongThuc === 'POST') {
      const ngDung = canAdmin(nguCanh);
      return batDauDongBo(hai, ngDung, nguCanh);
    }
  }

  if (dau === 'upload' && phuongThuc === 'POST') {
    const ngDung = canAdmin(nguCanh);
    kiemTraSan(hai);
    return napTep(hai, goc, ngDung);
  }

  if (dau === 'watcher' && hai === 'status') {
    return { interval_seconds: 30, last_scan_at: '2026-08-23T16:52:30+07:00', pending_files: 0 };
  }

  if (dau === 'insights' && hai === 'generate' && phuongThuc === 'POST') {
    return sinhNhanDinh(goc);
  }

  if (dau === 'compare' && hai === 'platforms') {
    return engine.comparePlatforms(goc);
  }

  if (dau === 'shopee' || dau === 'tiktok') {
    const bang = {
      filters: () => engine.filters(dau),
      kpi: () => engine.kpi(dau, goc),
      'revenue-trend': () => engine.revenueTrend(dau, goc),
      'top-products': () => engine.topProducts(dau, goc),
      'by-affiliate': () => engine.byAffiliate(dau, goc),
      'by-province': () => engine.byProvince(dau, goc),
      'by-hour': () => engine.byHour(dau, goc),
      alerts: () => engine.alerts(dau, goc),
    };
    if (bang[hai]) {
      return bang[hai]();
    }
  }

  throw new LoiMock(404, 'Không tìm thấy');
}
