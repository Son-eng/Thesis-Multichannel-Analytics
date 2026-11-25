import { createContext, useContext, useEffect, useState } from 'react';
import { chuyenDongDangTat, duongCong, thoiLuong, troGiup, doTroiLen } from '../theme/motion.js';

// Trình tự mở trang: thẻ hiện dần, thẻ sau trễ hơn, rồi biểu đồ mọc.

const NguCanhChuyenDong = createContext({ sanSang: true, tat: true });

/** sanSang đổi sang true sau hai khung hình để trình duyệt vẽ trạng thái đầu rồi mới chạy chuyển tiếp. */
export function TrangChuyenDong({ children }) {
  const tat = chuyenDongDangTat();
  const [sanSang, setSanSang] = useState(tat);

  useEffect(() => {
    if (tat) {
      return undefined;
    }
    let k2 = 0;
    const k1 = requestAnimationFrame(() => {
      k2 = requestAnimationFrame(() => setSanSang(true));
    });
    return () => {
      cancelAnimationFrame(k1);
      cancelAnimationFrame(k2);
    };
  }, [tat]);

  return <NguCanhChuyenDong.Provider value={{ sanSang, tat }}>{children}</NguCanhChuyenDong.Provider>;
}

/** Không bọc thì coi như tắt chuyển động. */
export function useChuyenDong() {
  return useContext(NguCanhChuyenDong);
}

export function kieuVao({ sanSang, tat }, thuTu = 0) {
  if (tat) {
    return {};
  }
  const tre = troGiup.batDau + thuTu * troGiup.giuaThe;
  return {
    opacity: sanSang ? 1 : 0,
    transform: sanSang ? 'none' : `translateY(${doTroiLen}px)`,
    transition: sanSang
      ? `opacity ${thoiLuong.theHien}ms ease-out ${tre}ms, transform ${thoiLuong.theTroiLen}ms ${duongCong} ${tre}ms`
      : 'none',
  };
}

export function kieuChuyen({ sanSang, tat }, thuocTinh, thoiGian, tre = 0) {
  if (tat || !sanSang) {
    return 'none';
  }
  return `${thuocTinh} ${thoiGian}ms ${duongCong} ${tre}ms`;
}

export function daMoc({ sanSang, tat }) {
  return tat || sanSang;
}
