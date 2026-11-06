import { createContext, useContext, useEffect, useState } from 'react';
import { chuyenDongDangTat, duongCong, thoiLuong, troGiup, doTroiLen } from '../theme/motion.js';

// Trình tự mở trang (thiết kế): thẻ hiện dần và trồi lên, thẻ sau trễ hơn; sau đó biểu đồ mọc.
// Một ngữ cảnh chung cho cả trang để mọi phần tử cùng biết "trang đã sẵn sàng chạy chuyển động chưa".

const NguCanhChuyenDong = createContext({ sanSang: true, tat: true });

/**
 * Bọc một trang để cung cấp trạng thái chuyển động cho mọi thẻ và biểu đồ bên trong.
 * `sanSang` đổi false -> true sau hai khung hình (đủ để trình duyệt vẽ trạng thái đầu rồi mới chạy chuyển tiếp CSS).
 * Đổi `key` của phần tử này (ví dụ theo sàn) thì chạy lại toàn bộ trình tự.
 */
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

/** Đọc trạng thái chuyển động của trang gần nhất. Không bọc thì coi như tắt (hiện ngay). */
export function useChuyenDong() {
  return useContext(NguCanhChuyenDong);
}

/**
 * Style cho một khối hiện dần và trồi lên.
 * @param {number} thuTu vị trí của khối (khối sau trễ hơn khối trước ~80 ms)
 */
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

/**
 * Chuỗi `transition` cho một thuộc tính. Chưa sẵn sàng hoặc tắt chuyển động thì không chuyển tiếp.
 * Chỉ dùng cho transform, opacity, height/width, stroke-dasharray, stroke-dashoffset.
 */
export function kieuChuyen({ sanSang, tat }, thuocTinh, thoiGian, tre = 0) {
  if (tat || !sanSang) {
    return 'none';
  }
  return `${thuocTinh} ${thoiGian}ms ${duongCong} ${tre}ms`;
}

/** Trạng thái "đã mọc" của biểu đồ: tắt chuyển động -> luôn true; còn lại -> theo sanSang. */
export function daMoc({ sanSang, tat }) {
  return tat || sanSang;
}
