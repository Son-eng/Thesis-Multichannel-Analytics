import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as apiAuth from '../api/auth.js';
import { layToken, datToken, xoaToken, SU_KIEN_HET_PHIEN } from '../api/client.js';

// Token nằm trong localStorage (api/client.js); ngữ cảnh này giữ thông tin người dùng.

const NguCanhXacThuc = createContext(null);

export const NHAN_VAI_TRO = { admin: 'Quản trị viên', user: 'Người dùng' };

export function AuthProvider({ children }) {
  const [nguoiDung, setNguoiDung] = useState(null);
  // Có token thì phải hỏi /auth/me trước, trong lúc đó chưa chuyển trang.
  const [dangTai, setDangTai] = useState(() => layToken() !== null);

  useEffect(() => {
    let conHieuLuc = true;
    if (layToken() === null) {
      return undefined;
    }
    apiAuth
      .layNguoiDungHienTai()
      .then((u) => {
        if (conHieuLuc) {
          setNguoiDung(u);
        }
      })
      .catch(() => {
        xoaToken();
      })
      .finally(() => {
        if (conHieuLuc) {
          setDangTai(false);
        }
      });
    return () => {
      conHieuLuc = false;
    };
  }, []);

  // Token hết hạn giữa chừng thì client.js phát sự kiện, đưa người dùng về trang đăng nhập.
  useEffect(() => {
    const khiHetPhien = () => setNguoiDung(null);
    window.addEventListener(SU_KIEN_HET_PHIEN, khiHetPhien);
    return () => window.removeEventListener(SU_KIEN_HET_PHIEN, khiHetPhien);
  }, []);

  const dangNhap = useCallback(async (tenDangNhap, matKhau) => {
    const kq = await apiAuth.dangNhap(tenDangNhap, matKhau);
    datToken(kq.access_token);
    setNguoiDung(kq.user);
    return kq.user;
  }, []);

  const dangXuat = useCallback(async () => {
    try {
      await apiAuth.dangXuat();
    } finally {
      xoaToken();
      setNguoiDung(null);
    }
  }, []);

  const giaTri = useMemo(
    () => ({ nguoiDung, dangTai, laAdmin: nguoiDung !== null && nguoiDung.role === 'admin', dangNhap, dangXuat }),
    [nguoiDung, dangTai, dangNhap, dangXuat],
  );

  return <NguCanhXacThuc.Provider value={giaTri}>{children}</NguCanhXacThuc.Provider>;
}

export function useAuth() {
  const ngu = useContext(NguCanhXacThuc);
  if (ngu === null) {
    throw new Error('useAuth phải nằm trong AuthProvider');
  }
  return ngu;
}
