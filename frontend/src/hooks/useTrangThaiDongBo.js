import { useCallback, useEffect, useRef, useState } from 'react';
import { layTrangThaiDongBo } from '../api/sync.js';

/** Hỏi /api/sync/status ngay khi mở rồi mỗi 30 giây; lỗi thì giữ kết quả cũ. */
export function useTrangThaiDongBo(chuKyMs = 30000) {
  const [trangThai, setTrangThai] = useState(null);
  const [loi, setLoi] = useState(null);
  const conSong = useRef(true);

  const lamMoi = useCallback(async () => {
    try {
      const kq = await layTrangThaiDongBo();
      if (conSong.current) {
        setTrangThai(kq);
        setLoi(null);
      }
      return kq;
    } catch (e) {
      if (conSong.current) {
        setLoi(e);
      }
      return null;
    }
  }, []);

  useEffect(() => {
    conSong.current = true;
    lamMoi();
    const dong = chuKyMs > 0 ? setInterval(lamMoi, chuKyMs) : null;
    return () => {
      conSong.current = false;
      if (dong !== null) {
        clearInterval(dong);
      }
    };
  }, [lamMoi, chuKyMs]);

  return { trangThai, loi, lamMoi };
}
