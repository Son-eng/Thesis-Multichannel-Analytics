// Màn hình đối chiếu 2 sàn

import { useSearchParams } from 'react-router-dom';
import { mau, chuDao, san, coChu, khoangCach } from '../theme/tokens.js';
import { TrangChuyenDong } from '../hooks/useChuyenDong.jsx';
import { useTaiDuLieu } from '../hooks/useTaiDuLieu.js';
import { soSanhHaiSan } from '../api/compare.js';
import { layBoLoc } from '../api/dashboard.js';
import { docLoi } from '../api/client.js';
import Card from '../components/Card.jsx';
import PageTitle from '../components/PageTitle.jsx';
import ChipChon from '../components/ChipChon.jsx';
import ChipNgay from '../components/ChipNgay.jsx';
import Icon from '../components/Icon.jsx';
import { KhungXam } from '../components/KhoiDuLieu.jsx';
import TieuDeKhoi from '../components/dashboard/TieuDeKhoi.jsx';
import HourLines from '../components/charts/HourLines.jsx';
import CanhDoanhThu from '../components/compare/CanhDoanhThu.jsx';
import BangHaiCanh from '../components/compare/BangHaiCanh.jsx';
import BangSanPham from '../components/compare/BangSanPham.jsx';
import { MUC_THOI_GIAN, NHAN_MUC, maKyChuaNgay, maKyHopLe, danhSachKy } from '../utils/period.js';
import { dungBanner } from '../utils/vanBanDoiChieu.js';
import { dinhDangPhanTram } from '../utils/format.js';

function chuCaoDiem(khoi) {
  if (khoi.status === 'no_data' || khoi.by_hour.length === 0) {
    return 'không có dữ liệu';
  }
  let dinh = khoi.by_hour[0];
  khoi.by_hour.forEach((g) => {
    if (g.share_pct > dinh.share_pct) {
      dinh = g;
    }
  });
  return `${dinh.hour}h – ${dinh.hour + 1}h (${dinhDangPhanTram(dinh.share_pct)})`;
}

