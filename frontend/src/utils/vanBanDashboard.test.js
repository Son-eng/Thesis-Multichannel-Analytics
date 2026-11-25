import { describe, it, expect } from 'vitest';
import { TOOLTIP_DOANH_THU, tieuDeDoanhThu, chuKyDemRaSoSanh, dongChatLuongDuLieu, dongKyChuaDuNgay, cauKhongSoCaKy } from './vanBanDashboard.js';

describe('Quy tắc 7: kỳ chưa đủ ngày', () => {
  it('tiêu đề khối doanh thu ghi "tính đến DD/MM"', () => {
    expect(tieuDeDoanhThu(false, '2026-08-16')).toBe('Doanh thu tính đến 16/08');
    expect(tieuDeDoanhThu(true, '2026-07-31')).toBe('Doanh thu');
  });

  it('dòng so sánh ghi khoảng ngày kỳ trước lấy nguyên từ API', () => {
    expect(chuKyDemRaSoSanh({ period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-16' })).toBe('so với 01/07 – 16/07');
    expect(chuKyDemRaSoSanh({ period: '2026-08-22', date_from: '2026-08-22', date_to: '2026-08-22' })).toBe('so với 22/08');
    expect(chuKyDemRaSoSanh(null)).toBe('Không đủ dữ liệu để so sánh');
  });

  it('dòng thông tin kỳ chưa kết thúc nói rõ vì sao cắt', () => {
    const kpi = {
      period: '2026-08',
      current: { date_from: '2026-08-01', date_to: '2026-08-16' },
      previous: { period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-16' },
    };
    expect(dongKyChuaDuNgay('month', kpi)).toBe(
      'Tháng 8/2026 chưa kết thúc: số liệu tính đến 16/08, kỳ trước lấy 01/07 – 16/07 để hai kỳ cùng 16 ngày.',
    );
  });

  it('câu giải thích dùng previous_full.pct_change_if_used của API, không tự tính', () => {
    const kpi = {
      period: '2026-08',
      current: { date_from: '2026-08-01', date_to: '2026-08-16' },
      metrics: { revenue: { pct_change: 34.6 } },
      previous_full: { period: '2026-07', revenue: 1068925905, pct_change_if_used: -21.4 },
    };
    const cau = cauKhongSoCaKy('month', kpi);
    expect(cau).toContain('−21,4%');
    expect(cau).toContain('sai cả chiều tăng giảm');
    expect(cau).toContain('16 ngày');
  });
});

describe('Quy tắc 8: tooltip doanh thu', () => {
  it('ghi rõ NMV sau thuế, không hủy không hoàn, chưa phải lợi nhuận', () => {
    expect(TOOLTIP_DOANH_THU).toBe(
      'Tổng NMV sau thuế của các đơn không bị hủy và không bị hoàn. Đây là doanh thu bán hàng, chưa phải lợi nhuận.',
    );
  });
});

describe('Quy tắc 10: chất lượng dữ liệu', () => {
  it('luôn hiện số dòng unknown, kể cả 0', () => {
    const dong = dongChatLuongDuLieu({ rows_status_unknown: 0, rows_nmv_provisional: null });
    expect(dong[0]).toBe('0 dòng chưa rõ trạng thái đơn, vẫn tính vào doanh thu');
  });

  it('Shopee hiện thêm số dòng NMV tạm tính', () => {
    const dong = dongChatLuongDuLieu({ rows_status_unknown: 7, rows_nmv_provisional: 0 });
    expect(dong).toEqual(['7 dòng chưa rõ trạng thái đơn, vẫn tính vào doanh thu', '0 dòng có NMV tạm tính, chờ đối soát']);
  });

  it('TikTok (rows_nmv_provisional = null) ghi không áp dụng, không hiện 0', () => {
    const dong = dongChatLuongDuLieu({ rows_status_unknown: 0, rows_nmv_provisional: null });
    expect(dong[1]).toBe('NMV tạm tính: không áp dụng với sàn này');
  });

  it('kỳ không có dữ liệu thì ghi "Không có dữ liệu"', () => {
    expect(dongChatLuongDuLieu({ rows_status_unknown: null, rows_nmv_provisional: null })).toEqual(['Không có dữ liệu']);
  });
});
