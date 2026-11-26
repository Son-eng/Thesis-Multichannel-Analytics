import { describe, it, expect } from 'vitest';
import { xuLyMock, datCauHinhMock } from './handlers.js';

const SAN = ['shopee', 'tiktok'];

function duyet(giaTri, kiemTra, duongDan = '$') {
  if (Array.isArray(giaTri)) {
    giaTri.forEach((v, i) => duyet(v, kiemTra, `${duongDan}[${i}]`));
  } else if (giaTri && typeof giaTri === 'object') {
    kiemTra(giaTri, duongDan);
    Object.keys(giaTri).forEach((k) => duyet(giaTri[k], kiemTra, `${duongDan}.${k}`));
  }
}

describe('compare', () => {
  it('chỉ có hai khóa sàn, KHÔNG có khóa total', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', { granularity: 'month', period: '2026-08' });
    expect(Object.keys(kq)).not.toContain('total');
    expect(kq.shopee).toBeDefined();
    expect(kq.tiktok).toBeDefined();
    const toanBo = JSON.stringify(kq).toLowerCase();
    expect(toanBo).not.toContain('"total"');
  });

  it('mỗi sàn có current/previous riêng, cắt theo MAX(order_date) của chính sàn đó', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', { granularity: 'month', period: '2026-08' });
    expect(kq.shopee.current).toEqual({ date_from: '2026-08-01', date_to: '2026-08-16' });
    expect(kq.shopee.previous.date_to).toBe('2026-07-16');
    expect(kq.tiktok.current).toEqual({ date_from: '2026-08-01', date_to: '2026-08-23' });
    expect(kq.tiktok.previous.date_to).toBe('2026-07-23');
    expect(kq.shopee.data_max_date).toBe('2026-08-16');
    expect(kq.tiktok.data_max_date).toBe('2026-08-23');
  });

  it('không có period thì dùng kỳ chứa ngày dữ liệu mới nhất của cả hai sàn', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', {});
    expect(kq.period).toBe('2026-08');
  });

  it('by_hour đủ 24 phần tử, by_province_top tối đa 10 và không có "Khác"', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', { granularity: 'month', period: '2026-08' });
    SAN.forEach((san) => {
      expect(kq[san].by_hour).toHaveLength(24);
      expect(kq[san].by_province_top.length).toBeLessThanOrEqual(10);
      expect(kq[san].by_province_top.some((t) => t.province === 'Khác')).toBe(false);
    });
  });

  it('B3, M22, M23 chỉ có ở TikTok', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', { granularity: 'month', period: '2026-08' });
    const maShopee = kq.shopee.by_product.map((m) => m.product_code);
    const maTiktok = kq.tiktok.by_product.map((m) => m.product_code);
    ['B3', 'M22', 'M23'].forEach((ma) => {
      expect(maShopee).not.toContain(ma);
      expect(maTiktok).toContain(ma);
    });
  });

  it('chọn 2026-03: nhánh shopee no_data (mọi số null, danh sách rỗng), tiktok vẫn có số', async () => {
    const kq = await xuLyMock('GET', '/api/compare/platforms', { granularity: 'month', period: '2026-03' });
    expect(kq.shopee.status).toBe('no_data');
    expect(kq.shopee.metrics.revenue.value).toBeNull();
    expect(kq.shopee.metrics.cancel_rate.value).toBeNull();
    expect(kq.shopee.by_hour).toEqual([]);
    expect(kq.shopee.by_product).toEqual([]);
    expect(kq.tiktok.status).toBe('ok');
    expect(kq.tiktok.metrics.revenue.value).toBe(1459153482);
  });
});

describe('by-hour', () => {
  it('luôn đủ 24 phần tử, giờ 0 đến 23, share_pct cộng ~100', async () => {
    for (const san of SAN) {
      const kq = await xuLyMock('GET', `/api/${san}/by-hour`, { granularity: 'month', period: '2026-08' });
      expect(kq.items).toHaveLength(24);
      expect(kq.items.map((m) => m.hour)).toEqual(Array.from({ length: 24 }, (_, i) => i));
      expect(kq.items[0].label).toBe('0H - 1H');
      const tong = kq.items.reduce((a, m) => a + m.share_pct, 0);
      expect(Math.abs(tong - 100)).toBeLessThan(1);
    }
  });
});

