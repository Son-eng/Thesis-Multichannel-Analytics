import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from '../App.jsx';
import { xuLyMock, datCauHinhMock } from '../api/mock/handlers.js';

// Bốn màn hình quản trị và đăng nhập (lượt 2D). Chạy trong ứng dụng đầy đủ để kiểm cả phân quyền.

const ADMIN = 'mock-token-admin.vh';

function mo(duongDan, token = ADMIN) {
  window.localStorage.setItem('dak_token', token);
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <App />
    </MemoryRouter>,
  );
}

function tepCsv(ten) {
  return new File(['a,b\n1,2'], ten, { type: 'text/csv' });
}

describe('Đồng bộ dữ liệu', () => {
  it('thẻ từng gian hàng: trạng thái, lần thành công gần nhất, hạn quyền, nhãn "Sắp hết quyền"', async () => {
    mo('/admin/sync');
    const c = await screen.findByTestId('shop-Shop C');
    expect(c.textContent).toContain('Sắp hết quyền');
    expect(c.textContent).toContain('Đồng bộ thành công gần nhất');
    expect(c.textContent).toContain('16:40, 23/08');
    expect(c.textContent).toContain('Quyền truy cập còn hạn đến');
    expect(c.textContent).toContain('28/08/2026'); // refresh_expires_at
    const a = screen.getByTestId('shop-Shop A');
    expect(a.textContent).toContain('Sẵn sàng');
    expect(a.textContent).toContain('30/08/2026'); // refresh_expires_at null -> hiện access_expires_at
  });

  it('không có chỗ nào hiện giá trị token', async () => {
    const { container } = mo('/admin/sync');
    await screen.findByTestId('shop-Shop C');
    expect(container.textContent).not.toMatch(/mock-token|access_token|refresh_token|bearer/i);
  });

  it('"Ủy quyền lại" hiện "Chưa hỗ trợ trong bản demo"', async () => {
    mo('/admin/sync');
    const c = await screen.findByTestId('shop-Shop C');
    await userEvent.click(within(c).getByRole('button', { name: 'Ủy quyền lại' }));
    expect(within(c).getByText('Chưa hỗ trợ trong bản demo')).toBeInTheDocument();
  });

  it('nút đồng bộ bị khóa khi sàn đang chạy (running = true)', async () => {
    datCauHinhMock({ thoiGianDongBo: 60000 });
    await xuLyMock('POST', '/api/sync/tiktok', {}, { token: ADMIN });
    mo('/admin/sync');
    const nutTiktok = await screen.findByRole('button', { name: 'TikTok Shop đang đồng bộ' });
    expect(nutTiktok).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Đồng bộ Shopee' })).toBeEnabled();
  });

  it('bấm "Đồng bộ Shopee" thì nút khóa lại (sàn chuyển sang đang chạy)', async () => {
    datCauHinhMock({ thoiGianDongBo: 60000 });
    mo('/admin/sync');
    await userEvent.click(await screen.findByRole('button', { name: 'Đồng bộ Shopee' }));
    expect(await screen.findByRole('button', { name: 'Shopee đang đồng bộ' })).toBeDisabled();
  });

  it('409 hiện đúng thông báo của máy chủ', async () => {
    datCauHinhMock({ thoiGianDongBo: 60000 });
    mo('/admin/sync');
    const nut = await screen.findByRole('button', { name: 'Đồng bộ TikTok Shop' });
    // Nút bị khóa cho tới khi trạng thái đồng bộ tải xong.
    await waitFor(() => expect(nut).toBeEnabled());
    // Có lượt khác bắt đầu sau khi trang tải trạng thái: bấm nút sẽ nhận 409.
    await xuLyMock('POST', '/api/sync/tiktok', {}, { token: ADMIN });
    await userEvent.click(nut);
    expect(await screen.findByRole('alert')).toHaveTextContent('TikTok Shop đang có lượt đồng bộ chạy');
  });

  it('lịch sử: tổng 137 lượt, phân trang 20 dòng, "Tự động" khi triggered_by = null', async () => {
    mo('/admin/sync');
    const khoi = await screen.findByLabelText('Lịch sử đưa dữ liệu vào');
    await waitFor(() => expect(khoi.textContent).toContain('137 lượt · Trang 1 / 7'));
    expect(within(khoi).getAllByRole('row')).toHaveLength(21); // 1 dòng tiêu đề + 20 dòng
    expect(khoi.textContent).toContain('Tự động');
    await userEvent.click(within(khoi).getByRole('button', { name: 'Trang sau' }));
    await waitFor(() => expect(khoi.textContent).toContain('Trang 2 / 7'));
  });

  it('lịch sử có đủ 5 cột bộ đếm chất lượng và số > 0 được tô vàng', async () => {
    mo('/admin/sync');
    const khoi = await screen.findByLabelText('Lịch sử đưa dữ liệu vào');
    for (const t of ['SKU dự phòng', 'Thiếu SKU', 'Trạng thái lạ', 'Tỉnh chưa chuẩn hóa', 'Chưa có mã SP']) {
      expect(await within(khoi).findByRole('columnheader', { name: t })).toBeInTheDocument();
    }
    // Lọc nguồn "Tệp thủ công" để thấy lượt nạp tệp mẫu Shopee (6 / 19 là số thật, SPEC §3.3).
    await userEvent.selectOptions(within(khoi).getByRole('combobox', { name: 'Nguồn' }), 'file_manual');
    await waitFor(() => expect(within(khoi).getAllByRole('row').length).toBeLessThan(10));
    const o19 = within(khoi).getByText('19');
    expect(o19).toHaveAttribute('data-canh-bao', 'true');
    expect(within(khoi).getByText('6')).toHaveAttribute('data-canh-bao', 'true');
    // Số bằng 0 không tô vàng.
    expect(khoi.querySelectorAll('[data-canh-bao="false"]').length).toBeGreaterThan(0);
  });

  it('lọc Sàn, Nguồn, Kết quả hoạt động', async () => {
    mo('/admin/sync');
    const khoi = await screen.findByLabelText('Lịch sử đưa dữ liệu vào');
    await userEvent.selectOptions(within(khoi).getByRole('combobox', { name: 'Kết quả' }), 'failed');
    await waitFor(() => expect(khoi.textContent).toContain('2 lượt'));
    expect(within(khoi).getAllByText('Thất bại').length).toBeGreaterThan(0);
    await userEvent.selectOptions(within(khoi).getByRole('combobox', { name: 'Sàn' }), 'shopee');
    await waitFor(() => expect(khoi.textContent).toMatch(/\d+ lượt · Trang 1/));
  });
});

