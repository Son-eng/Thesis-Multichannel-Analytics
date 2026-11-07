import { mau, chuDao, boGoc, font, canhBao } from './tokens.js';

// CSS toàn cục sinh từ token. Viết ở dạng chuỗi JS (không phải file .css)
// để mọi mã màu nằm trong src/theme/ và test quét hex không bị vướng.
export const cssToanCuc = `
html, body, #root { margin: 0; min-height: 100%; }
body { background: ${mau.nenTrang}; font-family: ${font.chu}; font-size: 14px; line-height: 1.5; color: ${mau.chuChinh}; }
a { color: ${chuDao.chinh}; text-underline-offset: 3px; }
a:hover { color: ${chuDao.dam}; }
::selection { background: ${chuDao.chonVan}; }
button, select, input { font: inherit; color: inherit; }
button:focus-visible, a:focus-visible, select:focus-visible { outline: 2px solid ${chuDao.chinh}; outline-offset: 2px; }
.so { font-variant-numeric: tabular-nums; }
.chip { position: relative; display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 10px; border: 1px solid ${mau.vienChip}; border-radius: ${boGoc.nut}px; background: ${mau.nenThe}; font-size: 13px; color: ${mau.chuPhu}; cursor: pointer; }
.chip:hover { border-color: ${mau.vienChipHover}; }
.chip select { appearance: none; -webkit-appearance: none; border: 0; background: transparent; padding: 0 18px 0 0; font-size: 13px; font-weight: 500; color: ${mau.chuChinh}; cursor: pointer; }
.chip select:focus-visible { outline: none; }
.chip:focus-within { outline: 2px solid ${chuDao.chinh}; outline-offset: 2px; }
.nav { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border: 0; border-radius: ${boGoc.nut}px; text-align: left; cursor: pointer; font-size: 14px; color: ${mau.chuPhu}; text-decoration: none; background: transparent; width: 100%; box-sizing: border-box; }
.nav:hover { background: ${mau.nenHang}; color: ${mau.chuChinh}; }
.nhom { font-size: 11px; font-weight: 600; letter-spacing: .06em; color: ${mau.chuMo}; padding: 16px 10px 6px; }
.bang { width: 100%; border-collapse: collapse; }
.bang th { font-size: 11px; font-weight: 600; letter-spacing: .05em; color: ${mau.chuMo}; text-align: right; padding: 9px 12px; background: ${mau.nenHang}; text-transform: uppercase; }
.bang th:first-child { border-radius: 8px 0 0 8px; text-align: left; }
.bang th:last-child { border-radius: 0 8px 8px 0; }
.bang td { padding: 12px; border-bottom: 1px solid ${mau.vienTrong}; text-align: right; font-variant-numeric: tabular-nums; }
.bang td:first-child { text-align: left; }
.bang tr:last-child td { border-bottom: 0; }
/* Bảng nhiều cột (lịch sử đồng bộ): lề hẹp, tiêu đề được xuống dòng, ô không xuống dòng — vừa khung 1440 px, hẹp hơn thì cuộn ngang trong khung bảng. */
.bang-gon th, .bang-gon td { padding-left: 8px; padding-right: 8px; }
.bang-gon th { white-space: normal; line-height: 1.25; vertical-align: bottom; }
.bang-gon td { white-space: nowrap; }
.nut { display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 34px; padding: 0 14px; border-radius: ${boGoc.nut}px; border: 1px solid ${mau.vienChip}; background: ${mau.nenThe}; cursor: pointer; font-size: 13px; font-weight: 500; color: ${mau.chuChinh}; text-decoration: none; }
.nut:hover:not(:disabled) { border-color: ${mau.vienChipHover}; background: ${mau.nenPhu}; }
.nut:disabled { opacity: .55; cursor: not-allowed; }
.nut-chinh { background: ${chuDao.chinh}; border-color: ${chuDao.chinh}; color: ${mau.nenThe}; }
.nut-chinh:hover:not(:disabled) { background: ${chuDao.nutChinhHover}; border-color: ${chuDao.nutChinhHover}; }
.nut-nguy { color: ${canhBao.chuDam}; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.o-nhap { display: block; width: 100%; box-sizing: border-box; height: 42px; padding: 0 12px; border: 1px solid ${mau.vienChip}; border-radius: ${boGoc.nut}px; background: ${mau.nenThe}; font-size: 14px; color: ${mau.chuChinh}; }
.o-nhap:hover { border-color: ${mau.vienChipHover}; }
.o-nhap:focus-visible { outline: 2px solid ${chuDao.chinh}; outline-offset: 1px; }
.nhan-o { display: block; font-size: 13px; font-weight: 500; color: ${mau.chuPhu}; margin-bottom: 6px; }
.dang-nhap { min-height: 100vh; display: grid; grid-template-columns: 1.1fr 1fr; }
@media (max-width: 900px) { .dang-nhap { grid-template-columns: 1fr; } .dang-nhap-tranh { display: none !important; } }
@keyframes xoay { to { transform: rotate(360deg); } }
.xoay { width: 12px; height: 12px; border-radius: 50%; border: 2px solid currentColor; border-right-color: transparent; display: inline-block; animation: xoay .8s linear infinite; }
@keyframes khungXam { 0% { opacity: .55; } 50% { opacity: 1; } 100% { opacity: .55; } }
.khung-xam { background: ${mau.thanhNen}; border-radius: 8px; animation: khungXam 1.4s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .khung-xam, .xoay { animation: none; } * { transition: none !important; } }
`;
