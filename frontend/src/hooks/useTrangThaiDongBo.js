import { useCallback, useEffect, useRef, useState } from 'react';
import { layTrangThaiDongBo } from '../api/sync.js';

/**
 * Hỏi `/api/sync/status` và giữ kết quả.
 * - Hỏi ngay khi mở, rồi hỏi lại mỗi `chuKyMs` (mặc định 30 giây) để ô chân menu luôn mới.
 * - `lamMoi()` hỏi lại ngay (dùng sau khi bấm "Đồng bộ ngay").
 * - Lỗi: giữ kết quả cũ, trả `loi` để nơi dùng quyết định hiện hay không.
 *
 * @returns {{trangThai: object|null, loi: object|null, lamMoi: () => Promise<object|null>}}
 */
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
