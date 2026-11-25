// Dải phân bố doanh thu

import { useState, useRef, useEffect } from 'react';
import { mau, chuDao, canhBao, coChu, bong, boGoc } from '../../theme/tokens.js';
import { thoiLuong, troGiup } from '../../theme/motion.js';
import { useChuyenDong, kieuChuyen, daMoc } from '../../hooks/useChuyenDong.jsx';
import { rutGonTien, dinhDangTien, dinhDangPhanTram } from '../../utils/format.js';

const RONG = 720;
const DAY_CHAN = 248;
const CAO_TOI_DA = 196;
const KHE_LOP = 3;
const NHAN_THANG_Y = 270;

const NGUONG_PHONG_TO = 14;
const TOI_THIEU_CO_THE_XEM = 7;
const HE_SO_PHONG = 0.7;
// Cột càng sít càng bớt chữ trên đầu cột; chi tiết luôn có ở khung chú thích.
const NGUONG_NHAN_PHAN_TRAM = 10;
const NGUONG_NHAN_TONG = 20;

function kep(x, thap, cao) {
  return Math.max(thap, Math.min(cao, x));
}

/** Cột chồng theo kỳ, mỗi lớp một mã sản phẩm; nhiều cột thì phóng to, kéo để lướt, rê chuột xem chi tiết. */
export default function StackedRibbonChart({ thang, danhSachLop, kyDangChon, canhBaoTheoKy = {}, ariaLabel, donVi = 'kỳ' }) {
  const cd = useChuyenDong();
  const moc = daMoc(cd);
  const soCotTong = thang.length;
  const coThePhongTo = soCotTong > NGUONG_PHONG_TO;
  const toiThieu = Math.min(TOI_THIEU_CO_THE_XEM, soCotTong);

  // null là xem tất cả, ngược lại {tu: cột đầu, so: số cột}.
  const [cua, datCua] = useState(null);
  const [ro, datRo] = useState(null);
  const khungRef = useRef(null);
  const keoRef = useRef(null);

  const so = cua ? Math.min(cua.so, soCotTong) : soCotTong;
  const tu = cua ? kep(cua.tu, 0, soCotTong - so) : 0;
  const dangPhongTo = so < soCotTong;

  // Đổi dữ liệu thì xem lại từ đầu.
  const keyDau = soCotTong > 0 ? thang[0].key : '';
  const keyCuoi = soCotTong > 0 ? thang[soCotTong - 1].key : '';
  useEffect(() => {
    datCua(null);
    datRo(null);
  }, [soCotTong, keyDau, keyCuoi]);

  function datDoan(soMoi, tuMoi) {
    const soKep = kep(Math.round(soMoi), toiThieu, soCotTong);
    if (soKep >= soCotTong) {
      datCua(null);
    } else {
      datCua({ tu: kep(Math.round(tuMoi), 0, soCotTong - soKep), so: soKep });
    }
  }

  /** Giữ nguyên cột ở vị trí con trỏ khi đổi số cột. */
  function phongTo(heSo, tamPhanSo = 0.5) {
    const soMoi = kep(Math.round(so * heSo), toiThieu, soCotTong);
    if (soMoi === so) {
      return;
    }
    const cotNeo = tu + so * tamPhanSo;
    datDoan(soMoi, cotNeo - soMoi * tamPhanSo);
  }

  function luot(soCot) {
    datDoan(so, tu + soCot);
  }

  // Ctrl + lăn chuột để phóng to, lăn thường vẫn cuộn trang.
  const phongToRef = useRef(phongTo);
  phongToRef.current = phongTo;
  useEffect(() => {
    const khung = khungRef.current;
    if (!khung || !coThePhongTo) {
      return undefined;
    }
    function khiLan(e) {
      if (!e.ctrlKey && !e.metaKey) {
        return;
      }
      e.preventDefault();
      const r = khung.getBoundingClientRect();
      const tam = r.width > 0 ? kep((e.clientX - r.left) / r.width, 0, 1) : 0.5;
      phongToRef.current(e.deltaY < 0 ? HE_SO_PHONG : 1 / HE_SO_PHONG, tam);
    }
    khung.addEventListener('wheel', khiLan, { passive: false });
    return () => khung.removeEventListener('wheel', khiLan);
  }, [coThePhongTo]);

  const hien = thang.slice(tu, tu + so);
  const soCot = hien.length;
  // Thang chiều cao tính trên toàn bộ dữ liệu để cột không đổi chiều cao khi lướt.
  const lonNhat = thang.reduce((a, m) => (m.tong !== null && m.tong > a ? m.tong : a), 1);
  const o = (RONG - 16) / Math.max(soCot, 1);
  const rongCot = Math.min(72, o * 0.46);
  const day = soCot > NGUONG_NHAN_TONG;
  const coPhanTram = soCot <= NGUONG_NHAN_PHAN_TRAM;
  const buocNhan = soCot > 14 ? Math.ceil(soCot / 12) : 1;
  const chiSoDangChon = hien.findIndex((m) => m.key === kyDangChon);

  const cot = hien.map((m, i) => {
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

  function khiRe(e) {
    if (keoRef.current) {
      return;
    }
    const r = khungRef.current.getBoundingClientRect();
    if (r.width <= 0) {
      return;
    }
    const xSvg = ((e.clientX - r.left) / r.width) * RONG;
    const chiSo = Math.floor((xSvg - 8) / o);
    if (chiSo < 0 || chiSo >= soCot) {
      datRo(null);
      return;
    }
    datRo({ chiSo, x: e.clientX - r.left, y: e.clientY - r.top, rongKhung: r.width });
  }

  function batDauKeo(e) {
    if (!dangPhongTo || (e.button !== undefined && e.button !== 0)) {
      return;
    }
    const r = khungRef.current.getBoundingClientRect();
    keoRef.current = { x0: e.clientX, tu0: tu, rongCot: r.width / so };
    if (e.currentTarget.setPointerCapture && e.pointerId !== undefined) {
      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch (loi) {
        // Không bắt được con trỏ (ví dụ môi trường test) thì vẫn kéo được trong khung.
      }
    }
    datRo(null);
  }

  function dangKeo(e) {
    const k = keoRef.current;
    if (!k || k.rongCot <= 0) {
      return;
    }
    datDoan(so, k.tu0 - (e.clientX - k.x0) / k.rongCot);
  }

  function ketThucKeo() {
    keoRef.current = null;
  }

  const cotRo = ro ? cot[ro.chiSo] : null;

  return (
    <div>
      {coThePhongTo ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', flexWrap: 'wrap', gap: 6, marginTop: 6, fontSize: coChu.ratNho, color: mau.chuNhan }}>
          <span style={{ marginRight: 'auto' }} aria-live="polite">
            {dangPhongTo
              ? `Đang xem ${so}/${soCotTong} ${donVi} (${thang[tu].nhanNgan}–${thang[tu + so - 1].nhanNgan}) · kéo biểu đồ để lướt`
              : `Ctrl + lăn chuột hoặc nút + để phóng to · ${soCotTong} ${donVi}`}
          </span>
          <button type="button" className="nut" style={{ height: 28, padding: '0 9px' }} aria-label="Lướt về trước" disabled={!dangPhongTo || tu === 0} onClick={() => luot(-Math.max(1, Math.round(so / 3)))}>
            ‹
          </button>
          <button type="button" className="nut" style={{ height: 28, padding: '0 9px' }} aria-label="Lướt về sau" disabled={!dangPhongTo || tu + so >= soCotTong} onClick={() => luot(Math.max(1, Math.round(so / 3)))}>
            ›
          </button>
          <button type="button" className="nut" style={{ height: 28, padding: '0 10px' }} aria-label="Thu nhỏ biểu đồ" disabled={!dangPhongTo} onClick={() => phongTo(1 / HE_SO_PHONG)}>
            −
          </button>
          <button type="button" className="nut" style={{ height: 28, padding: '0 10px' }} aria-label="Phóng to biểu đồ" disabled={so <= toiThieu} onClick={() => phongTo(HE_SO_PHONG)}>
            +
          </button>
          <button type="button" className="nut" style={{ height: 28, padding: '0 10px', fontSize: coChu.ratNho }} aria-label="Xem tất cả" disabled={!dangPhongTo} onClick={() => datCua(null)}>
            Tất cả
          </button>
        </div>
      ) : null}

      <div
        ref={khungRef}
        data-testid="khung-bieu-do"
        style={{ position: 'relative', marginTop: 6, cursor: dangPhongTo ? 'grab' : 'default', touchAction: dangPhongTo ? 'pan-y' : 'auto', userSelect: 'none' }}
        onMouseMove={khiRe}
        onMouseLeave={() => datRo(null)}
        onPointerDown={batDauKeo}
        onPointerMove={dangKeo}
        onPointerUp={ketThucKeo}
        onPointerCancel={ketThucKeo}
      >
        <svg viewBox={`0 0 ${RONG} 286`} role="img" aria-label={ariaLabel} style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}>
          {cotRo ? <rect data-testid="nen-re-chuot" x={(cotRo.x - 8).toFixed(1)} y="10" width={(rongCot + 16).toFixed(1)} height="262" rx="8" fill={mau.nenHang} /> : null}

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
              />
            )),
          )}

          {cot.map((c) => {
            if (c.m.tong === null) {
              return null;
            }
            const pct = canhBaoTheoKy[c.m.key];
            const coCanhBao = pct !== undefined;
            const x = (c.x + rongCot / 2).toFixed(1);
            if (day) {
              if (coCanhBao) {
                return <circle key={`canh-bao-${c.i}`} data-testid="cham-canh-bao" cx={x} cy={(c.dinh - 8).toFixed(1)} r="3.5" fill={canhBao.chinh} />;
              }
              if (c.m.key !== kyDangChon) {
                return null;
              }
            }
            const chu = coCanhBao && coPhanTram ? `${rutGonTien(c.m.tong)} · −${dinhDangPhanTram(Math.abs(pct))}` : rutGonTien(c.m.tong);
            return (
              <text
                key={`nhan-tong-${c.i}`}
                x={x}
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
            const dangChon = c.i === chiSoDangChon;
            const coCanhBao = canhBaoTheoKy[c.m.key] !== undefined;
            const dungBuoc = c.i % buocNhan === 0;
            // Nhãn theo bước sát kỳ đang chọn thì bỏ để không đè.
            const satDangChon = chiSoDangChon >= 0 && !dangChon && Math.abs(c.i - chiSoDangChon) < buocNhan;
            const hienNhan = dangChon || (dungBuoc && !satDangChon) || (!day && coCanhBao);
            if (!hienNhan) {
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

        {cotRo ? <KhungChuThich cot={cotRo} danhSachLop={danhSachLop} canhBaoTheoKy={canhBaoTheoKy} ro={ro} /> : null}
      </div>
    </div>
  );
}

function KhungChuThich({ cot, danhSachLop, canhBaoTheoKy, ro }) {
  const m = cot.m;
  const pct = canhBaoTheoKy[m.key];
  const veBenTrai = ro.x > ro.rongKhung * 0.6; // gần mép phải thì mở khung sang trái cho khỏi tràn
  const lopTrenXuong = [];
  if (m.tong !== null) {
    m.lop.forEach((l, L) => {
      if (l.doanhThu > 0) {
        lopTrenXuong.unshift({ ...l, ...danhSachLop[L] });
      }
    });
  }
  return (
    <div
      role="tooltip"
      data-testid="khung-chu-thich"
      style={{
        position: 'absolute',
        left: ro.x,
        top: Math.max(0, ro.y - 8),
        transform: `translate(${veBenTrai ? 'calc(-100% - 14px)' : '14px'}, 0)`,
        zIndex: 5,
        minWidth: 190,
        maxWidth: 260,
        padding: '10px 12px',
        background: mau.nenThe,
        border: `1px solid ${mau.vienThe}`,
        borderRadius: boGoc.oTrangThai,
        boxShadow: bong.danhSachXo,
        fontSize: coChu.ratNho,
        color: mau.chuPhu,
        pointerEvents: 'none',
      }}
    >
      <div style={{ fontWeight: 600, color: mau.chuChinh, fontSize: coChu.nho }}>
        {m.nhanDayDu}
        {m.daDu ? '' : ' · chưa đủ ngày'}
      </div>
      {m.tong === null ? (
        <div style={{ marginTop: 4 }}>Không có dữ liệu</div>
      ) : (
        <>
          <div style={{ marginTop: 4, display: 'flex', justifyContent: 'space-between', gap: 12 }}>
            <span>Doanh thu</span>
            <span className="so" style={{ fontWeight: 600, color: mau.chuChinh }}>
              {dinhDangTien(m.tong)}
            </span>
          </div>
          {lopTrenXuong.length > 0 ? (
            <div style={{ marginTop: 6, paddingTop: 6, borderTop: `1px solid ${mau.vienTrong}`, display: 'grid', gap: 3 }}>
              {lopTrenXuong.map((l) => (
                <div key={l.nhan} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 3, background: l.mau, flex: 'none' }} />
                  <span style={{ flex: 1 }}>{l.nhan}</span>
                  <span className="so">{dinhDangTien(l.doanhThu)}</span>
                  <span className="so" style={{ width: 44, textAlign: 'right', color: mau.chuMo }}>
                    {dinhDangPhanTram((l.doanhThu / m.tong) * 100, 0)}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
          {pct !== undefined ? (
            <div style={{ marginTop: 6, color: canhBao.chuDam, fontWeight: 600 }}>
              Giảm {dinhDangPhanTram(Math.abs(pct))} so với kỳ trước, vượt ngưỡng cảnh báo
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
