import { KHONG_CO_DU_LIEU, KHONG_DU_DU_LIEU, dinhDangThapPhan } from './format.js';

// Quy tắc hiển thị mức thay đổi so với kỳ trước (SPEC §12.1.0.2, §9.3).
// MỘT chỗ duy nhất quyết định chữ, màu, hướng của nhãn, để mọi thẻ và bảng hiện nhất quán.

/** Ngưỡng coi là "không đổi" (dưới 0,05 thì làm tròn 1 chữ số cũng ra 0,0). */
const NGUONG_PHANG = 0.05;

/**
 * Chữ khi kỳ trước bằng 0 (SPEC §12.1.0.2, quy tắc 3).
 * @param {'doanh_thu'|'don'} loai chỉ số đếm đơn thì ghi "không có đơn"
 */
export function chuKyTruocBangKhong(loai = 'doanh_thu') {
  if (loai === 'don') {
    return 'Kỳ trước không có đơn';
  }
  return 'Kỳ trước không có doanh thu';
}

/**
 * Xác định tông màu theo nghĩa tốt / xấu (quy tắc 5), không theo dấu.
 * @param {number} x mức thay đổi
 * @param {boolean|null} tangLaTot true: tăng là tốt (doanh thu); false: tăng là xấu (hủy, hoàn); null: trung tính
 */
function chonTong(x, tangLaTot) {
  if (Math.abs(x) < NGUONG_PHANG || tangLaTot === null) {
    return 'trungTinh';
  }
  const laTang = x > 0;
  const laTot = tangLaTot ? laTang : !laTang;
  return laTot ? 'tot' : 'xau';
}

/**
 * Tạo nhãn thay đổi cho một chỉ số.
 *
 * @param {object} chiSo   object chỉ số trong hợp đồng: {value, previous, pct_change, previous_zero} hoặc {value, previous, change_pp}
 * @param {object} tuyChon
 * @param {string} [tuyChon.status]       status của khối: ok | no_data | insufficient_data
 * @param {'phanTram'|'diemPhanTram'} [tuyChon.dang] phanTram dùng pct_change; diemPhanTram dùng change_pp (quy tắc 4)
 * @param {boolean|null} [tuyChon.tangLaTot] xem chonTong
 * @param {'doanh_thu'|'don'} [tuyChon.loai] ảnh hưởng chữ "kỳ trước bằng 0"
 * @returns {{text: string, tone: 'tot'|'xau'|'trungTinh', huong: 'tang'|'giam'|'khong', laThongBao: boolean}}
 *   laThongBao = true khi chỉ là câu chữ (không có số), để giao diện không vẽ mũi tên.
 */
export function taoNhanThayDoi(chiSo, tuyChon = {}) {
  const { status = 'ok', dang = 'phanTram', tangLaTot = true, loai = 'doanh_thu' } = tuyChon;
  const thongBao = (text) => ({ text, tone: 'trungTinh', huong: 'khong', laThongBao: true });

  // Quy tắc 1: kỳ này không có dữ liệu -> "Không có dữ liệu", tuyệt đối không hiện 0.
  if (status === 'no_data' || !chiSo || chiSo.value === null || chiSo.value === undefined) {
    return thongBao(KHONG_CO_DU_LIEU);
  }
  // Quy tắc 2: không tồn tại kỳ trước -> không hiện −100%.
  if (status === 'insufficient_data') {
    return thongBao(KHONG_DU_DU_LIEU);
  }
  // Quy tắc 3: kỳ trước bằng 0 (chỉ có ở chỉ số có pct_change).
  if (dang === 'phanTram' && chiSo.previous_zero === true) {
    return thongBao(chuKyTruocBangKhong(loai));
  }

  const x = dang === 'phanTram' ? chiSo.pct_change : chiSo.change_pp;
  if (x === null || x === undefined) {
    return thongBao(KHONG_DU_DU_LIEU);
  }

  const tone = chonTong(x, tangLaTot);
  if (Math.abs(x) < NGUONG_PHANG) {
    const khongDoi = dang === 'phanTram' ? '0,0%' : '0,0 điểm %';
    return { text: khongDoi, tone: 'trungTinh', huong: 'khong', laThongBao: false };
  }

  const huong = x > 0 ? 'tang' : 'giam';
  const mui = x > 0 ? '▲' : '▼';
  const tuyetDoi = dinhDangThapPhan(Math.abs(x), 1);
  // Quy tắc 4: tỷ lệ ghi "điểm %" (không dấu, mũi tên đã chỉ hướng); số tiền, số đơn ghi "%" kèm dấu.
  if (dang === 'diemPhanTram') {
    return { text: `${mui} ${tuyetDoi} điểm %`, tone, huong, laThongBao: false };
  }
  const dau = x > 0 ? '+' : '−';
  return { text: `${mui} ${dau}${tuyetDoi}%`, tone, huong, laThongBao: false };
}

/**
 * Chữ phụ "so với ..." dưới số lớn của thẻ chỉ số.
 * Quy tắc 7: khoảng ngày kỳ trước lấy từ API (previous.date_from/date_to), frontend không tự tính.
 */
export function layChuKyTruoc(previous, dinhDangKhoang) {
  if (!previous) {
    return KHONG_DU_DU_LIEU;
  }
  return 'so với ' + dinhDangKhoang(previous.date_from, previous.date_to);
}