describe('Upload tệp dữ liệu', () => {
  it('Shopee chưa chọn gian hàng thì nút "Nạp tệp" bị khóa; chọn đủ thì mở', async () => {
    mo('/admin/upload');
    const nut = await screen.findByRole('button', { name: /Nạp tệp/ });
    expect(nut).toBeDisabled();
    await userEvent.upload(screen.getByLabelText(/bấm để chọn/), tepCsv('don-hang.csv'));
    expect(nut).toBeDisabled(); // có tệp nhưng chưa chọn gian hàng
    const chon = await screen.findByRole('combobox', { name: 'Gian hàng' });
    await waitFor(() => expect(within(chon).getByRole('option', { name: 'Shop C' })).toBeInTheDocument());
    await userEvent.selectOptions(chon, 'Shop C');
    expect(nut).toBeEnabled();
  });

  it('TikTok ghi "Tệp TikTok Shop đã có cột gian hàng, hệ thống tự nhận", không có ô chọn gian hàng', async () => {
    mo('/admin/upload');
    await userEvent.click(await screen.findByRole('radio', { name: 'TikTok Shop' }));
    expect(screen.getByText('Tệp TikTok Shop đã có cột gian hàng, hệ thống tự nhận.')).toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: 'Gian hàng' })).not.toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText(/bấm để chọn/), tepCsv('tiktok.csv'));
    expect(screen.getByRole('button', { name: /Nạp tệp/ })).toBeEnabled();
  });

  it('nạp thành công: "Kết quả lần nạp gần nhất" vẽ từ SyncRun, bộ đếm > 0 tô vàng', async () => {
    mo('/admin/upload');
    await userEvent.upload(await screen.findByLabelText(/bấm để chọn/), tepCsv('don-hang.csv'));
    const chon = await screen.findByRole('combobox', { name: 'Gian hàng' });
    await waitFor(() => expect(within(chon).getByRole('option', { name: 'Shop C' })).toBeInTheDocument());
    await userEvent.selectOptions(chon, 'Shop C');
    await userEvent.click(screen.getByRole('button', { name: /Nạp tệp/ }));
    const khoi = await screen.findByLabelText('Kết quả lần nạp gần nhất');
    await waitFor(() => expect(khoi.textContent).toContain('Đã nạp xong 1.774 dòng.'));
    expect(within(khoi).getByText('19')).toHaveAttribute('data-canh-bao', 'true');
    expect(within(khoi).getByText('6')).toHaveAttribute('data-canh-bao', 'true');
    expect(khoi.textContent).toContain('don-hang.csv');
  });

  it('422 missing_columns: liệt kê cột thiếu và nói "không dòng nào được ghi"', async () => {
    mo('/admin/upload');
    await userEvent.upload(await screen.findByLabelText(/bấm để chọn/), tepCsv('don-hang-thieu-cot.csv'));
    const chon = await screen.findByRole('combobox', { name: 'Gian hàng' });
    await waitFor(() => expect(within(chon).getByRole('option', { name: 'Shop C' })).toBeInTheDocument());
    await userEvent.selectOptions(chon, 'Shop C');
    await userEvent.click(screen.getByRole('button', { name: /Nạp tệp/ }));
    const loi = await screen.findByRole('alert');
    expect(loi.textContent).toContain('không dòng nào được ghi');
    expect(loi.textContent).toContain('Mã đơn hàng');
  });

  it('422 invalid_file: báo tệp không đọc được, không dòng nào được ghi, KHÔNG có danh sách cột', async () => {
    mo('/admin/upload');
    await userEvent.upload(await screen.findByLabelText(/bấm để chọn/), tepCsv('don-khong-doc-duoc.csv'));
    const chon = await screen.findByRole('combobox', { name: 'Gian hàng' });
    await waitFor(() => expect(within(chon).getByRole('option', { name: 'Shop C' })).toBeInTheDocument());
    await userEvent.selectOptions(chon, 'Shop C');
    await userEvent.click(screen.getByRole('button', { name: /Nạp tệp/ }));
    const loi = await screen.findByRole('alert');
    expect(loi.textContent).toContain('Tệp không đọc được, không dòng nào được ghi');
    expect(loi.textContent).not.toContain('Cột còn thiếu');
  });

  it('tệp không phải .csv bị từ chối ngay ở giao diện', async () => {
    mo('/admin/upload');
    const o = await screen.findByLabelText(/bấm để chọn/);
    await userEvent.upload(o, new File(['x'], 'anh.png', { type: 'image/png' }), { applyAccept: false });
    expect(await screen.findByRole('alert')).toHaveTextContent('Chỉ nhận tệp CSV');
    expect(screen.getByRole('button', { name: /Nạp tệp/ })).toBeDisabled();
  });
});

