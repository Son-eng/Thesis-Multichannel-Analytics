import { mau, chuDao, coChu } from '../../theme/tokens.js';
import { thoiLuong, troGiup } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import { rutGonTien } from '../../utils/format.js';

/**
 * Cột doanh thu từng ngày. Mọi cột xám nhạt; ngày cao nhất tô màu chủ đạo chuyển sắc và có nhãn giá trị.
 * Cột mọc lần lượt, nhãn của cột cao nhất hiện cuối cùng.
 *
 * Nhận dữ liệu qua props, KHÔNG gọi API.
 *
 * @param {{khoa: string, nhan: string, giaTri: number, goiY: string}[]} ngay mỗi phần tử một ngày;
 *   `khoa` duy nhất (ví dụ ngày ISO), `nhan` là chữ ghi dưới cột ("1", "2"... hoặc "16/08")
 * @param {number} [chieuCao] chiều cao vùng cột (px)
 * @param {number} [nhanMoiN] cứ N cột ghi một nhãn (ngoài cột đầu và cột cao nhất); nhiều cột thì tăng lên cho khỏi đè
 */
export default function DailyBars({ ngay, chieuCao = 150, nhanMoiN = 5 }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  let viTriDinh = 0;
  ngay.forEach((d, i) => {
    if (d.giaTri > ngay[viTriDinh].giaTri) {
      viTriDinh = i;
    }
  });
  const lonNhat = Math.max(ngay[viTriDinh] ? ngay[viTriDinh].giaTri : 0, 1);
  const coNhan = (i) => i === 0 || (i + 1) % nhanMoiN === 0 || i === viTriDinh;

  return (
    <div>
      <div style={{ position: 'relative', marginTop: 14, height: chieuCao, display: 'flex', alignItems: 'flex-end', gap: 3 }}>
        {ngay.map((d, i) => {
          const laDinh = i === viTriDinh;
          // Số 0 thật vẫn vẽ cột thấp nhất (3%), không biến mất.
          const cao = moc ? Math.max(3, (d.giaTri / lonNhat) * 82) : 0;
          return (
            <div key={d.khoa} title={d.goiY} style={{ flex: '1 1 0', minWidth: 0, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', position: 'relative' }}>
              {laDinh ? (
                <span
                  className="so"
                  style={{ position: 'absolute', bottom: `calc(${cao}% + 6px)`, fontSize: coChu.nhan, fontWeight: 600, color: chuDao.dam, whiteSpace: 'nowrap', opacity: moc ? 1 : 0, transition: kieuChuyen(cd, 'opacity', thoiLuong.nhanDinh, 200 + ngay.length * troGiup.giuaNgay + 200) }}
                >
                  {rutGonTien(d.giaTri)}
                </span>
              ) : null}
              <div
                data-testid={laDinh ? 'cot-ngay-dinh' : 'cot-ngay'}
                style={{
                  width: '100%',
                  maxWidth: 22,
                  height: `${cao}%`,
                  borderRadius: 6,
                  background: laDinh ? `linear-gradient(180deg, ${chuDao.chinh} 0%, ${chuDao.sang} 100%)` : mau.cotXam,
                  transition: kieuChuyen(cd, 'height', thoiLuong.cotNgay, 200 + i * troGiup.giuaNgay),
                }}
              />
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 3, marginTop: 6, fontSize: coChu.nhan, color: mau.chuMo }}>
        {ngay.map((d, i) => (
          <div key={d.khoa} className="so" style={{ flex: '1 1 0', minWidth: 0, textAlign: 'center', whiteSpace: 'nowrap', fontWeight: i === viTriDinh ? 700 : 400, color: i === viTriDinh ? mau.chuChinh : mau.chuMo }}>
            {coNhan(i) ? d.nhan : ''}
          </div>
        ))}
      </div>
    </div>
  );
}
