import { mau, san, nhanThayDoi, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import Card from '../Card.jsx';
import { HANG_CHI_SO, dungO, toiDaCuaHang } from './hangChiSo.js';

const CUNG_LUOI = 'minmax(0, 1fr) 200px minmax(0, 1fr)';

/** Thanh mọc từ giữa ra ngoài: cánh trái neo bên phải, cánh phải neo bên trái. */
function ThanhCanh({ phanTram, mauThanh, ben, tre }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  return (
    <div style={{ width: 150, height: 10, background: mau.thanhNen, borderRadius: 5, display: 'flex', justifyContent: ben === 'trai' ? 'flex-end' : 'flex-start', overflow: 'hidden' }}>
      <div
        data-testid="thanh-hai-canh"
        style={{ width: `${moc ? phanTram : 0}%`, height: 10, borderRadius: 5, background: mauThanh, transition: kieuChuyen(cd, 'width', thoiLuong.banNguyet2, tre) }}
      />
    </div>
  );
}

function NoiDungO({ o, ben }) {
  const mauThayDoi = o.nhan ? nhanThayDoi[o.nhan.tone].chu : mau.chuNhan;
  return (
    <div style={{ textAlign: ben === 'trai' ? 'right' : 'left' }}>
      <div className="so" style={{ fontSize: 17, fontWeight: 600, color: o.coSo ? mau.chuChinh : mau.chuMo }}>
        {o.giaTri}
      </div>
      {o.nhan ? (
        <div className="so" style={{ fontSize: coChu.ratNho, color: mauThayDoi }}>
          {o.nhan.text}
        </div>
      ) : null}
    </div>
  );
}

/** Không có hàng hay ô nào cộng hai sàn. */
export default function BangHaiCanh({ shopee, tiktok, thuTu }) {
  return (
    <Card thuTu={thuTu} aria-label="Chỉ số hai sàn" style={{ padding: '8px 20px 14px', overflowX: 'auto' }}>
      <div style={{ minWidth: 720 }}>
        <div style={{ display: 'grid', gridTemplateColumns: CUNG_LUOI, alignItems: 'center', padding: '12px 0', borderBottom: `1px solid ${mau.vienTrong}`, fontSize: coChu.nhan, fontWeight: 600, letterSpacing: '.05em', color: mau.chuMo }}>
          <div style={{ textAlign: 'right', paddingRight: 24 }}>SHOPEE</div>
          <div style={{ textAlign: 'center' }}>CHỈ SỐ</div>
          <div style={{ paddingLeft: 24 }}>TIKTOK SHOP</div>
        </div>
        {HANG_CHI_SO.map((hang, i) => {
          const toiDa = hang.thanh ? toiDaCuaHang(shopee, tiktok, hang) : 0;
          const oS = dungO(shopee, hang, toiDa);
          const oT = dungO(tiktok, hang, toiDa);
          return (
            <div key={hang.khoa} data-testid={`hang-${hang.khoa}`} style={{ display: 'grid', gridTemplateColumns: CUNG_LUOI, alignItems: 'center', padding: '13px 0', borderBottom: `1px solid ${mau.vienTrong}` }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 16, paddingRight: 24 }}>
                <NoiDungO o={oS} ben="trai" />
                {hang.thanh && oS.coSo ? <ThanhCanh phanTram={oS.thanh} mauThanh={san.shopee.chinh} ben="trai" tre={600 + i * 80} /> : null}
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 500 }}>{hang.nhan}</div>
                <div style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>{hang.phu}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingLeft: 24 }}>
                {hang.thanh && oT.coSo ? <ThanhCanh phanTram={oT.thanh} mauThanh={san.tiktok.chinh} ben="phai" tre={600 + i * 80} /> : null}
                <NoiDungO o={oT} ben="phai" />
              </div>
            </div>
          );
        })}
        <p style={{ margin: '12px 0 0', fontSize: coChu.ratNho, color: mau.chuNhan, textAlign: 'center' }}>
          Mức thay đổi của mỗi sàn so với kỳ trước của chính sàn đó. Thanh ngang chỉ vẽ cho tỷ lệ, vì tỷ lệ so được giữa hai sàn dù số ngày khác nhau.
        </p>
      </div>
    </Card>
  );
}
