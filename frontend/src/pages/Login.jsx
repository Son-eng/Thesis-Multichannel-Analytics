import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { mau, tranhDangNhap, canhBao, coChu } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { docLoi } from '../api/client.js';

/**
 * Trang Đăng nhập phong cách Neumorphism / Glassmorphism nổi (Glasses).
 * - 2 ô nhập liệu dạng viên thuốc nổi 3D (glassmorphic shadow/border) kèm biểu tượng người dùng và ổ khóa.
 * - Hàng tùy chọn: Ô tick Remember Me bo góc và liên kết "Forgot Password?".
 * - Bấm "Forgot Password?" hiển thị popup giữa màn hình với icon mặt buồn to và dòng:
 *   "Liên hệ với quản lý để lấy lại mật khẩu nhé".
 * - Nút Login dạng pill viền tròn kèm huy hiệu mũi tên sang phải.
 */
export default function Login() {
  const { nguoiDung, dangNhap } = useAuth();
  const [tenDangNhap, setTenDangNhap] = useState('');
  const [matKhau, setMatKhau] = useState('');
  const [hienMatKhau, setHienMatKhau] = useState(false);
  const [ghiNho, setGhiNho] = useState(false);
  const [moPopupQuenMk, setMoPopupQuenMk] = useState(false);
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
    <main className="dang-nhap-wrapper">
      {/* Các mảng màu nền trừu tượng phía sau thẻ chính */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: -120,
          right: -80,
          width: 520,
          height: 520,
          borderRadius: '45% 55% 60% 40% / 50% 60% 40% 50%',
          background: tranhDangNhap.nenBlobA,
          opacity: 0.7,
          filter: 'blur(30px)',
          pointerEvents: 'none',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          bottom: -140,
          left: -100,
          width: 580,
          height: 580,
          borderRadius: '55% 45% 40% 60% / 60% 50% 50% 40%',
          background: tranhDangNhap.nenBlobB,
          opacity: 0.75,
          filter: 'blur(40px)',
          pointerEvents: 'none',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '30%',
          left: '5%',
          width: 240,
          height: 240,
          borderRadius: '50%',
          background: tranhDangNhap.nenBlobA,
          opacity: 0.5,
          filter: 'blur(25px)',
          pointerEvents: 'none',
        }}
      />

      {/* Thẻ đăng nhập chính viền xanh bo góc */}
      <div className="dang-nhap-the">
        {/* CỘT TRÁI: FORM ĐĂNG NHẬP */}
        <div
          style={{
            padding: '44px 40px 36px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
            zIndex: 3,
            background: tranhDangNhap.nenThe,
          }}
        >
          {/* Nhãn thương hiệu góc trên */}
          <div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: '0.14em',
                color: tranhDangNhap.chuTieuDe,
                textTransform: 'uppercase',
                marginBottom: 36,
              }}
            >
            
            </div>

            {/* Tiêu đề & mô tả */}
            <h1
              aria-label="Đăng nhập"
              style={{
                fontSize: 34,
                lineHeight: 1.15,
                fontWeight: 700,
                color: tranhDangNhap.chuTieuDe,
                margin: '0 0 8px',
                letterSpacing: '-0.02em',
              }}
            >
              Login
            </h1>
            <p
              style={{
                margin: '0 0 28px',
                color: tranhDangNhap.chuMo,
                fontSize: 13,
                lineHeight: 1.5,
                maxWidth: 290,
              }}
            >
              Welcome back!!
            </p>

            {/* Thông báo lỗi nếu đăng nhập sai */}
            {loi ? (
              <div
                role="alert"
                style={{
                  marginBottom: 18,
                  padding: '10px 14px',
                  borderRadius: 12,
                  background: canhBao.nen,
                  border: `1px solid ${canhBao.vien}`,
                  color: canhBao.chu,
                  fontSize: coChu.nho,
                }}
              >
                {loi}
              </div>
            ) : null}

            {/* Biểu mẫu đăng nhập */}
            <form onSubmit={gui}>
              {/* Ô 1: Username or Email dạng nổi Glassmorphism */}
              <div style={{ marginBottom: 16 }}>
                <label htmlFor="ten-dang-nhap" className="sr-only">
                  Tên đăng nhập
                </label>
                <div className="o-nhap-glass-khung">
                  <span className="o-nhap-glass-icon" aria-hidden="true">
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </span>
                  <input
                    id="ten-dang-nhap"
                    className="o-nhap-glass-ruot"
                    autoComplete="username"
                    placeholder="Username or Email"
                    value={tenDangNhap}
                    onChange={(e) => setTenDangNhap(e.target.value)}
                  />
                </div>
              </div>

              {/* Ô 2: Password dạng nổi Glassmorphism kèm icon khóa & ẩn/hiện mắt */}
              <div style={{ marginBottom: 14 }}>
                <label htmlFor="mat-khau" className="sr-only">
                  Mật khẩu
                </label>
                <div className="o-nhap-glass-khung">
                  <span className="o-nhap-glass-icon" aria-hidden="true">
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    id="mat-khau"
                    className="o-nhap-glass-ruot"
                    type={hienMatKhau ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Password"
                    value={matKhau}
                    onChange={(e) => setMatKhau(e.target.value)}
                    style={{ paddingRight: 44 }}
                  />
                  {/* Nút bật/tắt mắt xem mật khẩu */}
                  <button
                    type="button"
                    onClick={() => setHienMatKhau(!hienMatKhau)}
                    title={hienMatKhau ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    aria-label={hienMatKhau ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                    style={{
                      position: 'absolute',
                      right: 14,
                      background: 'transparent',
                      border: 'none',
                      padding: 4,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: tranhDangNhap.iconO,
                    }}
                  >
                    {hienMatKhau ? (
                      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    ) : (
                      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Hàng tùy chọn: Remember Me (bo góc) & Forgot Password? */}
              <div className="hang-tuy-chon">
                <label className="checkbox-bo-goc" onClick={() => setGhiNho(!ghiNho)}>
                  <span
                    className={`checkbox-bo-goc-hop ${ghiNho ? 'da-chon' : ''}`}
                    role="checkbox"
                    aria-checked={ghiNho}
                  >
                    {ghiNho ? (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={mau.nenThe} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : null}
                  </span>
                  <span>Remember Me</span>
                </label>

                <button
                  type="button"
                  className="link-quen-mk"
                  onClick={() => setMoPopupQuenMk(true)}
                >
                  Forgot Password?
                </button>
              </div>

              {/* Nút bấm Login dạng pill viền tròn kèm mũi tên */}
              <div>
                <button
                  type="submit"
                  aria-label="Đăng nhập"
                  className="nut-login-pill"
                  disabled={dangGui}
                >
                  <span>{dangGui ? '...' : 'Login'}</span>
                  <span className="nut-login-pill-mui-ten" aria-hidden="true">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={mau.nenThe} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </span>
                </button>
              </div>
            </form>
          </div>

          {/* Dòng chú thích nhỏ ở đáy form */}
          <div style={{ marginTop: 24, fontSize: coChu.ratNho, color: tranhDangNhap.chuMo }}>
            
          </div>
        </div>

        {/* CỘT PHẢI: TRANH MINH HỌA DASHBOARD VÀ NHÂN VẬT VECTOR */}
        <div
          className="dang-nhap-tranh-moi"
          style={{
            position: 'relative',
            overflow: 'hidden',
            background: tranhDangNhap.nenThe,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 24px 24px 0',
          }}
        >
          <svg
            viewBox="0 0 760 540"
            style={{ width: '100%', height: '100%', maxHeight: 520 }}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            {/* LỚP 1: CÁC MẢNG MÂY / ĐỒI HỮU CƠ XANH PASTEL PHÍA SAU */}
            <path
              d="M320 320 C240 310 210 240 230 180 C250 120 330 90 410 110 C480 70 570 80 630 130 C690 180 710 260 670 330 C640 380 570 420 480 410 C390 420 340 370 320 320 Z"
              fill={tranhDangNhap.mayA}
              opacity="0.85"
            />
            <path
              d="M360 300 C300 290 280 230 300 180 C320 130 380 110 440 130 C500 100 580 110 620 160 C660 210 660 280 620 320 C580 360 520 380 460 370 C410 380 380 340 360 300 Z"
              fill={tranhDangNhap.mayB}
              opacity="0.75"
            />
            <path
              d="M400 280 C360 270 340 220 360 180 C380 140 430 130 470 150 C520 120 590 140 610 190 C630 240 620 290 580 320 C540 350 490 350 450 340 C420 340 410 310 400 280 Z"
              fill={tranhDangNhap.mayC}
              opacity="0.65"
            />
            {/* Vòm cây/gò đồi nhô lên phía sau màn hình */}
            <ellipse cx="370" cy="240" rx="45" ry="65" fill={tranhDangNhap.mayD} opacity="0.6" />
            <ellipse cx="430" cy="220" rx="35" ry="55" fill={tranhDangNhap.mayC} opacity="0.7" />

            {/* ĐƯỜNG KẺ SÀN / ĐƯỜNG CHÂN TRỜI */}
            <line x1="240" y1="410" x2="710" y2="410" stroke={tranhDangNhap.keSan} strokeWidth="2" strokeLinecap="round" />

            {/* LỚP 2: BÓNG VÀ HỐ CỘT 3D DƯỚI SÀN (GÓC PHẢI DƯỚI) */}
            <ellipse cx="535" cy="445" rx="38" ry="12" fill={tranhDangNhap.ho3D} />
            <ellipse cx="535" cy="445" rx="36" ry="10" fill="none" stroke={tranhDangNhap.ho3DVien} strokeWidth="1.5" />

            {/* 3 CỘT BIỂU ĐỒ 3D ISOMETRIC NHÔ LÊN TỪ HỐ */}
            {/* Cột 1 (Cao nhất, bên trái) */}
            <g transform="translate(515, 385)">
              <polygon points="0,15 15,22 15,55 0,48" fill={tranhDangNhap.cot3DA} />
              <polygon points="15,22 30,15 30,48 15,55" fill={tranhDangNhap.cot3DB} />
              <polygon points="0,15 15,8 30,15 15,22" fill={tranhDangNhap.cot3DSang} />
            </g>

            {/* Cột 2 (Vừa, ở giữa) */}
            <g transform="translate(532, 400)">
              <polygon points="0,13 14,19 14,45 0,39" fill={tranhDangNhap.cot3DB} />
              <polygon points="14,19 28,13 28,39 14,45" fill={tranhDangNhap.cot3DC} />
              <polygon points="0,13 14,7 28,13 14,19" fill={tranhDangNhap.cot3DA} />
            </g>

            {/* Cột 3 (Thấp nhất, phía trước) */}
            <g transform="translate(524, 420)">
              <polygon points="0,10 12,15 12,28 0,23" fill={tranhDangNhap.cot3DA} />
              <polygon points="12,15 24,10 24,23 12,28" fill={tranhDangNhap.cot3DC} />
              <polygon points="0,10 12,5 24,10 12,15" fill={tranhDangNhap.cot3DSang} />
            </g>

            {/* BÓNG ĐỔ DƯỚI BẢNG DASHBOARD CHÍNH */}
            <rect x="335" y="405" width="280" height="12" rx="6" fill={tranhDangNhap.bongMo} />

            {/* BẢNG DASHBOARD LỚN TRUNG TÂM */}
            <g transform="translate(340, 195)">
              <rect x="0" y="0" width="275" height="210" rx="14" fill={tranhDangNhap.bangNen} stroke={tranhDangNhap.bangVien} strokeWidth="2.5" />

              {/* Thanh điều khiển dọc bên trái bảng (Dock với 5 nút tròn) */}
              <rect x="0" y="0" width="26" height="210" rx="14" fill={tranhDangNhap.bangDock} />
              <rect x="14" y="0" width="12" height="210" fill={tranhDangNhap.bangDock} />
              <circle cx="13" cy="28" r="3.5" fill={tranhDangNhap.bangCham} />
              <circle cx="13" cy="50" r="3.5" fill={tranhDangNhap.bangCham} />
              <circle cx="13" cy="72" r="3.5" fill={tranhDangNhap.bangCham} />
              <circle cx="13" cy="94" r="3.5" fill={tranhDangNhap.bangCham} />
              <circle cx="13" cy="116" r="3.5" fill={tranhDangNhap.bangCham} />

              {/* Dòng tiêu đề và thanh ngang đầu bảng */}
              <rect x="42" y="20" width="60" height="5" rx="2.5" fill={tranhDangNhap.cotThanhA} />
              <rect x="42" y="30" width="40" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />
              <rect x="88" y="30" width="25" height="4" rx="2" fill={tranhDangNhap.cotThanhB} />

              {/* Khối biểu đồ ngang bên trái bảng */}
              <g transform="translate(42, 54)">
                <circle cx="4" cy="5" r="2.5" fill={tranhDangNhap.bangCham} />
                <circle cx="14" cy="5" r="2.5" fill={tranhDangNhap.bangCham} />
                <circle cx="24" cy="5" r="2.5" fill={tranhDangNhap.bangCham} />
                <circle cx="34" cy="5" r="2.5" fill={tranhDangNhap.bangCham} />

                <rect x="0" y="16" width="55" height="8" rx="4" fill={tranhDangNhap.theMini} />
                <rect x="0" y="16" width="38" height="8" rx="4" fill={tranhDangNhap.cotThanhA} />

                <rect x="0" y="32" width="55" height="8" rx="4" fill={tranhDangNhap.theMini} />
                <rect x="0" y="32" width="24" height="8" rx="4" fill={tranhDangNhap.cotThanhB} />
              </g>

              {/* BIỂU ĐỒ TRÒN LỚN (PIE CHART) Ở GIỮA BẢNG */}
              <g transform="translate(162, 85)">
                <path d="M 0 0 L 0 -44 A 44 44 0 0 0 0 44 Z" fill={tranhDangNhap.pieVua} />
                <path d="M 0 0 L 0 -44 A 44 44 0 0 1 44 0 Z" fill={tranhDangNhap.pieNhat} />
                <path d="M 3 3 L 44 3 A 44 44 0 0 1 3 44 Z" fill={tranhDangNhap.pieDam} />
              </g>

              {/* Danh sách chỉ số bên phải biểu đồ tròn */}
              <g transform="translate(220, 60)">
                <rect x="0" y="0" width="6" height="6" rx="1.5" fill={tranhDangNhap.pieVua} />
                <rect x="10" y="1" width="30" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />

                <rect x="0" y="14" width="6" height="6" rx="1.5" fill={tranhDangNhap.pieNhat} />
                <rect x="10" y="15" width="24" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />

                <rect x="0" y="28" width="6" height="6" rx="1.5" fill={tranhDangNhap.pieDam} />
                <rect x="10" y="29" width="28" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />
              </g>

              {/* 3 THẺ TỔNG KẾT NHỎ DƯỚI ĐÁY BẢNG */}
              <g transform="translate(42, 160)">
                <rect x="0" y="0" width="62" height="26" rx="5" fill={tranhDangNhap.theMini} stroke={tranhDangNhap.theMiniVien} strokeWidth="1" />
                <circle cx="12" cy="13" r="5" fill={tranhDangNhap.cotThanhB} opacity="0.6" />
                <rect x="23" y="11" width="30" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />

                <rect x="74" y="0" width="62" height="26" rx="5" fill={tranhDangNhap.theMini} stroke={tranhDangNhap.theMiniVien} strokeWidth="1" />
                <circle cx="86" cy="13" r="5" fill={tranhDangNhap.pieDam} opacity="0.6" />
                <rect x="97" y="11" width="30" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />

                <rect x="148" y="0" width="62" height="26" rx="5" fill={tranhDangNhap.theMini} stroke={tranhDangNhap.theMiniVien} strokeWidth="1" />
                <circle cx="160" cy="13" r="5" fill={tranhDangNhap.pieVua} opacity="0.6" />
                <rect x="171" y="11" width="30" height="4" rx="2" fill={tranhDangNhap.cotThanhNhat} />
              </g>
            </g>

            {/* NHÂN VẬT NỮ (BÊN TRÁI BẢNG) ĐANG CẦM BẢNG BIỂU ĐỒ CỘT */}
            <g transform="translate(295, 305)">
              <ellipse cx="20" cy="118" rx="16" ry="4" fill={tranhDangNhap.bongMo} />

              <path d="M 12 60 L 6 112 L 14 114 L 20 62 Z" fill={tranhDangNhap.aoQuanDam} />
              <path d="M 22 60 L 26 110 L 34 112 L 28 62 Z" fill={tranhDangNhap.aoQuan} />
              <ellipse cx="9" cy="115" rx="6" ry="3" fill={tranhDangNhap.giay} />
              <ellipse cx="31" cy="113" rx="6" ry="3" fill={tranhDangNhap.giay} />

              <path d="M 10 24 L 2 62 L 34 62 L 28 24 Z" fill={tranhDangNhap.aoQuan} />

              <rect x="16" y="17" width="6" height="8" fill={tranhDangNhap.da} />
              <ellipse cx="19" cy="14" rx="8" ry="9" fill={tranhDangNhap.da} />
              <path d="M 10 14 C 10 5 28 5 28 14 C 28 20 26 23 25 24 L 13 24 C 12 23 10 20 10 14 Z" fill={tranhDangNhap.toc} />

              <path d="M 8 28 L -15 48 L -12 55 L 8 36 Z" fill={tranhDangNhap.aoQuanDam} />
              <path d="M 28 28 L -2 52 L 2 58 L 28 36 Z" fill={tranhDangNhap.aoQuan} />

              {/* BẢNG BIỂU ĐỒ CỘT CẦM TAY */}
              <g transform="translate(-48, 44)">
                <rect x="0" y="0" width="46" height="52" rx="4" fill={tranhDangNhap.bangNen} stroke={tranhDangNhap.bangVien} strokeWidth="1.5" />
                <circle cx="7" cy="8" r="1.5" fill={tranhDangNhap.bangCham} />
                <circle cx="12" cy="8" r="1.5" fill={tranhDangNhap.bangCham} />
                <circle cx="17" cy="8" r="1.5" fill={tranhDangNhap.bangCham} />

                <rect x="6" y="28" width="4" height="16" rx="1.5" fill={tranhDangNhap.cotThanhB} />
                <rect x="13" y="20" width="4" height="24" rx="1.5" fill={tranhDangNhap.cotThanhA} />
                <rect x="20" y="15" width="4" height="29" rx="1.5" fill={tranhDangNhap.pieDam} />
                <rect x="27" y="24" width="4" height="20" rx="1.5" fill={tranhDangNhap.cotThanhB} />
                <rect x="34" y="18" width="4" height="26" rx="1.5" fill={tranhDangNhap.cotThanhA} />
              </g>
            </g>

            {/* NHÂN VẬT NAM (BÊN PHẢI BẢNG) ĐANG ĐỠ THẺ KẾ BÊN */}
            <g transform="translate(635, 310)">
              <ellipse cx="14" cy="120" rx="16" ry="4" fill={tranhDangNhap.bongMo} />

              <path d="M 8 62 L 2 116 L 10 118 L 14 64 Z" fill={tranhDangNhap.aoQuanDam} />
              <path d="M 16 62 L 24 112 L 32 114 L 22 64 Z" fill={tranhDangNhap.aoQuan} />
              <ellipse cx="5" cy="118" rx="6" ry="3" fill={tranhDangNhap.giay} />
              <ellipse cx="29" cy="115" rx="6" ry="3" fill={tranhDangNhap.giay} />

              <path d="M 6 24 L 2 64 L 24 64 L 22 24 Z" fill={tranhDangNhap.aoQuan} />

              <rect x="11" y="16" width="6" height="8" fill={tranhDangNhap.da} />
              <ellipse cx="14" cy="13" rx="7.5" ry="8.5" fill={tranhDangNhap.da} />
              <path d="M 6 12 C 6 4 21 4 21 12 C 21 16 20 18 19 19 L 9 19 C 7 18 6 15 6 12 Z" fill={tranhDangNhap.toc} />

              <path d="M 8 30 L -22 36 L -20 42 L 8 38 Z" fill={tranhDangNhap.aoQuanDam} />

              <g transform="translate(-46, 26)">
                <rect x="0" y="0" width="36" height="20" rx="3" fill={tranhDangNhap.theMini} stroke={tranhDangNhap.theMiniVien} strokeWidth="1.2" />
                <rect x="6" y="5" width="24" height="3" rx="1.5" fill={tranhDangNhap.cotThanhB} />
                <rect x="6" y="11" width="16" height="3" rx="1.5" fill={tranhDangNhap.cotThanhNhat} />
              </g>
            </g>

            {/* ĐỒNG XU BIỂU ĐỒ TRÒN 3D LƠ LỬNG TRÊN CAO (GÓC TRÁI TRÊN) */}
            <g transform="translate(200, 75) rotate(-18)">
              <ellipse cx="25" cy="62" rx="22" ry="7" fill={tranhDangNhap.bongMo} />
              <path d="M 2 24 C 2 34 48 34 48 24 L 48 36 C 48 46 2 46 2 36 Z" fill={tranhDangNhap.dongXuCanh} />
              <ellipse cx="25" cy="24" rx="23" ry="11" fill={tranhDangNhap.dongXuTop} />
              <path d="M 25 24 L 25 13 A 23 11 0 0 0 4 26 Z" fill={tranhDangNhap.dongXuDam} />
              <path d="M 25 24 L 46 26 A 23 11 0 0 1 25 35 Z" fill={tranhDangNhap.cot3DA} />
            </g>

            {/* QUẢ CẦU 3D LƠ LỬNG (GÓC PHẢI TRÊN) */}
            <g transform="translate(630, 150)">
              <circle cx="10" cy="10" r="10" fill={tranhDangNhap.cot3DA} />
              <circle cx="8" cy="7" r="8" fill={tranhDangNhap.cot3DSang} opacity="0.4" />
              <circle cx="6" cy="5" r="3" fill={tranhDangNhap.bangNen} opacity="0.6" />
            </g>
          </svg>
        </div>
      </div>

      {/* POPUP QUÊN MẬT KHẨU Ở GIỮA MÀN HÌNH VỚI ICON MẶT BUỒN TO */}
      {moPopupQuenMk ? (
        <div
          className="popup-quen-mk-overlay"
          onClick={() => setMoPopupQuenMk(false)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="popup-quen-mk-the"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Icon mặt buồn to ở giữa theo đúng yêu cầu */}
            <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'center' }}>
              <svg width="84" height="84" viewBox="0 0 84 84" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                {/* Khuôn mặt tròn vàng cam */}
                <circle cx="42" cy="42" r="38" fill={tranhDangNhap.matBuonVang} stroke={tranhDangNhap.matBuonVien} strokeWidth="3" />
                {/* Vệt sáng trên trán */}
                <circle cx="30" cy="24" r="6" fill={mau.nenThe} opacity="0.35" />
                {/* Hai mắt buồn cụp */}
                <ellipse cx="28" cy="36" rx="4" ry="5.5" fill={tranhDangNhap.matBuonMat} />
                <ellipse cx="56" cy="36" rx="4" ry="5.5" fill={tranhDangNhap.matBuonMat} />
                {/* Giọt nước mắt màu xanh biển */}
                <path d="M63 42 C63 46 60 48 57 48 C54 48 51 46 51 42 C51 38 57 32 57 32 C57 32 63 38 63 42 Z" fill={tranhDangNhap.matBuonNuocMat} />
                {/* Miệng mếu buồn cong xuống */}
                <path d="M 28 58 C 34 50 50 50 56 58" stroke={tranhDangNhap.matBuonMat} strokeWidth="3.5" strokeLinecap="round" fill="none" />
              </svg>
            </div>

            {/* Dòng chữ yêu cầu: "Liên hệ với quản lý để lấy lại mật khẩu nhé" */}
            <h3 style={{ margin: '0 0 10px', fontSize: 18, fontWeight: 700, color: tranhDangNhap.chuTieuDe }}>
              Quên mật khẩu?
            </h3>
            <p style={{ margin: '0 0 26px', fontSize: 14.5, lineHeight: 1.55, color: tranhDangNhap.chuNhan, fontWeight: 500 }}>
              Liên hệ với quản lý để lấy lại mật khẩu nhé
            </p>

            {/* Nút bấm đóng popup */}
            <button
              type="button"
              className="popup-nut-dong"
              onClick={() => setMoPopupQuenMk(false)}
            >
              Đã hiểu
            </button>
          </div>
        </div>
      ) : null}
    </main>
  );
}