describe('mọi object có pct_change đều có previous_zero', () => {
  it('quét kpi, top-products, alerts, compare ở nhiều kỳ và mức', async () => {
    const lanGoi = [];
    SAN.forEach((san) => {
      ['2026-08', '2026-07', '2026-04', '2026-03', '2026-Q3', '2026'].forEach((period) => {
        const granularity = period.includes('Q') ? 'quarter' : period.length === 4 ? 'year' : 'month';
        lanGoi.push(['GET', `/api/${san}/kpi`, { granularity, period }]);
        lanGoi.push(['GET', `/api/${san}/top-products`, { granularity, period }]);
      });
      lanGoi.push(['GET', `/api/${san}/alerts`, { granularity: 'month' }]);
      lanGoi.push(['GET', `/api/${san}/alerts`, { granularity: 'day' }]);
    });
    lanGoi.push(['GET', '/api/compare/platforms', { granularity: 'month', period: '2026-08' }]);
    lanGoi.push(['GET', '/api/compare/platforms', { granularity: 'month', period: '2026-03' }]);

    for (const [pt, dd, tham] of lanGoi) {
      const kq = await xuLyMock(pt, dd, tham);
      duyet(kq, (o, duongDan) => {
        if ('pct_change' in o) {
          expect(o, `${dd} ${JSON.stringify(tham)} ${duongDan}`).toHaveProperty('previous_zero');
        }
      });
    }
  });

  it('previous_zero = true thì pct_change = null và không bao giờ có trong alerts', async () => {
    const kq = await xuLyMock('GET', '/api/tiktok/top-products', { granularity: 'month', period: '2026-08' });
    const m22 = kq.items.find((m) => m.product_code === 'M22');
    expect(m22).toBeDefined();
    expect(m22.previous_zero).toBe(true);
    expect(m22.pct_change).toBeNull();
    const canhBao = await xuLyMock('GET', '/api/tiktok/alerts', { granularity: 'month' });
    canhBao.items.forEach((m) => expect(m.previous_zero).toBe(false));
  });
});

describe('alerts tháng', () => {
  it('TikTok có đúng 1 phần tử 2026-04, Shopee 0 phần tử', async () => {
    const t = await xuLyMock('GET', '/api/tiktok/alerts', { granularity: 'month' });
    expect(t.items.map((m) => m.period)).toEqual(['2026-04']);
    const s = await xuLyMock('GET', '/api/shopee/alerts', { granularity: 'month' });
    expect(s.items).toHaveLength(0);
  });
});

describe('các trạng thái của kpi', () => {
  it('insufficient_data: Shopee 2026-07, 2026-Q3, 2026; TikTok 2026-01, 2026', async () => {
    const trường = [
      ['shopee', 'month', '2026-07'],
      ['shopee', 'quarter', '2026-Q3'],
      ['shopee', 'year', '2026'],
      ['tiktok', 'month', '2026-01'],
      ['tiktok', 'year', '2026'],
    ];
    for (const [san, granularity, period] of trường) {
      const k = await xuLyMock('GET', `/api/${san}/kpi`, { granularity, period });
      expect(k.status, `${san} ${period}`).toBe('insufficient_data');
      expect(k.previous).toBeNull();
      expect(k.metrics.revenue.pct_change).toBeNull();
      expect(k.metrics.revenue.previous).toBeNull();
      expect(k.metrics.revenue.value).not.toBeNull();
      expect(k.alert.triggered).toBe(false);
    }
  });

  it('no_data: Shopee mọi kỳ trước 2026-07, ví dụ 2026-03: mọi value là null, không phải 0', async () => {
    const k = await xuLyMock('GET', '/api/shopee/kpi', { granularity: 'month', period: '2026-03' });
    expect(k.status).toBe('no_data');
    ['revenue', 'order_count', 'order_count_all', 'quantity_sold', 'aov', 'cancel_rate', 'return_rate', 'affiliate_share'].forEach((ten) => {
      expect(k.metrics[ten].value, ten).toBeNull();
    });
    const s = await xuLyMock('GET', '/api/shopee/by-hour', { granularity: 'month', period: '2026-03' });
    expect(s.status).toBe('no_data');
  });

  it('kỳ đủ ngày: TikTok 2026-07 không cắt, previous_full là null', async () => {
    const k = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-07' });
    expect(k.period_complete).toBe(true);
    expect(k.previous).toEqual({ period: '2026-06', date_from: '2026-06-01', date_to: '2026-06-30' });
  });

  it('mức ngày không cắt cùng số ngày và daily là null', async () => {
    const k = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'day', period: '2026-08-23' });
    expect(k.previous).toEqual({ period: '2026-08-22', date_from: '2026-08-22', date_to: '2026-08-22' });
    expect(k.daily).toBeNull();
  });

  it('daily: một phần tử cho mỗi ngày của kỳ hiện tại và có số 0 thật được phép', async () => {
    const k = await xuLyMock('GET', '/api/shopee/kpi', { granularity: 'month', period: '2026-08' });
    expect(k.daily).toHaveLength(16);
    expect(k.daily[0]).toMatchObject({ day_index: 1, date: '2026-08-01', previous_date: '2026-07-01' });
    const tong = k.daily.reduce((a, d) => a + d.current, 0);
    expect(tong).toBe(840035154);
  });

  it('kỳ sai định dạng: 422 invalid_period', async () => {
    await expect(xuLyMock('GET', '/api/shopee/kpi', { granularity: 'month', period: '2026-Q9' })).rejects.toMatchObject({
      status: 422,
      detail: { code: 'invalid_period' },
    });
  });
});

