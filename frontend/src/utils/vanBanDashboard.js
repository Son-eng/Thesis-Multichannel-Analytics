import { KHONG_CO_DU_LIEU, KHONG_DU_DU_LIEU, dinhDangSo, dinhDangNgayNgan, dinhDangPhanTram } from './format.js';
import { nhanKy, dinhDangKhoang, demNgay } from './period.js';

// Frontend không tự tính khoảng ngày kỳ trước, mọi ngày lấy nguyên từ API.

export const TOOLTIP_DOANH_THU =
  'Tổng NMV sau thuế của các đơn không bị hủy và không bị hoàn. Đây là doanh thu bán hàng, chưa phải lợi nhuận.';

/** Kỳ chưa đủ ngày thì ghi "tính đến dd/MM". */
export function tieuDeDoanhThu(kyDayDu, ngayCuoi) {
  if (kyDayDu) {
    return 'Doanh thu';
  }
  return `Doanh thu tính đến ${dinhDangNgayNgan(ngayCuoi)}`;
}

function khoangHoacNgay(tu, den) {
  if (tu === den) {
    return dinhDangNgayNgan(tu);
  }
  return dinhDangKhoang(tu, den);
}

export function chuKyDemRaSoSanh(truoc) {
  if (!truoc) {
    return KHONG_DU_DU_LIEU;
  }
  return `so với ${khoangHoacNgay(truoc.date_from, truoc.date_to)}`;
}

export function chuThuong(chu) {
  return chu.charAt(0).toLowerCase() + chu.slice(1);
}

export function dongKyChuaDuNgay(muc, kpi) {
  const soNgay = demNgay(kpi.current.date_from, kpi.current.date_to);
  const phanKyTruoc = kpi.previous
    ? `kỳ trước lấy ${khoangHoacNgay(kpi.previous.date_from, kpi.previous.date_to)} để hai kỳ cùng ${soNgay} ngày`
    : 'chưa có kỳ trước để so sánh';
  return `${nhanKy(muc, kpi.period)} chưa kết thúc: số liệu tính đến ${dinhDangNgayNgan(kpi.current.date_to)}, ${phanKyTruoc}.`;
}

/** Dùng previous_full từ API, không tự tính %. */
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

/** Luôn hiện số dòng unknown; Shopee hiện thêm số dòng NMV tạm tính. */
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
