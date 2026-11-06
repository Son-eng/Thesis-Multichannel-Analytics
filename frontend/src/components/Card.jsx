import { kieu, khoangCach } from '../theme/tokens.js';
import { useChuyenDong, kieuVao } from '../hooks/useChuyenDong.jsx';

/**
 * Thẻ trắng dùng chung cho mọi khối (viền, bo góc 16, bóng theo tokens).
 * Vì sao có một component: sinh viên đổi giao diện thẻ ở một chỗ, mọi trang đổi theo.
 *
 * @param {number} [thuTu] vị trí trong trình tự mở trang; thẻ sau hiện trễ hơn thẻ trước
 * @param {boolean} [khongChuyenDong] thẻ không tham gia chuyển động vào (ví dụ thẻ nằm trong cửa sổ)
 * @param {string} [tag] thẻ HTML (mặc định section)
 * @param {object} [style] style bổ sung
 */
export default function Card({ children, thuTu = 0, khongChuyenDong = false, tag: Tag = 'section', style, ...conLai }) {
  const cd = useChuyenDong();
  const vao = khongChuyenDong ? {} : kieuVao(cd, thuTu);
  return (
    <Tag
      {...conLai}
      style={{
        ...kieu.the,
        padding: khoangCach.trongThe,
        ...vao,
        ...style,
      }}
    >
      {children}
    </Tag>
  );
}
