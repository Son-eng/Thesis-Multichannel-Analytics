// Định dạng số, tiền, phần trăm, ngày theo kiểu Việt Nam.
// Vì sao tự viết thay vì toLocaleString: kết quả không phụ thuộc bộ ICU của máy chạy,
// nên test và ảnh chụp báo cáo ra cùng một chuỗi trên mọi máy.

/** Chữ hiện thay cho null. Quy tắc 1: null KHÔNG BAO GIỜ hiện thành 0. */
export const KHONG_CO_DU_LIEU = 'Không có dữ liệu';

/** Chữ hiện khi không tồn tại kỳ trước (khối có status = insufficient_data). Quy tắc 2. */
export const KHONG_DU_DU_LIEU = 'Không đủ dữ liệu để so sánh';

/**
 * Chèn dấu chấm ngăn cách hàng nghìn vào số nguyên.
 * @param {number} n số bất kỳ (được làm tròn về nguyên)
 * @returns {string} ví dụ 840035154 -> "840.035.154"
 */
export function nhomNghin(n) {
  const nguyen = Math.round(Math.abs(n));
  const chu = String(nguyen);
  const nhom = chu.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return n < 0 && nguyen !== 0 ? '−' + nhom : nhom;
}

/**
 * Số đếm (số đơn, số sản phẩm...). null -> "Không có dữ liệu", số 0 thật vẫn hiện 0.
 */
export function dinhDangSo(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return nhomNghin(n);
}

/**
 * Tiền đồng đầy đủ: "840.035.154 đ". null -> "Không có dữ liệu".
 */
export function dinhDangTien(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return nhomNghin(n) + ' đ';
}

/**
 * Tiền rút gọn cho trục biểu đồ và nhãn cột: "1,07 tỷ", "624 tr".
 * Từ 1 tỷ trở lên ghi 2 chữ số thập phân; dưới 1 tỷ ghi theo triệu, làm tròn.
 */
export function rutGonTien(n) {
  if (n === null || n === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  if (n >= 1e9) {
    return (n / 1e9).toFixed(2).replace('.', ',') + ' tỷ';
  }
  return Math.round(n / 1e6) + ' tr';
}

/**
 * Phần trăm với dấu phẩy thập phân: 34.6 -> "34,6%". null -> "Không có dữ liệu".
 */
export function dinhDangPhanTram(x, soChuSo = 1) {
  if (x === null || x === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return x.toFixed(soChuSo).replace('.', ',') + '%';
}

/** Số thực với dấu phẩy thập phân, không kèm đơn vị. */
export function dinhDangThapPhan(x, soChuSo = 1) {
  if (x === null || x === undefined) {
    return KHONG_CO_DU_LIEU;
  }
  return x.toFixed(soChuSo).replace('.', ',');
}

/** "2026-08-16" -> "16/08/2026". Cắt chuỗi, không qua Date, để không lệch múi giờ. */
export function dinhDangNgay(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const [nam, thang, ngay] = iso.slice(0, 10).split('-');
  return `${ngay}/${thang}/${nam}`;
}

/** "2026-08-16" -> "16/08". */
export function dinhDangNgayNgan(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const [, thang, ngay] = iso.slice(0, 10).split('-');
  return `${ngay}/${thang}`;
}

/**
 * Thời điểm ISO có múi giờ -> "16:40, 23/08".
 * Backend đã gắn +07:00 nên chỉ cần đọc phần giờ như đã ghi, không đổi múi giờ.
 */
export function dinhDangThoiDiem(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  const ngay = iso.slice(0, 10);
  const gio = iso.slice(11, 16);
  return `${gio}, ${dinhDangNgayNgan(ngay)}`;
}

/** Như dinhDangThoiDiem nhưng có năm: "16:40, 23/08/2026". */
export function dinhDangThoiDiemDayDu(iso) {
  if (!iso) {
    return KHONG_CO_DU_LIEU;
  }
  return `${iso.slice(11, 16)}, ${dinhDangNgay(iso.slice(0, 10))}`;
}
