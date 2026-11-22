import { NavLink } from 'react-router-dom';
import { message } from 'antd';
import { mau, chuDao, san, canhBao, boGoc, coChu, khoangCach } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { chayDongBo, layTrangThaiDongBo } from '../api/sync.js';
import { docLoi } from '../api/client.js';
import { dinhDangThoiDiem } from '../utils/format.js';
import Icon from './Icon.jsx';
import logoShopee from '../assets/shopee.png';
import logoTiktok from '../assets/tiktok.png';

// Menu trắng bên trái (theo bản thiết kế): nhóm TỔNG QUAN, nhóm QUẢN TRỊ (chỉ admin thấy),
// chân menu là ô "Tự đồng bộ mỗi N phút · Gần nhất ..." và nút "Đồng bộ ngay" (chỉ admin).

function MucMenu({ den, children, bieuTuongSan }) {
  return (
    <NavLink
      to={den}
      className="nav"
      style={({ isActive }) => ({
        background: isActive ? chuDao.nhat : 'transparent',
        color: isActive ? chuDao.chinh : mau.chuPhu,
        fontWeight: isActive ? 600 : 400,
      })}
    >
      {bieuTuongSan ? <img src={bieuTuongSan} alt="" width={20} height={20} style={{ flex: 'none', margin: '0 -1px' }} /> : null}
      {children}
    </NavLink>
  );
}

const SAN_DONG_BO = [
  { ma: 'shopee', ten: 'Shopee' },
  { ma: 'tiktok', ten: 'TikTok Shop' },
];

/** Câu thông báo sau "Đồng bộ ngay": "Đã bắt đầu đồng bộ Shopee. TikTok Shop đang đồng bộ nên bỏ qua." */
function dungThongBaoDongBo(batDau, boQua) {
  const phan = [];
  if (batDau.length > 0) {
    phan.push(`Đã bắt đầu đồng bộ ${batDau.join(' và ')}.`);
  }
  if (boQua.length > 0) {
    phan.push(`${boQua.join(' và ')} đang đồng bộ nên bỏ qua.`);
  }
  return phan.join(' ');
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

  /**
   * "Đồng bộ ngay" ở chân menu. Đọc trạng thái MỚI NHẤT trước, chỉ gọi sàn không đang chạy;
   * sàn đang chạy được bỏ qua và ghi trong thông báo (không phải lỗi). Nếu giữa lúc đọc và lúc gọi
   * sàn kia kịp chạy (409) thì cũng coi là "đang đồng bộ, bỏ qua". Lỗi khác vẫn báo là lỗi.
   */
  const dongBoNgay = async () => {
    let tt;
    try {
      tt = await layTrangThaiDongBo();
    } catch (e) {
      thongBao.error(docLoi(e).message);
      return;
    }
    const batDau = [];
    const boQua = [];
    const loiKhac = [];
    const dsSan = SAN_DONG_BO.filter((s) => {
      if (tt.platforms[s.ma].running) {
        boQua.push(s.ten);
        return false;
      }
      return true;
    });
    const ketQua = await Promise.allSettled(dsSan.map((s) => chayDongBo(s.ma)));
    ketQua.forEach((k, i) => {
      if (k.status === 'fulfilled') {
        batDau.push(dsSan[i].ten);
      } else if (k.reason && k.reason.status === 409) {
        boQua.push(dsSan[i].ten);
      } else {
        loiKhac.push(docLoi(k.reason).message);
      }
    });
    if (loiKhac.length > 0) {
      thongBao.error(loiKhac[0]);
    } else {
      thongBao.info(dungThongBaoDongBo(batDau, boQua));
    }
    lamMoi();
  };

  return (
    <nav
      aria-label="Điều hướng chính"
      className="thanh-nav-noi"
      style={{
        position: 'sticky',
        top: 14,
        alignSelf: 'flex-start',
        height: 'calc(100vh - 28px)',
        maxHeight: 'calc(100vh - 28px)',
        flex: `0 0 ${khoangCach.rongMenu}px`,
        width: khoangCach.rongMenu,
        margin: '14px 10px 14px 14px',
        boxSizing: 'border-box',
        overflowY: 'auto',
        zIndex: 50,
      }}
    >
      {boThongBao}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '2px 6px 14px', borderBottom: `1px solid ${mau.vienTrong}`, flexShrink: 0 }}>
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
      <MucMenu den="/dashboard/shopee" bieuTuongSan={logoShopee}>Shopee</MucMenu>
      <MucMenu den="/dashboard/tiktok" bieuTuongSan={logoTiktok}>TikTok Shop</MucMenu>
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

      <div style={{ marginTop: 'auto', paddingTop: 20, display: 'flex', flexDirection: 'column', gap: 10, flexShrink: 0 }}>
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
          <button type="button" className="nut" onClick={dongBoNgay} disabled={dangChayCaHai} style={{ width: '100%', height: 36, borderRadius: boGoc.nut }}>
            Đồng bộ ngay
          </button>
        ) : null}
      </div>
    </nav>
  );
}
