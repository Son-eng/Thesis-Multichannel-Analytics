import { useState } from 'react';
import { mau, chuDao, san, nhanThayDoi as mauNhan, boGoc, bong, coChu } from '../../theme/tokens.js';
import { thoiLuong } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import Card from '../Card.jsx';
import TieuDeKhoi from '../dashboard/TieuDeKhoi.jsx';
import { ghepSanPham } from './hangChiSo.js';
import { dinhDangTien, KHONG_CO_DU_LIEU } from '../../utils/format.js';

const LOC = [
  { khoa: 'tatCa', nhan: 'Tất cả' },
  { khoa: 'shopee', nhan: 'Chỉ Shopee' },
  { khoa: 'tiktok', nhan: 'Chỉ TikTok Shop' },
];

const NHAN_LOAI = {
  both: { chu: 'Cả hai sàn', nen: chuDao.nhat, mau: chuDao.dam },
  tiktok: { chu: 'Chỉ TikTok Shop', nen: san.tiktok.nhat, mau: san.tiktok.chu },
  shopee: { chu: 'Chỉ Shopee', nen: san.shopee.nhat, mau: san.shopee.chu },
  chuaSoDuoc: { chu: 'Chưa so được', nen: mauNhan.trungTinh.nen, mau: mauNhan.trungTinh.chu },
};

function OTien({ giaTri, sanKhongCoDuLieu }) {
  if (sanKhongCoDuLieu) {
    return <span style={{ color: mau.chuMo }}>{KHONG_CO_DU_LIEU}</span>;
  }
  // Sàn không bán mã này thì ghi "Không bán", không ghi 0.
  if (giaTri === null) {
    return <span style={{ color: mau.chuMo }}>Không bán</span>;
  }
  return <span>{dinhDangTien(giaTri)}</span>;
}

function DongSanPham({ sp, chiSo, shopeeKhongCoDuLieu }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const nhan = NHAN_LOAI[sp.loai];
  return (
    <tr style={{ opacity: moc ? 1 : 0, transition: kieuChuyen(cd, 'opacity', thoiLuong.hienDong, 700 + chiSo * 45) }}>
      <td style={{ fontWeight: 600 }}>{sp.ma}</td>
      <td>
        <OTien giaTri={sp.shopee} sanKhongCoDuLieu={shopeeKhongCoDuLieu} />
      </td>
      <td>
        <OTien giaTri={sp.tiktok} sanKhongCoDuLieu={false} />
      </td>
      <td style={{ textAlign: 'left' }}>
        <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: boGoc.nhan, fontSize: coChu.ratNho, fontWeight: 500, background: nhan.nen, color: nhan.mau }}>{nhan.chu}</span>
      </td>
    </tr>
  );
}

/** Cột "Bán trên" do frontend tự ghép từ hai by_product. */
export default function BangSanPham({ shopee, tiktok, thuTu }) {
  const [loc, setLoc] = useState('tatCa');
  const tatCa = ghepSanPham(shopee, tiktok);
  const hienThi = tatCa.filter((sp) => loc === 'tatCa' || sp.loai === loc);

  return (
    <Card thuTu={thuTu} aria-label="Theo mã sản phẩm" style={{ flex: '1.3 1 520px', padding: '18px 20px 8px', overflowX: 'auto' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <TieuDeKhoi bieuTuong="box">Theo mã sản phẩm</TieuDeKhoi>
        <div role="group" aria-label="Lọc sản phẩm" style={{ display: 'flex', background: mau.thanhNen, borderRadius: boGoc.nut, padding: 3 }}>
          {LOC.map((l) => {
            const dangChon = loc === l.khoa;
            return (
              <button
                key={l.khoa}
                type="button"
                aria-pressed={dangChon}
                onClick={() => setLoc(l.khoa)}
                style={{ height: 28, padding: '0 12px', border: 0, borderRadius: 7, cursor: 'pointer', fontSize: coChu.ratNho, fontWeight: 500, background: dangChon ? mau.nenThe : 'transparent', color: dangChon ? mau.chuChinh : mau.chuNhan, boxShadow: dangChon ? bong.nutChon : 'none' }}
              >
                {l.nhan}
              </button>
            );
          })}
        </div>
      </div>
      <table className="bang" style={{ marginTop: 12, minWidth: 520 }}>
        <thead>
          <tr>
            <th scope="col">Mã</th>
            <th scope="col">Doanh thu Shopee</th>
            <th scope="col">Doanh thu TikTok Shop</th>
            <th scope="col" style={{ textAlign: 'left' }}>
              Bán trên
            </th>
          </tr>
        </thead>
        <tbody>
          {hienThi.map((sp, i) => (
            <DongSanPham key={sp.ma} sp={sp} chiSo={i} shopeeKhongCoDuLieu={shopee.status === 'no_data'} />
          ))}
          {hienThi.length === 0 ? (
            <tr>
              <td colSpan={4} style={{ textAlign: 'left', color: mau.chuNhan }}>
                {loc === 'shopee' ? 'Không có mã nào chỉ bán trên Shopee' : 'Không có mã nào để hiển thị'}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </Card>
  );
}
