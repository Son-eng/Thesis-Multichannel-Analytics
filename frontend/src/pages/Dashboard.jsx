import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { mau, canhBao, coChu, khoangCach } from '../theme/tokens.js';
import { TrangChuyenDong } from '../hooks/useChuyenDong.jsx';
import { useTaiDuLieu } from '../hooks/useTaiDuLieu.js';
import { layBoLoc, layKpi, layCanhBao } from '../api/dashboard.js';
import { docLoi } from '../api/client.js';
import Card from '../components/Card.jsx';
import PageTitle from '../components/PageTitle.jsx';
import ChipChon from '../components/ChipChon.jsx';
import Icon from '../components/Icon.jsx';
import { KhungXam } from '../components/KhoiDuLieu.jsx';
import CacTheChiSo from '../components/dashboard/CacTheChiSo.jsx';
import KhoiDoanhThuThang from '../components/dashboard/KhoiDoanhThuThang.jsx';
import KhoiDoanhThuNgay from '../components/dashboard/KhoiDoanhThuNgay.jsx';
import KhoiKenhBan from '../components/dashboard/KhoiKenhBan.jsx';
import KhoiSanPham from '../components/dashboard/KhoiSanPham.jsx';
import KhoiKhungGio from '../components/dashboard/KhoiKhungGio.jsx';
import KhoiTinh from '../components/dashboard/KhoiTinh.jsx';
import KhoiCanhBaoNhanDinh from '../components/dashboard/KhoiCanhBaoNhanDinh.jsx';
import { MUC_THOI_GIAN, NHAN_MUC, maKyChuaNgay, maKyHopLe, danhSachKy, congNgay, nhanKy } from '../utils/period.js';
import { dinhDangNgay, dinhDangTien, dinhDangPhanTram } from '../utils/format.js';
import { chuThuong, dongKyChuaDuNgay } from '../utils/vanBanDashboard.js';

/** Tên hiển thị của từng sàn. */
export const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };

/**
 * Mức ngày: biểu đồ cột chồng chỉ lấy 31 ngày kết thúc ở ngày đang chọn (không vẽ cả 200+ cột).
 * Mức khác lấy toàn bộ khoảng dữ liệu (không truyền date_from/date_to).
 */
function khoangXuHuong(muc, ky, ngayMin) {
  if (muc !== 'day') {
    return {};
  }
  const tu = congNgay(ky, -30);
  return { date_from: tu > ngayMin ? tu : ngayMin, date_to: ky };
}

function dongGianHang(loc) {
  if (loc.shops.length > 1) {
    return `${loc.shops.length} gian hàng (${loc.shops.join(', ')})`;
  }
  return `Gian hàng ${loc.shops[0]}`;
}

/**
 * MỘT trang dashboard dùng chung cho cả hai sàn (route /dashboard/:platform).
 * Hai sàn cùng khuôn, cùng hợp đồng JSON, chỉ khác tham số `platform` (SPEC §13).
 *
 * Lựa chọn của người dùng (mức, kỳ, gian hàng, mã sản phẩm) nằm trên địa chỉ (?muc=&ky=&shop=&ma=),
 * nên tải lại trang hay gửi đường dẫn vẫn giữ nguyên kỳ đang xem. Mặc định mỗi sàn mở ở kỳ chứa
 * `data_max_date` của CHÍNH sàn đó (hai sàn có khoảng dữ liệu khác nhau).
 * Mỗi khối gọi endpoint riêng, tự xử lý đang tải / lỗi / không có dữ liệu của mình.
 */
