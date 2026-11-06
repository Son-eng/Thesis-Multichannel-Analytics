import { mau, kenhBan, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import KhoiDuLieu, { KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import HalfGauge from '../charts/HalfGauge.jsx';
import { useTaiDuLieu } from '../../hooks/useTaiDuLieu.js';
import { layKenhBan } from '../../api/dashboard.js';
import { dinhDangSo, dinhDangPhanTram } from '../../utils/format.js';

function MotKenh({ nhan, mauThanh, phanTram, doanhThu }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: coChu.ratNho, color: mau.chuNhan }}>
        <span style={{ width: 3, height: 12, borderRadius: 2, background: mauThanh }} />
        {nhan}
      </div>
      <div className="so" style={{ fontSize: 20, fontWeight: 600, marginTop: 2 }}>
        {dinhDangPhanTram(phanTram)}
      </div>
      <div className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
        {dinhDangSo(doanhThu)} đ
      </div>
    </div>
  );
}

/** Khối "Doanh thu theo kênh bán": bán nguyệt tiếp thị liên kết / shop tự bán, từ by-affiliate. */
export default function KhoiKenhBan({ san, muc, thamSo, ky, thuTu }) {
  const tt = useTaiDuLieu(
    () => layKenhBan(san, { ...thamSo, granularity: muc, period: ky }),
    [san, muc, ky, thamSo.shop_name, thamSo.product_code],
  );
  return (
    <Card thuTu={thuTu} aria-label="Doanh thu theo kênh bán" style={{ flex: '1 1 340px', padding: '18px 20px' }}>
      <TieuDeKhoi bieuTuong="gauge">Doanh thu theo kênh bán</TieuDeKhoi>
      <KhoiDuLieu tt={tt} cao={200}>
        {(dl) => {
          if (dl.status === 'no_data') {
            return <KhongCoDuLieu cao={200} />;
          }
          return (
            <>
              <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                <MotKenh nhan="Tiếp thị liên kết" mauThanh={kenhBan.lienKet} phanTram={dl.affiliate.share_pct} doanhThu={dl.affiliate.revenue} />
                <MotKenh nhan="Shop tự bán" mauThanh={kenhBan.tuBan} phanTram={dl.self_sold.share_pct} doanhThu={dl.self_sold.revenue} />
              </div>
              <HalfGauge
                phanTramA={dl.affiliate.share_pct}
                mauA={kenhBan.lienKet}
                mauB={kenhBan.tuBan}
                nhanGiua="KOL, KOC, creator"
                ariaLabel={`Tiếp thị liên kết ${dinhDangPhanTram(dl.affiliate.share_pct)}, shop tự bán ${dinhDangPhanTram(dl.self_sold.share_pct)}`}
              />
            </>
          );
        }}
      </KhoiDuLieu>
    </Card>
  );
}
