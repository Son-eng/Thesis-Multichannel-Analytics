// Biểu đồ nhiệt khung giờ đặt hàng

import { mau, chuDao, coChu } from '../../theme/tokens.js';
import { thoiLuong, troGiup } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';

/** 24 cột theo khung giờ, giờ cao điểm tô màu chủ đạo. */
export default function HourBars({ gio, chieuCao = 130 }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  let viTriDinh = 0;
  gio.forEach((g, i) => {
    if (g.giaTri > gio[viTriDinh].giaTri) {
      viTriDinh = i;
    }
  });
  const lonNhat = Math.max(gio[viTriDinh] ? gio[viTriDinh].giaTri : 0, 1);

  return (
    <div>
      <div style={{ marginTop: 14, height: chieuCao, display: 'flex', alignItems: 'flex-end', gap: 3 }}>
        {gio.map((g, i) => (
          <div
            key={g.gio}
            title={g.goiY}
            data-testid={i === viTriDinh ? 'cot-gio-dinh' : 'cot-gio'}
            style={{
              flex: '1 1 0',
              minWidth: 0,
              height: `${moc ? Math.max(3, (g.giaTri / lonNhat) * 100) : 0}%`,
              borderRadius: 4,
              background: i === viTriDinh ? `linear-gradient(180deg, ${chuDao.chinh} 0%, ${chuDao.sang} 100%)` : mau.cotXam,
              transition: kieuChuyen(cd, 'height', thoiLuong.cotNgay, 800 + i * troGiup.giuaGio),
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 3, marginTop: 6, fontSize: coChu.nhan, color: mau.chuMo }}>
        {gio.map((g) => (
          <div key={g.gio} className="so" style={{ flex: '1 1 0', minWidth: 0, textAlign: 'center' }}>
            {g.gio % 3 === 0 ? `${g.gio}h` : ''}
          </div>
        ))}
      </div>
    </div>
  );
}
