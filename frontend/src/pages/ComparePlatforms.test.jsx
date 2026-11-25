import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ComparePlatforms from './ComparePlatforms.jsx';

function mo(duongDan = '/compare') {
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <ComparePlatforms />
    </MemoryRouter>,
  );
}

async function chuaTai() {
  const canh = await screen.findByTestId('canh-tiktok');
  await waitFor(() => expect(canh.textContent).toMatch(/\d\.\d{3}/));
  return canh;
}

describe('trang Đối chiếu: không cộng gộp hai sàn (quy tắc 9)', () => {
  it('không có chữ "Tổng hai sàn" và không có ô nào là "Tổng" kèm số tiền', async () => {
    const { container } = mo();
    await chuaTai();
    const chu = container.textContent;
    expect(chu).not.toContain('Tổng hai sàn');
    expect(chu).not.toMatch(/Tổng[^.]{0,40}\d{1,3}(\.\d{3})+ ?đ/);
    expect(screen.queryByText(/^Tổng/)).not.toBeInTheDocument();
  });

  it('có đúng hai thẻ doanh thu, Shopee và TikTok Shop, mỗi thẻ có số riêng', async () => {
    mo();
    const tiktok = await chuaTai();
    const shopee = screen.getByTestId('canh-shopee');
    await waitFor(() => expect(shopee.textContent).toContain('840.035.154'));
    expect(tiktok.textContent).toContain('863.491.460');
    expect(shopee.textContent).toContain('▲ +34,6%');
    expect(tiktok.textContent).toContain('▲ +49,0%');
    expect(shopee.textContent).toContain('so với 01/07 – 16/07: 624.277.755 đ');
    expect(tiktok.textContent).toContain('so với 01/07 – 23/07: 579.379.192 đ');
  });
});

describe('banner', () => {
  it('nói rõ mỗi sàn có dữ liệu đến ngày nào (từ hai data_max_date)', async () => {
    mo();
    const banner = await screen.findByRole('note');
    await waitFor(() => expect(banner.textContent).toContain('Shopee đến 16/08, TikTok Shop đến 23/08'));
    expect(banner.textContent).toContain('so với kỳ trước của chính nó');
    expect(banner.textContent).toContain('16 và 23 ngày');
  });

  it('kỳ chỉ TikTok có dữ liệu: banner nói Shopee chưa có dữ liệu và giải thích không phải 0 đồng', async () => {
    mo('/compare?ky=2026-03');
    const banner = await screen.findByRole('note');
    await waitFor(() => expect(banner.textContent).toContain('Shopee chưa có dữ liệu'));
    expect(banner.textContent).toContain('thay vì 0 đồng');
  });
});

describe('chọn 2026-03: cánh Shopee không có dữ liệu, cánh TikTok vẫn có số', () => {
  it('cánh Shopee hiện "Không có dữ liệu", không hiện 0', async () => {
    mo('/compare?ky=2026-03');
    const tiktok = await screen.findByTestId('canh-tiktok');
    await waitFor(() => expect(tiktok.textContent).toContain('1.459.153.482'));
    const shopee = screen.getByTestId('canh-shopee');
    expect(shopee.textContent).toContain('Không có dữ liệu');
    expect(shopee.textContent).not.toMatch(/(^|\D)0 đ/);
    const hang = screen.getByTestId('hang-cancel_rate');
    expect(hang.textContent).toContain('Không có dữ liệu');
    expect(hang.textContent).toMatch(/\d+,\d%/);
  });

  it('bảng sản phẩm: cột Shopee ghi "Không có dữ liệu", cột Bán trên ghi "Chưa so được"', async () => {
    mo('/compare?ky=2026-03');
    const bang = await screen.findByLabelText('Theo mã sản phẩm');
    const dong = (await within(bang).findByText('M15')).closest('tr');
    expect(dong.textContent).toContain('Không có dữ liệu');
    expect(dong.textContent).toContain('Chưa so được');
  });

  it('khung giờ chỉ vẽ một đường và ghi Shopee không có dữ liệu', async () => {
    const { container } = mo('/compare?ky=2026-03');
    await waitFor(() => expect(container.querySelectorAll('[data-testid="duong-gio"]').length).toBe(1));
    expect(screen.getByText('Shopee: không có dữ liệu trong kỳ này.')).toBeInTheDocument();
  });
});

