import { LoiApi, dungMock, layToken, xoaToken, SU_KIEN_HET_PHIEN } from './client.js';

// Tệp Excel là nhị phân nên gọi fetch riêng, vẫn kèm Authorization và vẫn báo hết phiên khi gặp 401.

export function tenTepTuTieuDe(tieuDe, duPhong = 'bao-cao.xlsx') {
  const khop = /filename="?([^";]+)"?/i.exec(tieuDe || '');
  return khop ? khop[1] : duPhong;
}

/** Tách riêng để test thay được. */
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
