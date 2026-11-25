import { taoNhanThayDoi } from '../../utils/delta.js';
import { dinhDangTien, dinhDangSo, dinhDangPhanTram, KHONG_CO_DU_LIEU } from '../../utils/format.js';

/** Không có hàng "Doanh thu" vì hai sàn khác số ngày, đặt cạnh nhau dễ bị đọc như so sánh. */
export const HANG_CHI_SO = [
  { khoa: 'order_count', nhan: 'Số đơn hợp lệ', phu: 'Không hủy, không hoàn', kieu: 'so', dang: 'phanTram', tangLaTot: true, loai: 'don', thanh: false },
  { khoa: 'aov', nhan: 'Giá trị đơn trung bình', phu: 'Doanh thu / số đơn hợp lệ', kieu: 'tien', dang: 'phanTram', tangLaTot: true, loai: 'don', thanh: false },
  { khoa: 'cancel_rate', nhan: 'Tỷ lệ hủy', phu: 'Trên tổng số đơn', kieu: 'tyLe', dang: 'diemPhanTram', tangLaTot: false, loai: 'don', thanh: true },
  { khoa: 'return_rate', nhan: 'Tỷ lệ hoàn', phu: 'Trên tổng số đơn', kieu: 'tyLe', dang: 'diemPhanTram', tangLaTot: false, loai: 'don', thanh: true },
  // Tỷ trọng affiliate tăng không tốt cũng không xấu nên để trung tính.
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

/** Mỗi sàn so với kỳ trước của chính nó; sàn no_data thì ghi "Không có dữ liệu", không có thanh. */
export function dungO(khoiSan, hang, toiDa) {
  const chiSo = khoiSan.metrics[hang.khoa];
  if (khoiSan.status === 'no_data' || chiSo.value === null) {
    return { giaTri: KHONG_CO_DU_LIEU, coSo: false, nhan: null, thanh: 0 };
  }
  const nhan = taoNhanThayDoi(chiSo, { status: khoiSan.status, dang: hang.dang, tangLaTot: hang.tangLaTot, loai: hang.loai });
  const thanh = hang.thanh && toiDa > 0 ? Math.round((chiSo.value / toiDa) * 100) : 0;
  return { giaTri: dinhDangGiaTri(hang.kieu, chiSo.value), coSo: true, nhan, thanh };
}

/** Nhân 1,1 để thanh dài nhất không chạm mép. */
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

/** Mã có trong danh sách của sàn nào thì sàn đó bán; không có thì ghi "Không bán", không ghi 0. */
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
