// Định nghĩa các hàng của bảng "hai cánh" và hàm dựng nội dung một ô (một sàn, một chỉ số).
// Tách khỏi component để test được và để thêm/bớt chỉ số chỉ sửa một chỗ.

import { taoNhanThayDoi } from '../../utils/delta.js';
import { dinhDangTien, dinhDangSo, dinhDangPhanTram, KHONG_CO_DU_LIEU } from '../../utils/format.js';

/**
 * Các chỉ số cả hai sàn đều tính được (SPEC §12). Tỷ lệ mới có thanh ngang, vì tỷ lệ so được giữa
 * hai sàn dù số ngày khác nhau; số tiền và số đơn thì không (hai sàn khác số ngày).
 * Cố ý KHÔNG có hàng "Doanh thu": doanh thu đã nằm ở hai thẻ phía trên, đặt hai số tiền cạnh nhau
 * trong bảng sẽ dễ bị đọc như so hai sàn trong khi số ngày khác nhau (duyệt F01, F02 việc A1).
 */
export const HANG_CHI_SO = [
  { khoa: 'order_count', nhan: 'Số đơn hợp lệ', phu: 'Không hủy, không hoàn', kieu: 'so', dang: 'phanTram', tangLaTot: true, loai: 'don', thanh: false },
  { khoa: 'aov', nhan: 'Giá trị đơn trung bình', phu: 'Doanh thu / số đơn hợp lệ', kieu: 'tien', dang: 'phanTram', tangLaTot: true, loai: 'don', thanh: false },
  { khoa: 'cancel_rate', nhan: 'Tỷ lệ hủy', phu: 'Trên tổng số đơn', kieu: 'tyLe', dang: 'diemPhanTram', tangLaTot: false, loai: 'don', thanh: true },
  { khoa: 'return_rate', nhan: 'Tỷ lệ hoàn', phu: 'Trên tổng số đơn', kieu: 'tyLe', dang: 'diemPhanTram', tangLaTot: false, loai: 'don', thanh: true },
  // Tỷ trọng affiliate không có nghĩa "tốt" hay "xấu" khi tăng nên để trung tính.
  { khoa: 'affiliate_share', nhan: 'Tiếp thị liên kết', phu: 'Tỷ trọng doanh thu', kieu: 'tyLe', dang: 'diemPhanTram', tangLaTot: null, loai: 'doanh_thu', thanh: true },
];

function dinhDangGiaTri(kieu, v) {
  if (kieu === 'tien') {
    return dinhDangTien(v);
  }
  if (kieu === 'tyLe') {
    return dinhDangPhanTram(v);
  }
  return dinhDangSo(v);
}

/**
 * Nội dung một ô: số, mức thay đổi so với kỳ trước CỦA CHÍNH SÀN ĐÓ, và độ dài thanh (nếu là tỷ lệ).
 * Sàn `no_data` -> "Không có dữ liệu", không có thay đổi, không có thanh (quy tắc 1).
 *
 * @param {object} khoiSan nhánh `shopee` hoặc `tiktok` của /api/compare/platforms
 * @param {object} hang một phần tử của HANG_CHI_SO
 * @param {number} toiDa giá trị lớn nhất của hàng (hai sàn) để quy ra độ dài thanh 0..100
 */
export function dungO(khoiSan, hang, toiDa) {
  const chiSo = khoiSan.metrics[hang.khoa];
  if (khoiSan.status === 'no_data' || chiSo.value === null) {
    return { giaTri: KHONG_CO_DU_LIEU, coSo: false, nhan: null, thanh: 0 };
  }
  const nhan = taoNhanThayDoi(chiSo, { status: khoiSan.status, dang: hang.dang, tangLaTot: hang.tangLaTot, loai: hang.loai });
  const thanh = hang.thanh && toiDa > 0 ? Math.round((chiSo.value / toiDa) * 100) : 0;
  return { giaTri: dinhDangGiaTri(hang.kieu, chiSo.value), coSo: true, nhan, thanh };
}

/** Giá trị lớn nhất của một hàng tỷ lệ (nhân 1,1 cho thanh không chạm mép), 0 nếu không có số nào. */
export function toiDaCuaHang(canhShopee, canhTiktok, hang) {
  const cacGiaTri = [canhShopee, canhTiktok]
    .filter((k) => k.status !== 'no_data')
    .map((k) => k.metrics[hang.khoa].value)
    .filter((v) => v !== null);
  if (cacGiaTri.length === 0) {
    return 0;
  }
  return Math.max(...cacGiaTri, 1) * 1.1;
}

/**
 * Ghép hai danh sách `by_product` thành một bảng theo mã (frontend tự ghép, SPEC §12.1.2).
 * Mã có trong danh sách của sàn nào thì sàn đó "bán"; không có thì ô ghi "Không bán", không ghi 0.
 *
 * @returns {{ma: string, shopee: number|null, tiktok: number|null, loai: 'both'|'shopee'|'tiktok'|'chuaSoDuoc'}[]}
 *   shopee/tiktok = doanh thu, hoặc null nếu sàn không bán mã đó.
 */
export function ghepSanPham(canhShopee, canhTiktok) {
  const theoMa = {};
  canhShopee.by_product.forEach((m) => {
    theoMa[m.product_code] = { ma: m.product_code, shopee: m.revenue, tiktok: null };
  });
  canhTiktok.by_product.forEach((m) => {
    const cu = theoMa[m.product_code] || { ma: m.product_code, shopee: null, tiktok: null };
    cu.tiktok = m.revenue;
    theoMa[m.product_code] = cu;
  });
  const ds = Object.values(theoMa).map((m) => {
    let loai = 'both';
    if (canhShopee.status === 'no_data') {
      loai = 'chuaSoDuoc';
    } else if (m.shopee === null) {
      loai = 'tiktok';
    } else if (m.tiktok === null) {
      loai = 'shopee';
    }
    return { ...m, loai };
  });
  ds.sort((a, b) => Math.max(b.shopee || 0, b.tiktok || 0) - Math.max(a.shopee || 0, a.tiktok || 0) || (a.ma < b.ma ? -1 : 1));
  return ds;
}
