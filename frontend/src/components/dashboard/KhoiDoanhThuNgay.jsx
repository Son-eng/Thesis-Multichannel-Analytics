import { mau, chuDao, gachCheo, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import { KhungXam, KhongCoDuLieu } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import DailyBars from '../charts/DailyBars.jsx';
import RatioBar from '../charts/RatioBar.jsx';
import { rutGonTien, dinhDangSo, dinhDangTien, dinhDangNgayNgan } from '../../utils/format.js';
import { nhanKy } from '../../utils/period.js';
import { chuThuong, cauKhongSoCaKy } from '../../utils/vanBanDashboard.js';
import { docLoi } from '../../api/client.js';

function dungNhanNgay(muc, daily) {
  return daily.map((d) => {
    const goiY = `Ngày ${dinhDangNgayNgan(d.date)}: ${dinhDangTien(d.current)}`;
    if (muc === 'month') {
      return { khoa: d.date, nhan: String(Number(d.date.slice(8, 10))), giaTri: d.current, goiY };
    }
    return { khoa: d.date, nhan: dinhDangNgayNgan(d.date), giaTri: d.current, goiY };
  });
}

/** Câu giải thích lấy previous_full.pct_change_if_used từ API, frontend không tự tính. */
export default function KhoiDoanhThuNgay({ tt, muc, thuTu }) {
  return (
    <Card thuTu={thuTu} aria-label="Doanh thu từng ngày" style={{ flex: '1 1 340px', padding: '18px 20px 16px', display: 'flex', flexDirection: 'column' }}>
      <TieuDeKhoi bieuTuong="calendar">Doanh thu từng ngày</TieuDeKhoi>
      {tt.loi ? (
        <div role="alert" style={{ marginTop: 12, fontSize: coChu.nho, color: mau.chuNhan }}>
          Không tải được khối này: {docLoi(tt.loi).message}
        </div>
      ) : null}
      {!tt.loi && tt.duLieu === null ? <KhungXam cao={260} style={{ marginTop: 12 }} /> : null}
      {tt.duLieu ? <NoiDung kpi={tt.duLieu} muc={muc} /> : null}
    </Card>
  );
}

function NoiDung({ kpi, muc }) {
  if (kpi.status === 'no_data') {
    return <KhongCoDuLieu cao={200} />;
  }
  if (kpi.daily === null || kpi.daily.length === 0) {
    return (
      <p style={{ margin: '12px 0 0', fontSize: coChu.nho, color: mau.chuNhan }}>
        Đang xem theo ngày nên không chia nhỏ hơn.
      </p>
    );
  }
  const ngay = dungNhanNgay(muc, kpi.daily);
  const cao = kpi.daily.reduce((a, d) => (d.current > a.current ? d : a), kpi.daily[0]);
  const thanh = [];
  const tuoi = kpi.metrics.revenue;
  const nhanMoiN = muc === 'month' ? 5 : Math.max(5, Math.ceil(ngay.length / 6));

  const giaTriCacThanh = [tuoi.value];
  if (tuoi.previous !== null) {
    giaTriCacThanh.push(tuoi.previous);
  }
  if (kpi.previous_full) {
    giaTriCacThanh.push(kpi.previous_full.revenue);
  }
  const lonNhat = Math.max(...giaTriCacThanh, 1);
  const tiLe = (v) => (v / lonNhat) * 100;

  thanh.push({ khoa: 'nay', nhan: 'Kỳ này', giaTri: rutGonTien(tuoi.value), tiLe: tiLe(tuoi.value), nen: chuDao.chinh, tre: 500 });
  if (tuoi.previous !== null && kpi.previous) {
    const khoang = kpi.previous.date_from === kpi.previous.date_to ? dinhDangNgayNgan(kpi.previous.date_from) : `${dinhDangNgayNgan(kpi.previous.date_from)} – ${dinhDangNgayNgan(kpi.previous.date_to)}`;
    thanh.push({ khoa: 'truoc', nhan: `Kỳ trước (${khoang})`, giaTri: rutGonTien(tuoi.previous), tiLe: tiLe(tuoi.previous), nen: chuDao.sang, tre: 600 });
  }
  if (kpi.previous_full) {
    thanh.push({
      khoa: 'ca-ky',
      nhan: `Cả ${chuThuong(nhanKy(muc, kpi.previous_full.period))}`,
      giaTri: rutGonTien(kpi.previous_full.revenue),
      tiLe: tiLe(kpi.previous_full.revenue),
      nen: `repeating-linear-gradient(135deg, ${gachCheo.dam} 0 3px, ${gachCheo.nhat} 3px 6px)`,
      mauChu: mau.chuMo,
      gachNgang: true,
      tre: 700,
    });
  }

  let cauGiaiThich = 'Hai kỳ đều đủ ngày nên so nguyên kỳ.';
  if (kpi.status === 'insufficient_data') {
    cauGiaiThich = 'Không đủ dữ liệu để so sánh: hệ thống chưa có dữ liệu của kỳ liền trước.';
  } else if (kpi.previous_full) {
    cauGiaiThich = cauKhongSoCaKy(muc, kpi);
  }

  return (
    <>
      <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '4px 10px' }}>
        <span className="so" style={{ fontSize: coChu.soLon, fontWeight: 600, letterSpacing: '-0.02em' }}>
          {dinhDangSo(cao.current)}
          <span style={{ fontSize: 15, fontWeight: 500, color: mau.chuDonVi, marginLeft: 4 }}>đ</span>
        </span>
        <span className="so" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
          Ngày cao nhất, {dinhDangNgayNgan(cao.date)}
        </span>
      </div>
      <DailyBars ngay={ngay} nhanMoiN={nhanMoiN} />
      <div style={{ marginTop: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {thanh.map((t) => (
          <RatioBar key={t.khoa} nhan={t.nhan} giaTri={t.giaTri} tiLe={t.tiLe} nen={t.nen} mauChu={t.mauChu} gachNgang={t.gachNgang} tre={t.tre} />
        ))}
        <p style={{ margin: '2px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan, lineHeight: 1.55 }}>{cauGiaiThich}</p>
      </div>
    </>
  );
}
