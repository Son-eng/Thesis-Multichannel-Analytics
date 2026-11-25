// Hiệu ứng số nhảy tăng dần

import { useEffect, useRef, useState } from 'react';
import { chuyenDongDangTat, thoiLuong } from '../theme/motion.js';

/** Chạy nhanh lúc đầu rồi chậm dần: 1 - 2^(-10p). */
export function lamMuot(p) {
  if (p >= 1) {
    return 1;
  }
  return 1 - Math.pow(2, -10 * p);
}

/** Đổi kỳ thì chạy từ giá trị đang hiện sang giá trị mới; dich là null thì trả null, không bao giờ thành 0. */
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
    // Chỉ chạy lại khi dich đổi.
  }, [dich]);

  return giaTri;
}
