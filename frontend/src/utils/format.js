// Tự viết thay vì toLocaleString để kết quả không phụ thuộc bộ icu của máy chạy.

/** null không bao giờ hiện thành 0. */
export const KHONG_CO_DU_LIEU = 'Không có dữ liệu';

export const KHONG_DU_DU_LIEU = 'Không đủ dữ liệu để so sánh';

function nhomNghin(n) {
  const nguyen = Math.round(Math.abs(n));
  const chu = String(nguyen);
  const nhom = chu.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return n < 0 && nguyen !== 0 ? '−' + nhom : nhom;
}

/** Số 0 thật vẫn hiện 0. */
export function dinhDangSo(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return nhomNghin(n);
}

export function dinhDangTien(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return nhomNghin(n) + ' đ';
}

/** Từ 1 tỷ trở lên ghi 2 chữ số thập phân; dưới 1 tỷ ghi theo triệu. */
export function rutGonTien(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  if (n >= 1e9) {
    return (n / 1e9).toFixed(2).replace('.', ',') + ' tỷ';
  }
  return Math.round(n / 1e6) + ' tr';
}

export function dinhDangPhanTram(x, soChuSo = 1) {
  if (x === null || x === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return x.toFixed(soChuSo).replace('.', ',') + '%';
}

export function dinhDangThapPhan(x, soChuSo = 1) {
  if (x === null || x === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return x.toFixed(soChuSo).replace('.', ',');
}

/** Cắt chuỗi, không qua Date, để không lệch múi giờ. */
export function dinhDangNgay(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const [nam, thang, ngay] = iso.slice(0, 10).split('-');
  return `${ngay}/${thang}/${nam}`;
}

export function dinhDangNgayNgan(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const [, thang, ngay] = iso.slice(0, 10).split('-');
  return `${ngay}/${thang}`;
}

/** Backend đã gắn +07:00 nên đọc phần giờ như đã ghi, không đổi múi giờ. */
export function dinhDangThoiDiem(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const ngay = iso.slice(0, 10);
  const gio = iso.slice(11, 16);
  return `${gio}, ${dinhDangNgayNgan(ngay)}`;
}
