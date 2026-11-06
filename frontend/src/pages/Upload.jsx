import { useRef, useState } from 'react';
import { mau, chuDao, canhBao, nhanThayDoi, coChu, khoangCach, boGoc } from '../theme/tokens.js';
import { useTaiDuLieu } from '../hooks/useTaiDuLieu.js';
import { layBoLoc } from '../api/dashboard.js';
import { napTep } from '../api/upload.js';
import { docLoi } from '../api/client.js';
import Card from '../components/Card.jsx';
import PageTitle from '../components/PageTitle.jsx';
import Icon from '../components/Icon.jsx';
import { COT_CHAT_LUONG, OBoDem } from '../components/ChatLuongTep.jsx';
import { dinhDangSo, dinhDangThoiDiem } from '../utils/format.js';

const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };

/** Dung lượng dễ đọc: "1,4 MB". */
function dinhDangDungLuong(byte) {
  if (byte < 1024) {
    return `${byte} B`;
  }
  if (byte < 1024 * 1024) {
    return `${(byte / 1024).toFixed(1).replace('.', ',')} KB`;
  }
  return `${(byte / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`;
}

/**
 * Nạp tệp CSV dự phòng (admin) (SPEC §2.4, §12.1.3.5).
 * - Shopee bắt buộc chọn gian hàng (tệp Shopee không có cột gian hàng); TikTok tự nhận từ cột trong tệp.
 * - Lỗi 422 nói rõ "không dòng nào được ghi"; `missing_columns` liệt kê cột thiếu, `invalid_file` thì không có danh sách cột.
 * - Khối "Kết quả lần nạp gần nhất" vẽ trực tiếp từ SyncRun mà API trả về.
 */
