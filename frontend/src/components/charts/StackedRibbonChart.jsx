import { mau, chuDao, canhBao, coChu } from '../../theme/tokens.js';
import { thoiLuong, troGiup } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import { rutGonTien, dinhDangTien, dinhDangPhanTram } from '../../utils/format.js';

// Kích thước hình vẽ (đơn vị SVG), theo bản thiết kế Dashboard.
const RONG = 720;
const DAY_CHAN = 248; // đường đáy của cột
const CAO_TOI_DA = 196; // chiều cao cột lớn nhất
const KHE_LOP = 3; // khe giữa các lớp chồng
const NHAN_THANG_Y = 270;

/**
 * Cột chồng theo kỳ, mỗi lớp một mã sản phẩm, có dải nối cùng màu giữa các cột.
 *
 * Nhận dữ liệu và màu qua props, KHÔNG gọi API.
 *
 * @param {object[]} thang mỗi phần tử một kỳ: {key, nhanNgan, nhanDayDu, tong, daDu, lop}
 *   - tong: tổng doanh thu kỳ (null = kỳ không có dữ liệu, không vẽ cột)
 *   - daDu: kỳ đã đủ ngày; chưa đủ thì cột nhạt màu và nhãn có dấu *
 *   - lop: [{ma, doanhThu}] đúng thứ tự của danhSachLop (tổng bằng tong)
 * @param {{ma: string|null, nhan: string, mau: string}[]} danhSachLop các lớp từ dưới lên; lớp cuối là "Mã khác"
 * @param {string} kyDangChon key của kỳ đang chọn (có nền nhạt phía sau)
 * @param {Object<string, number>} canhBaoTheoKy key kỳ -> % giảm (âm) cho kỳ vượt ngưỡng; kỳ đó ghi đỏ kèm %
 * @param {string} ariaLabel mô tả cho trình đọc màn hình
 */
