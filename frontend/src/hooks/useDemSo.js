import { useEffect, useRef, useState } from 'react';
import { chuyenDongDangTat, thoiLuong } from '../theme/motion.js';

/**
 * Hàm làm mượt: chạy nhanh lúc đầu rồi chậm dần về cuối (giống thiết kế: 1 - 2^(-10p)).
 * @param {number} p tiến độ 0..1
 */
export function lamMuot(p) {
  if (p >= 1) {
    return 1;
  }
  return 1 - Math.pow(2, -10 * p);
}

/**
 * Hook đếm số: trả về giá trị đang hiển thị, chạy từ giá trị hiện tại đến `dich`.
 *
 * - Lần đầu: chạy từ `batDauTu` (mặc định 0) đến `dich` (thiết kế: số chạy từ 0 trong ~1,2 giây).
 * - Khi `dich` đổi (đổi kỳ): chạy từ giá trị đang hiện sang giá trị mới, KHÔNG chạy lại từ 0.
 * - `dich` là null (không có dữ liệu): trả null ngay, không đếm. Quy tắc 1: null không bao giờ thành 0.
 * - Chuyển động tắt (cờ, hoặc hệ điều hành bật giảm chuyển động): trả ngay giá trị cuối.
 *
 * @param {number|null} dich giá trị cần đạt
 * @param {{batDauTu?: number, tat?: boolean}} [tuyChon] `tat` ép tắt chuyển động (dùng trong test)
 * @returns {number|null}
 */
export function useDemSo(dich, tuyChon = {}) {
  const { batDauTu = 0, tat = false } = tuyChon;
  const tatChuyenDong = tat || chuyenDongDangTat();
  const [giaTri, setGiaTri] = useState(() => (tatChuyenDong ? dich : batDauTu));
  const hienTai = useRef(tatChuyenDong ? dich : batDauTu);
  const khung = useRef(null);

  useEffect(() => {
    if (khung.current !== null) {
      cancelAnimationFrame(khung.current);
      khung.current = null;
    }
    if (dich === null || dich === undefined || tatChuyenDong) {
      hienTai.current = dich;
      setGiaTri(dich);
      return undefined;
    }
    const tu = hienTai.current === null || hienTai.current === undefined ? batDauTu : hienTai.current;
    let batDau = null;
    const buoc = (thoiGian) => {
      if (batDau === null) {
        batDau = thoiGian;
      }
      const p = Math.min(1, (thoiGian - batDau) / thoiLuong.demSo);
      const v = tu + (dich - tu) * lamMuot(p);
      hienTai.current = v;
      setGiaTri(v);
      if (p < 1) {
        khung.current = requestAnimationFrame(buoc);
      } else {
        khung.current = null;
      }
    };
    khung.current = requestAnimationFrame(buoc);
    return () => {
      if (khung.current !== null) {
        cancelAnimationFrame(khung.current);
        khung.current = null;
      }
    };
    // batDauTu và tatChuyenDong cố tình không nằm trong danh sách: chỉ chạy lại khi `dich` đổi.
  }, [dich]);

  return giaTri;
}
