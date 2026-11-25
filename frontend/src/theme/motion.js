// Thông số chuyển động khai báo một lần ở đây; đặt TAT_CHUYEN_DONG = true để tắt toàn bộ.

/** Nội dung vẫn đầy đủ, chỉ hiện ngay ở trạng thái cuối. */
export const TAT_CHUYEN_DONG = false;

export const duongCong = 'cubic-bezier(.16,1,.3,1)';

export const thoiLuong = {
  demSo: 1200,
  theHien: 600,
  theTroiLen: 800,
  cotChong: 700,
  dai: 700,
  cotNgay: 650,
  nhanDinh: 400,
  thanhTyTrong: 800,
  banNguyet: 1100,
  banNguyet2: 900,
  duongGio: 1400,
  vungDuoiDuong: 800,
  hienDong: 450,
};

export const troGiup = {
  batDau: 120,
  giuaThe: 80,
  giuaCot: 90,
  giuaLop: 70,
  giuaNgay: 22,
  giuaGio: 18,
  giuaDong: 70,
};

export const doTroiLen = 16;

/** Người dùng bật "giảm chuyển động" thì mọi thứ phải hiện ngay. */
function heDieuHanhGiamChuyenDong() {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function chuyenDongDangTat() {
  return TAT_CHUYEN_DONG || heDieuHanhGiamChuyenDong();
}