export default function StackedRibbonChart({ thang, danhSachLop, kyDangChon, canhBaoTheoKy = {}, ariaLabel }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const soCot = thang.length;
  const lonNhat = thang.reduce((a, m) => (m.tong !== null && m.tong > a ? m.tong : a), 1);
  const o = (RONG - 16) / Math.max(soCot, 1);
  const rongCot = Math.min(72, o * 0.46);
  // Nhiều cột (mức ngày) thì thưa bớt nhãn để không đè nhau.
  const buocNhan = soCot > 14 ? Math.ceil(soCot / 12) : 1;

  const cot = thang.map((m, i) => {
    const x = 8 + o * i + (o - rongCot) / 2;
    if (m.tong === null) {
      return { m, i, x, lop: [], dinh: DAY_CHAN };
    }
    let cong = 0;
    const lop = m.lop.map((l) => {
      const h = (l.doanhThu / lonNhat) * CAO_TOI_DA;
      const y = DAY_CHAN - cong - h;
      const kq = { ma: l.ma, doanhThu: l.doanhThu, y, h, top: y, bot: DAY_CHAN - cong - KHE_LOP };
      cong += h;
      return kq;
    });
    return { m, i, x, lop, dinh: DAY_CHAN - cong };
  });

  const dai = [];
  for (let c = 0; c + 1 < cot.length; c += 1) {
    const a = cot[c];
    const b = cot[c + 1];
    if (a.lop.length > 0 && b.lop.length > 0) {
      danhSachLop.forEach((l, L) => {
        const diem = [
          `${(a.x + rongCot).toFixed(1)},${a.lop[L].top.toFixed(1)}`,
          `${b.x.toFixed(1)},${b.lop[L].top.toFixed(1)}`,
          `${b.x.toFixed(1)},${b.lop[L].bot.toFixed(1)}`,
          `${(a.x + rongCot).toFixed(1)},${a.lop[L].bot.toFixed(1)}`,
        ];
        dai.push({ khoa: `${c}-${L}`, diem: diem.join(' '), mau: l.mau, c });
      });
    }
  }

  return (
    <svg viewBox={`0 0 ${RONG} 286`} role="img" aria-label={ariaLabel} style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6, overflow: 'visible' }}>
      {cot
        .filter((c) => c.m.key === kyDangChon && c.m.tong !== null)
        .map((c) => (
          <rect key="nen-chon" x={(c.x - 12).toFixed(1)} y="10" width={(rongCot + 24).toFixed(1)} height="262" rx="10" fill={chuDao.nenSlot} />
        ))}

      {dai.map((d) => (
        <polygon
          key={d.khoa}
          data-testid="dai-noi"
          points={d.diem}
          fill={d.mau}
          fillOpacity={0.13}
          style={{ opacity: moc ? 1 : 0, transition: kieuChuyen(cd, 'opacity', thoiLuong.dai, 600 + d.c * troGiup.giuaCot) }}
        />
      ))}

      {cot.map((c) =>
        c.lop.map((l, L) => (
          <rect
            key={`${c.i}-${L}`}
            data-lop={l.ma === null ? 'khac' : l.ma}
            x={c.x.toFixed(1)}
            y={l.y.toFixed(1)}
            width={rongCot.toFixed(1)}
            height={Math.max(1, l.h - KHE_LOP).toFixed(1)}
            rx="4"
            fill={danhSachLop[L].mau}
            fillOpacity={c.m.daDu ? 1 : 0.55}
            style={{
              transformBox: 'view-box',
              transformOrigin: `0px ${DAY_CHAN}px`,
              transform: moc ? 'scaleY(1)' : 'scaleY(0)',
              transition: kieuChuyen(cd, 'transform', thoiLuong.cotChong, c.i * troGiup.giuaCot + L * troGiup.giuaLop),
            }}
          >
            <title>{`${danhSachLop[L].nhan}, ${c.m.nhanDayDu}: ${dinhDangTien(l.doanhThu)}`}</title>
          </rect>
        )),
      )}

      {cot.map((c) => {
        if (c.m.tong === null) {
          return null;
        }
        const pct = canhBaoTheoKy[c.m.key];
        const coCanhBao = pct !== undefined;
        const chu = coCanhBao ? `${rutGonTien(c.m.tong)} · −${dinhDangPhanTram(Math.abs(pct))}` : rutGonTien(c.m.tong);
        return (
          <text
            key={`nhan-tong-${c.i}`}
            x={(c.x + rongCot / 2).toFixed(1)}
            y={(c.dinh - 9).toFixed(1)}
            textAnchor="middle"
            fontSize={coChu.ratNho}
            fontWeight="600"
            fill={coCanhBao ? canhBao.chuDam : mau.chuChinh}
            style={{ fontVariantNumeric: 'tabular-nums', opacity: moc ? 1 : 0, transition: kieuChuyen(cd, 'opacity', 500, c.i * troGiup.giuaCot + 420) }}
          >
            {chu}
          </text>
        );
      })}

      {cot.map((c) => {
        const dangChon = c.m.key === kyDangChon;
        const coCanhBao = canhBaoTheoKy[c.m.key] !== undefined;
        if (!dangChon && !coCanhBao && c.i % buocNhan !== 0) {
          return null;
        }
        let mauNhan = mau.chuMo;
        if (coCanhBao) {
          mauNhan = canhBao.chuDam;
        } else if (dangChon) {
          mauNhan = mau.chuChinh;
        }
        return (
          <text key={`nhan-ky-${c.i}`} x={(c.x + rongCot / 2).toFixed(1)} y={NHAN_THANG_Y} textAnchor="middle" fontSize={coChu.ratNho} fontWeight={dangChon ? 700 : 500} fill={mauNhan}>
            {c.m.nhanNgan + (c.m.daDu ? '' : '*')}
          </text>
        );
      })}
    </svg>
  );
}
