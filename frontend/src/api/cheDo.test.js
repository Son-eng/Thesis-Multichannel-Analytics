import { describe, it, expect, vi, afterEach } from 'vitest';
import { goiApi } from './client.js';
import { luonGiaLap, nhomCuaDuongDan, NHOM_LUON_GIA_LAP } from './cheDo.js';

// Chế độ giả lập lai (F02 việc B): VITE_USE_MOCK=false vẫn giả lập các nhóm backend chưa có.

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

function giaFetch(thanBang = { shops: ['Shop C'] }) {
  const hamFetch = vi.fn(async () => ({ ok: true, status: 200, json: async () => thanBang }));
  vi.stubGlobal('fetch', hamFetch);
  return hamFetch;
}

describe('danh sách nhóm luôn giả lập', () => {
  it('đúng bốn nhóm theo hợp đồng §12.1 mục 5', () => {
    expect([...NHOM_LUON_GIA_LAP].sort()).toEqual(['auth', 'export', 'insights', 'users']);
  });

  it('nhận ra nhóm từ đường dẫn, bỏ qua query', () => {
    expect(nhomCuaDuongDan('/api/auth/login')).toBe('auth');
    expect(nhomCuaDuongDan('/api/users/3?x=1')).toBe('users');
    expect(nhomCuaDuongDan('/khong-phai-api')).toBeNull();
    expect(luonGiaLap('/api/insights/generate')).toBe(true);
    expect(luonGiaLap('/api/export/report')).toBe(true);
    expect(luonGiaLap('/api/shopee/kpi')).toBe(false);
    expect(luonGiaLap('/api/sync/status')).toBe(false);
    // Tên nhóm phải khớp nguyên đoạn, không khớp tiền tố.
    expect(luonGiaLap('/api/authx/login')).toBe(false);
  });
});

describe('VITE_USE_MOCK=false', () => {
  it('nhóm auth vẫn vào mock: đăng nhập thành công mà không gọi fetch', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const hamFetch = giaFetch();
    const kq = await goiApi('POST', '/api/auth/login', { username: 'admin.vh', password: 'demo123' });
    expect(kq.access_token).toBeTruthy();
    expect(hamFetch).not.toHaveBeenCalled();
  });

  it('nhóm users cũng vào mock', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const hamFetch = giaFetch();
    window.localStorage.setItem('dak_token', 'mock-token-admin.vh');
    const ds = await goiApi('GET', '/api/users');
    expect(Array.isArray(ds)).toBe(true);
    expect(hamFetch).not.toHaveBeenCalled();
  });

  it('/api/shopee/kpi gọi fetch tới VITE_API_BASE_URL', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubEnv('VITE_API_BASE_URL', 'http://may-chu-thu.test:9000');
    const hamFetch = giaFetch({ ok: 1 });
    const kq = await goiApi('GET', '/api/shopee/kpi', { period: '2026-08' });
    expect(kq).toEqual({ ok: 1 });
    expect(hamFetch).toHaveBeenCalledTimes(1);
    const [url, tuyChon] = hamFetch.mock.calls[0];
    expect(url).toBe('http://may-chu-thu.test:9000/api/shopee/kpi?period=2026-08');
    expect(tuyChon.method).toBe('GET');
  });
});

describe('VITE_USE_MOCK=true', () => {
  it('giả lập mọi thứ như cũ, kể cả /api/shopee/kpi, không gọi fetch', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const hamFetch = giaFetch();
    window.localStorage.setItem('dak_token', 'mock-token-admin.vh');
    const kq = await goiApi('GET', '/api/shopee/filters');
    expect(kq.shops).toBeTruthy();
    expect(hamFetch).not.toHaveBeenCalled();
  });
});
