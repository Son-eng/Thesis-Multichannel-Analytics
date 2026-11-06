import { Navigate, Route, Routes, useLocation, useParams, Outlet } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import viVN from 'antd/locale/vi_VN';
import { layAntdTheme } from './theme/antdTheme.js';
import { cssToanCuc } from './theme/globalStyles.js';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import AppLayout from './components/AppLayout.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import ComparePlatforms from './pages/ComparePlatforms.jsx';
import SyncStatus from './pages/SyncStatus.jsx';
import Upload from './pages/Upload.jsx';
import Users from './pages/Users.jsx';

/** Chưa đăng nhập thì về /login (nhớ trang đang định vào để quay lại sau khi đăng nhập). */
export function CanDangNhap() {
  const { nguoiDung, dangTai } = useAuth();
  const viTri = useLocation();
  if (dangTai) {
    return null;
  }
  if (!nguoiDung) {
    return <Navigate to="/login" replace state={{ tu: viTri.pathname }} />;
  }
  return <AppLayout />;
}

/** Route quản trị: người dùng thường bị chuyển về dashboard (SPEC §11). */
export function CanQuyenAdmin() {
  const { laAdmin } = useAuth();
  if (!laAdmin) {
    return <Navigate to="/dashboard/shopee" replace />;
  }
  return <Outlet />;
}

/** /dashboard/:platform chỉ nhận shopee | tiktok; giá trị khác chuyển về /dashboard/shopee. */
export function TuyenDashboard() {
  const { platform } = useParams();
  if (platform !== 'shopee' && platform !== 'tiktok') {
    return <Navigate to="/dashboard/shopee" replace />;
  }
  // key theo sàn: đổi sàn thì dựng lại trang, chạy lại toàn bộ trình tự chuyển động.
  return <Dashboard key={platform} />;
}

/** Danh sách route của ứng dụng. Tách khỏi App để test bọc MemoryRouter riêng. */
export function TuyenUngDung() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<CanDangNhap />}>
        <Route index element={<Navigate to="/dashboard/shopee" replace />} />
        <Route path="dashboard/:platform" element={<TuyenDashboard />} />
        <Route path="compare" element={<ComparePlatforms />} />
        <Route element={<CanQuyenAdmin />}>
          <Route path="admin/sync" element={<SyncStatus />} />
          <Route path="admin/upload" element={<Upload />} />
          <Route path="admin/users" element={<Users />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/dashboard/shopee" replace />} />
    </Routes>
  );
}

/** Gốc ứng dụng: theme Ant Design từ tokens, CSS toàn cục, phiên đăng nhập, router. */
export default function App() {
  return (
    <ConfigProvider locale={viVN} theme={layAntdTheme()}>
      <style>{cssToanCuc}</style>
      <AuthProvider>
        <TuyenUngDung />
      </AuthProvider>
    </ConfigProvider>
  );
}
