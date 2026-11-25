import { mau, chuDao, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import Card from '../Card.jsx';
import KhoiDuLieu, { KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import { useTaiDuLieu } from '../../hooks/useTaiDuLieu.js';
import { layTheoTinh } from '../../api/dashboard.js';
import { dinhDangPhanTram } from '../../utils/format.js';

const SO_TINH_RIENG = 5;

function DongTinh({ ten, phanTram, tiLe, mauThanh, mauChu, nghieng, tre }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 54px', gap: '4px 10px', alignItems: 'center', fontSize: coChu.nho }}>
      <span style={{ color: mauChu, fontStyle: nghieng ? 'italic' : 'normal', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ten}</span>
      <span className="so" style={{ textAlign: 'right', fontWeight: 600, color: mauChu }}>
        {dinhDangPhanTram(phanTram)}
      </span>
      <div style={{ gridColumn: '1 / -1', height: 5, borderRadius: 3, background: mau.thanhNen, overflow: 'hidden' }}>
        <div style={{ height: 5, width: `${moc ? tiLe : 0}%`, borderRadius: 3, background: mauThanh, transition: kieuChuyen(cd, 'width', thoiLuong.thanhTyTrong, tre) }} />
      </div>
    </div>
  );
}

/** Nhóm "Khác" luôn cuối; ghi "N tỉnh/thành có đơn", không ghi "x/63". */
export default function KhoiTinh({ san, muc, thamSo, ky, thuTu }) {
  const tt = useTaiDuLieu(
    () => layTheoTinh(san, { ...thamSo, granularity: muc, period: ky }),
    [san, muc, ky, thamSo.shop_name, thamSo.product_code],
  );
  return (
    <Card thuTu={thuTu} aria-label="Doanh thu theo tỉnh thành" style={{ flex: '1 1 320px', padding: '18px 20px 14px' }}>
      <TieuDeKhoi bieuTuong="pin" chuThich={tt.duLieu && tt.duLieu.status === 'ok' ? `${tt.duLieu.province_count} tỉnh/thành có đơn` : undefined}>
        Tỉnh/thành
      </TieuDeKhoi>
      <KhoiDuLieu tt={tt} cao={220}>
        {(dl) => {
          if (dl.status === 'no_data') {
            return <KhongCoDuLieu cao={200} />;
          }
          const tinh = dl.items.filter((m) => !m.is_other);
          const khac = dl.items.find((m) => m.is_other);
          const rieng = tinh.slice(0, SO_TINH_RIENG);
          const conLai = tinh.slice(SO_TINH_RIENG);
          const hang = rieng.map((m) => ({ khoa: m.province, ten: m.province, phanTram: m.share_pct, mauThanh: chuDao.thanhTinh, mauChu: mau.chuChinh, nghieng: false }));
          if (conLai.length > 0) {
            const tong = conLai.reduce((a, m) => a + m.share_pct, 0);
            hang.push({ khoa: 'con-lai', ten: `${conLai.length} tỉnh/thành còn lại`, phanTram: tong, mauThanh: chuDao.thanhPhu, mauChu: mau.chuPhu, nghieng: false });
          }
          if (khac) {
            hang.push({ khoa: 'khac', ten: 'Khác (chưa chuẩn hóa được tên)', phanTram: khac.share_pct, mauThanh: mau.vienChip, mauChu: mau.chuNhan, nghieng: true });
          }
          const lonNhat = Math.max(...hang.map((h) => h.phanTram), 1);
          return (
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 9 }}>
              {hang.map((h, i) => (
                <DongTinh key={h.khoa} ten={h.ten} phanTram={h.phanTram} tiLe={(h.phanTram / lonNhat) * 100} mauThanh={h.mauThanh} mauChu={h.mauChu} nghieng={h.nghieng} tre={900 + i * 60} />
              ))}
            </div>
          );
        }}
      </KhoiDuLieu>
    </Card>
  );
}
