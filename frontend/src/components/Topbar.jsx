import { useLocation, useNavigate } from 'react-router-dom';
import { mau, chuDao, coChu, boGoc, bong, khoangCach } from '../theme/tokens.js';
import { useAuth, NHAN_VAI_TRO } from '../context/AuthContext.jsx';
import Icon from './Icon.jsx';

// Thanh trên: đường dẫn trang bên trái; tên người dùng, vai trò, nút Đăng xuất bên phải.

const TEN_TRANG = {
  '/dashboard/shopee': ['Dashboard', 'Shopee'],
  '/dashboard/tiktok': ['Dashboard', 'TikTok Shop'],
  '/compare': ['Dashboard', 'Đối chiếu hai sàn'],
  '/admin/sync': ['Quản trị', 'Đồng bộ dữ liệu'],
  '/admin/upload': ['Quản trị', 'Upload tệp dữ liệu'],
  '/admin/users': ['Quản trị', 'Người dùng'],
};

/** Hai chữ cái đầu của tên đăng nhập, in hoa, để làm ảnh đại diện. */
function chuVietTat(ten) {
  const phan = ten.split('.');
  if (phan.length >= 2) {
    return (phan[0][0] + phan[1][0]).toUpperCase();
  }
  return ten.slice(0, 2).toUpperCase();
}

export default function Topbar() {
  const { nguoiDung, dangXuat } = useAuth();
  const viTri = useLocation();
  const dieuHuong = useNavigate();
  const [nhom, trang] = TEN_TRANG[viTri.pathname] || ['Dashboard', ''];

  const thoat = async () => {
    await dangXuat();
    dieuHuong('/login', { replace: true });
  };

  return (
    <header className="thanh-topbar-noi" aria-label="Thanh điều hướng trên">
      <div style={{ fontSize: coChu.nho, color: mau.chuMo }}>
        {nhom}
        <span aria-hidden="true" style={{ margin: '0 6px' }}>/</span>
        <b style={{ color: mau.chuChinh, fontWeight: 500 }}>{trang}</b>
      </div>
      {nguoiDung ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 32, height: 32, borderRadius: '50%', background: chuDao.nenAvatar, color: chuDao.dam, fontSize: coChu.ratNho, fontWeight: 700, display: 'grid', placeItems: 'center' }}>
            {chuVietTat(nguoiDung.username)}
          </span>
          <div style={{ lineHeight: 1.3 }}>
            <div style={{ fontSize: coChu.nho, fontWeight: 600 }}>{nguoiDung.username}</div>
            <div style={{ fontSize: coChu.nhan, color: mau.chuMo }}>{NHAN_VAI_TRO[nguoiDung.role]}</div>
          </div>
          <button type="button" className="nut" onClick={thoat} style={{ marginLeft: 6 }}>
            <Icon ten="logout" kichThuoc={14} />
            Đăng xuất
          </button>
        </div>
      ) : null}
    </header>
  );
}
