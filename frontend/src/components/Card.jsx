import { kieu, khoangCach } from '../theme/tokens.js';
import { useChuyenDong, kieuVao } from '../hooks/useChuyenDong.jsx';

/** Thẻ dùng chung cho mọi khối; thuTu quyết định thẻ hiện trễ bao nhiêu khi mở trang. */
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
