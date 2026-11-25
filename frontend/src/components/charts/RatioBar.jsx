import { mau, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';

/** Thanh tỷ lệ nằm ngang; gachNgang dùng cho kỳ trước nguyên tháng, không được dùng để so. */
export default function RatioBar({ nhan, giaTri, tiLe, nen, mauChu = mau.chuChinh, gachNgang = false, tre = 500 }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '150px minmax(0, 1fr) 70px', alignItems: 'center', gap: 10, fontSize: coChu.ratNho }}>
      <span style={{ color: mauChu, textDecoration: gachNgang ? 'line-through' : 'none' }}>{nhan}</span>
      <div style={{ height: 8, borderRadius: 4, background: mau.thanhNen, overflow: 'hidden' }}>
        <div
          data-testid="thanh-ty-le"
          style={{ height: 8, width: `${moc ? tiLe : 0}%`, borderRadius: 4, background: nen, transition: kieuChuyen(cd, 'width', thoiLuong.thanhTyTrong, tre) }}
        />
      </div>
      <span className="so" style={{ textAlign: 'right', fontWeight: 600, color: mauChu }}>
        {giaTri}
      </span>
    </div>
  );
}
