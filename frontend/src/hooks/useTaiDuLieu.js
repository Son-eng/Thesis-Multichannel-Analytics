// Hook dùng cho khối giao diện, quản lý 3 trạng thái bất đồng bộ (dangTai, duLieu, loi và hàm thuLai())

import { useCallback, useEffect, useRef, useState } from 'react';

/** Mỗi khối gọi hook riêng để một khối lỗi không làm hỏng khối khác; dữ liệu cũ giữ tới khi dữ liệu mới về. */
export function useTaiDuLieu(hamTai, phuThuoc) {
  const [trangThai, setTrangThai] = useState({ duLieu: null, loi: null, dangTai: true });
  const [lanThu, setLanThu] = useState(0);
  const hamTaiMoiNhat = useRef(hamTai);
  hamTaiMoiNhat.current = hamTai;

  useEffect(() => {
    let daHuy = false;
    const lenhGoi = hamTaiMoiNhat.current();
    if (lenhGoi === null) {
      setTrangThai({ duLieu: null, loi: null, dangTai: true });
      return undefined;
    }
    setTrangThai((cu) => ({ ...cu, loi: null, dangTai: true }));
    lenhGoi
      .then((duLieu) => {
        if (!daHuy) {
          setTrangThai({ duLieu, loi: null, dangTai: false });
        }
      })
      .catch((e) => {
        if (!daHuy) {
          setTrangThai({ duLieu: null, loi: e, dangTai: false });
        }
      });
    return () => {
      daHuy = true;
    };
    // phuThuoc do nơi gọi truyền vào nên không thể kiểm tĩnh được.
  }, [...phuThuoc, lanThu]);

  const thuLai = useCallback(() => setLanThu((n) => n + 1), []);
  return { ...trangThai, thuLai };
}
