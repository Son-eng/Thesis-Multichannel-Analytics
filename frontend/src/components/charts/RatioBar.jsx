import { mau, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';

/**
 * Một thanh tỷ lệ nằm ngang kèm nhãn bên trái và giá trị bên phải.
 * Thanh kéo dài ra từ trái. Dùng cho "Kỳ này / Kỳ trước / Cả tháng trước" và thanh tỷ trọng.
 *
 * Nhận dữ liệu và màu qua props, KHÔNG gọi API.
 *
 * @param {string} nhan chữ bên trái
 * @param {string} giaTri chữ bên phải (đã định dạng)
 * @param {number} tiLe độ dài thanh 0..100 (% so với thanh dài nhất do nơi gọi tính)
 * @param {string} nen màu hoặc gradient của thanh
 * @param {string} [mauChu] màu chữ nhãn và giá trị
 * @param {boolean} [gachNgang] gạch ngang chữ (dùng cho kỳ trước nguyên tháng không được dùng để so)
 * @param {number} [tre] độ trễ chuyển động (ms)
 */
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
