import { KHONG_CO_DU_LIEU, KHONG_DU_DU_LIEU, dinhDangSo, dinhDangNgayNgan, dinhDangPhanTram } from './format.js';
import { nhanKy, dinhDangKhoang, demNgay } from './period.js';

// Câu chữ của dashboard gắn với quy tắc nghiệp vụ (quy tắc 7, 8, 10). Tách khỏi component để test được.
// Frontend KHÔNG tự tính khoảng ngày kỳ trước: mọi ngày lấy nguyên từ API (previous.date_from/date_to).

/** Quy tắc 8: tooltip của thẻ doanh thu. */
export const TOOLTIP_DOANH_THU =
  'Tổng NMV sau thuế của các đơn không bị hủy và không bị hoàn. Đây là doanh thu bán hàng, chưa phải lợi nhuận.';

/**
 * Quy tắc 7: tiêu đề khối doanh thu. Kỳ chưa đủ ngày ghi "tính đến DD/MM".
 * @param {boolean} kyDayDu kpi.period_complete
 * @param {string} ngayCuoi kpi.current.date_to
 */
export function tieuDeDoanhThu(kyDayDu, ngayCuoi) {
  if (kyDayDu) {
    return 'Doanh thu';
  }
  return `Doanh thu tính đến ${dinhDangNgayNgan(ngayCuoi)}`;
}

/** Một ngày hoặc một khoảng: "22/08" hoặc "01/07 – 16/07". */
function khoangHoacNgay(tu, den) {
  if (tu === den) {
    return dinhDangNgayNgan(tu);
  }
  return dinhDangKhoang(tu, den);
}

/**
 * Quy tắc 7: câu "so với 01/07 – 16/07" lấy từ previous.date_from/date_to.
 * @param {{date_from: string, date_to: string}|null} truoc kpi.previous
 */
export function chuKyDemRaSoSanh(truoc) {
  if (!truoc) {
    return KHONG_DU_DU_LIEU;
  }
  return `so với ${khoangHoacNgay(truoc.date_from, truoc.date_to)}`;
}

/** Chữ thường hóa chữ cái đầu: "Tháng 8/2026" -> "tháng 8/2026" (đặt giữa câu). */
export function chuThuong(chu) {
  return chu.charAt(0).toLowerCase() + chu.slice(1);
}

/**
 * Dòng thông tin khi kỳ chưa đủ ngày (quy tắc 7).
 * Ví dụ: "Tháng 8/2026 chưa kết thúc: số liệu tính đến 16/08, kỳ trước lấy 01/07 – 16/07 để hai kỳ cùng 16 ngày."
 */
export function dongKyChuaDuNgay(muc, kpi) {
  const soNgay = demNgay(kpi.current.date_from, kpi.current.date_to);
  const phanKyTruoc = kpi.previous
    ? `kỳ trước lấy ${khoangHoacNgay(kpi.previous.date_from, kpi.previous.date_to)} để hai kỳ cùng ${soNgay} ngày`
    : 'chưa có kỳ trước để so sánh';
  return `${nhanKy(muc, kpi.period)} chưa kết thúc: số liệu tính đến ${dinhDangNgayNgan(kpi.current.date_to)}, ${phanKyTruoc}.`;
}

/**
 * Câu giải thích vì sao không so với cả kỳ trước (dùng previous_full, không tự tính %).
 * @param {{period: string, revenue: number, pct_change_if_used: number}} truocNguyen kpi.previous_full
 */
export function cauKhongSoCaKy(muc, kpi) {
  const truocNguyen = kpi.previous_full;
  const soNgay = demNgay(kpi.current.date_from, kpi.current.date_to);
  const pct = truocNguyen.pct_change_if_used;
  const dau = pct > 0 ? '+' : pct < 0 ? '−' : '';
  const chu = `${dau}${dinhDangPhanTram(Math.abs(pct))}`;
  const phanThat = kpi.metrics.revenue.pct_change;
  let nhanXet = 'chênh lệch nhiều so với mức so sánh đúng';
  if (phanThat !== null && (pct < 0) !== (phanThat < 0)) {
    nhanXet = 'sai cả chiều tăng giảm';
  }
  return `Không so với cả ${chuThuong(nhanKy(muc, truocNguyen.period))}: ${chuThuong(nhanKy(muc, kpi.period))} mới có ${soNgay} ngày, nếu so cả kỳ sẽ ra ${chu}, ${nhanXet}.`;
}

/**
 * Quy tắc 10: hai dòng chất lượng dữ liệu. Luôn hiện số dòng `unknown`; Shopee hiện thêm số dòng NMV tạm tính.
 * @param {{rows_status_unknown: number|null, rows_nmv_provisional: number|null}} chatLuong kpi.data_quality
 * @returns {string[]}
 */
export function dongChatLuongDuLieu(chatLuong) {
  if (!chatLuong || chatLuong.rows_status_unknown === null) {
    return [KHONG_CO_DU_LIEU];
  }
  const dong = [`${dinhDangSo(chatLuong.rows_status_unknown)} dòng chưa rõ trạng thái đơn, vẫn tính vào doanh thu`];
  if (chatLuong.rows_nmv_provisional === null) {
    dong.push('NMV tạm tính: không áp dụng với sàn này');
  } else {
    dong.push(`${dinhDangSo(chatLuong.rows_nmv_provisional)} dòng có NMV tạm tính, chờ đối soát`);
  }
  return dong;
}
