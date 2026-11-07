import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Dashboard from './Dashboard.jsx';
import { datCauHinhMock } from '../api/mock/handlers.js';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  window.localStorage.clear();
});

function mo(duongDan) {
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <Routes>
        <Route path="/dashboard/:platform" element={<Dashboard />} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Chờ thẻ doanh thu có số (đã tải xong), trả về thẻ. */
async function theDoanhThu() {
  const the = await screen.findByTestId('the-doanh-thu');
  await waitFor(() => expect(the).not.toBeEmptyDOMElement());
  return the;
}

describe('thẻ chỉ số', () => {
  it('insufficient_data: thẻ doanh thu ghi "Không đủ dữ liệu để so sánh", không hiện % và không hiện −100%', async () => {
    mo('/dashboard/shopee?ky=2026-07');
    const the = await screen.findByTestId('the-doanh-thu');
    await waitFor(() => expect(within(the).getAllByText('Không đủ dữ liệu để so sánh', { exact: false }).length).toBeGreaterThan(0));
    expect(the.textContent).not.toContain('%');
    expect(the.textContent).not.toContain('100');
    // Số doanh thu vẫn hiện (kỳ này có dữ liệu).
    expect(the.textContent).toContain('1.068.925.905');
  });

  it('thẻ tỷ lệ hủy hiện thay đổi bằng "điểm %"', async () => {
    mo('/dashboard/tiktok');
    const the = await screen.findByTestId('the-ty-le-huy');
    await waitFor(() => expect(the.textContent).toContain('điểm %'));
    expect(the.textContent).not.toMatch(/[+−]\d+,\d%/);
  });

  it('thẻ doanh thu và thẻ số đơn hiện thay đổi bằng %', async () => {
    mo('/dashboard/shopee');
    const the = await screen.findByTestId('the-doanh-thu');
    await waitFor(() => expect(the.textContent).toContain('▲ +34,6%'));
  });

  it('no_data: Shopee tháng 3 hiện "Không có dữ liệu", không hiện số 0', async () => {
    mo('/dashboard/shopee?ky=2026-03');
    const the = await screen.findByTestId('the-doanh-thu');
    await waitFor(() => expect(within(the).getAllByText('Không có dữ liệu', { exact: false }).length).toBeGreaterThan(0));
    expect(the.textContent).not.toMatch(/(^|\D)0 đ/);
    const theDon = screen.getByTestId('the-so-don');
    expect(theDon.textContent).toContain('Không có dữ liệu');
  });

  it('tooltip của thẻ doanh thu nói "chưa phải lợi nhuận"', async () => {
    mo('/dashboard/shopee');
    await theDoanhThu();
    expect(await screen.findByTitle(/chưa phải lợi nhuận/)).toBeInTheDocument();
  });

  it('kỳ chưa đủ ngày: tiêu đề "tính đến 16/08" và dòng so sánh ghi khoảng ngày kỳ trước', async () => {
    mo('/dashboard/shopee');
    const the = await screen.findByTestId('the-doanh-thu');
    await waitFor(() => expect(the.textContent).toContain('Doanh thu tính đến 16/08'));
    expect(the.textContent).toContain('so với 01/07 – 16/07: 624.277.755 đ');
    expect(await screen.findByText(/Tháng 8\/2026 chưa kết thúc/)).toBeInTheDocument();
  });

  it('dòng phụ "N sản phẩm bán" lấy đúng metrics.quantity_sold (TikTok tháng 7: 513)', async () => {
    mo('/dashboard/tiktok?ky=2026-07');
    const the = await screen.findByTestId('the-so-don');
    await waitFor(() => expect(the.textContent).toContain('513 sản phẩm bán'));
    expect(the.textContent).toContain('510');
  });

  it('quantity_sold = null thì dòng phụ ghi "Không có dữ liệu"', async () => {
    mo('/dashboard/shopee?ky=2026-03');
    const the = await screen.findByTestId('the-so-don');
    await waitFor(() => expect(the.textContent).toContain('Không có dữ liệu'));
    expect(the.textContent).not.toContain('sản phẩm bán');
  });

  it('TikTok tháng 4 vượt ngưỡng: dải cảnh báo đỏ ghi −30,5% và ngưỡng 30%', async () => {
    mo('/dashboard/tiktok?ky=2026-04');
    const dai = await screen.findByRole('alert');
    expect(dai.textContent).toContain('giảm 30,5%');
    expect(dai.textContent).toContain('vượt ngưỡng cảnh báo giảm 30%');
    expect(dai.textContent).toContain('1.014.538.449 đ so với 1.459.153.482 đ');
  });

  it('kỳ không vượt ngưỡng thì không có dải cảnh báo', async () => {
    mo('/dashboard/tiktok?ky=2026-07');
    await theDoanhThu();
    await screen.findByText('Sản phẩm bán chạy');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('biểu đồ và bảng', () => {
  it('StackedRibbonChart vẽ đúng số lớp = số mã trong top_product_codes + 1', async () => {
    const { container } = mo('/dashboard/tiktok');
    await waitFor(() => expect(container.querySelectorAll('[data-lop]').length).toBeGreaterThan(0));
    const lop = new Set(Array.from(container.querySelectorAll('[data-lop]')).map((e) => e.getAttribute('data-lop')));
    // TikTok: 4 mã dẫn đầu + "Mã khác".
    expect(lop.size).toBe(5);
    expect(lop.has('khac')).toBe(true);
  });

  it('tháng vượt ngưỡng ghi đỏ kèm % giảm trên biểu đồ (từ /alerts)', async () => {
    const { container } = mo('/dashboard/tiktok');
    await waitFor(() => expect(container.querySelector('svg[role="img"]')).not.toBeNull());
    await waitFor(() => expect(container.textContent).toContain('· −30,5%'));
  });

  it('"Tổng toàn bộ dữ liệu" bằng tổng doanh thu mọi tháng (7.538.502.584 đ)', async () => {
    mo('/dashboard/tiktok');
    const khoi = await screen.findByLabelText('Doanh thu theo tháng');
    await waitFor(() => expect(khoi.textContent).toContain('7.538.502.584'));
    expect(khoi.textContent).toContain('8 tháng');
  });

  it('bảng sản phẩm: mã có kỳ trước bằng 0 ghi "Kỳ trước không có doanh thu" (M22, TikTok tháng 8)', async () => {
    mo('/dashboard/tiktok');
    const bang = await screen.findByLabelText('Sản phẩm bán chạy');
    const dong = await within(bang).findByText('M22');
    const hang = dong.closest('tr');
    expect(hang.textContent).toContain('Kỳ trước không có doanh thu');
  });

  it('Tỉnh/thành: ghi "N tỉnh/thành có đơn", không ghi "x/63", nhóm Khác cuối', async () => {
    mo('/dashboard/shopee');
    const khoi = await screen.findByLabelText('Doanh thu theo tỉnh thành');
    await waitFor(() => expect(khoi.textContent).toMatch(/\d+ tỉnh\/thành có đơn/));
    expect(khoi.textContent).not.toContain('/63');
    const chu = khoi.textContent;
    expect(chu.lastIndexOf('Khác (chưa chuẩn hóa được tên)')).toBeGreaterThan(chu.indexOf('tỉnh/thành còn lại'));
  });

  it('Đơn hàng theo khung giờ có đủ 24 cột', async () => {
    mo('/dashboard/shopee');
    const khoi = await screen.findByLabelText('Đơn hàng theo khung giờ');
    await waitFor(() => expect(khoi.querySelectorAll('[data-testid^="cot-gio"]').length).toBe(24));
  });
});

describe('chất lượng dữ liệu (quy tắc 10)', () => {
  it('Shopee hiện số dòng unknown và số dòng NMV tạm tính', async () => {
    mo('/dashboard/shopee');
    const khoi = await screen.findByLabelText('Cảnh báo và nhận định');
    await waitFor(() => expect(khoi.textContent).toContain('dòng chưa rõ trạng thái đơn, vẫn tính vào doanh thu'));
    expect(khoi.textContent).toContain('dòng có NMV tạm tính, chờ đối soát');
  });

  it('TikTok ghi NMV tạm tính không áp dụng', async () => {
    mo('/dashboard/tiktok');
    const khoi = await screen.findByLabelText('Cảnh báo và nhận định');
    await waitFor(() => expect(khoi.textContent).toContain('NMV tạm tính: không áp dụng với sàn này'));
    expect(khoi.textContent).toContain('0 dòng chưa rõ trạng thái đơn');
  });
});

describe('cảnh báo biến động', () => {
  it('kỳ khác vượt ngưỡng thì có liên kết dẫn tới kỳ đó', async () => {
    mo('/dashboard/tiktok');
    const khoi = await screen.findByLabelText('Cảnh báo và nhận định');
    const lienKet = await within(khoi).findByRole('button', { name: /tháng 4\/2026/ });
    expect(lienKet.textContent).toContain('−30,5%');
    await userEvent.click(lienKet);
    const the = screen.getByTestId('the-doanh-thu');
    await waitFor(() => expect(the.textContent).toContain('1.014.538.449'));
  });

  it('Shopee không có kỳ nào vượt ngưỡng', async () => {
    mo('/dashboard/shopee');
    const khoi = await screen.findByLabelText('Cảnh báo và nhận định');
    await waitFor(() => expect(khoi.textContent).toContain('Không có kỳ nào giảm từ 30% so với kỳ liền trước.'));
    expect(khoi.textContent).toContain('Ngưỡng hiện tại: giảm từ 30%');
  });
});

describe('nhận định tự động và lỗi từng khối', () => {
  it('nhận định lỗi 503: chỉ thẻ nhận định báo lỗi, thẻ doanh thu vẫn hiện số', async () => {
    datCauHinhMock({ llmLoi: true });
    mo('/dashboard/shopee');
    const nut = await screen.findByRole('button', { name: 'Sinh nhận định' });
    await userEvent.click(nut);
    const loi = await screen.findByText(/Không sinh được nhận định/);
    expect(loi).toBeInTheDocument();
    const the = screen.getByTestId('the-doanh-thu');
    expect(the.textContent).toContain('840.035.154');
  });

  it('nhận định chỉ được gọi khi bấm nút; có kết quả thì hiện văn bản', async () => {
    mo('/dashboard/tiktok?ky=2026-07');
    await theDoanhThu();
    expect(await screen.findByText(/Chỉ chạy khi bấm nút/)).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Sinh nhận định' }));
    expect(await screen.findByText(/dẫn đầu doanh thu/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sinh lại' })).toBeInTheDocument();
  });

  it('một khối lỗi (khung giờ) không làm hỏng khối khác', async () => {
    datCauHinhMock({ loiKhoi: ['by-hour'] });
    mo('/dashboard/shopee');
    const gio = await screen.findByLabelText('Đơn hàng theo khung giờ');
    await waitFor(() => expect(gio.textContent).toContain('Không tải được khối này'));
    const the = screen.getByTestId('the-doanh-thu');
    await waitFor(() => expect(the.textContent).toContain('840.035.154'));
    const san = await screen.findByLabelText('Sản phẩm bán chạy');
    await waitFor(() => expect(within(san).getAllByRole('row').length).toBeGreaterThan(1));
  });
});

describe('đầu trang và ô chọn', () => {
  it('mặc định mở ở kỳ chứa data_max_date của chính sàn đó', async () => {
    mo('/dashboard/shopee');
    const chonKy = await screen.findByRole('combobox', { name: 'Kỳ' });
    expect(chonKy).toHaveValue('2026-08');
    expect(within(chonKy).getByRole('option', { name: 'Tháng 8/2026 *' })).toBeInTheDocument();
    expect(within(chonKy).getByRole('option', { name: 'Tháng 7/2026' })).toBeInTheDocument();
  });

  it('dòng phụ ghi gian hàng và khoảng dữ liệu của sàn', async () => {
    mo('/dashboard/tiktok');
    expect(await screen.findByText('2 gian hàng (Shop A, Shop B) · Dữ liệu 01/01/2026 – 23/08/2026')).toBeInTheDocument();
  });

  it('đổi kỳ thì thẻ doanh thu đổi sang số của kỳ mới', async () => {
    mo('/dashboard/tiktok');
    const the = await screen.findByTestId('the-doanh-thu');
    await waitFor(() => expect(the.textContent).toContain('863.491.460'));
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Kỳ' }), '2026-07');
    await waitFor(() => expect(the.textContent).toContain('814.595.996'));
    expect(the.textContent).toContain('▲ +43,9%');
  });

  it('có ô chọn gian hàng và mã sản phẩm lấy từ /filters, không viết cứng', async () => {
    mo('/dashboard/tiktok');
    const chonShop = await screen.findByRole('combobox', { name: 'Gian hàng' });
    expect(within(chonShop).getByRole('option', { name: 'Shop A' })).toBeInTheDocument();
    expect(within(chonShop).getByRole('option', { name: 'Shop B' })).toBeInTheDocument();
    const chonMa = screen.getByRole('combobox', { name: 'Mã sản phẩm' });
    expect(within(chonMa).getByRole('option', { name: 'M22' })).toBeInTheDocument();
  });

  it('"Xuất PDF" hiện "Chưa hỗ trợ trong bản demo" và không gọi máy chủ', async () => {
    const hamFetch = vi.fn();
    vi.stubGlobal('fetch', hamFetch);
    mo('/dashboard/shopee');
    await userEvent.click(await screen.findByRole('button', { name: /Xuất PDF/ }));
    expect(screen.getByText('Chưa hỗ trợ trong bản demo')).toBeInTheDocument();
    expect(hamFetch).not.toHaveBeenCalled();
  });

  it('"Xuất Excel" ở chế độ giả lập nói rõ cần máy chủ thật (không tạo tệp giả)', async () => {
    mo('/dashboard/shopee');
    await userEvent.click(await screen.findByRole('button', { name: /Xuất Excel/ }));
    expect(await screen.findByText(/cần chạy với máy chủ thật/)).toBeInTheDocument();
  });

  it('"Xuất Excel" với máy chủ thật: gọi đúng kỳ và bộ lọc đang xem, kèm token, rồi lưu tệp', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    window.localStorage.setItem('dak_token', 'token-that');
    const hamFetch = vi.fn(async (url) => {
      if (String(url).includes('/api/export/')) {
        return { ok: true, status: 200, headers: { get: () => 'attachment; filename="bao-cao-shopee-2026-07.xlsx"' }, blob: async () => new Blob(['x']) };
      }
      // Các endpoint dữ liệu khác: dùng chính bộ xử lý mock làm "máy chủ thật" để trang dựng được.
      const { xuLyMock } = await import('../api/mock/handlers.js');
      const u = new URL(url);
      const thamSo = Object.fromEntries(u.searchParams);
      return { ok: true, status: 200, json: async () => xuLyMock('GET', u.pathname, thamSo, { token: 'mock-token-admin.vh' }) };
    });
    vi.stubGlobal('fetch', hamFetch);
    URL.createObjectURL = () => 'blob:thu';
    URL.revokeObjectURL = () => {};
    mo('/dashboard/shopee?ky=2026-07&ma=M15');
    await userEvent.click(await screen.findByRole('button', { name: /Xuất Excel/ }));
    expect(await screen.findByText('Đã tải bao-cao-shopee-2026-07.xlsx')).toBeInTheDocument();
    const loiGoi = hamFetch.mock.calls.find(([url]) => String(url).includes('/api/export/'));
    expect(loiGoi[0]).toContain('/api/export/shopee/excel?');
    expect(loiGoi[0]).toContain('granularity=month');
    expect(loiGoi[0]).toContain('period=2026-07');
    expect(loiGoi[0]).toContain('product_code=M15');
    expect(loiGoi[1].headers.Authorization).toBe('Bearer token-that');
  });

  it('không còn khung debug, nút test hay JSON thô trên giao diện', async () => {
    const { container } = mo('/dashboard/shopee');
    await theDoanhThu();
    expect(container.querySelector('pre')).toBeNull();
    expect(container.textContent).not.toMatch(/\{"/);
  });
});
