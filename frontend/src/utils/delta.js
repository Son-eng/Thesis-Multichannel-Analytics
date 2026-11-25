import { KHONG_CO_DU_LIEU, KHONG_DU_DU_LIEU, dinhDangThapPhan } from './format.js';

// Một chỗ duy nhất quyết định chữ, màu, hướng của nhãn thay đổi so với kỳ trước.

/** Dưới 0,05 thì làm tròn một chữ số cũng ra 0,0. */
const NGUONG_PHANG = 0.05;

export function chuKyTruocBangKhong(loai = 'doanh_thu') {
  if (loai === 'don') {
    return 'Kỳ trước không có đơn';
  }
  return 'Kỳ trước không có doanh thu';
}

/** Màu theo nghĩa tốt hay xấu, không theo dấu: tăng hủy, hoàn là xấu. */
function chonTong(x, tangLaTot) {
  if (Math.abs(x) < NGUONG_PHANG || tangLaTot === null) {
    return 'trungTinh';
  }
  const laTang = x > 0;
  const laTot = tangLaTot ? laTang : !laTang;
  return laTot ? 'tot' : 'xau';
}

/** laThongBao là true khi chỉ có câu chữ, không có số, để giao diện không vẽ mũi tên. */
export function taoNhanThayDoi(chiSo, tuyChon = {}) {
  const { status = 'ok', dang = 'phanTram', tangLaTot = true, loai = 'doanh_thu' } = tuyChon;
  const thongBao = (text) => ({ text, tone: 'trungTinh', huong: 'khong', laThongBao: true });

  // Kỳ này không có dữ liệu thì ghi "Không có dữ liệu", không bao giờ hiện 0.
  if (status === 'no_data' || !chiSo || chiSo.value === null || chiSo.value === undefined) {
    return thongBao(KHONG_CO_DU_LIEU);
  }
  // Không tồn tại kỳ trước thì không hiện −100%.
  if (status === 'insufficient_data') {
    return thongBao(KHONG_DU_DU_LIEU);
  }
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
  // Tỷ lệ ghi "điểm %" không dấu; số tiền, số đơn ghi "%" kèm dấu.
  if (dang === 'diemPhanTram') {
    return { text: `${mui} ${tuyetDoi} điểm %`, tone, huong, laThongBao: false };
  }
  const dau = x > 0 ? '+' : '−';
  return { text: `${mui} ${dau}${tuyetDoi}%`, tone, huong, laThongBao: false };
}