describe('revenue-trend', () => {
  it('top_product_codes tối đa 4; by_product đúng thứ tự, thêm một phần tử null, tổng bằng doanh thu kỳ', async () => {
    for (const san of SAN) {
      const kq = await xuLyMock('GET', `/api/${san}/revenue-trend`, { granularity: 'month' });
      expect(kq.top_product_codes.length).toBeLessThanOrEqual(4);
      kq.items.forEach((it) => {
        expect(it.by_product.map((m) => m.product_code)).toEqual([...kq.top_product_codes, null]);
        expect(it.by_product.reduce((a, m) => a + m.revenue, 0)).toBe(it.revenue);
      });
    }
  });

  it('kỳ nằm trong khoảng hỏi nhưng không có dữ liệu thì vẫn có phần tử với revenue null', async () => {
    const kq = await xuLyMock('GET', '/api/shopee/revenue-trend', { granularity: 'month', date_from: '2026-05-01', date_to: '2026-08-16' });
    expect(kq.items.map((m) => m.period)).toEqual(['2026-05', '2026-06', '2026-07', '2026-08']);
    expect(kq.items[0].revenue).toBeNull();
    expect(kq.items[0].by_product).toBeNull();
  });
});

describe('lọc theo gian hàng và mã sản phẩm', () => {
  it('lọc mã M15: doanh thu bằng doanh thu của mã đó', async () => {
    const tong = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-07' });
    const m15 = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-07', product_code: 'M15' });
    expect(m15.metrics.revenue.value).toBe(328663138);
    expect(m15.metrics.revenue.value).toBeLessThan(tong.metrics.revenue.value);
  });

  it('lọc gian hàng: doanh thu nhỏ hơn tổng', async () => {
    const a = await xuLyMock('GET', '/api/tiktok/kpi', { granularity: 'month', period: '2026-07', shop_name: 'Shop A' });
    expect(a.metrics.revenue.value).toBeGreaterThan(0);
    expect(a.metrics.revenue.value).toBeLessThan(814595996);
  });
});