export default function Upload() {
  const [maSan, setMaSan] = useState('shopee');
  const [gianHang, setGianHang] = useState('');
  const [tep, setTep] = useState(null);
  const [dangKeo, setDangKeo] = useState(false);
  const [dangGui, setDangGui] = useState(false);
  const [loi, setLoi] = useState(null);
  const [ketQua, setKetQua] = useState(null);
  const oChonTep = useRef(null);
  const ttLoc = useTaiDuLieu(() => layBoLoc('shopee'), []);
  const dsGianHang = ttLoc.duLieu ? ttLoc.duLieu.shops : [];

  const chonTep = (f) => {
    setLoi(null);
    if (f && !f.name.toLowerCase().endsWith('.csv')) {
      setTep(null);
      setLoi({ message: 'Chỉ nhận tệp CSV (đuôi .csv)', cot: [] });
      return;
    }
    setTep(f || null);
  };

  const doiSan = (s) => {
    setMaSan(s);
    setLoi(null);
  };

  const gui = async () => {
    setLoi(null);
    setDangGui(true);
    try {
      const luot = await napTep(maSan, tep, maSan === 'shopee' ? gianHang : undefined);
      setKetQua(luot);
      setTep(null);
      if (oChonTep.current) {
        oChonTep.current.value = '';
      }
    } catch (e) {
      const { message, extra } = docLoi(e);
      setLoi({ message, cot: extra.missing_columns || [] });
    } finally {
      setDangGui(false);
    }
  };

  // Shopee chưa chọn gian hàng thì khóa nút "Nạp tệp".
  const khoaNut = tep === null || dangGui || (maSan === 'shopee' && gianHang === '');

  return (
    <>
      <PageTitle tieuDe="Upload tệp dữ liệu" dongPhu="Dùng khi không lấy được dữ liệu qua API. Nạp lại một tệp đã nạp sẽ chỉ cập nhật, không tạo đơn trùng." />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: khoangCach.giuaThe, alignItems: 'flex-start' }}>
        <Card style={{ flex: '1 1 420px' }} aria-label="Nạp tệp">
          <div style={{ marginBottom: 16 }}>
            <span className="nhan-o">Sàn</span>
            <div role="radiogroup" aria-label="Sàn" style={{ display: 'flex', gap: 8 }}>
              {Object.keys(TEN_SAN).map((s) => (
                <label
                  key={s}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 14px', border: `1px solid ${maSan === s ? chuDao.chinh : mau.vienChip}`, borderRadius: boGoc.nut, background: maSan === s ? chuDao.nhat : mau.nenThe, cursor: 'pointer', fontSize: coChu.nho, fontWeight: 500 }}
                >
                  <input type="radio" name="san" value={s} checked={maSan === s} onChange={() => doiSan(s)} />
                  {TEN_SAN[s]}
                </label>
              ))}
            </div>
          </div>

          {maSan === 'shopee' ? (
            <div style={{ marginBottom: 16 }}>
              <label className="nhan-o" htmlFor="chon-gian-hang">Gian hàng</label>
              <select id="chon-gian-hang" className="o-nhap" value={gianHang} onChange={(e) => setGianHang(e.target.value)}>
                <option value="">Chọn gian hàng</option>
                {dsGianHang.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <span style={{ display: 'block', marginTop: 6, fontSize: coChu.ratNho, color: mau.chuNhan }}>Tệp xuất từ Shopee không có cột gian hàng nên cần chọn ở đây.</span>
            </div>
          ) : (
            <p style={{ margin: '0 0 16px', fontSize: coChu.ratNho, color: mau.chuNhan }}>Tệp TikTok Shop đã có cột gian hàng, hệ thống tự nhận.</p>
          )}

          <div
            onDragOver={(sk) => {
              sk.preventDefault();
              setDangKeo(true);
            }}
            onDragLeave={() => setDangKeo(false)}
            onDrop={(sk) => {
              sk.preventDefault();
              setDangKeo(false);
              chonTep(sk.dataTransfer.files[0]);
            }}
            style={{ border: `1.5px dashed ${dangKeo ? chuDao.chinh : mau.vienChipHover}`, borderRadius: boGoc.oTrangThai, background: dangKeo ? chuDao.nhat : mau.nenPhu, padding: '26px 16px', textAlign: 'center' }}
          >
            <span style={{ color: chuDao.chinh }}>
              <Icon ten="upload" kichThuoc={26} />
            </span>
            <p style={{ margin: '10px 0 4px', fontWeight: 600 }}>
              Kéo tệp CSV vào đây hoặc{' '}
              <label htmlFor="tep-csv" style={{ color: chuDao.chinh, cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 3 }}>
                bấm để chọn
              </label>
            </p>
            <input id="tep-csv" ref={oChonTep} className="sr-only" type="file" accept=".csv,text/csv" onChange={(e) => chonTep(e.target.files[0])} />
            <p style={{ margin: 0, fontSize: coChu.ratNho, color: mau.chuNhan }}>
              {tep ? (
                <>
                  Đã chọn: <b style={{ color: mau.chuPhu }}>{tep.name}</b> ({dinhDangDungLuong(tep.size)})
                </>
              ) : (
                'Chưa chọn tệp nào'
              )}
            </p>
          </div>

          {loi ? (
            <div role="alert" style={{ marginTop: 14, padding: '10px 12px', borderRadius: 10, background: canhBao.nen, border: `1px solid ${canhBao.vien}`, color: canhBao.chu, fontSize: coChu.nho }}>
              <div style={{ fontWeight: 600 }}>{loi.message}</div>
              {loi.cot.length > 0 ? (
                <div style={{ marginTop: 6 }}>
                  Cột còn thiếu:
                  <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                    {loi.cot.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}

          <button type="button" className="nut nut-chinh" disabled={khoaNut} onClick={gui} style={{ width: '100%', height: 44, marginTop: 16 }}>
            <Icon ten="upload" kichThuoc={15} />
            Nạp tệp
          </button>
        </Card>

        <Card style={{ flex: '1 1 420px' }} aria-label="Kết quả lần nạp gần nhất">
          <h2 style={{ margin: 0, fontSize: coChu.tieuDeThe + 1, fontWeight: 600 }}>Kết quả lần nạp gần nhất</h2>
          {ketQua ? <KetQuaNap luot={ketQua} /> : <p style={{ margin: '8px 0 0', fontSize: coChu.nho, color: mau.chuNhan }}>Chưa có lần nạp nào trong phiên này.</p>}
          <p style={{ margin: '12px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan }}>Tệp thiếu cột bắt buộc sẽ bị từ chối toàn bộ, không có dòng nào được ghi.</p>
        </Card>
      </div>
    </>
  );
}

/** Kết quả một lượt nạp tệp, vẽ trực tiếp từ SyncRun (SPEC §12.1.3.1). */
function KetQuaNap({ luot }) {
  return (
    <>
      <p style={{ margin: '4px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan }}>
        {luot.file_name}, lúc {dinhDangThoiDiem(luot.started_at)}
      </p>
      <div role="status" style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10, background: nhanThayDoi.tot.nen, color: nhanThayDoi.tot.chu, fontSize: coChu.nho, fontWeight: 500 }}>
        Đã nạp xong {dinhDangSo(luot.rows_total)} dòng.
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, margin: '14px 0' }}>
        {[
          ['Tổng số dòng trong tệp', luot.rows_total],
          ['Dòng thêm mới', luot.rows_inserted],
          ['Dòng cập nhật', luot.rows_updated],
        ].map(([nhan, so]) => (
          <div key={nhan}>
            <b className="so" style={{ display: 'block', fontSize: 20 }}>{dinhDangSo(so)}</b>
            <span style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>{nhan}</span>
          </div>
        ))}
      </div>
      <h3 style={{ margin: '0 0 8px', fontSize: coChu.nho, fontWeight: 600 }}>Dòng cần xem lại</h3>
      <table className="bang">
        <tbody>
          {COT_CHAT_LUONG.map((c) => (
            <tr key={c.khoa}>
              <td>{c.nhanDai}</td>
              <td>
                <OBoDem giaTri={luot.quality[c.khoa]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
