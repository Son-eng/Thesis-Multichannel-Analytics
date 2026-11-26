import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChipNgay from './ChipNgay.jsx';

function ve(khiDoi = vi.fn()) {
  render(<ChipNgay nhan="Kỳ" giaTri="2026-08-14" khiDoi={khiDoi} ngayMin="2026-07-01" ngayMax="2026-08-16" />);
  return khiDoi;
}

function moLich() {
  fireEvent.mouseDown(screen.getByLabelText('Kỳ'));
  fireEvent.click(screen.getByLabelText('Kỳ'));
}

describe('ChipNgay', () => {
  it('hiện ngày đang chọn theo kiểu dd/mm/yyyy', () => {
    ve();
    expect(screen.getByLabelText('Kỳ')).toHaveValue('14/08/2026');
  });

  it('chọn một ngày trên lịch thì trả về mã ngày YYYY-MM-DD', () => {
    const khiDoi = ve();
    moLich();
    const o = document.querySelector('td[title="2026-08-10"] .ant-picker-cell-inner');
    expect(o).not.toBeNull();
    fireEvent.click(o);
    expect(khiDoi).toHaveBeenCalledWith('2026-08-10');
  });

  it('ngày ngoài khoảng dữ liệu bị khóa, bấm vào không đổi kỳ', () => {
    const khiDoi = ve();
    moLich();
    const sauKhoang = document.querySelector('td[title="2026-08-20"]');
    expect(sauKhoang).not.toBeNull();
    expect(sauKhoang).toHaveClass('ant-picker-cell-disabled');
    fireEvent.click(sauKhoang.querySelector('.ant-picker-cell-inner'));
    expect(khiDoi).not.toHaveBeenCalled();
  });
});
