import { useEffect, useState } from 'react';
import { mau, canhBao, coChu } from '../../theme/tokens.js';
import Card from '../Card.jsx';
import { KhungXam } from '../KhoiDuLieu.jsx';
import TieuDeKhoi from './TieuDeKhoi.jsx';
import Icon from '../Icon.jsx';
import { sinhNhanDinh } from '../../api/insights.js';
import { docLoi } from '../../api/client.js';
import { dinhDangPhanTram } from '../../utils/format.js';
import { nhanKy } from '../../utils/period.js';
import { chuThuong, dongChatLuongDuLieu } from '../../utils/vanBanDashboard.js';

/**
 * Thẻ gộp ba phần: "Cảnh báo biến động", "Chất lượng dữ liệu" (quy tắc 10), "Nhận định tự động".
 * Nhận định chỉ gọi khi bấm nút; lỗi thì chỉ phần nhận định báo lỗi, các khối khác không bị ảnh hưởng.
 *
 * @param {object} props.ttKpi kết quả useTaiDuLieu của /kpi
 * @param {object} props.ttCanhBao kết quả useTaiDuLieu của /alerts
 * @param {(ky: string) => void} props.chonKy chuyển sang kỳ đã chọn (từ liên kết "kỳ vượt ngưỡng")
 */
