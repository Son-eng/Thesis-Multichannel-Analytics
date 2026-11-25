import { Outlet } from 'react-router-dom';
import { mau, khoangCach, font } from '../theme/tokens.js';
import { useTrangThaiDongBo } from '../hooks/useTrangThaiDongBo.js';
import Sidebar from './Sidebar.jsx';
import Topbar from './Topbar.jsx';

/** Khung ứng dụng sau khi đăng nhập: menu trái, thanh trên, vùng nội dung. */
export default function AppLayout() {
  const { trangThai, lamMoi } = useTrangThaiDongBo();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', fontFamily: font.chu, background: mau.nenTrang }}>
      <Sidebar trangThai={trangThai} lamMoi={lamMoi} />
      <div style={{ flex: '1 1 auto', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <Topbar />
        <main style={{ padding: `18px ${khoangCach.leNgang}px 48px`, boxSizing: 'border-box' }}>
          <div style={{ maxWidth: khoangCach.toiDaNoiDung, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: khoangCach.giuaKhoi }}>
            <Outlet context={{ trangThaiDongBo: trangThai, lamMoiDongBo: lamMoi }} />
          </div>
        </main>
      </div>
    </div>
  );
}
