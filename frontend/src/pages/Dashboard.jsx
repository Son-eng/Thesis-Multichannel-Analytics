import { useParams } from 'react-router-dom';
import PageTitle from '../components/PageTitle.jsx';

/** Tên hiển thị của từng sàn. */
export const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };

/**
 * MỘT trang dashboard dùng chung cho cả hai sàn (route /dashboard/:platform).
 * Hai sàn cùng khuôn, cùng hợp đồng JSON, chỉ khác tham số `platform` (SPEC §13).
 * Lượt 2A: mới có tiêu đề; nội dung dựng ở lượt 2B.
 */
export default function Dashboard() {
  const { platform } = useParams();
  return <PageTitle tieuDe={`Dashboard ${TEN_SAN[platform]}`} />;
}
