// Thông số chuyển động: thời lượng, độ trễ, đường cong khai báo MỘT lần ở đây.
// Muốn tắt toàn bộ chuyển động: đặt TAT_CHUYEN_DONG = true.
// Muốn nhanh / chậm hơn: sửa thoiLuong và troGiup.

/** Cờ tắt toàn bộ chuyển động. Nội dung trang vẫn đầy đủ, chỉ hiện ngay ở trạng thái cuối. */
export const TAT_CHUYEN_DONG = false;

/** Đường cong dùng chung: nhanh lúc đầu, chậm dần về cuối. */
export const duongCong = 'cubic-bezier(.16,1,.3,1)';

/** Thời lượng (ms). */
export const thoiLuong = {
  demSo: 1200, // số chạy từ 0 (hoặc giá trị cũ) đến giá trị mới
  theHien: 600, // thẻ hiện dần
  theTroiLen: 800, // thẻ trồi lên
  cotChong: 700, // một lớp của cột chồng mọc từ đáy
  dai: 700, // dải nối giữa các cột
  cotNgay: 650,
  nhanDinh: 400,
  thanhTyTrong: 800,
  banNguyet: 1100,
  banNguyet2: 900,
  duongGio: 1400,
  vungDuoiDuong: 800,
  hienDong: 450,
};

/** Độ trễ (ms). */
export const troGiup = {
  batDau: 120, // trễ trước thẻ đầu tiên
  giuaThe: 80, // thẻ sau trễ hơn thẻ trước
  giuaCot: 90, // giữa các tháng của cột chồng
  giuaLop: 70, // giữa các lớp trong một cột
  giuaNgay: 22,
  giuaGio: 18,
  giuaDong: 70, // giữa các dòng bảng
};

/** Độ trồi lên của thẻ khi hiện (px). */
export const doTroiLen = 16;

/**
 * Hệ điều hành có bật "giảm chuyển động" không.
 * Vì sao cần: người dùng bật cờ này thì mọi thứ phải hiện ngay, không chạy.
 */
function heDieuHanhGiamChuyenDong() {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Chuyển động có đang tắt không (cờ tắt hoặc hệ điều hành yêu cầu giảm). */
export function chuyenDongDangTat() {
  return TAT_CHUYEN_DONG || heDieuHanhGiamChuyenDong();
}
