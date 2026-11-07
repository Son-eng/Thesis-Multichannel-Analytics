import { useEffect, useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { mau, san, nhanThayDoi, canhBao, coChu, khoangCach } from '../theme/tokens.js';
import { useTrangThaiDongBo } from '../hooks/useTrangThaiDongBo.js';
import { useTaiDuLieu } from '../hooks/useTaiDuLieu.js';
import { chayDongBo, layLichSu } from '../api/sync.js';
import { docLoi } from '../api/client.js';
import Card from '../components/Card.jsx';
import PageTitle from '../components/PageTitle.jsx';
import Icon from '../components/Icon.jsx';
import KhoiDuLieu from '../components/KhoiDuLieu.jsx';
import { COT_CHAT_LUONG, OBoDem } from '../components/ChatLuongTep.jsx';
import { dinhDangThoiDiem, dinhDangNgay, dinhDangSo, KHONG_CO_DU_LIEU } from '../utils/format.js';

const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };
const NHAN_NGUON = { api: 'API', file_auto: 'Tệp tự động', file_manual: 'Tệp thủ công' };
const NHAN_KET_QUA = { success: 'Thành công', failed: 'Thất bại', running: 'Đang chạy' };
const SO_DONG_MOI_TRANG = 20;

/** Nhãn trạng thái của một gian hàng. Không có chỗ nào hiện giá trị token, chỉ có hạn. */
function trangThaiGianHang(shop, dangChay) {
  if (dangChay) {
    return { nhan: 'Đang đồng bộ', nen: nhanThayDoi.trungTinh.nen, chu: nhanThayDoi.trungTinh.chu, quay: true };
  }
  if (shop.token_status === 'expired') {
    return { nhan: 'Hết quyền', nen: nhanThayDoi.xau.nen, chu: nhanThayDoi.xau.chu };
  }
  if (shop.token_status === 'expiring') {
    return { nhan: 'Sắp hết quyền', nen: canhBao.nenVangNhat, chu: canhBao.chuVang };
  }
  return { nhan: 'Sẵn sàng', nen: nhanThayDoi.tot.nen, chu: nhanThayDoi.tot.chu };
}

function TheGianHang({ shop, dangChay }) {
  const [ghiChu, setGhiChu] = useState('');
  const tt = trangThaiGianHang(shop, dangChay);
  const mauSan = san[shop.platform].chinh;
  // Hạn hiển thị là hạn của refresh token (hết mới phải ủy quyền lại); TikTok không có thì dùng hạn của access token (§12.1.3.2).
  const hanDen = shop.refresh_expires_at || shop.access_expires_at;
  const sapHet = shop.token_status !== 'ok';
  return (
    <Card aria-label={`Gian hàng ${shop.shop_name}`} data-testid={`shop-${shop.shop_name}`} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: coChu.ratNho, fontWeight: 600 }}>
          <span style={{ width: 9, height: 9, borderRadius: 3, background: mauSan }} />
          {TEN_SAN[shop.platform]}
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '2px 9px', borderRadius: 999, fontSize: coChu.ratNho, fontWeight: 600, background: tt.nen, color: tt.chu }}>
          {tt.quay ? <span className="xoay" /> : null}
          {tt.nhan}
        </span>
      </div>
      <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>{shop.shop_name}</h2>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: coChu.nho, color: mau.chuNhan }}>
        <span>Đồng bộ thành công gần nhất</span>
        <b className="so" style={{ color: mau.chuChinh, fontWeight: 600 }}>{shop.last_success_at ? dinhDangThoiDiem(shop.last_success_at) : KHONG_CO_DU_LIEU}</b>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: coChu.nho, color: mau.chuNhan }}>
        <span>Quyền truy cập còn hạn đến</span>
        <b className="so" style={{ color: sapHet ? canhBao.chuDam : mau.chuChinh, fontWeight: 600 }}>{hanDen ? dinhDangNgay(hanDen) : KHONG_CO_DU_LIEU}</b>
      </div>
      <button type="button" className={sapHet ? 'nut nut-chinh' : 'nut'} style={{ alignSelf: 'flex-start' }} onClick={() => setGhiChu('Chưa hỗ trợ trong bản demo')}>
        Ủy quyền lại
      </button>
      {ghiChu ? (
        <span role="status" style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>
          {ghiChu}
        </span>
      ) : null}
    </Card>
  );
}

