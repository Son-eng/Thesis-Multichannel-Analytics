import { mau, maSanPham, nhanThayDoi, coChu } from '../../theme/tokens.js';
import { thoiLuong, troGiup } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import Card from '../Card.jsx';
import KhoiDuLieu, { KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import { useTaiDuLieu } from '../../hooks/useTaiDuLieu.js';
import { layTopSanPham } from '../../api/dashboard.js';
import { taoNhanThayDoi } from '../../utils/delta.js';
import { dinhDangTien, dinhDangPhanTram } from '../../utils/format.js';

/** Số sản phẩm hiện trong bảng. */
const SO_DONG_TOI_DA = 7;

/** Một dòng của bảng: ô mã, thanh tỷ trọng kéo dài ra, doanh thu, thay đổi so với kỳ trước. */
function DongSanPham({ sp, chiSo, tiLeThanh, status }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const dinhNghiaMau = maSanPham.theoMa[sp.product_code] || maSanPham.macDinh;
  const nhan = taoNhanThayDoi({ value: sp.revenue, pct_change: sp.pct_change, previous_zero: sp.previous_zero }, { status });
  return (
    <tr style={{ opacity: moc ? 1 : 0, transition: kieuChuyen(cd, 'opacity', thoiLuong.hienDong, 600 + chiSo * troGiup.giuaDong) }}>
      <td>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontWeight: 600 }}>
          <span style={{ width: 26, height: 26, borderRadius: 8, background: dinhNghiaMau.nhat, display: 'grid', placeItems: 'center' }}>
            <span style={{ width: 9, height: 9, borderRadius: 3, background: dinhNghiaMau.dam }} />
          </span>
          {sp.product_code}
        </span>
      </td>
      <td style={{ textAlign: 'left' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, width: '100%' }}>
          <span style={{ flex: '1 1 auto', maxWidth: 140, height: 6, borderRadius: 3, background: mau.thanhNen, overflow: 'hidden' }}>
            <span
              data-testid="thanh-ty-trong"
              style={{ display: 'block', height: 6, width: `${moc ? tiLeThanh : 0}%`, borderRadius: 3, background: dinhNghiaMau.dam, transition: kieuChuyen(cd, 'width', thoiLuong.thanhTyTrong, 700 + chiSo * troGiup.giuaDong) }}
            />
          </span>
          <span className="so" style={{ fontSize: coChu.nho, color: mau.chuPhu }}>
            {dinhDangPhanTram(sp.share_pct)}
          </span>
        </span>
      </td>
      <td style={{ fontWeight: 500 }}>{dinhDangTien(sp.revenue)}</td>
      <td style={{ fontWeight: 600, color: nhanThayDoi[nhan.tone].chu }}>{nhan.text}</td>
    </tr>
  );
}

/** Khối "Sản phẩm bán chạy": bảng top theo product_code (SPEC §7.3), có thanh tỷ trọng. */
export default function KhoiSanPham({ san, muc, thamSo, ky, thuTu }) {
  const tt = useTaiDuLieu(
    () => layTopSanPham(san, { ...thamSo, granularity: muc, period: ky, limit: SO_DONG_TOI_DA }),
    [san, muc, ky, thamSo.shop_name, thamSo.product_code],
  );
  return (
    <Card thuTu={thuTu} aria-label="Sản phẩm bán chạy" style={{ flex: '2 1 600px', padding: '18px 20px 8px', overflowX: 'auto' }}>
      <TieuDeKhoi bieuTuong="box" chuThich="Gộp theo mã sản phẩm, không theo SKU gốc">
        Sản phẩm bán chạy
      </TieuDeKhoi>
      <KhoiDuLieu tt={tt} cao={260}>
        {(dl) => {
          if (dl.status === 'no_data' || dl.items.length === 0) {
            return <KhongCoDuLieu cao={200} />;
          }
          const lonNhat = dl.items[0].revenue;
          return (
            <table className="bang" style={{ marginTop: 12, minWidth: 560 }}>
              <thead>
                <tr>
                  <th scope="col">Mã sản phẩm</th>
                  <th scope="col" style={{ textAlign: 'left' }}>
                    Tỷ trọng doanh thu
                  </th>
                  <th scope="col">Doanh thu</th>
                  <th scope="col">So với kỳ trước</th>
                </tr>
              </thead>
              <tbody>
                {dl.items.map((sp, i) => (
                  <DongSanPham key={sp.product_code} sp={sp} chiSo={i} tiLeThanh={(sp.revenue / lonNhat) * 100} status={dl.status} />
                ))}
              </tbody>
            </table>
          );
        }}
      </KhoiDuLieu>
    </Card>
  );
}
