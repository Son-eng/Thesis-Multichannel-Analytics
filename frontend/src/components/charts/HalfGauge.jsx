import { mau, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';

const CUNG = 'M 24 120 A 96 96 0 0 1 216 120';
const KHE = 0.6;

/** Bán nguyệt hai đoạn, ví dụ tiếp thị liên kết và shop tự bán. */
export default function HalfGauge({ phanTramA, mauA, mauB, nhanGiua, ariaLabel }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const a = Math.min(100, Math.max(0, phanTramA));
  const doDaiA = Math.max(0, a - KHE);
  const batDauB = Math.min(100, a + KHE);
  const doDaiB = Math.max(0, 100 - batDauB);

  return (
    <svg viewBox="0 0 240 130" role="img" aria-label={ariaLabel} style={{ width: '100%', maxWidth: 300, height: 'auto', display: 'block', margin: '16px auto 0' }}>
      <path d={CUNG} fill="none" stroke={mau.thanhNen} strokeWidth="30" />
      <path
        d={CUNG}
        pathLength="100"
        fill="none"
        stroke={mauA}
        strokeWidth="30"
        style={{ strokeDasharray: moc ? `${doDaiA.toFixed(1)} 100` : '0 100', transition: kieuChuyen(cd, 'stroke-dasharray', thoiLuong.banNguyet, 350) }}
      />
      <path
        d={CUNG}
        pathLength="100"
        fill="none"
        stroke={mauB}
        strokeWidth="30"
        style={{ strokeDasharray: moc ? `0 ${batDauB.toFixed(1)} ${doDaiB.toFixed(1)} 100` : `0 ${batDauB.toFixed(1)} 0 100`, transition: kieuChuyen(cd, 'stroke-dasharray', thoiLuong.banNguyet2, 900) }}
      />
      <text x="120" y="108" textAnchor="middle" fontSize={coChu.ratNho} fill={mau.chuNhan}>
        {nhanGiua}
      </text>
    </svg>
  );
}
