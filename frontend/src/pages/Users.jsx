import { useState } from 'react';
import { Modal } from 'antd';
import { mau, chuDao, canhBao, coChu, khoangCach } from '../theme/tokens.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useTaiDuLieu } from '../hooks/useTaiDuLieu.js';
import { layDanhSachNguoiDung, taoNguoiDung, doiVaiTro, datLaiMatKhau, xoaNguoiDung } from '../api/users.js';
import { docLoi } from '../api/client.js';
import Card from '../components/Card.jsx';
import PageTitle from '../components/PageTitle.jsx';
import Icon from '../components/Icon.jsx';
import KhoiDuLieu from '../components/KhoiDuLieu.jsx';
import { dinhDangNgay } from '../utils/format.js';

const NHAN_VAI_TRO = { admin: 'Admin', user: 'Người dùng' };

/** Nhãn vai trò: Admin màu chủ đạo, Người dùng màu trung tính. */
function NhanVaiTro({ vaiTro }) {
  const laAdmin = vaiTro === 'admin';
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 6, fontSize: coChu.ratNho, fontWeight: 500, background: laAdmin ? chuDao.nhat : mau.thanhNen, color: laAdmin ? chuDao.dam : mau.chuPhu }}>
      {NHAN_VAI_TRO[vaiTro]}
    </span>
  );
}

/**
 * Quản lý người dùng (UC03, admin): danh sách, thêm, đổi vai trò, đặt lại mật khẩu, xóa (có xác nhận).
 * Dòng của chính mình không có nút Xóa và Đổi vai trò (không tự xóa, không tự hạ quyền).
 * Không có nút khóa tài khoản: bảng `users` không có cột trạng thái (SPEC §12.1.4.2).
 */