/** Ô chọn có nhãn nhỏ phía trước (Sàn / Nguồn / Kết quả). */
function OLoc({ nhan, giaTri, khiDoi, luaChon }) {
  return (
    <label className="chip">
      <span style={{ color: mau.chuMo }}>{nhan}</span>
      <select aria-label={nhan} value={giaTri} onChange={(e) => khiDoi(e.target.value)}>
        {luaChon.map((l) => (
          <option key={l.value} value={l.value}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/**
 * Đồng bộ dữ liệu (UC04, UC05, UC07): nút đồng bộ từng sàn, thẻ từng gian hàng, lịch sử mọi lượt đưa dữ liệu vào.
 * Nút khóa khi sàn đang chạy; trong lúc có sàn chạy, hỏi lại trạng thái mỗi 3 giây (SPEC §12.1.3.3).
 */
export default function SyncStatus() {
  const ngCanh = useOutletContext();
  const [chuKy, setChuKy] = useState(30000);
  const { trangThai, lamMoi } = useTrangThaiDongBo(chuKy);
  const [loiDongBo, setLoiDongBo] = useState('');
  const [bo, setBo] = useState({ san: '', nguon: '', ketQua: '', trang: 1 });

  const dangChayBatKy = trangThai ? trangThai.platforms.shopee.running || trangThai.platforms.tiktok.running : false;
  useEffect(() => {
    setChuKy(dangChayBatKy ? 3000 : 30000);
  }, [dangChayBatKy]);

  // Khi một lượt vừa xong (running chuyển true -> false): tải lại lịch sử và cập nhật ô ở chân menu.
  const daChay = useRef(false);
  const [lanXong, setLanXong] = useState(0);
  useEffect(() => {
    if (daChay.current && !dangChayBatKy) {
      setLanXong((n) => n + 1);
      if (ngCanh && ngCanh.lamMoiDongBo) {
        ngCanh.lamMoiDongBo();
      }
    }
    daChay.current = dangChayBatKy;
  }, [dangChayBatKy, ngCanh]);

  const ttLichSu = useTaiDuLieu(
    () => layLichSu({ platform: bo.san, source: bo.nguon, status: bo.ketQua, page: bo.trang, page_size: SO_DONG_MOI_TRANG }),
    [bo.san, bo.nguon, bo.ketQua, bo.trang, lanXong],
  );

  const bamDongBo = async (maSan) => {
    setLoiDongBo('');
    try {
      await chayDongBo(maSan);
    } catch (e) {
      setLoiDongBo(docLoi(e).message);
    }
    lamMoi();
  };

  const nutDongBo = (maSan) => {
    const chay = trangThai ? trangThai.platforms[maSan].running : false;
    return (
      <button
        key={maSan}
        type="button"
        className={chay ? 'nut' : 'nut nut-chinh'}
        disabled={chay || trangThai === null}
        title={chay ? `${TEN_SAN[maSan]} đang có lượt đồng bộ chạy` : undefined}
        onClick={() => bamDongBo(maSan)}
      >
        {chay ? <span className="xoay" /> : <Icon ten="sync" kichThuoc={14} />}
        {chay ? `${TEN_SAN[maSan]} đang đồng bộ` : `Đồng bộ ${TEN_SAN[maSan]}`}
      </button>
    );
  };

  const doiLoc = (thayDoi) => setBo({ ...bo, ...thayDoi, trang: 1 });

  return (
    <>
      <PageTitle
        tieuDe="Đồng bộ dữ liệu"
        dongPhu={`Hệ thống tự lấy đơn hàng từ API của sàn mỗi ${trangThai ? trangThai.interval_minutes : 10} phút. Dùng nút đồng bộ khi cần số liệu mới ngay.`}
        benPhai={
          <>
            {nutDongBo('shopee')}
            {nutDongBo('tiktok')}
          </>
        }
      />
      {loiDongBo ? (
        <div role="alert" style={{ padding: '10px 14px', borderRadius: 10, background: canhBao.nenVang, color: canhBao.chuVang, fontSize: coChu.nho }}>
          {loiDongBo}
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: khoangCach.giuaThe }}>
        {trangThai
          ? trangThai.shops.map((s) => <TheGianHang key={`${s.platform}-${s.shop_name}`} shop={s} dangChay={trangThai.platforms[s.platform].running} />)
          : [0, 1, 2].map((i) => <Card key={i} style={{ height: 170 }} />)}
      </div>

      <Card aria-label="Lịch sử đưa dữ liệu vào" style={{ padding: '18px 20px 8px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: coChu.tieuDeThe + 1, fontWeight: 600 }}>Lịch sử đưa dữ liệu vào</h2>
            <p style={{ margin: '4px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan }}>
              Gồm cả lượt đồng bộ qua API và các tệp được nạp. Số màu vàng là dòng dữ liệu cần xem lại.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <OLoc nhan="Sàn" giaTri={bo.san} khiDoi={(v) => doiLoc({ san: v })} luaChon={[{ value: '', label: 'Tất cả' }, { value: 'shopee', label: 'Shopee' }, { value: 'tiktok', label: 'TikTok Shop' }]} />
            <OLoc nhan="Nguồn" giaTri={bo.nguon} khiDoi={(v) => doiLoc({ nguon: v })} luaChon={[{ value: '', label: 'Tất cả' }, ...Object.keys(NHAN_NGUON).map((k) => ({ value: k, label: NHAN_NGUON[k] }))]} />
            <OLoc nhan="Kết quả" giaTri={bo.ketQua} khiDoi={(v) => doiLoc({ ketQua: v })} luaChon={[{ value: '', label: 'Tất cả' }, ...Object.keys(NHAN_KET_QUA).map((k) => ({ value: k, label: NHAN_KET_QUA[k] }))]} />
          </div>
        </div>
        <KhoiDuLieu tt={ttLichSu} cao={300}>
          {(dl) => {
            const soTrang = Math.max(1, Math.ceil(dl.total / dl.page_size));
            return (
              <>
                <div style={{ overflowX: 'auto', marginTop: 12 }}>
                  <table className="bang bang-gon">
                    <thead>
                      <tr>
                        <th scope="col">Thời gian</th>
                        <th scope="col" style={{ textAlign: 'left' }}>Gian hàng</th>
                        <th scope="col" style={{ textAlign: 'left' }}>Nguồn</th>
                        <th scope="col" style={{ textAlign: 'left' }}>Người chạy</th>
                        <th scope="col" style={{ textAlign: 'left' }}>Kết quả</th>
                        <th scope="col">Thêm mới</th>
                        <th scope="col">Cập nhật</th>
                        {COT_CHAT_LUONG.map((c) => (
                          <th key={c.khoa} scope="col" title={c.goiY}>{c.nhan}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dl.items.map((m) => (
                        <tr key={m.id}>
                          <td className="so" style={{ textAlign: 'left' }}>{dinhDangThoiDiem(m.started_at)}</td>
                          <td style={{ textAlign: 'left' }}>
                            {m.shop_name || 'Nhiều gian hàng'}
                            <span style={{ marginLeft: 6, color: mau.chuMo, fontSize: coChu.ratNho }}>{TEN_SAN[m.platform]}</span>
                          </td>
                          <td style={{ textAlign: 'left' }}>{NHAN_NGUON[m.source]}</td>
                          <td style={{ textAlign: 'left' }}>{m.triggered_by ? m.triggered_by.username : 'Tự động'}</td>
                          <td style={{ textAlign: 'left' }} title={m.error_message || undefined}>{NHAN_KET_QUA[m.status]}</td>
                          <td>{dinhDangSo(m.rows_inserted)}</td>
                          <td>{dinhDangSo(m.rows_updated)}</td>
                          {COT_CHAT_LUONG.map((c) => (
                            <td key={c.khoa}>
                              <OBoDem giaTri={m.quality[c.khoa]} />
                            </td>
                          ))}
                        </tr>
                      ))}
                      {dl.items.length === 0 ? (
                        <tr>
                          <td colSpan={12} style={{ textAlign: 'left', color: mau.chuNhan }}>Không có lượt nào khớp bộ lọc.</td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '12px 0', fontSize: coChu.nho, color: mau.chuNhan }}>
                  <span>
                    {dinhDangSo(dl.total)} lượt · Trang {dl.page} / {soTrang}
                  </span>
                  <span style={{ display: 'inline-flex', gap: 8 }}>
                    <button type="button" className="nut" disabled={dl.page <= 1} onClick={() => setBo({ ...bo, trang: bo.trang - 1 })}>
                      Trang trước
                    </button>
                    <button type="button" className="nut" disabled={dl.page >= soTrang} onClick={() => setBo({ ...bo, trang: bo.trang + 1 })}>
                      Trang sau
                    </button>
                  </span>
                </div>
              </>
            );
          }}
        </KhoiDuLieu>
      </Card>
    </>
  );
}
