import { describe, it, expect } from 'vitest';
import * as that from './realFigures.js';
import { xuLyMock } from './handlers.js';

describe('realFigures.js khớp SPEC', () => {
  it('§17.2: tổng doanh thu, số đơn, AOV của hai sàn', () => {
    expect(that.TONG_TOAN_BO.shopee.revenue).toBe(1908961059);
    expect(that.TONG_TOAN_BO.shopee.order_count).toBe(1165);
    expect(that.TONG_TOAN_BO.shopee.order_count_all).toBe(1761);
    expect(that.TONG_TOAN_BO.shopee.aov).toBe(1638593);
    expect(that.TONG_TOAN_BO.tiktok.revenue).toBe(7538502584);
    expect(that.TONG_TOAN_BO.tiktok.order_count).toBe(5211);
    expect(that.TONG_TOAN_BO.tiktok.order_count_all).toBe(7526);
    expect(that.TONG_TOAN_BO.tiktok.aov).toBe(1446652);
  });

  it('§17.3: doanh thu từng tháng', () => {
    expect(that.DOANH_THU_THANG.shopee).toEqual({ '2026-07': 1068925905, '2026-08': 840035154 });
    expect(that.DOANH_THU_THANG.tiktok['2026-01']).toBe(963328583);
    expect(that.DOANH_THU_THANG.tiktok['2026-02']).toBe(1056998596);
    expect(that.DOANH_THU_THANG.tiktok['2026-03']).toBe(1459153482);
    expect(that.DOANH_THU_THANG.tiktok['2026-04']).toBe(1014538449);
    expect(that.DOANH_THU_THANG.tiktok['2026-05']).toBe(800122017);
    expect(that.DOANH_THU_THANG.tiktok['2026-06']).toBe(566274001);
    expect(that.DOANH_THU_THANG.tiktok['2026-07']).toBe(814595996);
    expect(that.DOANH_THU_THANG.tiktok['2026-08']).toBe(863491460);
  });

  it('tổng doanh thu các tháng bằng tổng toàn bộ (§17.2 = Σ §17.3)', () => {
    ['shopee', 'tiktok'].forEach((san) => {
      const tong = Object.values(that.DOANH_THU_THANG[san]).reduce((a, b) => a + b, 0);
      expect(tong).toBe(that.TONG_TOAN_BO[san].revenue);
    });
  });

  it('§9.4: kỳ trước đã cắt cùng số ngày và pct_change đúng (Shopee +34,6; TikTok +49,0)', () => {
    expect(that.KY_TRUOC_DA_CAT.shopee.revenue).toBe(624277755);
    expect(that.KY_TRUOC_DA_CAT.shopee.pct_change).toBe(34.6);
    expect(that.KY_TRUOC_DA_CAT.shopee.date_to).toBe('2026-07-16');
    expect(that.KY_TRUOC_DA_CAT.tiktok.revenue).toBe(579379192);
    expect(that.KY_TRUOC_DA_CAT.tiktok.pct_change).toBe(49.0);
    expect(that.KY_TRUOC_DA_CAT.tiktok.date_to).toBe('2026-07-23');
    expect(that.SO_VOI_NGUYEN_THANG.shopee.pct_change_if_used).toBe(-21.4);
    expect(that.SO_VOI_NGUYEN_THANG.tiktok.pct_change_if_used).toBe(6.0);
  });

  it('§9.1: cảnh báo tháng 4 TikTok −30,5% và T5, T6', () => {
    expect(that.CANH_BAO_THANG_4_TIKTOK).toMatchObject({
      period: '2026-04',
      revenue: 1014538449,
      revenue_previous: 1459153482,
      pct_change: -30.5,
    });
    expect(that.TIKTOK_T4_T5_T6.map((m) => m.pct_change)).toEqual([-30.5, -21.1, -29.2]);
    expect(that.NGUONG_CANH_BAO_PCT).toBe(-30.0);
  });

  it('§10: TikTok tháng 7 trong ví dụ prompt LLM', () => {
    const t = that.TIKTOK_THANG_7;
    expect(t.revenue).toBe(814595996);
    expect(t.revenue_previous).toBe(566274001);
    expect(t.pct_change).toBe(43.9);
    expect(t.order_count).toBe(510);
    expect(t.quantity_sold).toBe(513);
    expect(t.aov).toBe(1597247);
    expect(t.top5.map((m) => [m.product_code, m.revenue, m.pct_change])).toEqual([
      ['M15', 328663138, 26.8],
      ['BU01', 252093194, 41.1],
      ['M5', 102675334, 266.7],
      ['M6 Pro', 61734709, 12.7],
      ['M3 Plus', 45314808, 97.4],
    ]);
  });

  it('§17.1: khoảng dữ liệu, 10 mã Shopee và 13 mã TikTok', () => {
    expect(that.KHOANG_DU_LIEU.shopee).toEqual({ min: '2026-07-01', max: '2026-08-16' });
    expect(that.KHOANG_DU_LIEU.tiktok).toEqual({ min: '2026-01-01', max: '2026-08-23' });
    expect(that.MA_SAN_PHAM.shopee).toHaveLength(10);
    expect(that.MA_SAN_PHAM.tiktok).toHaveLength(13);
    expect(that.GIAN_HANG).toEqual({ shopee: ['Shop C'], tiktok: ['Shop A', 'Shop B'] });
  });

  it('§3.3: năm bộ đếm chất lượng khi nạp tệp mẫu', () => {
    expect(that.CHAT_LUONG_TEP_MAU.shopee).toEqual({
      rows_sku_fallback: 6,
      rows_sku_unknown: 0,
      rows_status_unknown: 19,
      rows_province_unmapped: 0,
      rows_product_unmapped: 0,
    });
    expect(Object.values(that.CHAT_LUONG_TEP_MAU.tiktok).every((v) => v === 0)).toBe(true);
  });
});