export default function Users() {
  const { nguoiDung } = useAuth();
  const tt = useTaiDuLieu(() => layDanhSachNguoiDung(), []);
  const [hop, setHop] = useState(null); // {loai: 'vaiTro'|'matKhau'|'xoa', nguoi}; giữ lại sau khi đóng để nội dung không biến mất giữa chừng lúc hộp thoại khép lại
  const [hopMo, setHopMo] = useState(false);
  const [giaTriNhap, setGiaTriNhap] = useState('');
  const [loiHop, setLoiHop] = useState('');
  const [dangGui, setDangGui] = useState(false);
  const [moi, setMoi] = useState({ username: '', password: '', role: 'user' });
  const [loiThem, setLoiThem] = useState('');
  const [daThem, setDaThem] = useState('');

  const moHop = (loai, nguoi) => {
    setHop({ loai, nguoi });
    setHopMo(true);
    setLoiHop('');
    setGiaTriNhap(loai === 'vaiTro' ? nguoi.role : '');
  };
  const dongHop = () => setHopMo(false);

  /** Chạy một thao tác của hộp thoại: thành công thì đóng và tải lại danh sách, lỗi thì hiện trong hộp. */
  const chayThaoTac = async (viec) => {
    setDangGui(true);
    setLoiHop('');
    try {
      await viec();
      setHopMo(false);
      tt.thuLai();
    } catch (e) {
      setLoiHop(docLoi(e).message);
    } finally {
      setDangGui(false);
    }
  };

  const xacNhanHop = () => {
    if (hop.loai === 'vaiTro') {
      return chayThaoTac(() => doiVaiTro(hop.nguoi.id, giaTriNhap));
    }
    if (hop.loai === 'matKhau') {
      return chayThaoTac(() => datLaiMatKhau(hop.nguoi.id, giaTriNhap));
    }
    return chayThaoTac(() => xoaNguoiDung(hop.nguoi.id));
  };

  const them = async (sk) => {
    sk.preventDefault();
    setLoiThem('');
    setDaThem('');
    try {
      await taoNguoiDung(moi);
      setDaThem(`Đã tạo tài khoản ${moi.username}`);
      setMoi({ username: '', password: '', role: 'user' });
      tt.thuLai();
    } catch (e) {
      setLoiThem(docLoi(e).message);
    }
  };

  return (
    <>
      <PageTitle tieuDe="Người dùng" dongPhu="Tài khoản đăng nhập và vai trò của từng người." />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'flex-start' }}>
        <Card style={{ flex: '2 1 560px', padding: '8px 20px 8px', overflowX: 'auto' }} aria-label="Danh sách tài khoản">
          <KhoiDuLieu tt={tt} cao={200}>
            {(ds) => (
              <table className="bang" style={{ minWidth: 520 }}>
                <thead>
                  <tr>
                    <th scope="col">Tên đăng nhập</th>
                    <th scope="col" style={{ textAlign: 'left' }}>Vai trò</th>
                    <th scope="col" style={{ textAlign: 'left' }}>Ngày tạo</th>
                    <th scope="col">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {ds.map((u) => {
                    const laMinh = nguoiDung !== null && u.id === nguoiDung.id;
                    return (
                      <tr key={u.id} data-testid={`nguoi-${u.username}`}>
                        <td>
                          <b>{u.username}</b>
                          {laMinh ? <span style={{ marginLeft: 6, padding: '1px 6px', border: `1px solid ${mau.vienChip}`, borderRadius: 6, fontSize: coChu.nhan, color: mau.chuMo }}>Bạn</span> : null}
                        </td>
                        <td style={{ textAlign: 'left' }}>
                          <NhanVaiTro vaiTro={u.role} />
                        </td>
                        <td className="so" style={{ textAlign: 'left' }}>{dinhDangNgay(u.created_at)}</td>
                        <td>
                          <div style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                            {laMinh ? null : (
                              <button type="button" className="nut" onClick={() => moHop('vaiTro', u)}>
                                Đổi vai trò
                              </button>
                            )}
                            <button type="button" className="nut" onClick={() => moHop('matKhau', u)}>
                              Đặt lại mật khẩu
                            </button>
                            {laMinh ? null : (
                              <button type="button" className="nut nut-nguy" onClick={() => moHop('xoa', u)}>
                                Xóa
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </KhoiDuLieu>
        </Card>

        <Card style={{ flex: '1 1 300px' }} aria-label="Thêm tài khoản">
          <h2 style={{ margin: '0 0 14px', fontSize: coChu.tieuDeThe, fontWeight: 500, color: mau.chuPhu, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon ten="plus" />
            Thêm tài khoản
          </h2>
          <form onSubmit={them} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label className="nhan-o" htmlFor="tk-ten">Tên đăng nhập</label>
              <input id="tk-ten" className="o-nhap" placeholder="ví dụ: nhanvien.vh" value={moi.username} onChange={(e) => setMoi({ ...moi, username: e.target.value })} />
            </div>
            <div>
              <label className="nhan-o" htmlFor="tk-mk">Mật khẩu</label>
              <input id="tk-mk" className="o-nhap" type="password" value={moi.password} onChange={(e) => setMoi({ ...moi, password: e.target.value })} />
            </div>
            <div>
              <label className="nhan-o" htmlFor="tk-vt">Vai trò</label>
              <select id="tk-vt" className="o-nhap" value={moi.role} onChange={(e) => setMoi({ ...moi, role: e.target.value })}>
                <option value="user">Người dùng</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            {loiThem ? (
              <div role="alert" style={{ fontSize: coChu.nho, color: canhBao.chuDam }}>
                {loiThem}
              </div>
            ) : null}
            {daThem ? (
              <div role="status" style={{ fontSize: coChu.nho, color: mau.chuPhu }}>
                {daThem}
              </div>
            ) : null}
            <button type="submit" className="nut nut-chinh" disabled={moi.username.trim() === '' || moi.password === ''}>
              Tạo tài khoản
            </button>
          </form>
        </Card>
      </div>

      {/* Modal của Ant Design lo phần trợ năng: đưa con trỏ vào trong khi mở, giữ Tab trong hộp, trả con trỏ về nút đã bấm khi đóng, Esc để đóng.
          Màu và bo góc lấy từ token qua ConfigProvider (theme/antdTheme.js). */}
      <Modal
        open={hopMo}
        title={hop ? { vaiTro: `Đổi vai trò của ${hop.nguoi.username}`, matKhau: `Đặt lại mật khẩu của ${hop.nguoi.username}`, xoa: `Xóa tài khoản ${hop.nguoi.username}` }[hop.loai] : ''}
        onCancel={dongHop}
        onOk={xacNhanHop}
        okText={hop ? { vaiTro: 'Lưu vai trò', matKhau: 'Đặt lại', xoa: 'Xóa tài khoản' }[hop.loai] : ''}
        cancelText="Hủy"
        okButtonProps={{ danger: hop !== null && hop.loai === 'xoa', disabled: dangGui || (hop !== null && hop.loai === 'matKhau' && giaTriNhap === '') }}
        maskClosable
        width={420}
      >
        {hop ? (
          <form
            onSubmit={(sk) => {
              sk.preventDefault();
              if (!(dangGui || (hop.loai === 'matKhau' && giaTriNhap === ''))) {
                xacNhanHop();
              }
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
          >
            {hop.loai === 'vaiTro' ? (
              <div>
                <label className="nhan-o" htmlFor="hop-vai-tro">Vai trò mới</label>
                <select id="hop-vai-tro" className="o-nhap" value={giaTriNhap} onChange={(e) => setGiaTriNhap(e.target.value)}>
                  <option value="user">Người dùng</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            ) : null}
            {hop.loai === 'matKhau' ? (
              <div>
                <label className="nhan-o" htmlFor="hop-mat-khau">Mật khẩu mới</label>
                <input id="hop-mat-khau" className="o-nhap" type="password" autoFocus value={giaTriNhap} onChange={(e) => setGiaTriNhap(e.target.value)} />
              </div>
            ) : null}
            {hop.loai === 'xoa' ? <p style={{ margin: 0, color: mau.chuPhu }}>Tài khoản sẽ bị xóa và không đăng nhập được nữa. Không hoàn tác được.</p> : null}
            {loiHop ? (
              <div role="alert" style={{ fontSize: coChu.nho, color: canhBao.chuDam }}>
                {loiHop}
              </div>
            ) : null}
          </form>
        ) : null}
      </Modal>
    </>
  );
}