describe('Người dùng', () => {
  it('user thường vào /admin/users bị chuyển về dashboard', async () => {
    mo('/admin/users', 'mock-token-quanly.kd');
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Dashboard Shopee' })).toBeInTheDocument());
  });

  it('danh sách: dòng của chính mình không có nút Xóa và Đổi vai trò; không có nút khóa tài khoản', async () => {
    mo('/admin/users');
    const minh = await screen.findByTestId('nguoi-admin.vh');
    expect(within(minh).getByText('Bạn')).toBeInTheDocument();
    expect(within(minh).queryByRole('button', { name: 'Xóa' })).not.toBeInTheDocument();
    expect(within(minh).queryByRole('button', { name: 'Đổi vai trò' })).not.toBeInTheDocument();
    expect(within(minh).getByRole('button', { name: 'Đặt lại mật khẩu' })).toBeInTheDocument();
    const khac = screen.getByTestId('nguoi-quanly.kd');
    ['Đổi vai trò', 'Đặt lại mật khẩu', 'Xóa'].forEach((t) => expect(within(khac).getByRole('button', { name: t })).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /khóa/i })).not.toBeInTheDocument();
  });

  it('thêm tài khoản; trùng tên thì báo lỗi', async () => {
    mo('/admin/users');
    await screen.findByTestId('nguoi-admin.vh');
    await userEvent.type(screen.getByLabelText('Tên đăng nhập'), 'nhanvien.vh');
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'mk-gia-1');
    await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }));
    expect(await screen.findByTestId('nguoi-nhanvien.vh')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Tên đăng nhập'), 'admin.vh');
    await userEvent.type(screen.getByLabelText('Mật khẩu'), 'mk-gia-2');
    await userEvent.click(screen.getByRole('button', { name: 'Tạo tài khoản' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Tên đăng nhập đã tồn tại');
  });

  it('đổi vai trò', async () => {
    mo('/admin/users');
    const khac = await screen.findByTestId('nguoi-quanly.kd');
    expect(khac.textContent).toContain('Người dùng');
    await userEvent.click(within(khac).getByRole('button', { name: 'Đổi vai trò' }));
    const hop = await screen.findByRole('dialog');
    await userEvent.selectOptions(within(hop).getByLabelText('Vai trò mới'), 'admin');
    await userEvent.click(within(hop).getByRole('button', { name: 'Lưu vai trò' }));
    await waitFor(() => expect(screen.getByTestId('nguoi-quanly.kd').textContent).toContain('Admin'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('đặt lại mật khẩu: nút khóa khi chưa nhập', async () => {
    mo('/admin/users');
    const khac = await screen.findByTestId('nguoi-quanly.kd');
    await userEvent.click(within(khac).getByRole('button', { name: 'Đặt lại mật khẩu' }));
    const hop = await screen.findByRole('dialog');
    expect(within(hop).getByRole('button', { name: 'Đặt lại' })).toBeDisabled();
    await userEvent.type(within(hop).getByLabelText('Mật khẩu mới'), 'mk-moi-gia');
    await userEvent.click(within(hop).getByRole('button', { name: 'Đặt lại' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('xóa có xác nhận: Hủy thì giữ, xác nhận thì mất', async () => {
    mo('/admin/users');
    const khac = await screen.findByTestId('nguoi-quanly.kd');
    await userEvent.click(within(khac).getByRole('button', { name: 'Xóa' }));
    let hop = await screen.findByRole('dialog');
    await userEvent.click(within(hop).getByRole('button', { name: 'Hủy' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByTestId('nguoi-quanly.kd')).toBeInTheDocument();
    await userEvent.click(within(screen.getByTestId('nguoi-quanly.kd')).getByRole('button', { name: 'Xóa' }));
    hop = await screen.findByRole('dialog');
    await userEvent.click(within(hop).getByRole('button', { name: 'Xóa tài khoản' }));
    await waitFor(() => expect(screen.queryByTestId('nguoi-quanly.kd')).not.toBeInTheDocument());
  });
});