describe('bảng chỉ số hai cánh', () => {
  it('có đủ năm hàng và KHÔNG có hàng Doanh thu; thanh ngang chỉ vẽ cho ba tỷ lệ (hai cánh mỗi hàng)', async () => {
    const { container } = mo();
    await chuaTai();
    ['order_count', 'aov', 'cancel_rate', 'return_rate', 'affiliate_share'].forEach((k) => {
      expect(screen.getByTestId(`hang-${k}`)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('hang-revenue')).not.toBeInTheDocument();
    await waitFor(() => expect(container.querySelectorAll('[data-testid="thanh-hai-canh"]').length).toBe(6));
    ['order_count', 'aov'].forEach((k) => {
      expect(within(screen.getByTestId(`hang-${k}`)).queryAllByTestId('thanh-hai-canh')).toHaveLength(0);
    });
  });

  it('thay đổi của tỷ lệ ghi "điểm %", của số đơn ghi "%", mỗi sàn so với kỳ trước của chính nó', async () => {
    mo();
    await chuaTai();
    const huy = screen.getByTestId('hang-cancel_rate');
    expect(huy.textContent).toContain('điểm %');
    const don = screen.getByTestId('hang-order_count');
    expect(don.textContent).toMatch(/[▲▼] [+−]\d+,\d%/);
  });

  it('Shopee tháng 7 (không có kỳ trước): ghi "Không đủ dữ liệu để so sánh", TikTok vẫn có mức thay đổi', async () => {
    mo('/compare?ky=2026-07');
    await screen.findByTestId('canh-tiktok');
    const shopee = screen.getByTestId('canh-shopee');
    await waitFor(() => expect(shopee.textContent).toContain('Không đủ dữ liệu để so sánh'));
    expect(shopee.textContent).not.toContain('%');
    const tiktok = screen.getByTestId('canh-tiktok');
    await waitFor(() => expect(tiktok.textContent).toContain('▲ +43,9%'));
  });
});

describe('bảng theo sản phẩm', () => {
  it('B3, M22, M23 được đánh dấu "Chỉ TikTok Shop"', async () => {
    mo();
    const bang = await screen.findByLabelText('Theo mã sản phẩm');
    for (const ma of ['B3', 'M22', 'M23']) {
      const dong = (await within(bang).findByText(ma)).closest('tr');
      expect(within(dong).getByText('Chỉ TikTok Shop')).toBeInTheDocument();
      expect(dong.textContent).toContain('Không bán');
      expect(dong.textContent).not.toMatch(/(^|\D)0 đ/);
    }
    const m15 = (await within(bang).findByText('M15')).closest('tr');
    expect(within(m15).getByText('Cả hai sàn')).toBeInTheDocument();
  });

  it('bộ lọc "Chỉ TikTok Shop" chỉ giữ ba mã đó; "Chỉ Shopee" báo không có mã nào', async () => {
    mo();
    const bang = await screen.findByLabelText('Theo mã sản phẩm');
    await within(bang).findByText('M15');
    await userEvent.click(within(bang).getByRole('button', { name: 'Chỉ TikTok Shop' }));
    expect(within(bang).queryByText('M15')).not.toBeInTheDocument();
    ['B3', 'M22', 'M23'].forEach((ma) => expect(within(bang).getByText(ma)).toBeInTheDocument());
    await userEvent.click(within(bang).getByRole('button', { name: 'Chỉ Shopee' }));
    expect(within(bang).getByText('Không có mã nào chỉ bán trên Shopee')).toBeInTheDocument();
    await userEvent.click(within(bang).getByRole('button', { name: 'Tất cả' }));
    expect(within(bang).getByText('M15')).toBeInTheDocument();
  });
});

describe('biểu đồ khung giờ', () => {
  it('vẽ hai đường theo share_pct, màu hai sàn', async () => {
    const { container } = mo();
    await waitFor(() => expect(container.querySelectorAll('[data-testid="duong-gio"]').length).toBe(2));
    const khoa = Array.from(container.querySelectorAll('[data-testid="duong-gio"]')).map((e) => e.getAttribute('data-duong'));
    expect(khoa).toEqual(['shopee', 'tiktok']);
    expect(screen.getByText(/Shopee · cao điểm \d+h – \d+h/)).toBeInTheDocument();
  });
});

describe('đổi kỳ', () => {
  it('chọn Tháng 7/2026 thì banner và số liệu đổi theo', async () => {
    mo();
    await waitFor(() => expect(screen.getByRole('note').textContent).toContain('chưa kết thúc'));
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Kỳ' }), '2026-07');
    await waitFor(() => expect(screen.getByRole('note').textContent).toContain('đã đủ ngày'));
    await waitFor(() => expect(screen.getByTestId('canh-tiktok').textContent).toContain('814.595.996'));
  });
});
