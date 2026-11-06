// Chế độ giả lập lai: khi VITE_USE_MOCK=false (chạy với backend thật), một số nhóm endpoint VẪN được giả lập
// vì backend chưa có và theo hợp đồng sẽ không có trước buổi demo.
//
// Nguồn: SPEC §12.1 mục 5, các nhóm này ghi là "Mock khi demo".
// Khi backend làm xong nhóm nào: XÓA nhóm đó khỏi danh sách dưới đây. Không phải sửa trang nào.

/** Nhóm endpoint luôn đi vào mock. Nhóm = đoạn đứng ngay sau "/api/" của đường dẫn. */
export const NHOM_LUON_GIA_LAP = ['auth', 'users', 'insights', 'export'];

/** Nhóm của một đường dẫn: "/api/auth/login" -> "auth"; "/api/users/3?x=1" -> "users". */
export function nhomCuaDuongDan(duongDan) {
  const khop = /^\/api\/([^/?#]+)/.exec(duongDan);
  return khop ? khop[1] : null;
}

/** Đường dẫn này có phải luôn giả lập, bất kể VITE_USE_MOCK? */
export function luonGiaLap(duongDan) {
  const nhom = nhomCuaDuongDan(duongDan);
  return nhom !== null && NHOM_LUON_GIA_LAP.includes(nhom);
}
