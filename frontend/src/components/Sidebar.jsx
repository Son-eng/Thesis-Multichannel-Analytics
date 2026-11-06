import { NavLink } from 'react-router-dom';
import { message } from 'antd';
import { mau, chuDao, san, canhBao, boGoc, coChu, khoangCach } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { chayDongBo } from '../api/sync.js';
import { docLoi } from '../api/client.js';
import { dinhDangThoiDiem } from '../utils/format.js';
import Icon from './Icon.jsx';

// Menu trắng bên trái (theo bản thiết kế): nhóm TỔNG QUAN, nhóm QUẢN TRỊ (chỉ admin thấy),
// chân menu là ô "Tự đồng bộ mỗi N phút · Gần nhất ..." và nút "Đồng bộ ngay" (chỉ admin).

function MucMenu({ den, children, chamMau }) {
  return (
    <NavLink
      to={den}
      className="nav"
      style={({ isActive }) => ({
        background: isActive ? chuDao.nhat : 'transparent',
        fontWeight: isActive ? 600 : 400,
      })}
    >
      {chamMau ? <span style={{ width: 9, height: 9, borderRadius: 3, background: chamMau, margin: '0 3px' }} /> : null}
      {children}
    </NavLink>
  );
}

/** Lần đồng bộ thành công gần nhất của mọi gian hàng (mới nhất). */
function lanGanNhat(trangThai) {
  const danhSach = trangThai.shops.map((s) => s.last_success_at).filter((t) => t !== null);
  if (danhSach.length === 0) {
    return null;
  }
  return danhSach.reduce((a, b) => (a > b ? a : b));
}

/**
 * @param {object|null} trangThai kết quả /api/sync/status (null khi đang tải)
 * @param {() => void} lamMoi hỏi lại trạng thái sau khi bấm "Đồng bộ ngay"
 */
export default function Sidebar({ trangThai, lamMoi }) {
  const { laAdmin } = useAuth();
  const [thongBao, boThongBao] = message.useMessage();

  const soSapHetQuyen = trangThai ? trangThai.shops.filter((s) => s.token_status === 'expiring').length : 0;
  const dangChayCaHai = trangThai ? trangThai.platforms.shopee.running && trangThai.platforms.tiktok.running : false;

  /** "Đồng bộ ngay" ở chân menu: chạy cả hai sàn; sàn nào đang chạy thì báo 409 riêng. */
  const dongBoNgay = async () => {
    const ketQua = await Promise.allSettled([chayDongBo('shopee'), chayDongBo('tiktok')]);
    const loi = ketQua.find((k) => k.status === 'rejected');
    if (loi) {
      thongBao.warning(docLoi(loi.reason).message);
    } else {
      thongBao.success('Đã bắt đầu đồng bộ');
    }
    lamMoi();
  };

  return (
    <nav
      aria-label="Điều hướng chính"
      style={{
        flex: `1 1 ${khoangCach.rongMenu}px`,
        maxWidth: khoangCach.rongMenu,
        boxSizing: 'border-box',
        background: mau.nenThe,
        borderRight: `1px solid ${mau.vienThe}`,
        padding: '18px 14px',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
      }}
    >
      {boThongBao}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '2px 6px 14px', borderBottom: `1px solid ${mau.vienTrong}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
            <rect x="2" y="6" width="9" height="16" rx="3" fill={chuDao.chinh} />
            <rect x="8.5" y="3" width="9" height="13" rx="3" fill={san.tiktok.chinh} opacity=".9" />
            <rect x="15" y="9" width="9" height="13" rx="3" fill={chuDao.thanhTinh} opacity=".85" />
          </svg>
          <span style={{ fontSize: 17, fontWeight: 700, color: chuDao.chinh, letterSpacing: '-0.01em' }}>Đa Kênh</span>
        </div>
        <span style={{ fontSize: coChu.nhan, color: mau.chuMo, border: `1px solid ${mau.vienChip}`, borderRadius: boGoc.nhan, padding: '1px 6px' }}>Bản demo</span>
      </div>

      <div className="nhom">TỔNG QUAN</div>
      <MucMenu den="/dashboard/shopee" chamMau={san.shopee.chinh}>Shopee</MucMenu>
      <MucMenu den="/dashboard/tiktok" chamMau={san.tiktok.chinh}>TikTok Shop</MucMenu>
      <MucMenu den="/compare">
        <Icon ten="compare" />
        Đối chiếu hai sàn
      </MucMenu>

      {laAdmin ? (
        <>
          <div className="nhom">QUẢN TRỊ</div>
          <MucMenu den="/admin/sync">
            <Icon ten="sync" />
            <span style={{ flex: '1 1 auto' }}>Đồng bộ dữ liệu</span>
            {soSapHetQuyen > 0 ? (
              <span
                title={`${soSapHetQuyen} gian hàng sắp hết quyền truy cập API`}
                style={{ minWidth: 18, height: 18, borderRadius: 9, background: canhBao.nenVangNhat, color: canhBao.chuVang, fontSize: coChu.nhan, fontWeight: 600, display: 'grid', placeItems: 'center' }}
              >
                {soSapHetQuyen}
              </span>
            ) : null}
          </MucMenu>
          <MucMenu den="/admin/upload">
            <Icon ten="upload" />
            Upload tệp dữ liệu
          </MucMenu>
          <MucMenu den="/admin/users">
            <Icon ten="users" />
            Người dùng
          </MucMenu>
        </>
      ) : null}

      <div style={{ marginTop: 'auto', paddingTop: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 10, border: `1px solid ${mau.vienThe}`, borderRadius: boGoc.oTrangThai, background: mau.nenPhu }}>
          <span style={{ width: 32, height: 32, borderRadius: boGoc.nut, background: canhBao.nenOChay, color: canhBao.chuOChay, display: 'grid', placeItems: 'center', flex: 'none' }}>
            <Icon ten="sync" />
          </span>
          <div style={{ lineHeight: 1.35, minWidth: 0 }}>
            <div style={{ fontSize: coChu.nhan, color: mau.chuMo }}>
              {trangThai ? `Tự đồng bộ mỗi ${trangThai.interval_minutes} phút` : 'Đang tải trạng thái đồng bộ'}
            </div>
            <div className="so" style={{ fontSize: coChu.nho, fontWeight: 500 }}>
              {trangThai && lanGanNhat(trangThai) ? `Gần nhất ${dinhDangThoiDiem(lanGanNhat(trangThai))}` : 'Chưa có lần nào'}
            </div>
          </div>
        </div>
        {laAdmin ? (
          <button type="button" className="nut" onClick={dongBoNgay} disabled={dangChayCaHai}>
            Đồng bộ ngay
          </button>
        ) : null}
      </div>
    </nav>
  );
}
