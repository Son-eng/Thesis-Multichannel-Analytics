// Mã kỳ (period) và phép tính lịch (SPEC §12.1.0): ngày 2026-08-16 · tháng 2026-08 · quý 2026-Q3 · năm 2026.
// Dùng ở hai nơi: ô chọn kỳ trên giao diện và máy chủ giả lập (mock).
// Mọi phép tính ngày dùng UTC để không lệch múi giờ của máy chạy.

/** Mức thời gian hợp lệ. */
export const MUC_THOI_GIAN = ['day', 'month', 'quarter', 'year'];

/** Nhãn mức thời gian cho ô chọn. */
export const NHAN_MUC = {
  day: 'Theo ngày',
  month: 'Theo tháng',
  quarter: 'Theo quý',
  year: 'Theo năm',
};

function hai(n) {
  return String(n).padStart(2, '0');
}

/** "YYYY-MM-DD" -> Date UTC 00:00. */
export function docNgay(iso) {
  const [nam, thang, ngay] = iso.split('-').map(Number);
  return new Date(Date.UTC(nam, thang - 1, ngay));
}

/** Date UTC -> "YYYY-MM-DD". */
export function ghiNgay(d) {
  return `${d.getUTCFullYear()}-${hai(d.getUTCMonth() + 1)}-${hai(d.getUTCDate())}`;
}

/** Cộng (hoặc trừ) số ngày vào một ngày ISO. */
export function congNgay(iso, soNgay) {
  const d = docNgay(iso);
  d.setUTCDate(d.getUTCDate() + soNgay);
  return ghiNgay(d);
}

/** Số ngày giữa hai ngày ISO (tính cả hai đầu): 01 -> 16 là 16 ngày. */
export function demNgay(tu, den) {
  const ms = docNgay(den).getTime() - docNgay(tu).getTime();
  return Math.round(ms / 86400000) + 1;
}

/** Ngày cuối cùng của một tháng (nam, thang 1-12). */
function ngayCuoiThang(nam, thang) {
  return ghiNgay(new Date(Date.UTC(nam, thang, 0)));
}

/**
 * Mã kỳ chứa một ngày, theo mức đã chọn.
 * @example maKyChuaNgay('quarter', '2026-08-16') // '2026-Q3'
 */
export function maKyChuaNgay(muc, iso) {
  const nam = iso.slice(0, 4);
  const thang = Number(iso.slice(5, 7));
  if (muc === 'day') {
    return iso;
  }
  if (muc === 'month') {
    return iso.slice(0, 7);
  }
  if (muc === 'quarter') {
    return `${nam}-Q${Math.floor((thang - 1) / 3) + 1}`;
  }
  return nam;
}

/** Kiểm tra mã kỳ có đúng định dạng của mức không (dùng ở mock để trả 422 invalid_period). */
export function maKyHopLe(muc, ma) {
  if (typeof ma !== 'string') {
    return false;
  }
  if (muc === 'day') {
    return /^\d{4}-\d{2}-\d{2}$/.test(ma);
  }
  if (muc === 'month') {
    return /^\d{4}-(0[1-9]|1[0-2])$/.test(ma);
  }
  if (muc === 'quarter') {
    return /^\d{4}-Q[1-4]$/.test(ma);
  }
  return /^\d{4}$/.test(ma);
}

/** Ngày đầu của kỳ. */
export function ngayDauKy(muc, ma) {
  if (muc === 'day') {
    return ma;
  }
  if (muc === 'month') {
    return `${ma}-01`;
  }
  if (muc === 'quarter') {
    const quy = Number(ma.slice(6, 7));
    return `${ma.slice(0, 4)}-${hai((quy - 1) * 3 + 1)}-01`;
  }
  return `${ma}-01-01`;
}

/** Ngày cuối (theo lịch) của kỳ. */
export function ngayCuoiKy(muc, ma) {
  if (muc === 'day') {
    return ma;
  }
  if (muc === 'month') {
    return ngayCuoiThang(Number(ma.slice(0, 4)), Number(ma.slice(5, 7)));
  }
  if (muc === 'quarter') {
    const quy = Number(ma.slice(6, 7));
    return ngayCuoiThang(Number(ma.slice(0, 4)), quy * 3);
  }
  return `${ma}-12-31`;
}

/** Kỳ liền trước. */
export function kyTruocCua(muc, ma) {
  if (muc === 'day') {
    return congNgay(ma, -1);
  }
  return maKyChuaNgay(muc, congNgay(ngayDauKy(muc, ma), -1));
}

/** Kỳ liền sau. */
export function kyKeTiep(muc, ma) {
  return maKyChuaNgay(muc, congNgay(ngayCuoiKy(muc, ma), 1));
}

/**
 * Kỳ đã đủ ngày chưa? So ngày cuối theo lịch của kỳ với ngày dữ liệu mới nhất
 * (SPEC §9.2: dùng MAX(order_date) của dữ liệu, KHÔNG dùng ngày hôm nay).
 */
export function kyDayDu(muc, ma, ngayDuLieuMoiNhat) {
  return ngayCuoiKy(muc, ma) <= ngayDuLieuMoiNhat;
}

/**
 * Nhãn kỳ hiển thị.
 * @example nhanKy('month', '2026-08') // 'Tháng 8/2026'
 */
export function nhanKy(muc, ma) {
  if (muc === 'day') {
    return `${ma.slice(8, 10)}/${ma.slice(5, 7)}/${ma.slice(0, 4)}`;
  }
  if (muc === 'month') {
    return `Tháng ${Number(ma.slice(5, 7))}/${ma.slice(0, 4)}`;
  }
  if (muc === 'quarter') {
    return `Quý ${ma.slice(6, 7)}/${ma.slice(0, 4)}`;
  }
  return `Năm ${ma}`;
}

/** Nhãn ngắn trên trục: "T8", "Q3", "2026", "16/08". */
export function nhanKyNgan(muc, ma) {
  if (muc === 'day') {
    return `${ma.slice(8, 10)}/${ma.slice(5, 7)}`;
  }
  if (muc === 'month') {
    return `T${Number(ma.slice(5, 7))}`;
  }
  if (muc === 'quarter') {
    return `Q${ma.slice(6, 7)}`;
  }
  return ma;
}

/**
 * Danh sách kỳ cho ô chọn, sinh từ khoảng dữ liệu của sàn (`/filters`).
 * Chỉ giữ kỳ có giao với khoảng dữ liệu. Kỳ chưa đủ ngày có dấu * (đã gắn vào label).
 * Mới nhất xếp đầu.
 * @returns {{key: string, label: string, complete: boolean}[]}
 */
export function danhSachKy(muc, ngayMin, ngayMax) {
  const ketQua = [];
  let ma = maKyChuaNgay(muc, ngayMin);
  const cuoi = maKyChuaNgay(muc, ngayMax);
  // Vòng lặp dừng khi vượt kỳ cuối; chặn thêm 5000 bước để không bao giờ treo trình duyệt.
  for (let i = 0; i < 5000; i += 1) {
    const dayDu = kyDayDu(muc, ma, ngayMax);
    ketQua.push({ key: ma, label: nhanKy(muc, ma) + (dayDu ? '' : ' *'), complete: dayDu });
    if (ma === cuoi) {
      break;
    }
    ma = kyKeTiep(muc, ma);
  }
  return ketQua.reverse();
}

/** Khoảng ngày dạng chữ: "01/08 – 16/08". */
export function dinhDangKhoang(tu, den) {
  const ngan = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
  return `${ngan(tu)} – ${ngan(den)}`;
}
