import { mau, chuDao, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import DeltaBadge from '../DeltaBadge.jsx';
import Icon from '../Icon.jsx';
import { useDemSo } from '../../hooks/useDemSo.js';
import { dinhDangSo, dinhDangThapPhan, KHONG_CO_DU_LIEU } from '../../utils/format.js';

/**
 * Một thẻ chỉ số: biểu tượng, nhãn, số lớn chạy từ giá trị cũ sang giá trị mới, nhãn thay đổi, dòng phụ.
 *
 * @param {number} thuTu vị trí trong trình tự mở trang
 * @param {string} nhan tiêu đề thẻ
 * @param {string} goiY nội dung tooltip ở dấu "i"
 * @param {string} bieuTuong tên biểu tượng
 * @param {number|null} giaTri giá trị (null: kỳ này không có dữ liệu -> ghi "Không có dữ liệu", KHÔNG hiện 0)
 * @param {number} soThapPhan số chữ số thập phân (0 cho tiền và số đơn, 1 cho tỷ lệ)
 * @param {string} [donVi] "đ" hoặc "%"
 * @param {object} nhanThayDoi kết quả taoNhanThayDoi()
 * @param {string[]} dongPhu các dòng chữ nhỏ bên dưới
 * @param {string} testId để test tìm thẻ
 */
export default function TheChiSo({ thuTu, nhan, goiY, bieuTuong, giaTri, soThapPhan = 0, donVi, nhanThayDoi, dongPhu, testId }) {
  const dangHien = useDemSo(giaTri);
  let chuSo = KHONG_CO_DU_LIEU;
  if (giaTri !== null && dangHien !== null) {
    chuSo = soThapPhan === 0 ? dinhDangSo(dangHien) : dinhDangThapPhan(dangHien, soThapPhan);
  }
  const coSo = giaTri !== null;

  return (
    <Card thuTu={thuTu} data-testid={testId} aria-label={nhan} style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: mau.chuPhu, fontSize: coChu.nho, fontWeight: 500 }}>
        <span style={{ width: 26, height: 26, borderRadius: 8, background: chuDao.nhatHon, color: chuDao.chinh, display: 'grid', placeItems: 'center' }}>
          <Icon ten={bieuTuong} kichThuoc={14} doDay={1.6} />
        </span>
        <span style={{ flex: '1 1 auto' }}>{nhan}</span>
        <span
          title={goiY}
          style={{ width: 16, height: 16, borderRadius: '50%', border: `1.3px solid ${mau.chuMo}`, color: mau.chuMo, fontSize: 10, fontWeight: 600, display: 'grid', placeItems: 'center', cursor: 'help' }}
        >
          i
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 10px' }}>
        <span className="so" style={{ fontSize: coSo ? coChu.soLon : 18, fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
          {chuSo}
          {coSo && donVi ? <span style={{ fontSize: 15, fontWeight: 500, color: mau.chuDonVi, marginLeft: 4 }}>{donVi}</span> : null}
        </span>
        {nhanThayDoi && coSo ? <DeltaBadge nhan={nhanThayDoi} /> : null}
      </div>
      {dongPhu.map((dong) => (
        <div key={dong} className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
          {dong}
        </div>
      ))}
    </Card>
  );
}
