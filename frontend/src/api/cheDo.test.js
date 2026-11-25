import { describe, it, expect, vi, afterEach } from 'vitest';
import { goiApi } from './client.js';
import { luonGiaLap, nhomCuaDuongDan, NHOM_LUON_GIA_LAP } from './cheDo.js';

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
  it('không còn nhóm nào luôn giả lập (auth, users, export, insights đều có backend thật từ 07/11/2026)', () => {
    expect([...NHOM_LUON_GIA_LAP].sort()).toEqual([]);
  });

  it('nhận ra nhóm từ đường dẫn, bỏ qua query', () => {
    expect(nhomCuaDuongDan('/api/auth/login')).toBe('auth');
    expect(nhomCuaDuongDan('/api/users/3?x=1')).toBe('users');
    expect(luonGiaLap('/api/auth/login')).toBe(false);
    expect(luonGiaLap('/api/users')).toBe(false);
    expect(nhomCuaDuongDan('/khong-phai-api')).toBeNull();
    expect(luonGiaLap('/api/export/shopee/excel')).toBe(false);
    expect(luonGiaLap('/api/insights/generate')).toBe(false);
    expect(luonGiaLap('/api/shopee/kpi')).toBe(false);
    expect(luonGiaLap('/api/sync/status')).toBe(false);
    expect(luonGiaLap('/api/authx/login')).toBe(false);
  });
});

describe('VITE_USE_MOCK=false', () => {
  it('nhóm auth đi vào backend thật: đăng nhập gọi fetch tới VITE_API_BASE_URL, không dùng mock', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubEnv('VITE_API_BASE_URL', 'http://may-chu-thu.test:9000');
    const hamFetch = giaFetch({ access_token: 't', token_type: 'bearer', user: { id: 1, username: 'a', role: 'admin' } });
    const kq = await goiApi('POST', '/api/auth/login', { username: 'a', password: 'b' });
    expect(kq.access_token).toBe('t');
    expect(hamFetch).toHaveBeenCalledTimes(1);
    expect(hamFetch.mock.calls[0][0]).toBe('http://may-chu-thu.test:9000/api/auth/login');
  });

  it('nhóm users cũng gọi fetch, kèm tiêu đề Authorization từ token đã lưu', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const hamFetch = giaFetch([]);
    window.localStorage.setItem('dak_token', 'token-that');
    await goiApi('GET', '/api/users');
    expect(hamFetch).toHaveBeenCalledTimes(1);
    expect(hamFetch.mock.calls[0][1].headers.Authorization).toBe('Bearer token-that');
  });

  it('nhóm insights đi vào backend thật: gọi fetch tới /api/insights/generate', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubEnv('VITE_API_BASE_URL', 'http://may-chu-thu.test:9000');
    const hamFetch = giaFetch({ text: 'Nhận định thử', generated_at: 'x', period_complete: true, data_max_date: '2026-08-16' });
    const kq = await goiApi('POST', '/api/insights/generate', { platform: 'shopee', granularity: 'month', period: '2026-08' });
    expect(kq.text).toBe('Nhận định thử');
    expect(hamFetch.mock.calls[0][0]).toBe('http://may-chu-thu.test:9000/api/insights/generate');
    expect(JSON.parse(hamFetch.mock.calls[0][1].body)).toEqual({ platform: 'shopee', granularity: 'month', period: '2026-08' });
  });

  it('401 từ backend thật: xóa token và phát sự kiện hết phiên (trừ lời gọi đăng nhập)', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 401, json: async () => ({ detail: { code: 'not_authenticated', message: 'Cần đăng nhập' } }) })));
    window.localStorage.setItem('dak_token', 'token-het-han');
    const nghe = vi.fn();
    window.addEventListener('dak-het-phien', nghe);
    await expect(goiApi('GET', '/api/shopee/kpi')).rejects.toMatchObject({ status: 401 });
    expect(window.localStorage.getItem('dak_token')).toBeNull();
    expect(nghe).toHaveBeenCalledTimes(1);
    window.localStorage.setItem('dak_token', 'x');
    await expect(goiApi('POST', '/api/auth/login', { username: 'a', password: 'b' })).rejects.toMatchObject({ status: 401 });
    expect(nghe).toHaveBeenCalledTimes(1);
    window.removeEventListener('dak-het-phien', nghe);
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
