import { describe, it, expect, vi, afterEach } from 'vitest';
import { taiBaoCaoExcel, tenTepTuTieuDe } from './export.js';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

function giaFetch(phanHoi) {
  const ham = vi.fn(async () => phanHoi);
  vi.stubGlobal('fetch', ham);
  return ham;
}

describe('tên tệp từ Content-Disposition', () => {
  it('đọc tên trong ngoặc kép, không ngoặc và dùng tên dự phòng khi thiếu', () => {
    expect(tenTepTuTieuDe('attachment; filename="bao-cao-shopee-2026-08.xlsx"')).toBe('bao-cao-shopee-2026-08.xlsx');
    expect(tenTepTuTieuDe('attachment; filename=a.xlsx')).toBe('a.xlsx');
    expect(tenTepTuTieuDe(null, 'du-phong.xlsx')).toBe('du-phong.xlsx');
  });
});

describe('taiBaoCaoExcel', () => {
  it('chế độ giả lập: báo lỗi rõ, không gọi fetch', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const ham = giaFetch({});
    await expect(taiBaoCaoExcel('shopee', {})).rejects.toMatchObject({ detail: { code: 'mock' } });
    expect(ham).not.toHaveBeenCalled();
  });

  it('máy chủ thật: gọi đúng URL, bỏ tham số rỗng, kèm token, lưu tệp với tên từ tiêu đề', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubEnv('VITE_API_BASE_URL', 'http://may-chu-thu.test:9000');
    window.localStorage.setItem('dak_token', 'token-that');
    const blob = new Blob(['xlsx']);
    const ham = giaFetch({ ok: true, status: 200, headers: { get: () => 'attachment; filename="bao-cao-tiktok-2026-Q3.xlsx"' }, blob: async () => blob });
    const luu = vi.fn();
    const ten = await taiBaoCaoExcel('tiktok', { granularity: 'quarter', period: '2026-Q3', shop_name: '', product_code: 'M15' }, luu);
    expect(ten).toBe('bao-cao-tiktok-2026-Q3.xlsx');
    expect(ham.mock.calls[0][0]).toBe('http://may-chu-thu.test:9000/api/export/tiktok/excel?granularity=quarter&period=2026-Q3&product_code=M15');
    expect(ham.mock.calls[0][1].headers.Authorization).toBe('Bearer token-that');
    expect(luu).toHaveBeenCalledWith(blob, 'bao-cao-tiktok-2026-Q3.xlsx');
  });

  it('lỗi từ máy chủ: ném LoiApi với thông báo của máy chủ, không lưu tệp', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    giaFetch({ ok: false, status: 422, headers: { get: () => null }, json: async () => ({ detail: { code: 'invalid_period', message: 'Mã kỳ sai' } }) });
    const luu = vi.fn();
    await expect(taiBaoCaoExcel('shopee', { period: 'x' }, luu)).rejects.toMatchObject({ status: 422, detail: { message: 'Mã kỳ sai' } });
    expect(luu).not.toHaveBeenCalled();
  });

  it('401: xóa token và phát sự kiện hết phiên', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    window.localStorage.setItem('dak_token', 'het-han');
    giaFetch({ ok: false, status: 401, headers: { get: () => null }, json: async () => ({ detail: { code: 'not_authenticated', message: 'Cần đăng nhập' } }) });
    const nghe = vi.fn();
    window.addEventListener('dak-het-phien', nghe);
    await expect(taiBaoCaoExcel('shopee', {})).rejects.toMatchObject({ status: 401 });
    expect(window.localStorage.getItem('dak_token')).toBeNull();
    expect(nghe).toHaveBeenCalledTimes(1);
    window.removeEventListener('dak-het-phien', nghe);
  });

  it('mất kết nối: báo "Không kết nối được máy chủ"', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('net'); }));
    await expect(taiBaoCaoExcel('shopee', {})).rejects.toMatchObject({ detail: { code: 'network' } });
  });
});
