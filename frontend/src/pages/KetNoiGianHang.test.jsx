import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from '../App.jsx';
import SyncStatus from './SyncStatus.jsx';
import { AuthProvider } from '../context/AuthContext.jsx';
import { LoiApi } from '../api/client.js';
import { datCauHinhMock } from '../api/mock/handlers.js';
import { batDauKetNoi, chuyenTrinhDuyet } from '../api/connections.js';

vi.mock('../api/connections.js', async (goc) => ({
  ...(await goc()),
  batDauKetNoi: vi.fn(),
  chuyenTrinhDuyet: vi.fn(),
}));

const ADMIN = 'mock-token-admin.vh';
const USER = 'mock-token-quanly.kd';

function mo(duongDan, token = ADMIN) {
  window.localStorage.setItem('dak_token', token);
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  batDauKetNoi.mockReset();
  chuyenTrinhDuyet.mockReset();
});

afterEach(() => {
  datCauHinhMock({ themShopDongBo: [] });
});

describe('Kết nối gian hàng — nút và phân quyền', () => {
  it('admin thấy "Kết nối gian hàng mới" và nút "Kết nối lại" ở từng gian hàng; không còn nút "Ủy quyền lại"', async () => {
    mo('/admin/sync');
    const c = await screen.findByTestId('shop-Shop C');
    expect(within(c).getByRole('button', { name: 'Kết nối lại' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Kết nối gian hàng mới/ })).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Kết nối lại' })).toHaveLength(3);
    expect(screen.queryByRole('button', { name: 'Ủy quyền lại' })).not.toBeInTheDocument();
  });

  it('người dùng thường không vào được màn này nên không thấy nút nào để kết nối', async () => {
    mo('/admin/sync', USER);
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Đồng bộ dữ liệu' })).not.toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /Kết nối/ })).not.toBeInTheDocument();
  });

  it('chính màn Đồng bộ (không qua route) cũng ẩn mọi nút kết nối với người dùng thường — không chỉ dựa vào việc route chặn', async () => {
    window.localStorage.setItem('dak_token', USER);
    render(
      <MemoryRouter initialEntries={['/admin/sync']}>
        <AuthProvider>
          <SyncStatus />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('shop-Shop C')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Kết nối/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Đồng bộ Shopee' })).toBeInTheDocument();
  });

  it('nhãn trạng thái dễ hiểu: Đang hoạt động / Sắp hết hạn / Mất quyền, kèm lời nhắc kết nối lại', async () => {
    datCauHinhMock({ themShopDongBo: [{ platform: 'shopee', shop_name: 'Shop X', token_status: 'expired' }] });
    mo('/admin/sync');
    expect((await screen.findByTestId('shop-Shop C')).textContent).toContain('Sắp hết hạn – cần kết nối lại');
    expect(screen.getByTestId('shop-Shop A').textContent).toContain('Đang hoạt động');
    expect(screen.getByTestId('shop-Shop X').textContent).toContain('Mất quyền – cần kết nối lại');
  });
});

describe('Kết nối gian hàng — bấm nút', () => {
  it('"Kết nối lại" gọi backend với đúng sàn và tên gian hàng rồi chuyển trình duyệt sang trang của sàn', async () => {
    batDauKetNoi.mockResolvedValue('http://localhost:8001/api/v2/shop/auth_partner?x=1');
    mo('/admin/sync');
    const c = await screen.findByTestId('shop-Shop C');
    await userEvent.click(within(c).getByRole('button', { name: 'Kết nối lại' }));
    await waitFor(() => expect(chuyenTrinhDuyet).toHaveBeenCalledWith('http://localhost:8001/api/v2/shop/auth_partner?x=1'));
    expect(batDauKetNoi).toHaveBeenCalledWith('shopee', 'Shop C');
  });

  it('"Kết nối lại" gặp lỗi thì báo ngay trong thẻ gian hàng, không chuyển trình duyệt', async () => {
    batDauKetNoi.mockRejectedValue(new LoiApi(0, { code: 'network', message: 'Không kết nối được máy chủ' }));
    mo('/admin/sync');
    const a = await screen.findByTestId('shop-Shop A');
    await userEvent.click(within(a).getByRole('button', { name: 'Kết nối lại' }));
    expect(await within(a).findByRole('alert')).toHaveTextContent('Không kết nối được máy chủ');
    expect(chuyenTrinhDuyet).not.toHaveBeenCalled();
    expect(batDauKetNoi).toHaveBeenCalledWith('tiktok', 'Shop A');
  });

  it('hộp thoại: Shopee bắt buộc tên hiển thị; nhập đủ thì sang trang của sàn', async () => {
    batDauKetNoi.mockResolvedValue('http://localhost:8001/trang-uy-quyen');
    mo('/admin/sync');
    await userEvent.click(await screen.findByRole('button', { name: /Kết nối gian hàng mới/ }));
    const hop = await screen.findByRole('dialog');
    const nut = within(hop).getByRole('button', { name: 'Sang trang của sàn' });
    expect(nut).toBeDisabled();
    await userEvent.type(within(hop).getByLabelText('Tên hiển thị của gian hàng'), '  Shop D ');
    expect(nut).toBeEnabled();
    await userEvent.click(nut);
    await waitFor(() => expect(chuyenTrinhDuyet).toHaveBeenCalledWith('http://localhost:8001/trang-uy-quyen'));
    expect(batDauKetNoi).toHaveBeenCalledWith('shopee', 'Shop D');
  });

  it('hộp thoại: TikTok không cần nhập tên (tên lấy từ sàn)', async () => {
    batDauKetNoi.mockResolvedValue('http://localhost:8001/open/authorize');
    mo('/admin/sync');
    await userEvent.click(await screen.findByRole('button', { name: /Kết nối gian hàng mới/ }));
    const hop = await screen.findByRole('dialog');
    await userEvent.selectOptions(within(hop).getByLabelText('Sàn'), 'tiktok');
    expect(within(hop).queryByLabelText('Tên hiển thị của gian hàng')).not.toBeInTheDocument();
    await userEvent.click(within(hop).getByRole('button', { name: 'Sang trang của sàn' }));
    await waitFor(() => expect(chuyenTrinhDuyet).toHaveBeenCalledWith('http://localhost:8001/open/authorize'));
    expect(batDauKetNoi).toHaveBeenCalledWith('tiktok', '');
  });

  it('hộp thoại: backend từ chối (tên không hợp lệ) thì báo trong hộp, không chuyển trình duyệt, bấm lại được', async () => {
    batDauKetNoi.mockRejectedValueOnce(new LoiApi(422, { code: 'shop_name_invalid', message: 'Tên gian hàng không hợp lệ' }));
    mo('/admin/sync');
    await userEvent.click(await screen.findByRole('button', { name: /Kết nối gian hàng mới/ }));
    const hop = await screen.findByRole('dialog');
    await userEvent.type(within(hop).getByLabelText('Tên hiển thị của gian hàng'), 'a/b');
    await userEvent.click(within(hop).getByRole('button', { name: 'Sang trang của sàn' }));
    expect(await within(hop).findByRole('alert')).toHaveTextContent('Tên gian hàng không hợp lệ');
    expect(chuyenTrinhDuyet).not.toHaveBeenCalled();
    expect(within(hop).getByRole('button', { name: 'Sang trang của sàn' })).toBeEnabled();
  });
});

describe('Kết nối gian hàng — quay về từ trang của sàn', () => {
  it('thành công với gian hàng mới: báo rõ và nói hệ thống đang đồng bộ lần đầu', async () => {
    mo('/admin/sync?ket_noi=thanh_cong&shop=Shop%20D&lai=0');
    const tb = await screen.findByTestId('thong-bao-ket-noi');
    expect(tb).toHaveTextContent('Đã kết nối Shop D');
    expect(tb).toHaveTextContent('đồng bộ lần đầu');
    expect(tb).toHaveAttribute('role', 'status');
  });

  it('thành công khi kết nối lại: nói "kết nối lại"', async () => {
    mo('/admin/sync?ket_noi=thanh_cong&shop=Shop%20C&lai=1');
    expect(await screen.findByTestId('thong-bao-ket-noi')).toHaveTextContent('Đã kết nối lại Shop C');
  });

  it.each([
    ['chu_shop_tu_choi', 'Chủ shop đã từ chối ủy quyền. Chưa có gì thay đổi.'],
    ['state_khong_hop_le', 'Phiên kết nối đã hết hạn hoặc không hợp lệ'],
    ['loi_san', 'Không hoàn tất được kết nối với sàn'],
    ['ten_trung', 'Tên gian hàng này đã dùng cho một gian hàng khác'],
    ['thieu_ma_uy_quyen', 'Sàn không gửi về mã ủy quyền'],
    ['ly-do-la-chua-biet', 'Kết nối không thành công. Hãy thử lại.'],
  ])('lỗi %s hiện thông báo tiếng Việt dễ hiểu (role=alert)', async (lyDo, noiDung) => {
    mo(`/admin/sync?ket_noi=loi&ly_do=${lyDo}`);
    const tb = await screen.findByTestId('thong-bao-ket-noi');
    expect(tb).toHaveTextContent(noiDung);
    expect(tb).toHaveAttribute('role', 'alert');
  });

  it('không có tham số kết nối thì không có thông báo; tên shop trong địa chỉ chỉ được hiện như văn bản', async () => {
    const { container, unmount } = mo('/admin/sync');
    await screen.findByTestId('shop-Shop C');
    expect(screen.queryByTestId('thong-bao-ket-noi')).not.toBeInTheDocument();
    unmount();
    const hai = mo('/admin/sync?ket_noi=thanh_cong&shop=%3Cb%3Ex%3C%2Fb%3E&lai=0');
    const tb = await screen.findByTestId('thong-bao-ket-noi');
    expect(tb.textContent).toContain('<b>x</b>');
    expect(hai.container.querySelector('[data-testid="thong-bao-ket-noi"] b')).toBeNull();
    expect(container).toBeDefined();
  });
});

describe('Kết nối gian hàng — chế độ dữ liệu giả (không có backend)', () => {
  it('hàm thật báo "Cần chạy với backend" thay vì lỗi mạng', async () => {
    const goc = await vi.importActual('../api/connections.js');
    await expect(goc.batDauKetNoi('shopee', 'Shop D')).rejects.toThrow(/Cần chạy với backend/);
  });
});
