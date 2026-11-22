import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import StackedRibbonChart from './StackedRibbonChart.jsx';

// Dữ liệu tự dựng, không gọi API. Màu dùng từ khóa CSS (test không được viết mã hex).
const DANH_SACH_LOP = [
  { ma: 'M15', nhan: 'M15', mau: 'navy' },
  { ma: null, nhan: 'Mã khác', mau: 'teal' },
];

function tao(soNgay, dau = 1) {
  return Array.from({ length: soNgay }, (_, i) => {
    const d = String(dau + i).padStart(2, '0');
    const tong = 30000000 + (i % 7) * 4000000;
    return {
      key: `2026-08-${d}`,
      nhanNgan: `${d}/08`,
      nhanDayDu: `${d}/08/2026`,
      tong,
      daDu: true,
      lop: [
        { ma: 'M15', doanhThu: tong * 0.6 },
        { ma: null, doanhThu: tong * 0.4 },
      ],
    };
  });
}

function ve(thang, rieng = {}) {
  return render(<StackedRibbonChart thang={thang} danhSachLop={DANH_SACH_LOP} kyDangChon={thang[thang.length - 1].key} ariaLabel="Doanh thu" donVi="ngày" {...rieng} />);
}

// jsdom không có bố cục: giả lập khung rộng 720 để tọa độ chuột (clientX) trùng tọa độ SVG.
function gaKhung() {
  return vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ left: 0, top: 0, right: 720, bottom: 286, width: 720, height: 286, x: 0, y: 0, toJSON() {} });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('StackedRibbonChart — phóng to / thu nhỏ', () => {
  it('ít cột (mức tháng, quý, năm) thì không có nút phóng to', () => {
    ve(tao(8));
    expect(screen.queryByRole('button', { name: 'Phóng to biểu đồ' })).not.toBeInTheDocument();
  });

  it('nhiều cột: lúc đầu xem tất cả, chỉ nút Phóng to bấm được', () => {
    ve(tao(31));
    expect(screen.getByRole('button', { name: 'Phóng to biểu đồ' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Thu nhỏ biểu đồ' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Xem tất cả' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Lướt về trước' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Lướt về sau' })).toBeDisabled();
    expect(screen.getByText(/Ctrl \+ lăn chuột/)).toBeInTheDocument();
  });

  it('bấm Phóng to: số cột hiện giảm (31 → 22) và chữ cho biết đang xem đoạn nào', () => {
    const { container } = ve(tao(31));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(22);
    expect(screen.getByText(/Đang xem 22\/31 ngày/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Thu nhỏ biểu đồ' })).toBeEnabled();
  });

  it('phóng to tối đa còn 7 cột rồi nút Phóng to bị khóa', () => {
    const { container } = ve(tao(31));
    const them = screen.getByRole('button', { name: 'Phóng to biểu đồ' });
    for (let i = 0; i < 8; i += 1) {
      if (!them.disabled) {
        fireEvent.click(them);
      }
    }
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(7);
    expect(them).toBeDisabled();
  });

  it('Thu nhỏ và Xem tất cả đưa về đủ 31 cột', () => {
    const { container } = ve(tao(31));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(15);
    fireEvent.click(screen.getByRole('button', { name: 'Xem tất cả' }));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    fireEvent.click(screen.getByRole('button', { name: 'Thu nhỏ biểu đồ' }));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
  });

  it('lướt về sau / về trước đổi đoạn đang xem, không vượt hai đầu', () => {
    ve(tao(31));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    const truoc = screen.getByText(/Đang xem 15\/31/).textContent;
    fireEvent.click(screen.getByRole('button', { name: 'Lướt về sau' }));
    expect(screen.getByText(/Đang xem 15\/31/).textContent).not.toBe(truoc);
    for (let i = 0; i < 10; i += 1) {
      fireEvent.click(screen.getByRole('button', { name: 'Lướt về sau' }));
    }
    expect(screen.getByRole('button', { name: 'Lướt về sau' })).toBeDisabled();
    expect(screen.getByText(/17\/08–31\/08|\(\d\d\/08–31\/08\)/)).toBeInTheDocument();
    for (let i = 0; i < 12; i += 1) {
      fireEvent.click(screen.getByRole('button', { name: 'Lướt về trước' }));
    }
    expect(screen.getByRole('button', { name: 'Lướt về trước' })).toBeDisabled();
    expect(screen.getByText(/\(01\/08–/)).toBeInTheDocument();
  });

  it('Ctrl + lăn chuột phóng to; lăn thường không đổi gì', () => {
    gaKhung();
    const { container } = ve(tao(31));
    const khung = screen.getByTestId('khung-bieu-do');
    fireEvent.wheel(khung, { deltaY: -100, clientX: 360 });
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
    fireEvent.wheel(khung, { deltaY: -100, clientX: 360, ctrlKey: true });
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(22);
    fireEvent.wheel(khung, { deltaY: 100, clientX: 360, ctrlKey: true });
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
  });

  it('đổi dữ liệu (đổi mức, kỳ, bộ lọc) thì xem lại từ đầu', () => {
    const { container, rerender } = ve(tao(31));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(22);
    const khac = tao(31, 1).map((m) => ({ ...m, key: m.key.replace('2026-08', '2026-09') }));
    rerender(<StackedRibbonChart thang={khac} danhSachLop={DANH_SACH_LOP} kyDangChon={khac[30].key} ariaLabel="Doanh thu" donVi="ngày" />);
    expect(container.querySelectorAll('[data-lop="M15"]').length).toBe(31);
  });
});

describe('StackedRibbonChart — khung chú thích khi rê chuột', () => {
  it('rê vào một cột: hiện ngày, tổng, từng mã sản phẩm kèm tỷ trọng; rời chuột thì mất', () => {
    gaKhung();
    ve(tao(8));
    const khung = screen.getByTestId('khung-bieu-do');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    // 8 cột: mỗi ô rộng 88 đơn vị, cột thứ 3 (chỉ số 2) nằm trong khoảng 8+176 .. 8+264.
    fireEvent.mouseMove(khung, { clientX: 220, clientY: 100 });
    const ct = screen.getByRole('tooltip');
    expect(within(ct).getByText('03/08/2026')).toBeInTheDocument();
    expect(within(ct).getByText('Doanh thu')).toBeInTheDocument();
    expect(within(ct).getByText('38.000.000 đ')).toBeInTheDocument(); // 30 tr + 2 × 4 tr
    expect(within(ct).getByText('M15')).toBeInTheDocument();
    expect(within(ct).getByText('Mã khác')).toBeInTheDocument();
    expect(within(ct).getByText('60%')).toBeInTheDocument();
    expect(within(ct).getByText('40%')).toBeInTheDocument();
    fireEvent.mouseLeave(khung);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('kỳ vượt ngưỡng cảnh báo: khung chú thích ghi % giảm', () => {
    gaKhung();
    const thang = tao(8);
    ve(thang, { canhBaoTheoKy: { [thang[2].key]: -39.9 } });
    fireEvent.mouseMove(screen.getByTestId('khung-bieu-do'), { clientX: 220, clientY: 100 });
    expect(within(screen.getByRole('tooltip')).getByText(/Giảm 39,9% so với kỳ trước, vượt ngưỡng cảnh báo/)).toBeInTheDocument();
  });

  it('kỳ chưa đủ ngày được ghi rõ; kỳ không có dữ liệu ghi "Không có dữ liệu" (không phải 0)', () => {
    gaKhung();
    const thang = tao(8);
    thang[2] = { ...thang[2], daDu: false };
    thang[4] = { ...thang[4], tong: null, lop: [] };
    ve(thang);
    const khung = screen.getByTestId('khung-bieu-do');
    fireEvent.mouseMove(khung, { clientX: 220, clientY: 100 });
    expect(within(screen.getByRole('tooltip')).getByText(/03\/08\/2026 · chưa đủ ngày/)).toBeInTheDocument();
    fireEvent.mouseMove(khung, { clientX: 8 + 88 * 4 + 40, clientY: 100 });
    expect(within(screen.getByRole('tooltip')).getByText('Không có dữ liệu')).toBeInTheDocument();
    expect(within(screen.getByRole('tooltip')).queryByText('Doanh thu')).not.toBeInTheDocument();
  });

  it('khung chú thích vẫn đúng cột sau khi phóng to (chỉ số tính theo đoạn đang xem)', () => {
    gaKhung();
    ve(tao(31));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    fireEvent.click(screen.getByRole('button', { name: 'Phóng to biểu đồ' }));
    const dau = screen.getByText(/Đang xem 15\/31 ngày \((\d\d)\/08/).textContent.match(/\((\d\d)\/08/)[1];
    // Cột đầu của đoạn đang xem: ô đầu tiên (chỉ số 0), x vào khoảng 8..56.
    fireEvent.mouseMove(screen.getByTestId('khung-bieu-do'), { clientX: 30, clientY: 100 });
    expect(within(screen.getByRole('tooltip')).getByText(`${dau}/08/2026`)).toBeInTheDocument();
  });
});

describe('StackedRibbonChart — nhãn trên đầu cột theo số cột', () => {
  it('đến 10 cột: kỳ vượt ngưỡng ghi tổng kèm % giảm', () => {
    const thang = tao(8);
    const { container } = ve(thang, { canhBaoTheoKy: { [thang[2].key]: -30.5 } });
    expect(container.textContent).toContain('· −30,5%');
    expect(container.querySelectorAll('[data-testid="cham-canh-bao"]').length).toBe(0);
  });

  it('11–20 cột: vẫn ghi tổng từng cột nhưng bỏ % (xem ở khung chú thích)', () => {
    const thang = tao(15);
    const { container } = ve(thang, { canhBaoTheoKy: { [thang[2].key]: -30.5 } });
    expect(container.textContent).not.toContain('· −');
    expect(container.textContent).toContain('34 tr'); // tổng của cột có i % 7 = 1
    expect(container.querySelectorAll('[data-testid="cham-canh-bao"]').length).toBe(0);
  });

  it('hơn 20 cột (31 ngày): chấm đỏ cho kỳ vượt ngưỡng, chỉ kỳ đang chọn có nhãn tổng', () => {
    const thang = tao(31);
    const { container } = ve(thang, { canhBaoTheoKy: { [thang[2].key]: -30.5, [thang[9].key]: -20 } });
    expect(container.querySelectorAll('[data-testid="cham-canh-bao"]').length).toBe(2);
    expect(container.textContent).not.toContain('· −');
    const nhanTong = Array.from(container.querySelectorAll('text')).filter((t) => /\d+ tr$/.test(t.textContent));
    expect(nhanTong.length).toBe(1);
  });

  it('nhãn ngày không đè: kỳ đang chọn luôn có nhãn, nhãn bước sát nó bị bỏ', () => {
    const thang = tao(31);
    const { container } = ve(thang);
    const nhan = Array.from(container.querySelectorAll('text')).map((t) => t.textContent).filter((t) => /^\d\d\/08$/.test(t));
    expect(nhan).toContain('31/08');
    expect(nhan).not.toContain('30/08');
    expect(nhan).not.toContain('29/08');
  });
});
