// Thư viện tính toán lịch: chia kỳ theo ngày/tháng/quý/năm, xác định ngày bắt đầu/kết thúc của từng kỳ.

export const MUC_THOI_GIAN = ['day', 'month', 'quarter', 'year'];

export const NHAN_MUC = {
  day: 'Theo ngày',
  month: 'Theo tháng',
  quarter: 'Theo quý',
  year: 'Theo năm',
};

function hai(n) {
  return String(n).padStart(2, '0');
}

function docNgay(iso) {
  const [nam, thang, ngay] = iso.split('-').map(Number);
  return new Date(Date.UTC(nam, thang - 1, ngay));
}

function ghiNgay(d) {
  return `${d.getUTCFullYear()}-${hai(d.getUTCMonth() + 1)}-${hai(d.getUTCDate())}`;
}

export function congNgay(iso, soNgay) {
  const d = docNgay(iso);
  d.setUTCDate(d.getUTCDate() + soNgay);
  return ghiNgay(d);
}

/** Tính cả hai đầu: 01 đến 16 là 16 ngày. */
export function demNgay(tu, den) {
  const ms = docNgay(den).getTime() - docNgay(tu).getTime();
  return Math.round(ms / 86400000) + 1;
}

function ngayCuoiThang(nam, thang) {
  return ghiNgay(new Date(Date.UTC(nam, thang, 0)));
}

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

export function kyTruocCua(muc, ma) {
  if (muc === 'day') {
    return congNgay(ma, -1);
  }
  return maKyChuaNgay(muc, congNgay(ngayDauKy(muc, ma), -1));
}

export function kyKeTiep(muc, ma) {
  return maKyChuaNgay(muc, congNgay(ngayCuoiKy(muc, ma), 1));
}

/** So với MAX(order_date) của dữ liệu, không dùng ngày hôm nay. */
export function kyDayDu(muc, ma, ngayDuLieuMoiNhat) {
  return ngayCuoiKy(muc, ma) <= ngayDuLieuMoiNhat;
}

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

/** Chỉ giữ kỳ có giao với khoảng dữ liệu; kỳ chưa đủ ngày có dấu *. */
export function danhSachKy(muc, ngayMin, ngayMax) {
  const ketQua = [];
  let ma = maKyChuaNgay(muc, ngayMin);
  const cuoi = maKyChuaNgay(muc, ngayMax);
  // chặn thêm 5000 bước để không bao giờ treo trình duyệt
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

export function dinhDangKhoang(tu, den) {
  const ngan = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
  return `${ngan(tu)} – ${ngan(den)}`;
}
