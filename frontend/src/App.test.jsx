import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from './App.jsx';

// Khung ứng dụng, router, phân quyền menu.

function mo(duongDan, token) {
  if (token) {
    window.localStorage.setItem('dak_token', token);
  }
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <App />
    </MemoryRouter>,
  );
}

/**
 * Chờ tới khi tiêu đề xuất hiện. Dùng waitFor thay vì findByRole vì trang dashboard dựng lại phần tiêu đề
 * khi bộ lọc tải xong, nên phần tử tìm được lúc đầu có thể bị thay trước khi kiểm tra.
 */
async function coTieuDe(ten) {
  await waitFor(() => expect(screen.getByRole('heading', { name: ten })).toBeInTheDocument());
}

describe('router', () => {
  it('chưa đăng nhập thì về /login', async () => {
    mo('/dashboard/shopee');
    await coTieuDe('Đăng nhập');
  });

  it('đã đăng nhập mở /dashboard/shopee thấy tiêu đề', async () => {
    mo('/dashboard/shopee', 'mock-token-admin.vh');
    await coTieuDe('Dashboard Shopee');
  });

  it('/dashboard/tiktok có tiêu đề TikTok Shop', async () => {
    mo('/dashboard/tiktok', 'mock-token-admin.vh');
    await coTieuDe('Dashboard TikTok Shop');
  });

  it('/dashboard/abc (sàn không hợp lệ) chuyển về /dashboard/shopee', async () => {
    mo('/dashboard/abc', 'mock-token-admin.vh');
    await coTieuDe('Dashboard Shopee');
  });

  it('user thường vào /admin/users bị chuyển về dashboard', async () => {
    mo('/admin/users', 'mock-token-quanly.kd');
    await coTieuDe('Dashboard Shopee');
    expect(screen.queryByRole('heading', { name: 'Người dùng' })).not.toBeInTheDocument();
  });

  it('admin vào được /admin/users', async () => {
    mo('/admin/users', 'mock-token-admin.vh');
    await coTieuDe('Người dùng');
  });
});

describe('menu', () => {
  it('admin thấy nhóm QUẢN TRỊ và nút Đồng bộ ngay', async () => {
    mo('/compare', 'mock-token-admin.vh');
    expect(await screen.findByText('QUẢN TRỊ')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Đồng bộ ngay' })).toBeInTheDocument();
    expect(screen.getByText('Upload tệp dữ liệu')).toBeInTheDocument();
  });

  it('user thường KHÔNG thấy nhóm QUẢN TRỊ và không có nút Đồng bộ ngay', async () => {
    mo('/compare', 'mock-token-quanly.kd');
    await coTieuDe('Đối chiếu hai sàn');
    expect(screen.queryByText('QUẢN TRỊ')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Đồng bộ ngay' })).not.toBeInTheDocument();
  });

  it('"Đồng bộ dữ liệu" có số đếm gian hàng sắp hết quyền (token_status = expiring)', async () => {
    mo('/compare', 'mock-token-admin.vh');
    const so = await screen.findByTitle('1 gian hàng sắp hết quyền truy cập API');
    expect(so).toHaveTextContent('1');
  });

  it('chân menu ghi chu kỳ tự đồng bộ và lần gần nhất từ /api/sync/status', async () => {
    mo('/compare', 'mock-token-admin.vh');
    expect(await screen.findByText('Tự đồng bộ mỗi 10 phút')).toBeInTheDocument();
    expect(screen.getByText('Gần nhất 16:40, 23/08')).toBeInTheDocument();
  });

  it('thanh trên có tên người dùng, vai trò và nút Đăng xuất', async () => {
    mo('/compare', 'mock-token-admin.vh');
    expect(await screen.findByText('Quản trị viên')).toBeInTheDocument();
    expect(screen.getByText('admin.vh')).toBeInTheDocument();
    const nutThoat = screen.getByRole('button', { name: /Đăng xuất/ });
    await userEvent.click(nutThoat);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument());
  });
});

describe('đăng nhập', () => {
  it('sai thông tin hiện detail.message của lỗi', async () => {
    mo('/login');
    await userEvent.type(await screen.findByLabelText('Tên đăng nhập'), 'admin.vh');
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'sai');
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Tên đăng nhập hoặc mật khẩu không đúng');
  });

  it('đúng thông tin thì vào dashboard', async () => {
    mo('/login');
    await userEvent.type(await screen.findByLabelText('Tên đăng nhập'), 'quanly.kd');
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'demo123');
    await userEvent.click(screen.getByRole('button', { name: 'Đăng nhập' }));
    await coTieuDe('Dashboard Shopee');
  });
});
