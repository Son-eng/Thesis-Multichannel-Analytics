import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { mau, chuDao, san, canhBao, dangNhap as mauDangNhap, coChu } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { docLoi } from '../api/client.js';

/**
 * Đăng nhập (nội dung theo bản mẫu v2, dựng bằng hệ giao diện mới).
 * Sai thông tin thì hiện `detail.message` của lỗi trả về.
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
    <main className="dang-nhap">
      <div
        className="dang-nhap-tranh"
        style={{ position: 'relative', overflow: 'hidden', background: mau.chuChinh, color: mau.nenThe, padding: 48, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="28" height="28" viewBox="0 0 26 26" aria-hidden="true">
            <rect x="2" y="6" width="9" height="16" rx="3" fill={chuDao.chinh} />
            <rect x="8.5" y="3" width="9" height="13" rx="3" fill={san.tiktok.chinh} opacity=".9" />
            <rect x="15" y="9" width="9" height="13" rx="3" fill={chuDao.thanhTinh} opacity=".85" />
          </svg>
          <b style={{ fontSize: 16 }}>Phân tích bán hàng đa kênh</b>
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: 34, lineHeight: 1.2, fontWeight: 700, maxWidth: 440, letterSpacing: '-0.02em' }}>
            Doanh thu Shopee và TikTok Shop, đặt cạnh nhau trên một màn hình.
          </h2>
          <p style={{ marginTop: 14, color: mau.chuTrenNen, maxWidth: 420 }}>
            Dữ liệu đơn hàng được đồng bộ tự động từ hai sàn, chuẩn hóa theo cùng một quy tắc tính doanh thu.
          </p>
        </div>
        <svg viewBox="0 0 520 180" aria-hidden="true" style={{ width: '100%', maxWidth: 520, height: 'auto' }}>
          <path d="M0 150 C60 140 90 110 140 112 S230 70 280 80 S380 40 430 46 S500 20 520 18" fill="none" stroke={mauDangNhap.duongA} strokeWidth="4" strokeLinecap="round" />
          <path d="M0 165 C70 160 100 140 160 130 S250 120 300 100 S390 96 440 76 S500 70 520 60" fill="none" stroke={mauDangNhap.duongB} strokeWidth="4" strokeLinecap="round" />
        </svg>
      </div>

      <div style={{ display: 'grid', placeItems: 'center', padding: 40 }}>
        <form onSubmit={gui} style={{ width: '100%', maxWidth: 380 }}>
          <h1 style={{ fontSize: 26, margin: '0 0 6px', fontWeight: 600 }}>Đăng nhập</h1>
          <p style={{ margin: '0 0 22px', color: mau.chuNhan }}>Dùng tài khoản do quản trị viên cấp.</p>
          {loi ? (
            <div role="alert" style={{ marginBottom: 14, padding: '10px 12px', borderRadius: 10, background: canhBao.nen, border: `1px solid ${canhBao.vien}`, color: canhBao.chu, fontSize: coChu.nho }}>
              {loi}
            </div>
          ) : null}
          <div style={{ marginBottom: 14 }}>
            <label className="nhan-o" htmlFor="ten-dang-nhap">Tên đăng nhập</label>
            <input id="ten-dang-nhap" className="o-nhap" autoComplete="username" value={tenDangNhap} onChange={(e) => setTenDangNhap(e.target.value)} />
          </div>
          <div style={{ marginBottom: 18 }}>
            <label className="nhan-o" htmlFor="mat-khau">Mật khẩu</label>
            <input id="mat-khau" className="o-nhap" type="password" autoComplete="current-password" value={matKhau} onChange={(e) => setMatKhau(e.target.value)} />
          </div>
          <button type="submit" className="nut nut-chinh" disabled={dangGui} style={{ width: '100%', height: 44 }}>
            Đăng nhập
          </button>
          <p style={{ marginTop: 16, textAlign: 'center', fontSize: coChu.ratNho, color: mau.chuNhan }}>Quên mật khẩu? Liên hệ quản trị viên để được đặt lại.</p>
        </form>
      </div>
    </main>
  );
}
