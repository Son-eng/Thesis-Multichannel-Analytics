import { mau, nhanThayDoi, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import DeltaBadge from '../DeltaBadge.jsx';
import { useDemSo } from '../../hooks/useDemSo.js';
import { taoNhanThayDoi } from '../../utils/delta.js';
import { dinhDangSo, dinhDangTien, KHONG_CO_DU_LIEU } from '../../utils/format.js';
import { dinhDangKhoang } from '../../utils/period.js';

/** Thẻ doanh thu của một sàn; không có thẻ tổng hai sàn. */
export default function CanhDoanhThu({ ten, mauSan, khoi, thuTu, testId }) {
  const doanhThu = khoi.metrics.revenue;
  const dangHien = useDemSo(doanhThu.value);
  const coSo = khoi.status !== 'no_data' && doanhThu.value !== null;
  const nhan = taoNhanThayDoi(doanhThu, { status: khoi.status, loai: 'doanh_thu' });

  let khoangNgay = KHONG_CO_DU_LIEU;
  if (coSo) {
    khoangNgay = dinhDangKhoang(khoi.current.date_from, khoi.current.date_to);
  }
  let dongPhu = 'Không có dòng dữ liệu nào trong kỳ này';
  if (coSo && doanhThu.previous !== null && khoi.previous) {
    dongPhu = `so với ${dinhDangKhoang(khoi.previous.date_from, khoi.previous.date_to)}: ${dinhDangTien(doanhThu.previous)}`;
  } else if (coSo) {
    dongPhu = 'Chưa có kỳ trước trong dữ liệu';
  }

  return (
    <Card thuTu={thuTu} data-testid={testId} aria-label={`Doanh thu ${ten}`} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 15, fontWeight: 600 }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: mauSan }} />
          {ten}
        </span>
        <span className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
          {khoangNgay}
        </span>
      </div>
      <div style={{ fontSize: coChu.nho, color: mau.chuPhu }}>Doanh thu</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px 10px', marginTop: -6 }}>
        <span className="so" style={{ fontSize: coSo ? coChu.soLonNhat : 22, fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1.15, color: coSo ? mau.chuChinh : mau.chuMo }}>
          {coSo && dangHien !== null ? dinhDangSo(dangHien) : KHONG_CO_DU_LIEU}
          {coSo ? <span style={{ fontSize: 15, fontWeight: 500, color: mau.chuDonVi, marginLeft: 4 }}>đ</span> : null}
        </span>
        {coSo ? (
          <DeltaBadge nhan={nhan} />
        ) : (
          <DeltaBadge nhan={{ text: 'Chưa so được', tone: 'trungTinh', laThongBao: true }} style={{ background: nhanThayDoi.trungTinh.nen }} />
        )}
      </div>
      <div className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
        {dongPhu}
      </div>
    </Card>
  );
}