export default function KhoiCanhBaoNhanDinh({ san, muc, ky, ttKpi, ttCanhBao, chonKy, thuTu }) {
  const [nhanDinh, setNhanDinh] = useState({ trangThai: 'chua', van: '', loi: '' });

  // Đổi sàn / kỳ / mức thì bỏ nhận định cũ: nó diễn giải số của kỳ khác.
  useEffect(() => {
    setNhanDinh({ trangThai: 'chua', van: '', loi: '' });
  }, [san, muc, ky]);

  const sinh = async () => {
    setNhanDinh({ trangThai: 'dang', van: '', loi: '' });
    try {
      const kq = await sinhNhanDinh({ platform: san, granularity: muc, period: ky });
      setNhanDinh({ trangThai: 'xong', van: kq.text, loi: '' });
    } catch (e) {
      setNhanDinh({ trangThai: 'loi', van: '', loi: docLoi(e).message });
    }
  };

  return (
    <Card thuTu={thuTu} aria-label="Cảnh báo và nhận định" style={{ flex: '1 1 320px', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PhanCanhBao ttKpi={ttKpi} ttCanhBao={ttCanhBao} muc={muc} ky={ky} chonKy={chonKy} />
      <PhanChatLuong ttKpi={ttKpi} />
      <div style={{ borderTop: `1px solid ${mau.vienTrong}`, paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: coChu.nho, fontWeight: 600 }}>Nhận định tự động</h3>
          <button type="button" className="nut nut-chinh" onClick={sinh} disabled={nhanDinh.trangThai === 'dang'} style={{ height: 30, fontSize: coChu.ratNho }}>
            <Icon ten="spark" kichThuoc={13} doDay={1.6} />
            {nhanDinh.trangThai === 'xong' ? 'Sinh lại' : 'Sinh nhận định'}
          </button>
        </div>
        {nhanDinh.trangThai === 'dang' ? <KhungXam cao={56} /> : null}
        {nhanDinh.trangThai === 'xong' ? (
          <p style={{ margin: 0, fontSize: coChu.nho, color: mau.chuPhu, lineHeight: 1.6 }}>{nhanDinh.van}</p>
        ) : null}
        {nhanDinh.trangThai === 'loi' ? (
          <p role="alert" style={{ margin: 0, fontSize: coChu.nho, color: canhBao.chuDam }}>
            Không sinh được nhận định: {nhanDinh.loi}
          </p>
        ) : null}
        {nhanDinh.trangThai === 'chua' ? (
          <p style={{ margin: 0, fontSize: coChu.ratNho, color: mau.chuNhan }}>Diễn giải lại các số đã tính ở trên, không tự tính thêm số. Chỉ chạy khi bấm nút.</p>
        ) : null}
      </div>
    </Card>
  );
}

/** Phần "Cảnh báo biến động": kỳ này vượt ngưỡng / có kỳ khác vượt ngưỡng / không có. */
function PhanCanhBao({ ttKpi, ttCanhBao, muc, ky, chonKy }) {
  if (ttKpi.duLieu === null || ttCanhBao.duLieu === null) {
    return <KhungXam cao={72} />;
  }
  const kpi = ttKpi.duLieu;
  const nguong = Math.abs(kpi.alert.threshold_pct);
  const kyKhac = ttCanhBao.duLieu.items.filter((m) => m.period !== ky);
  const kyNay = ttCanhBao.duLieu.items.find((m) => m.period === ky);

  let kieuHop = { nen: canhBao.nenXanh, cham: canhBao.xanh, chu: mau.chuPhu };
  let noiDung = <span>Không có kỳ nào giảm từ {dinhDangPhanTram(nguong, 0)} so với kỳ liền trước.</span>;
  if (kpi.alert.triggered) {
    kieuHop = { nen: canhBao.nen, cham: canhBao.chinh, chu: canhBao.chu };
    const pct = kyNay ? kyNay.pct_change : kpi.metrics.revenue.pct_change;
    noiDung = (
      <span>
        Kỳ này giảm {dinhDangPhanTram(Math.abs(pct))}, vượt ngưỡng giảm {dinhDangPhanTram(nguong, 0)}.
      </span>
    );
  } else if (kyKhac.length > 0) {
    kieuHop = { nen: canhBao.nenVang, cham: canhBao.vang, chu: mau.chuPhu };
    const dau = kyKhac[0];
    noiDung = (
      <span>
        {kyKhac.length} kỳ vượt ngưỡng:{' '}
        <button
          type="button"
          onClick={() => chonKy(dau.period)}
          style={{ border: 0, background: 'none', padding: 0, color: 'inherit', fontWeight: 600, textDecoration: 'underline', textUnderlineOffset: 3, cursor: 'pointer' }}
        >
          {`${chuThuong(nhanKy(muc, dau.period))} (−${dinhDangPhanTram(Math.abs(dau.pct_change))})`}
        </button>
        {kyKhac.length > 1 ? ` và ${kyKhac.length - 1} kỳ khác` : ''}
      </span>
    );
  }

  return (
    <div>
      <TieuDeKhoi bieuTuong="bell">Cảnh báo biến động</TieuDeKhoi>
      <div data-testid="hop-canh-bao" style={{ marginTop: 10, display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', borderRadius: 10, background: kieuHop.nen }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', marginTop: 6, flex: 'none', background: kieuHop.cham }} />
        <div style={{ fontSize: coChu.nho, color: kieuHop.chu }}>
          {noiDung}
          <div style={{ fontSize: coChu.ratNho, color: mau.chuNhan, marginTop: 2 }}>Ngưỡng hiện tại: giảm từ {dinhDangPhanTram(nguong, 0)}</div>
        </div>
      </div>
    </div>
  );
}

/** Phần "Chất lượng dữ liệu" (quy tắc 10): luôn hiện số dòng `unknown`; Shopee hiện thêm số dòng NMV tạm tính. */
function PhanChatLuong({ ttKpi }) {
  if (ttKpi.duLieu === null) {
    return <KhungXam cao={48} />;
  }
  const dong = dongChatLuongDuLieu(ttKpi.duLieu.data_quality);
  return (
    <div style={{ borderTop: `1px solid ${mau.vienTrong}`, paddingTop: 12 }}>
      <h3 style={{ margin: 0, fontSize: coChu.nho, fontWeight: 600 }}>Chất lượng dữ liệu</h3>
      {dong.map((d) => (
        <p key={d} className="so" style={{ margin: '4px 0 0', fontSize: coChu.nho, color: mau.chuPhu }}>
          {d}
        </p>
      ))}
    </div>
  );
}