describe('đồng bộ, nạp tệp, đăng nhập, người dùng', () => {
  const admin = { token: 'mock-token-admin.vh' };

  it('POST /sync đặt running, gọi lại trong lúc đó trả 409 sync_running', async () => {
    datCauHinhMock({ thoiGianDongBo: 5000 });
    const kq = await xuLyMock('POST', '/api/sync/tiktok', {}, admin);
    expect(kq.run_ids).toHaveLength(2);
    const tt = await xuLyMock('GET', '/api/sync/status', {}, admin);
    expect(tt.platforms.tiktok.running).toBe(true);
    expect(tt.platforms.shopee.running).toBe(false);
    await expect(xuLyMock('POST', '/api/sync/tiktok', {}, admin)).rejects.toMatchObject({
      status: 409,
      detail: { code: 'sync_running', message: 'TikTok Shop đang có lượt đồng bộ chạy' },
    });
  });

  it('sync/status không bao giờ có giá trị token', async () => {
    const tt = await xuLyMock('GET', '/api/sync/status', {}, admin);
    expect(JSON.stringify(tt).toLowerCase()).not.toContain('access_token');
    expect(JSON.stringify(tt).toLowerCase()).not.toContain('refresh_token');
    expect(tt.shops.filter((s) => s.token_status === 'expiring')).toHaveLength(1);
  });

  it('sync/runs: tổng 137, phân trang, lọc nguồn', async () => {
    const r = await xuLyMock('GET', '/api/sync/runs', { page: 1, page_size: 20 }, admin);
    expect(r.total).toBe(137);
    expect(r.items).toHaveLength(20);
    const f = await xuLyMock('GET', '/api/sync/runs', { source: 'file_manual' }, admin);
    expect(f.items.every((m) => m.source === 'file_manual')).toBe(true);
  });

  it('upload: Shopee không chọn gian hàng -> 400 shop_required', async () => {
    const form = new FormData();
    form.append('file', new File(['a'], 'don-hang.csv'));
    await expect(xuLyMock('POST', '/api/upload/shopee', form, admin)).rejects.toMatchObject({ status: 400, detail: { code: 'shop_required' } });
  });

  it('upload: tên tệp có "thieu-cot" -> 422 missing_columns kèm danh sách cột', async () => {
    const form = new FormData();
    form.append('file', new File(['a'], 'don-hang-thieu-cot.csv'));
    form.append('shop_name', 'Shop C');
    await expect(xuLyMock('POST', '/api/upload/shopee', form, admin)).rejects.toMatchObject({
      status: 422,
      detail: { code: 'missing_columns', missing_columns: ['Mã đơn hàng'] },
    });
  });

  it('upload: tên tệp có "khong-doc-duoc" -> 422 invalid_file, không có danh sách cột', async () => {
    const form = new FormData();
    form.append('file', new File(['a'], 'don-khong-doc-duoc.csv'));
    form.append('shop_name', 'Shop C');
    await expect(xuLyMock('POST', '/api/upload/shopee', form, admin)).rejects.toMatchObject({
      status: 422,
      detail: { code: 'invalid_file', message: 'Tệp không đọc được, không dòng nào được ghi' },
    });
  });

  it('upload thành công trả SyncRun file_manual với bộ đếm chất lượng', async () => {
    const form = new FormData();
    form.append('file', new File(['a'], 'don-hang.csv'));
    form.append('shop_name', 'Shop C');
    const kq = await xuLyMock('POST', '/api/upload/shopee', form, admin);
    expect(kq.source).toBe('file_manual');
    expect(kq.quality.rows_status_unknown).toBe(19);
    expect(kq.quality.rows_sku_fallback).toBe(6);
    expect(kq.triggered_by).toEqual({ id: 1, username: 'admin.vh' });
  });

  it('insights: bật lỗi LLM thì trả 503 llm_unavailable', async () => {
    datCauHinhMock({ llmLoi: true });
    await expect(xuLyMock('POST', '/api/insights/generate', { platform: 'tiktok', granularity: 'month', period: '2026-07' })).rejects.toMatchObject({
      status: 503,
      detail: { code: 'llm_unavailable' },
    });
  });

  it('đăng nhập: sai mật khẩu 401; đúng trả token và user; tài khoản mock là tài khoản giả', async () => {
    await expect(xuLyMock('POST', '/api/auth/login', { username: 'admin.vh', password: 'sai' })).rejects.toMatchObject({
      status: 401,
      detail: { code: 'invalid_credentials' },
    });
    const kq = await xuLyMock('POST', '/api/auth/login', { username: 'quanly.kd', password: 'demo123' });
    expect(kq.user).toEqual({ id: 2, username: 'quanly.kd', role: 'user' });
  });

  it('người dùng: không xóa được chính mình (400), trùng tên 409, user thường bị 403', async () => {
    await expect(xuLyMock('DELETE', '/api/users/1', {}, admin)).rejects.toMatchObject({ status: 400, detail: { code: 'cannot_delete_self' } });
    await expect(xuLyMock('POST', '/api/users', { username: 'admin.vh', password: 'x', role: 'user' }, admin)).rejects.toMatchObject({
      status: 409,
      detail: { code: 'username_taken' },
    });
    await expect(xuLyMock('GET', '/api/users', {}, { token: 'mock-token-quanly.kd' })).rejects.toMatchObject({ status: 403 });
    const ds = await xuLyMock('GET', '/api/users', {}, admin);
    expect(ds.every((u) => !('password' in u))).toBe(true);
  });
});
