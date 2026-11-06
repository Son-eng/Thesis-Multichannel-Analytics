import { describe, it, expect } from 'vitest';
import {
  KHONG_CO_DU_LIEU,
  KHONG_DU_DU_LIEU,
  dinhDangTien,
  dinhDangSo,
  rutGonTien,
  dinhDangPhanTram,
  dinhDangNgay,
  dinhDangThoiDiem,
} from './format.js';
import { taoNhanThayDoi } from './delta.js';

// Mười quy tắc hiển thị (PROMPT_FRONTEND, mục "Quy tắc hiển thị"). Quy tắc 7, 8, 10 test ở lượt 2B.

describe('Quy tắc 1: null -> "Không có dữ liệu", không bao giờ hiện 0 thay cho null', () => {
  it('tiền, số đếm, phần trăm null', () => {
    expect(dinhDangTien(null)).toBe(KHONG_CO_DU_LIEU);
    expect(dinhDangSo(null)).toBe(KHONG_CO_DU_LIEU);
    expect(dinhDangPhanTram(null)).toBe(KHONG_CO_DU_LIEU);
    expect(rutGonTien(null)).toBe(KHONG_CO_DU_LIEU);
    expect(dinhDangTien(undefined)).toBe(KHONG_CO_DU_LIEU);
  });

  it('số 0 thật vẫn hiện 0 (ví dụ một ngày không có đơn trong daily)', () => {
    expect(dinhDangSo(0)).toBe('0');
    expect(dinhDangTien(0)).toBe('0 đ');
    expect(dinhDangPhanTram(0)).toBe('0,0%');
  });

  it('nhãn thay đổi của chỉ số có value null (no_data) là "Không có dữ liệu"', () => {
    const nhan = taoNhanThayDoi({ value: null, previous: null, pct_change: null, previous_zero: false });
    expect(nhan.text).toBe(KHONG_CO_DU_LIEU);
    const nhan2 = taoNhanThayDoi({ value: 5, pct_change: 3 }, { status: 'no_data' });
    expect(nhan2.text).toBe(KHONG_CO_DU_LIEU);
  });
});

describe('Quy tắc 2: insufficient_data -> "Không đủ dữ liệu để so sánh", không hiện −100%', () => {
  it('chữ đúng và không có dấu %', () => {
    const nhan = taoNhanThayDoi({ value: 1068925905, previous: null, pct_change: null, previous_zero: false }, { status: 'insufficient_data' });
    expect(nhan.text).toBe(KHONG_DU_DU_LIEU);
    expect(nhan.text).not.toContain('%');
    expect(nhan.text).not.toContain('100');
  });

  it('pct_change null ở khối ok cũng không hiện số', () => {
    const nhan = taoNhanThayDoi({ value: 10, previous: null, pct_change: null, previous_zero: false });
    expect(nhan.text).toBe(KHONG_DU_DU_LIEU);
  });
});

describe('Quy tắc 3: previous_zero -> "Kỳ trước không có doanh thu" / "không có đơn"', () => {
  it('doanh thu', () => {
    const nhan = taoNhanThayDoi({ value: 31800000, previous: 0, pct_change: null, previous_zero: true });
    expect(nhan.text).toBe('Kỳ trước không có doanh thu');
  });
  it('chỉ số đếm đơn', () => {
    const nhan = taoNhanThayDoi({ value: 12, previous: 0, pct_change: null, previous_zero: true }, { loai: 'don' });
    expect(nhan.text).toBe('Kỳ trước không có đơn');
  });
});

describe('Quy tắc 4: tỷ lệ đổi bằng "điểm %", số tiền và số đơn đổi bằng "%"', () => {
  it('change_pp hiện "▼ 1,4 điểm %"', () => {
    const nhan = taoNhanThayDoi({ value: 28.6, previous: 30, change_pp: -1.4 }, { dang: 'diemPhanTram', tangLaTot: false });
    expect(nhan.text).toBe('▼ 1,4 điểm %');
  });
  it('pct_change hiện "▲ +34,6%" với dấu phẩy thập phân', () => {
    const nhan = taoNhanThayDoi({ value: 840035154, previous: 624277755, pct_change: 34.6, previous_zero: false });
    expect(nhan.text).toBe('▲ +34,6%');
  });
  it('giảm hiện dấu trừ thật (−), không phải gạch nối', () => {
    const nhan = taoNhanThayDoi({ value: 1, previous: 2, pct_change: -30.5, previous_zero: false });
    expect(nhan.text).toBe('▼ −30,5%');
  });
});

describe('Quy tắc 5: màu theo nghĩa tốt / xấu', () => {
  it('doanh thu tăng là tốt, giảm là xấu', () => {
    expect(taoNhanThayDoi({ value: 2, previous: 1, pct_change: 100, previous_zero: false }).tone).toBe('tot');
    expect(taoNhanThayDoi({ value: 1, previous: 2, pct_change: -50, previous_zero: false }).tone).toBe('xau');
  });
  it('tỷ lệ hủy, hoàn tăng là xấu (đỏ), giảm là tốt (xanh)', () => {
    const tuyChon = { dang: 'diemPhanTram', tangLaTot: false };
    expect(taoNhanThayDoi({ value: 32, previous: 30, change_pp: 2 }, tuyChon).tone).toBe('xau');
    expect(taoNhanThayDoi({ value: 28, previous: 30, change_pp: -2 }, tuyChon).tone).toBe('tot');
  });
  it('thay đổi gần bằng 0 là trung tính', () => {
    expect(taoNhanThayDoi({ value: 1, previous: 1, pct_change: 0.0, previous_zero: false }).tone).toBe('trungTinh');
  });
  it('chỉ số không có nghĩa tốt/xấu (tỷ trọng affiliate) là trung tính', () => {
    const nhan = taoNhanThayDoi({ value: 61.8, previous: 60.4, change_pp: 1.4 }, { dang: 'diemPhanTram', tangLaTot: null });
    expect(nhan.tone).toBe('trungTinh');
  });
});

describe('Quy tắc 6: tiền và phần trăm', () => {
  it('tiền đầy đủ chấm ngăn nghìn', () => {
    expect(dinhDangTien(840035154)).toBe('840.035.154 đ');
    expect(dinhDangTien(1908961059)).toBe('1.908.961.059 đ');
  });
  it('tiền rút gọn trên trục biểu đồ', () => {
    expect(rutGonTien(624277755)).toBe('624 tr');
    expect(rutGonTien(1068925905)).toBe('1,07 tỷ');
    expect(rutGonTien(7538502584)).toBe('7,54 tỷ');
  });
  it('phần trăm dùng dấu phẩy thập phân', () => {
    expect(dinhDangPhanTram(34.6)).toBe('34,6%');
  });
  it('ngày và thời điểm', () => {
    expect(dinhDangNgay('2026-08-16')).toBe('16/08/2026');
    expect(dinhDangThoiDiem('2026-08-23T16:40:00+07:00')).toBe('16:40, 23/08');
  });
});
