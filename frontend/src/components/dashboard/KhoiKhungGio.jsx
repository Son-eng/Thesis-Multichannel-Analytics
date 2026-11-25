import { mau, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import KhoiDuLieu, { KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import HourBars from '../charts/HourBars.jsx';
import { useTaiDuLieu } from '../../hooks/useTaiDuLieu.js';
import { layTheoGio } from '../../api/dashboard.js';
import { dinhDangPhanTram } from '../../utils/format.js';

export default function KhoiKhungGio({ san, muc, thamSo, ky, thuTu }) {
  const tt = useTaiDuLieu(
    () => layTheoGio(san, { ...thamSo, granularity: muc, period: ky }),
    [san, muc, ky, thamSo.shop_name, thamSo.product_code],
  );
  return (
    <Card thuTu={thuTu} aria-label="Đơn hàng theo khung giờ" style={{ flex: '1.3 1 380px', padding: '18px 20px 16px' }}>
      <TieuDeKhoi bieuTuong="clock" vongTron>
        Đơn hàng theo khung giờ
      </TieuDeKhoi>
      <KhoiDuLieu tt={tt} cao={200}>
        {(dl) => {
          if (dl.status === 'no_data') {
            return <KhongCoDuLieu cao={200} />;
          }
          let dinh = dl.items[0];
          dl.items.forEach((g) => {
            if (g.order_count > dinh.order_count) {
              dinh = g;
            }
          });
          const gio = dl.items.map((g) => ({
            gio: g.hour,
            giaTri: g.order_count,
            goiY: `${g.hour}h – ${g.hour + 1}h: ${dinhDangPhanTram(g.share_pct)} số đơn`,
          }));
          return (
            <>
              <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '4px 10px' }}>
                <span className="so" style={{ fontSize: 22, fontWeight: 600 }}>
                  {dinh.hour}h – {dinh.hour + 1}h
                </span>
                <span className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
                  giờ cao điểm · {dinhDangPhanTram(dinh.share_pct)} số đơn
                </span>
              </div>
              <HourBars gio={gio} />
            </>
          );
        }}
      </KhoiDuLieu>
    </Card>
  );
}
