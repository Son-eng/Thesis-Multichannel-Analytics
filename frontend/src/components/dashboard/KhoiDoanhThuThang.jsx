import { mau, canhBao, maSanPham, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import KhoiDuLieu, { KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import StackedRibbonChart from '../charts/StackedRibbonChart.jsx';
import { useTaiDuLieu } from '../../hooks/useTaiDuLieu.js';
import { layXuHuong } from '../../api/dashboard.js';
import { dinhDangSo } from '../../utils/format.js';
import { nhanKy, nhanKyNgan } from '../../utils/period.js';

const DON_VI_KY = { day: 'ngày', month: 'tháng', quarter: 'quý', year: 'năm' };

/** Màu của lớp theo mã sản phẩm; mã ngoài bảng màu dùng màu mặc định. */
function mauLop(ma) {
  if (ma === null) {
    return maSanPham.day[4];
  }
  const dinhNghia = maSanPham.theoMa[ma] || maSanPham.macDinh;
  return dinhNghia.dam;
}

/**
 * Khối "Doanh thu theo tháng": cột chồng theo mã sản phẩm (revenue-trend) + tổng toàn bộ.
 * Tháng vượt ngưỡng ghi đỏ kèm % giảm lấy từ /alerts (ttCanhBao). Tháng chưa đủ ngày nhạt màu, có dấu *.
 *
 * @param {object} props.thamSo tham số truy vấn dùng chung {granularity, shop_name, product_code}
 * @param {{date_from?: string, date_to?: string}} props.khoang giới hạn khoảng (chỉ dùng cho mức ngày)
 * @param {object} props.ttCanhBao kết quả useTaiDuLieu của /alerts
 */
export default function KhoiDoanhThuThang({ san, muc, thamSo, khoang, kyDangChon, ttCanhBao, thuTu }) {
  const tt = useTaiDuLieu(
    () => layXuHuong(san, { ...thamSo, granularity: muc, ...khoang }),
    [san, muc, thamSo.shop_name, thamSo.product_code, khoang.date_from, khoang.date_to],
  );

  const canhBaoTheoKy = {};
  if (ttCanhBao.duLieu) {
    ttCanhBao.duLieu.items.forEach((m) => {
      canhBaoTheoKy[m.period] = m.pct_change;
    });
  }

  return (
    <Card thuTu={thuTu} aria-label={`Doanh thu theo ${DON_VI_KY[muc]}`} style={{ flex: '2 1 600px', padding: '18px 20px 14px' }}>
      <TieuDeKhoi bieuTuong="chart" chuThich="Tách theo mã sản phẩm · đã loại đơn hủy và đơn hoàn">
        Doanh thu theo {DON_VI_KY[muc]}
      </TieuDeKhoi>
      <KhoiDuLieu tt={tt} cao={300}>
        {(dl) => {
          const coSo = dl.items.filter((m) => m.revenue !== null);
          if (coSo.length === 0) {
            return <KhongCoDuLieu cao={300} />;
          }
          const tong = coSo.reduce((a, m) => a + m.revenue, 0);
          const danhSachLop = dl.top_product_codes.map((ma) => ({ ma, nhan: ma, mau: mauLop(ma) }));
          danhSachLop.push({ ma: null, nhan: 'Mã khác', mau: mauLop(null) });
          const thang = dl.items.map((m) => ({
            key: m.period,
            nhanNgan: nhanKyNgan(muc, m.period),
            nhanDayDu: nhanKy(muc, m.period),
            tong: m.revenue,
            daDu: m.period_complete,
            lop: m.by_product ? m.by_product.map((p) => ({ ma: p.product_code, doanhThu: p.revenue })) : [],
          }));
          return (
            <>
              <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '4px 10px' }}>
                <span className="so" style={{ fontSize: coChu.soLon, fontWeight: 600, letterSpacing: '-0.02em' }}>
                  {dinhDangSo(tong)}
                  <span style={{ fontSize: 15, fontWeight: 500, color: mau.chuDonVi, marginLeft: 4 }}>đ</span>
                </span>
                <span style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
                  Tổng {muc === 'day' ? 'trong khoảng hiển thị' : 'toàn bộ dữ liệu'} · {coSo.length} {DON_VI_KY[muc]}
                </span>
              </div>
              <StackedRibbonChart
                thang={thang}
                danhSachLop={danhSachLop}
                kyDangChon={kyDangChon}
                canhBaoTheoKy={canhBaoTheoKy}
                ariaLabel={`Doanh thu theo ${DON_VI_KY[muc]}, tách theo mã sản phẩm`}
                donVi={DON_VI_KY[muc]}
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '6px 16px', marginTop: 6, fontSize: coChu.ratNho, color: mau.chuNhan }}>
                {danhSachLop.map((l) => (
                  <span key={l.nhan} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 9, height: 9, borderRadius: 3, background: l.mau }} />
                    {l.nhan}
                  </span>
                ))}
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 9, height: 9, borderRadius: '50%', background: canhBao.chinh }} />
                  Kỳ vượt ngưỡng cảnh báo
                </span>
                <span>* chưa đủ ngày</span>
              </div>
            </>
          );
        }}
      </KhoiDuLieu>
    </Card>
  );
}
