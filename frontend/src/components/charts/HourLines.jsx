import { mau, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';

// Khung vẽ (đơn vị SVG), theo bản thiết kế trang Đối chiếu.
const X_TRAI = 36;
const X_PHAI = 592;
const Y_DAY = 200;
const Y_CAO = 180;

/**
 * Hai (hoặc một) đường tỷ lệ đơn theo giờ, tự vẽ từ trái sang phải khi mở trang.
 * Dùng tỷ lệ (share_pct) để so được dù tổng số đơn của hai sàn khác nhau.
 *
 * Nhận dữ liệu và màu qua props, KHÔNG gọi API.
 *
 * @param {{khoa: string, mau: string, giaTri: number[], vungDuoi?: boolean, tre: number}[]} duong
 *   mỗi đường: 24 giá trị % theo giờ 0..23; `vungDuoi` tô nhẹ vùng dưới đường; `tre` độ trễ chuyển động (ms)
 * @param {string} ariaLabel mô tả cho trình đọc màn hình
 */
export default function HourLines({ duong, ariaLabel }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const lonNhat = Math.max(...duong.flatMap((d) => d.giaTri), 1);
  // Trục đứng chia 3 khoảng bằng nhau, mỗi khoảng là số nguyên %: 12%, 8%, 4%, 0%.
  const yToiDa = Math.max(3, Math.ceil(lonNhat / 3) * 3);
  const buoc = yToiDa / 3;
  const toaDo = (v, gio) => {
    const x = X_TRAI + gio * ((X_PHAI - X_TRAI) / 23);
    const y = Y_DAY - (v / yToiDa) * Y_CAO;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };
  const viTriLuoi = [0, 1, 2, 3].map((k) => ({ y: Y_DAY - (k * Y_CAO) / 3, nhan: `${k * buoc}%` }));
  const nhanTrucX = [0, 3, 6, 9, 12, 15, 18, 21, 23];

  return (
    <svg viewBox="0 0 612 240" role="img" aria-label={ariaLabel} style={{ width: '100%', height: 'auto', marginTop: 10, display: 'block' }}>
      {viTriLuoi.map((l, k) => (
        <g key={l.nhan}>
          <line x1={X_TRAI} y1={l.y} x2={X_PHAI} y2={l.y} stroke={k === 0 ? mau.vienChip : mau.vienTrong} />
          <text x={X_TRAI - 6} y={l.y + 4} textAnchor="end" fontSize={coChu.nhan} fill={mau.chuMo}>
            {l.nhan}
          </text>
        </g>
      ))}
      {duong
        .filter((d) => d.vungDuoi)
        .map((d) => (
          <polygon
            key={`vung-${d.khoa}`}
            points={`${X_TRAI},${Y_DAY} ${d.giaTri.map(toaDo).join(' ')} ${X_PHAI},${Y_DAY}`}
            fill={d.mau}
            style={{ opacity: moc ? 0.08 : 0, transition: kieuChuyen(cd, 'opacity', thoiLuong.vungDuoiDuong, 1600) }}
          />
        ))}
      {duong.map((d) => (
        <polyline
          key={d.khoa}
          data-testid="duong-gio"
          data-duong={d.khoa}
          points={d.giaTri.map(toaDo).join(' ')}
          pathLength="100"
          fill="none"
          stroke={d.mau}
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          style={{ strokeDasharray: 100, strokeDashoffset: moc ? 0 : 100, transition: kieuChuyen(cd, 'stroke-dashoffset', thoiLuong.duongGio, d.tre) }}
        />
      ))}
      {nhanTrucX.map((g) => (
        <text key={g} x={(X_TRAI + g * ((X_PHAI - X_TRAI) / 23)).toFixed(1)} y="222" textAnchor="middle" fontSize={coChu.nhan} fill={mau.chuMo}>
          {g}h
        </text>
      ))}
    </svg>
  );
}
