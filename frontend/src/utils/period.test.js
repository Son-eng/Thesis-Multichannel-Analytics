import { describe, it, expect } from 'vitest';
import {
  maKyChuaNgay,
  ngayDauKy,
  ngayCuoiKy,
  kyTruocCua,
  kyDayDu,
  nhanKy,
  danhSachKy,
  maKyHopLe,
} from './period.js';

describe('mã kỳ', () => {
  it('kỳ chứa một ngày theo từng mức', () => {
    expect(maKyChuaNgay('day', '2026-08-16')).toBe('2026-08-16');
    expect(maKyChuaNgay('month', '2026-08-16')).toBe('2026-08');
    expect(maKyChuaNgay('quarter', '2026-08-16')).toBe('2026-Q3');
    expect(maKyChuaNgay('year', '2026-08-16')).toBe('2026');
  });

  it('ngày đầu và ngày cuối của kỳ', () => {
    expect(ngayDauKy('quarter', '2026-Q3')).toBe('2026-07-01');
    expect(ngayCuoiKy('quarter', '2026-Q3')).toBe('2026-09-30');
    expect(ngayCuoiKy('month', '2026-02')).toBe('2026-02-28');
    expect(ngayCuoiKy('year', '2026')).toBe('2026-12-31');
  });

  it('kỳ trước', () => {
    expect(kyTruocCua('month', '2026-01')).toBe('2025-12');
    expect(kyTruocCua('quarter', '2026-Q1')).toBe('2025-Q4');
    expect(kyTruocCua('day', '2026-03-01')).toBe('2026-02-28');
    expect(kyTruocCua('year', '2026')).toBe('2025');
  });

  it('kiểm tra định dạng', () => {
    expect(maKyHopLe('month', '2026-13')).toBe(false);
    expect(maKyHopLe('quarter', '2026-Q5')).toBe(false);
    expect(maKyHopLe('year', '26')).toBe(false);
    expect(maKyHopLe('month', '2026-08')).toBe(true);
  });
});

describe('kỳ đủ ngày dùng MAX(order_date) của dữ liệu, không dùng ngày hôm nay (SPEC §9.2)', () => {
  it('tháng 8 chưa đủ khi dữ liệu đến 16/08', () => {
    expect(kyDayDu('month', '2026-08', '2026-08-16')).toBe(false);
    expect(kyDayDu('month', '2026-07', '2026-08-16')).toBe(true);
  });
});

describe('danh sách kỳ cho ô chọn', () => {
  it('Shopee theo tháng: tháng 8 có dấu *, mới nhất xếp đầu', () => {
    const ds = danhSachKy('month', '2026-07-01', '2026-08-16');
    expect(ds.map((k) => k.key)).toEqual(['2026-08', '2026-07']);
    expect(ds[0].label).toBe('Tháng 8/2026 *');
    expect(ds[1].label).toBe('Tháng 7/2026');
  });

  it('TikTok theo quý và năm', () => {
    expect(danhSachKy('quarter', '2026-01-01', '2026-08-23').map((k) => k.key)).toEqual(['2026-Q3', '2026-Q2', '2026-Q1']);
    expect(danhSachKy('year', '2026-01-01', '2026-08-23')).toHaveLength(1);
    expect(nhanKy('quarter', '2026-Q3')).toBe('Quý 3/2026');
  });

  it('theo ngày: đủ số ngày giữa hai đầu', () => {
    expect(danhSachKy('day', '2026-07-01', '2026-08-16')).toHaveLength(47);
  });
});
