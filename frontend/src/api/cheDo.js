// Nhóm endpoint luôn đi vào mock dù VITE_USE_MOCK=false; hiện rỗng vì mọi nhóm đã có backend thật.

export const NHOM_LUON_GIA_LAP = [];

export function nhomCuaDuongDan(duongDan) {
  const khop = /^\/api\/([^/?#]+)/.exec(duongDan);
  return khop ? khop[1] : null;
}

export function luonGiaLap(duongDan) {
  const nhom = nhomCuaDuongDan(duongDan);
  return nhom !== null && NHOM_LUON_GIA_LAP.includes(nhom);
}