/** Đặt hai sàn cạnh nhau trong cùng kỳ, không cộng gộp; mỗi sàn so với kỳ trước của chính nó. */
export default function ComparePlatforms() {
  const [thamSoUrl, setThamSoUrl] = useSearchParams();
  const ttShopee = useTaiDuLieu(() => layBoLoc('shopee'), []);
  const ttTiktok = useTaiDuLieu(() => layBoLoc('tiktok'), []);
  const locShopee = ttShopee.duLieu;
  const locTiktok = ttTiktok.duLieu;

  const mucUrl = thamSoUrl.get('muc');
  const muc = MUC_THOI_GIAN.includes(mucUrl) ? mucUrl : 'month';
  const kyUrl = thamSoUrl.get('ky');
  const coLoc = locShopee !== null && locTiktok !== null;
  const ngayMin = coLoc ? (locShopee.data_min_date < locTiktok.data_min_date ? locShopee.data_min_date : locTiktok.data_min_date) : null;
  const ngayMax = coLoc ? (locShopee.data_max_date > locTiktok.data_max_date ? locShopee.data_max_date : locTiktok.data_max_date) : null;
  const kyMacDinh = coLoc ? maKyChuaNgay(muc, ngayMax) : null;
  const ky = kyUrl && maKyHopLe(muc, kyUrl) ? kyUrl : kyMacDinh;

  const capNhat = (thayDoi) => {
    const moi = { muc: mucUrl || '', ky: kyUrl || '', ...thayDoi };
    const p = new URLSearchParams();
    Object.keys(moi).forEach((k) => {
      if (moi[k]) {
        p.set(k, moi[k]);
      }
    });
    setThamSoUrl(p, { replace: true });
  };

  const tt = useTaiDuLieu(() => (coLoc ? soSanhHaiSan({ granularity: muc, period: ky }) : null), [muc, ky, coLoc]);

  const loiBoLoc = ttShopee.loi || ttTiktok.loi;
  if (loiBoLoc) {
    return (
      <>
        <PageTitle tieuDe="Đối chiếu hai sàn" />
        <Card role="alert">Không tải được khoảng dữ liệu của hai sàn: {docLoi(loiBoLoc).message}</Card>
      </>
    );
  }
  const tieuDe = (
    <PageTitle
      tieuDe="Đối chiếu hai sàn"
      dongPhu="Hai sàn đặt cạnh nhau trong cùng kỳ. Hệ thống không cộng gộp số liệu của hai sàn."
      benPhai={
        coLoc ? (
          <>
            {muc === 'day' ? (
              <ChipNgay nhan="Kỳ" giaTri={ky} khiDoi={(v) => capNhat({ ky: v })} ngayMin={ngayMin} ngayMax={ngayMax} />
            ) : (
              <ChipChon nhan="Kỳ" bieuTuong="calendar" giaTri={ky} khiDoi={(v) => capNhat({ ky: v })} luaChon={danhSachKy(muc, ngayMin, ngayMax).map((k) => ({ value: k.key, label: k.label }))} />
            )}
            <ChipChon nhan="Mức thời gian" giaTri={muc} khiDoi={(v) => capNhat({ muc: v === 'month' ? '' : v, ky: '' })} luaChon={MUC_THOI_GIAN.map((m) => ({ value: m, label: NHAN_MUC[m] }))} />
          </>
        ) : null
      }
    />
  );

  if (tt.loi) {
    return (
      <>
        {tieuDe}
        <Card role="alert">
          Không tải được số liệu đối chiếu: {docLoi(tt.loi).message}
          <button type="button" className="nut" onClick={tt.thuLai} style={{ marginLeft: 12 }}>
            Thử lại
          </button>
        </Card>
      </>
    );
  }
  if (tt.duLieu === null) {
    return (
      <>
        {tieuDe}
        <KhungXam cao={72} />
        <KhungXam cao={140} />
        <KhungXam cao={300} />
      </>
    );
  }

  const dl = tt.duLieu;
  const banner = dungBanner(muc, dl);
  const duongGio = [];
  if (dl.shopee.status !== 'no_data' && dl.shopee.by_hour.length === 24) {
    duongGio.push({ khoa: 'shopee', mau: san.shopee.chinh, giaTri: dl.shopee.by_hour.map((g) => g.share_pct), tre: 700 });
  }
  if (dl.tiktok.status !== 'no_data' && dl.tiktok.by_hour.length === 24) {
    duongGio.push({ khoa: 'tiktok', mau: san.tiktok.chinh, giaTri: dl.tiktok.by_hour.map((g) => g.share_pct), vungDuoi: true, tre: 850 });
  }

  return (
    // key theo kỳ và mức để đổi kỳ thì chạy lại chuyển động.
    <TrangChuyenDong key={`${muc}-${ky}`}>
      {tieuDe}
      <Card
        role="note"
        thuTu={0}
        style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 16px', background: chuDao.nenBanner, borderColor: chuDao.vienBanner }}
      >
        <span style={{ width: 30, height: 30, borderRadius: 9, background: chuDao.nenIconBanner, color: chuDao.dam, display: 'grid', placeItems: 'center', flex: 'none' }}>
          <Icon ten="info" vongTron doDay={1.6} />
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, fontSize: coChu.nho }}>
          <span style={{ color: mau.chuChinh }}>{banner.chinh}</span>
          {banner.phu ? <span style={{ color: mau.chuNhan }}>{banner.phu}</span> : null}
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: khoangCach.giuaThe }}>
        <CanhDoanhThu ten="Shopee" mauSan={san.shopee.chinh} khoi={dl.shopee} thuTu={1} testId="canh-shopee" />
        <CanhDoanhThu ten="TikTok Shop" mauSan={san.tiktok.chinh} khoi={dl.tiktok} thuTu={2} testId="canh-tiktok" />
      </div>

      <BangHaiCanh shopee={dl.shopee} tiktok={dl.tiktok} thuTu={3} />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'stretch' }}>
        <BangSanPham shopee={dl.shopee} tiktok={dl.tiktok} thuTu={4} />
        <Card thuTu={5} aria-label="Đơn theo khung giờ" style={{ flex: '1 1 420px' }}>
          <TieuDeKhoi bieuTuong="clock" vongTron>
            Đơn hàng theo khung giờ
          </TieuDeKhoi>
          <p style={{ margin: '4px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan }}>Tỷ lệ đơn trong ngày của từng sàn, để so được dù tổng số đơn khác nhau</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px', marginTop: 12, fontSize: coChu.ratNho, color: mau.chuPhu }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 16, height: 3, borderRadius: 2, background: san.shopee.chinh }} />
              Shopee · cao điểm {chuCaoDiem(dl.shopee)}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 16, height: 3, borderRadius: 2, background: san.tiktok.chinh }} />
              TikTok Shop · cao điểm {chuCaoDiem(dl.tiktok)}
            </span>
          </div>
          {duongGio.length > 0 ? <HourLines duong={duongGio} ariaLabel="Tỷ lệ đơn theo giờ của hai sàn" /> : null}
          {dl.shopee.status === 'no_data' ? (
            <p style={{ margin: '6px 0 0', fontSize: coChu.nho, color: mau.chuNhan }}>Shopee: không có dữ liệu trong kỳ này.</p>
          ) : null}
          {dl.tiktok.status === 'no_data' ? (
            <p style={{ margin: '6px 0 0', fontSize: coChu.nho, color: mau.chuNhan }}>TikTok Shop: không có dữ liệu trong kỳ này.</p>
          ) : null}
        </Card>
      </div>
    </TrangChuyenDong>
  );
}
