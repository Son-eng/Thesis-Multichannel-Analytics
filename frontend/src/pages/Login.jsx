import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { mau, coChu } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { docLoi } from '../api/client.js';

/**
 * Đăng nhập. Lượt 2A: biểu mẫu tối thiểu để vào được ứng dụng; lượt 2D dựng đầy đủ theo bản mẫu v2.
 * Tài khoản mock là tài khoản GIẢ (admin.vh, quanly.kd; mật khẩu giả demo123), không ghi lên giao diện.
 */
export default function Login() {
  const { nguoiDung, dangNhap } = useAuth();
  const [tenDangNhap, setTenDangNhap] = useState('');
  const [matKhau, setMatKhau] = useState('');
  const [loi, setLoi] = useState('');
  const [dangGui, setDangGui] = useState(false);
  const dieuHuong = useNavigate();
  const viTri = useLocation();

  if (nguoiDung) {
    return <Navigate to="/dashboard/shopee" replace />;
  }

  const gui = async (sk) => {
    sk.preventDefault();
    setLoi('');
    setDangGui(true);
    try {
      await dangNhap(tenDangNhap, matKhau);
      const diaChi = viTri.state && viTri.state.tu ? viTri.state.tu : '/dashboard/shopee';
      dieuHuong(diaChi, { replace: true });
    } catch (e) {
      setLoi(docLoi(e).message);
    } finally {
      setDangGui(false);
    }
  };

  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <form onSubmit={gui} style={{ width: '100%', maxWidth: 380 }}>
        <h1 style={{ fontSize: coChu.tieuDe, margin: '0 0 6px' }}>Đăng nhập</h1>
        <p style={{ margin: '0 0 22px', color: mau.chuNhan }}>Dùng tài khoản do quản trị viên cấp.</p>
        {loi ? (
          <div role="alert" style={{ marginBottom: 12 }}>
            {loi}
          </div>
        ) : null}
        <label htmlFor="ten-dang-nhap">Tên đăng nhập</label>
        <input id="ten-dang-nhap" value={tenDangNhap} onChange={(e) => setTenDangNhap(e.target.value)} style={{ display: 'block', width: '100%', marginBottom: 12 }} />
        <label htmlFor="mat-khau">Mật khẩu</label>
        <input id="mat-khau" type="password" value={matKhau} onChange={(e) => setMatKhau(e.target.value)} style={{ display: 'block', width: '100%', marginBottom: 16 }} />
        <button type="submit" className="nut nut-chinh" disabled={dangGui} style={{ width: '100%' }}>
          Đăng nhập
        </button>
      </form>
    </main>
  );
}
