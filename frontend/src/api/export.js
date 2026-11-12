import { LoiApi, dungMock, layToken, xoaToken, SU_KIEN_HET_PHIEN } from './client.js';

// Xuất báo cáo Excel (UC13, SPEC §12.1.4.4). Tệp nhị phân nên KHÔNG đi qua goiApi (chỉ đọc JSON):
// ở đây gọi fetch riêng, vẫn kèm tiêu đề Authorization và vẫn báo hết phiên khi gặp 401.
// PDF để hướng phát triển: nút PDF không gọi API, chỉ hiện "Chưa hỗ trợ trong bản demo".

/** Tên tệp từ tiêu đề Content-Disposition; không đọc được thì dùng tên dự phòng. */
export function tenTepTuTieuDe(tieuDe, duPhong = 'bao-cao.xlsx') {
  const khop = /filename="?([^";]+)"?/i.exec(tieuDe || '');
  return khop ? khop[1] : duPhong;
}

/** Cho trình duyệt tải một Blob về máy với tên `ten`. Tách riêng để test thay được. */
function luuTepVeMay(blob, ten) {
  const url = URL.createObjectURL(blob);
  const thePhu = document.createElement('a');
  thePhu.href = url;
  thePhu.download = ten;
  document.body.appendChild(thePhu);
  thePhu.click();
  thePhu.remove();
  URL.revokeObjectURL(url);
}

/**
 * Tải báo cáo Excel của một sàn, một kỳ, rồi lưu về máy.
 * @param {'shopee'|'tiktok'} san
 * @param {{granularity, period, shop_name, product_code}} thamSo cùng tham số với dashboard
 * @returns {Promise<string>} tên tệp đã lưu
 * @throws {LoiApi}
 */
export async function taiBaoCaoExcel(san, thamSo, luu = luuTepVeMay) {
  if (dungMock()) {
    throw new LoiApi(0, { code: 'mock', message: 'Xuất Excel cần chạy với máy chủ thật (đặt VITE_USE_MOCK=false)' });
  }
  const p = new URLSearchParams();
  Object.keys(thamSo || {}).forEach((khoa) => {
    if (thamSo[khoa]) {
      p.append(khoa, String(thamSo[khoa]));
    }
  });
  const goc = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const headers = {};
  const token = layToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let phanHoi;
  try {
    phanHoi = await fetch(`${goc}/api/export/${san}/excel?${p.toString()}`, { method: 'GET', headers });
  } catch (loi) {
    throw new LoiApi(0, { code: 'network', message: 'Không kết nối được máy chủ' });
  }
  if (!phanHoi.ok) {
    let noiDung = null;
    try {
      noiDung = await phanHoi.json();
    } catch (loi) {
      noiDung = null;
    }
    if (phanHoi.status === 401) {
      xoaToken();
      window.dispatchEvent(new Event(SU_KIEN_HET_PHIEN));
    }
    throw new LoiApi(phanHoi.status, noiDung && noiDung.detail !== undefined ? noiDung.detail : 'Lỗi máy chủ');
  }
  const ten = tenTepTuTieuDe(phanHoi.headers.get('Content-Disposition'), `bao-cao-${san}.xlsx`);
  luu(await phanHoi.blob(), ten);
  return ten;
}
