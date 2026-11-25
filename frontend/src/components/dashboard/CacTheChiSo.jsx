import { khoangCach } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import { KhungXam } from '../KhoiDuLieu.jsx';
import TheChiSo from './TheChiSo.jsx';
import { docLoi } from '../../api/client.js';
import { taoNhanThayDoi } from '../../utils/delta.js';
import { dinhDangSo, dinhDangTien, dinhDangPhanTram, KHONG_CO_DU_LIEU, KHONG_DU_DU_LIEU } from '../../utils/format.js';
import { TOOLTIP_DOANH_THU, tieuDeDoanhThu, chuKyDemRaSoSanh } from '../../utils/vanBanDashboard.js';

/** Không có kỳ trước thì nói rõ, không để trống. */
function dongSoSanh(kpi, chiSo, dinhDang, tienTo) {
  if (kpi.status === 'no_data') {
    return 'Kỳ này không có dòng dữ liệu nào';
  }
  if (kpi.status === 'insufficient_data') {
    return KHONG_DU_DU_LIEU;
  }
  if (chiSo.previous === null) {
    return 'Kỳ trước không xác định';
  }
  return `${tienTo} ${dinhDang(chiSo.previous)}`;
}

export default function CacTheChiSo({ tt }) {
  const khungCho = (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: khoangCach.giuaThe }}>
      {[0, 1, 2, 3].map((i) => (
        <Card key={i} thuTu={i}>
          <KhungXam cao={96} />
        </Card>
      ))}
    </div>
  );
  if (tt.loi) {
    return (
      <Card role="alert" thuTu={0}>
        Không tải được các thẻ chỉ số: {docLoi(tt.loi).message}
        <button type="button" className="nut" onClick={tt.thuLai} style={{ marginLeft: 12 }}>
          Thử lại
        </button>
      </Card>
    );
  }
  if (tt.duLieu === null) {
    return khungCho;
  }

  const kpi = tt.duLieu;
  const m = kpi.metrics;
  const status = kpi.status;
  const soSanhKy = status === 'ok' ? chuKyDemRaSoSanh(kpi.previous) : null;
  let dongDoanhThu = dongSoSanh(kpi, m.revenue, dinhDangTien, '');
  if (status === 'ok' && m.revenue.previous !== null) {
    dongDoanhThu = `${soSanhKy}: ${dinhDangTien(m.revenue.previous)}`;
  }

  let dongSanPham = KHONG_CO_DU_LIEU;
  if (m.quantity_sold.value !== null) {
    dongSanPham = `${dinhDangSo(m.quantity_sold.value)} sản phẩm bán`;
  }
  let dongHuy = KHONG_CO_DU_LIEU;
  if (m.order_count_all.value !== null && m.return_rate.value !== null) {
    dongHuy = `Trên tổng ${dinhDangSo(m.order_count_all.value)} đơn · tỷ lệ hoàn ${dinhDangPhanTram(m.return_rate.value)}`;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: khoangCach.giuaThe }}>
      <TheChiSo
        testId="the-doanh-thu"
        thuTu={0}
        nhan={tieuDeDoanhThu(kpi.period_complete, kpi.current.date_to)}
        goiY={TOOLTIP_DOANH_THU}
        bieuTuong="trend"
        giaTri={m.revenue.value}
        donVi="đ"
        nhanThayDoi={taoNhanThayDoi(m.revenue, { status, loai: 'doanh_thu' })}
        dongPhu={[dongDoanhThu]}
      />
      <TheChiSo
        testId="the-so-don"
        thuTu={1}
        nhan="Số đơn hợp lệ"
        goiY="Số đơn có ít nhất một dòng không hủy, không hoàn."
        bieuTuong="bag"
        giaTri={m.order_count.value}
        nhanThayDoi={taoNhanThayDoi(m.order_count, { status, loai: 'don' })}
        dongPhu={[dongSanPham, dongSoSanh(kpi, m.order_count, (v) => `${dinhDangSo(v)} đơn`, 'Kỳ trước')]}
      />
      <TheChiSo
        testId="the-aov"
        thuTu={2}
        nhan="Giá trị đơn trung bình"
        goiY="Doanh thu chia số đơn hợp lệ."
        bieuTuong="card"
        giaTri={m.aov.value}
        donVi="đ"
        nhanThayDoi={taoNhanThayDoi(m.aov, { status, loai: 'don' })}
        dongPhu={[dongSoSanh(kpi, m.aov, dinhDangTien, 'Kỳ trước')]}
      />
      <TheChiSo
        testId="the-ty-le-huy"
        thuTu={3}
        nhan="Tỷ lệ hủy"
        goiY="Số đơn bị hủy trên tổng số đơn của kỳ."
        bieuTuong="cancel"
        giaTri={m.cancel_rate.value}
        soThapPhan={1}
        donVi="%"
        nhanThayDoi={taoNhanThayDoi(m.cancel_rate, { status, dang: 'diemPhanTram', tangLaTot: false })}
        dongPhu={[dongHuy]}
      />
    </div>
  );
}