describe('mock tái hiện đúng số thật qua API', () => {
  it('Shopee 2026-08: doanh thu, kỳ trước đã cắt, +34,6%, cả tháng trước −21,4% (§9.4)', async () => {
    const k = await xuLyMock('GET', '/api/shopee/kpi', { granularity: 'month', period: '2026-08' });
    expect(k.metrics.revenue.value).toBe(840035154);
    expect(k.metrics.revenue.previous).toBe(624277755);
    expect(k.metrics.revenue.pct_change).toBe(34.6);
    expect(k.previous).toEqual({ period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-16' });
    expect(k.current).toEqual({ date_from: '2026-08-01', date_to: '2026-08-16' });
    expect(k.previous_full).toEqual({ period: '2026-07', revenue: 1068925905, pct_change_if_used: -21.4 });
    expect(k.period_complete).toBe(false);
  });

  it('TikTok 2026-08: +49,0% và cả tháng trước +6,0% (§9.4)', async () => {
    const k = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-08' });
    expect(k.metrics.revenue.value).toBe(863491460);
    expect(k.metrics.revenue.previous).toBe(579379192);
    expect(k.metrics.revenue.pct_change).toBe(49.0);
    expect(k.previous_full.revenue).toBe(814595996);
    expect(k.previous_full.pct_change_if_used).toBe(6.0);
  });

  it('TikTok 2026-07: 510 đơn, 513 sản phẩm, AOV 1.597.247, +43,9% (§10)', async () => {
    const k = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-07' });
    expect(k.metrics.revenue.value).toBe(814595996);
    expect(k.metrics.revenue.pct_change).toBe(43.9);
    expect(k.metrics.order_count.value).toBe(510);
    expect(k.metrics.quantity_sold.value).toBe(513);
    expect(k.metrics.aov.value).toBe(1597247);
    expect(k.period_complete).toBe(true);
    expect(k.previous_full).toBeNull();
  });

  it('TikTok 2026-07 top-products: doanh thu và pct_change của 5 mã đầu (§10)', async () => {
    const t = await xuLyMock('GET', '/api/tiktok/top-products', { granularity: 'month', period: '2026-07', limit: 5 });
    expect(t.items.map((m) => [m.product_code, m.revenue, m.pct_change])).toEqual([
      ['M15', 328663138, 26.8],
      ['BU01', 252093194, 41.1],
      ['M5', 102675334, 266.7],
      ['M6 Pro', 61734709, 12.7],
      ['M3 Plus', 45314808, 97.4],
    ]);
  });

  it('TikTok 2026-04: −30,5% và alert.triggered (§9.1)', async () => {
    const k = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-04' });
    expect(k.metrics.revenue.value).toBe(1014538449);
    expect(k.metrics.revenue.previous).toBe(1459153482);
    expect(k.metrics.revenue.pct_change).toBe(-30.5);
    expect(k.alert.triggered).toBe(true);
    expect(k.alert.threshold_pct).toBe(-30.0);
  });

  it('alerts tháng: TikTok đúng 1 phần tử 2026-04, Shopee 0 phần tử (§17.3)', async () => {
    const t = await xuLyMock('GET', '/api/tiktok/alerts', { granularity: 'month' });
    expect(t.items).toHaveLength(1);
    expect(t.items[0]).toMatchObject({
      period: '2026-04',
      previous_period: '2026-03',
      revenue: 1014538449,
      revenue_previous: 1459153482,
      pct_change: -30.5,
      previous_zero: false,
    });
    const s = await xuLyMock('GET', '/api/shopee/alerts', { granularity: 'month' });
    expect(s.items).toHaveLength(0);
  });

  it('tổng doanh thu các tháng trong revenue-trend bằng tổng toàn bộ (§17.2)', async () => {
    const s = await xuLyMock('GET', '/api/shopee/revenue-trend', { granularity: 'month' });
    expect(s.items.reduce((a, m) => a + m.revenue, 0)).toBe(1908961059);
    const t = await xuLyMock('GET', '/api/tiktok/revenue-trend', { granularity: 'month' });
    expect(t.items.reduce((a, m) => a + m.revenue, 0)).toBe(7538502584);
  });
});