export default function Dashboard() {
  const { platform: san } = useParams();
  const [thamSoUrl, setThamSoUrl] = useSearchParams();
  const [ghiChu, setGhiChu] = useState('');

  const ttLoc = useTaiDuLieu(() => layBoLoc(san), [san]);
  const loc = ttLoc.duLieu;

  const mucUrl = thamSoUrl.get('muc');
  const muc = MUC_THOI_GIAN.includes(mucUrl) ? mucUrl : 'month';
  const kyUrl = thamSoUrl.get('ky');
  const kyMacDinh = loc ? maKyChuaNgay(muc, loc.data_max_date) : null;
  const ky = kyUrl && maKyHopLe(muc, kyUrl) ? kyUrl : kyMacDinh;
  const shop = thamSoUrl.get('shop') || '';
  const ma = thamSoUrl.get('ma') || '';
  const thamSo = { shop_name: shop, product_code: ma };

  /** Ghi lựa chọn mới lên địa chỉ; giá trị rỗng thì bỏ khỏi địa chỉ cho gọn. */
  const capNhat = (thayDoi) => {
    const moi = { muc: mucUrl || '', ky: kyUrl || '', shop, ma, ...thayDoi };
    const p = new URLSearchParams();
    Object.keys(moi).forEach((k) => {
      if (moi[k]) {
        p.set(k, moi[k]);
      }
    });
    setThamSoUrl(p, { replace: true });
  };

  const sanSang = loc !== null && ky !== null;
  const ttKpi = useTaiDuLieu(
    () => (sanSang ? layKpi(san, { granularity: muc, period: ky, ...thamSo }) : null),
    [san, muc, ky, shop, ma, sanSang],
  );
  const ttCanhBao = useTaiDuLieu(
    () => (sanSang ? layCanhBao(san, { granularity: muc, ...thamSo }) : null),
    [san, muc, shop, ma, sanSang],
  );

  if (ttLoc.loi) {
    return (
      <>
        <PageTitle tieuDe={`Dashboard ${TEN_SAN[san]}`} />
        <Card role="alert">
          Không tải được bộ lọc của {TEN_SAN[san]}: {docLoi(ttLoc.loi).message}
          <button type="button" className="nut" onClick={ttLoc.thuLai} style={{ marginLeft: 12 }}>
            Thử lại
          </button>
        </Card>
      </>
    );
  }
  if (!sanSang) {
    return (
      <>
        <PageTitle tieuDe={`Dashboard ${TEN_SAN[san]}`} />
        <KhungXam cao={96} />
        <KhungXam cao={300} />
      </>
    );
  }

  const dsKy = danhSachKy(muc, loc.data_min_date, loc.data_max_date);
  const luaChonKy = dsKy.map((k) => ({ value: k.key, label: k.label }));
  const luaChonMuc = MUC_THOI_GIAN.map((m) => ({ value: m, label: NHAN_MUC[m] }));
  const luaChonShop = [{ value: '', label: 'Tất cả gian hàng' }].concat(loc.shops.map((s) => ({ value: s, label: s })));
  const luaChonMa = [{ value: '', label: 'Tất cả mã sản phẩm' }].concat(loc.product_codes.map((m) => ({ value: m, label: m })));

  const kpi = ttKpi.duLieu;
  const khoang = khoangXuHuong(muc, ky, loc.data_min_date);

  return (
    <TrangChuyenDong>
      <PageTitle
        tieuDe={`Dashboard ${TEN_SAN[san]}`}
        dongPhu={`${dongGianHang(loc)} · Dữ liệu ${dinhDangNgay(loc.data_min_date)} – ${dinhDangNgay(loc.data_max_date)}`}
        benPhai={
          <>
            <ChipChon nhan="Kỳ" bieuTuong="calendar" giaTri={ky} khiDoi={(v) => capNhat({ ky: v })} luaChon={luaChonKy} />
            <ChipChon nhan="Mức thời gian" giaTri={muc} khiDoi={(v) => capNhat({ muc: v === 'month' ? '' : v, ky: '' })} luaChon={luaChonMuc} />
            <ChipChon nhan="Gian hàng" bieuTuong="filter" giaTri={shop} khiDoi={(v) => capNhat({ shop: v })} luaChon={luaChonShop} />
            <ChipChon nhan="Mã sản phẩm" bieuTuong="box" giaTri={ma} khiDoi={(v) => capNhat({ ma: v })} luaChon={luaChonMa} />
            <button type="button" className="chip" onClick={() => setGhiChu('Chưa hỗ trợ trong bản demo')}>
              <Icon ten="download" kichThuoc={15} />
              Xuất báo cáo
            </button>
          </>
        }
      />
      {ghiChu ? (
        <p role="status" style={{ margin: '-6px 0 0', fontSize: coChu.nho, color: mau.chuNhan }}>
          {ghiChu}
        </p>
      ) : null}

      {kpi && kpi.alert.triggered ? (
        <Card
          role="alert"
          thuTu={0}
          style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: canhBao.nen, borderColor: canhBao.vien }}
        >
          <span style={{ width: 30, height: 30, borderRadius: 9, background: canhBao.nenIcon, color: canhBao.chuDam, display: 'grid', placeItems: 'center', flex: 'none' }}>
            <Icon ten="warn" doDay={1.6} />
          </span>
          <span style={{ color: canhBao.chu }}>
            Doanh thu {chuThuong(nhanKy(muc, kpi.period))} giảm {dinhDangPhanTram(Math.abs(kpi.metrics.revenue.pct_change))} so với{' '}
            {chuThuong(nhanKy(muc, kpi.previous.period))} ({dinhDangTien(kpi.metrics.revenue.value)} so với {dinhDangTien(kpi.metrics.revenue.previous)}), vượt ngưỡng cảnh báo giảm{' '}
            {dinhDangPhanTram(Math.abs(kpi.alert.threshold_pct), 0)}.
          </span>
        </Card>
      ) : null}
      {kpi && !kpi.period_complete && kpi.status !== 'no_data' ? (
        <div role="status" style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: coChu.nho, color: mau.chuPhu }}>
          <Icon ten="info" vongTron />
          <span>{dongKyChuaDuNgay(muc, kpi)}</span>
        </div>
      ) : null}

      <CacTheChiSo tt={ttKpi} />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'stretch' }}>
        <KhoiDoanhThuThang san={san} muc={muc} thamSo={thamSo} khoang={khoang} kyDangChon={ky} ttCanhBao={ttCanhBao} thuTu={4} />
        <KhoiDoanhThuNgay tt={ttKpi} muc={muc} thuTu={5} />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'stretch' }}>
        <KhoiKenhBan san={san} muc={muc} thamSo={thamSo} ky={ky} thuTu={6} />
        <KhoiSanPham san={san} muc={muc} thamSo={thamSo} ky={ky} thuTu={7} />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'stretch' }}>
        <KhoiKhungGio san={san} muc={muc} thamSo={thamSo} ky={ky} thuTu={8} />
        <KhoiTinh san={san} muc={muc} thamSo={thamSo} ky={ky} thuTu={9} />
        <KhoiCanhBaoNhanDinh san={san} muc={muc} ky={ky} ttKpi={ttKpi} ttCanhBao={ttCanhBao} chonKy={(k) => capNhat({ ky: k })} thuTu={10} />
      </div>
    </TrangChuyenDong>
  );
}
