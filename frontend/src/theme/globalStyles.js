import { mau, chuDao, boGoc, bong, font, canhBao, tranhDangNhap, khoangCach } from './tokens.js';

// CSS toàn cục viết dạng chuỗi JS để mọi mã màu nằm trong src/theme/.
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
/* Danh sách xổ ra bo góc (Chrome/Edge mới). Vẫn là thẻ <select> thật; trình duyệt chưa hỗ trợ thì bỏ qua khối này và dùng danh sách gốc. */
@supports (appearance: base-select) {
  .chip select, .chip select::picker(select) { appearance: base-select; }
  .chip select::picker-icon { display: none; }
  .chip { anchor-scope: --chip-chon; anchor-name: --chip-chon; }
  .chip select::picker(select) { position-anchor: --chip-chon; box-sizing: border-box; min-width: anchor-size(width); margin-top: 6px; padding: 6px; border: 1px solid ${mau.vienThe}; border-radius: ${boGoc.oTrangThai}px; background: ${mau.nenThe}; box-shadow: ${bong.danhSachXo}; }
  .chip select option { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: ${boGoc.nut - 1}px; font-size: 13px; font-weight: 500; color: ${mau.chuPhu}; cursor: pointer; white-space: nowrap; }
  .chip select option:hover { background: ${mau.nenHang}; color: ${mau.chuChinh}; }
  .chip select option:checked { background: ${chuDao.nhat}; color: ${chuDao.dam}; font-weight: 600; }
  .chip select option:focus-visible { outline: 2px solid ${chuDao.chinh}; outline-offset: -2px; }
  .chip select option::checkmark { display: none; }
}
.nav { display: flex; align-items: center; gap: 10px; height: 38px; padding: 0 12px; border: 0; border-radius: ${boGoc.nut + 2}px; text-align: left; cursor: pointer; font-size: 14px; color: ${mau.chuPhu}; text-decoration: none; background: transparent; width: 100%; box-sizing: border-box; transition: all .2s cubic-bezier(0.16, 1, 0.3, 1); }
.nav:hover { background: ${mau.nenHang}; color: ${mau.chuChinh}; transform: translateX(3px); }
.nav.active { background: ${chuDao.nhat}; color: ${chuDao.chinh}; font-weight: 600; box-shadow: ${bong.mucNavActive}; }
.nhom { font-size: 11px; font-weight: 700; letter-spacing: .08em; color: ${mau.chuMo}; padding: 18px 12px 6px; text-transform: uppercase; }

/* Thanh điều hướng nổi (floating navigation dock) */
.thanh-nav-noi { box-sizing: border-box; background: ${mau.nenThe}; border: 1px solid ${mau.vienThe}; border-radius: ${boGoc.navNoi}px; box-shadow: ${bong.navNoi}; padding: 16px 12px; display: flex; flex-direction: column; height: 100%; transition: box-shadow .25s ease; scrollbar-width: thin; scrollbar-color: ${mau.vienChip} transparent; }
.thanh-nav-noi:hover { box-shadow: 0 14px 40px -4px rgba(20, 24, 40, 0.12), 0 6px 16px -2px rgba(20, 24, 40, 0.05); }
.thanh-nav-noi::-webkit-scrollbar { width: 4px; }
.thanh-nav-noi::-webkit-scrollbar-thumb { background: ${mau.vienChip}; border-radius: 9999px; }
.thanh-nav-noi::-webkit-scrollbar-track { background: transparent; }

/* Thanh trên nổi bám dính khi cuộn trang (floating sticky topbar) */
.thanh-topbar-noi { position: sticky; top: 14px; z-index: 40; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 24px; margin: 14px ${khoangCach.leNgang}px 0 0; background: ${mau.nenTheKinh}; backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-radius: ${boGoc.the}px; border: 1px solid ${mau.vienThe}; box-shadow: ${bong.topbarNoi}; box-sizing: border-box; transition: box-shadow .2s ease; }
.thanh-topbar-noi:hover { box-shadow: ${bong.the}; }
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

/* Trang đăng nhập phong cách mới (khung bo viền xanh và tranh minh họa) */
.dang-nhap-wrapper { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 32px 20px; box-sizing: border-box; background: ${tranhDangNhap.nenTrang}; position: relative; overflow: hidden; }
.dang-nhap-the { width: 100%; max-width: 1060px; min-height: 580px; background: ${tranhDangNhap.nenThe}; border: 2.5px solid ${tranhDangNhap.vienThe}; border-radius: 36px; box-shadow: ${tranhDangNhap.bongThe}; display: grid; grid-template-columns: 370px 1fr; position: relative; z-index: 2; overflow: hidden; box-sizing: border-box; }
@media (max-width: 940px) {
  .dang-nhap-the { grid-template-columns: 1fr; max-width: 460px; border-radius: 24px; }
  .dang-nhap-tranh-moi { display: none !important; }
}
.o-nhap-gach-duoi { display: block; width: 100%; box-sizing: border-box; height: 38px; padding: 4px 0; border: none; border-bottom: 1.5px solid ${tranhDangNhap.duongKe}; background: transparent; font-size: 14px; color: ${tranhDangNhap.chuTieuDe}; outline: none; transition: border-color .2s ease; }
.o-nhap-gach-duoi:hover { border-bottom-color: ${tranhDangNhap.duongKeHover}; }
.o-nhap-gach-duoi:focus { border-bottom-color: ${tranhDangNhap.duongKeFocus}; }

/* 2 ô nhập liệu dạng nổi Glassmorphism theo ảnh mẫu */
.o-nhap-glass-khung { position: relative; display: flex; align-items: center; width: 100%; height: 50px; box-sizing: border-box; border-radius: 9999px; background: ${tranhDangNhap.glassNen}; border: 1.5px solid ${tranhDangNhap.glassVienNgoai}; box-shadow: ${tranhDangNhap.glassBong}; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); transition: all .2s ease; }
.o-nhap-glass-khung:hover { border-color: ${tranhDangNhap.vienTheNhat}; box-shadow: 0 10px 28px rgba(160, 188, 232, 0.35), inset 0 2px 3px rgba(255, 255, 255, 0.95); }
.o-nhap-glass-khung:focus-within { border-color: ${tranhDangNhap.vienThe}; box-shadow: ${tranhDangNhap.glassBongFocus}; }
.o-nhap-glass-icon { display: flex; align-items: center; justify-content: center; padding-left: 20px; color: ${tranhDangNhap.iconO}; flex-shrink: 0; }
.o-nhap-glass-ruot { width: 100%; height: 100%; border: none; background: transparent; padding: 0 18px 0 12px; font-size: 14px; color: ${tranhDangNhap.chuTieuDe}; outline: none; box-sizing: border-box; }
.o-nhap-glass-ruot::placeholder { color: ${tranhDangNhap.chuMo}; font-size: 13.5px; }

/* Hàng Remember Me và Forgot Password */
.hang-tuy-chon { display: flex; align-items: center; justify-content: space-between; margin: 16px 4px 26px; }
.checkbox-bo-goc { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; font-size: 13px; font-weight: 500; color: ${tranhDangNhap.chuNhan}; }
.checkbox-bo-goc-hop { width: 20px; height: 20px; border-radius: 6px; border: 1.5px solid ${tranhDangNhap.checkboxVien}; background: ${tranhDangNhap.nenThe}; display: flex; align-items: center; justify-content: center; transition: all .15s ease; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06); }
.checkbox-bo-goc-hop.da-chon { background: ${tranhDangNhap.nutLogin}; border-color: ${tranhDangNhap.nutLogin}; }
.link-quen-mk { background: transparent; border: none; padding: 0; color: ${tranhDangNhap.linkQuenMk}; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; transition: color .15s ease; }
.link-quen-mk:hover { color: ${tranhDangNhap.linkQuenMkHover}; text-decoration: underline; }

/* Nút Login dạng pill viền tròn kèm mũi tên */
.nut-login-pill { display: flex; align-items: center; justify-content: center; width: 100%; height: 48px; border-radius: 9999px; border: none; background: linear-gradient(135deg, ${tranhDangNhap.nutLogin} 0%, ${tranhDangNhap.nutLoginHover} 100%); color: ${mau.nenThe}; font-size: 15px; font-weight: 700; letter-spacing: .03em; cursor: pointer; box-shadow: ${tranhDangNhap.bongNut}; transition: all .2s ease; position: relative; }
.nut-login-pill:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 10px 28px rgba(43, 99, 230, 0.45); }
.nut-login-pill:active:not(:disabled) { transform: translateY(0); }
.nut-login-pill:disabled { opacity: .6; cursor: not-allowed; }
.nut-login-pill-mui-ten { position: absolute; right: 8px; width: 34px; height: 34px; border-radius: 50%; background: ${tranhDangNhap.muiTenNen}; display: flex; align-items: center; justify-content: center; transition: transform .2s ease; }
.nut-login-pill:hover .nut-login-pill-mui-ten { transform: translateX(2px); }

/* Popup Quên mật khẩu */
.popup-quen-mk-overlay { position: fixed; inset: 0; background: ${tranhDangNhap.popupOverlay}; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; animation: popupFadeIn .2s ease; }
@keyframes popupFadeIn { from { opacity: 0; } to { opacity: 1; } }
.popup-quen-mk-the { width: 100%; max-width: 410px; background: ${tranhDangNhap.nenThe}; border-radius: 28px; padding: 36px 30px 28px; text-align: center; box-shadow: 0 24px 60px rgba(15, 30, 70, 0.22); border: 1.5px solid ${tranhDangNhap.vienTheNhat}; animation: popupScaleUp .25s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes popupScaleUp { from { transform: scale(0.92); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.popup-nut-dong { width: 100%; height: 42px; border-radius: 9999px; border: none; background: ${tranhDangNhap.nutPopup}; color: ${mau.nenThe}; font-size: 14px; font-weight: 600; cursor: pointer; transition: background .15s ease; }
.popup-nut-dong:hover { background: ${tranhDangNhap.nutPopupHover}; }

.nut-login-moi { display: inline-flex; align-items: center; justify-content: center; height: 40px; padding: 0 34px; border-radius: 8px; border: none; background: ${tranhDangNhap.nutLogin}; color: ${mau.nenThe}; font-size: 13px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; cursor: pointer; box-shadow: ${tranhDangNhap.bongNut}; transition: background .15s ease, transform .1s ease, box-shadow .15s ease; }
.nut-login-moi:hover:not(:disabled) { background: ${tranhDangNhap.nutLoginHover}; transform: translateY(-1px); }
.nut-login-moi:active:not(:disabled) { transform: translateY(0); }
.nut-login-moi:disabled { opacity: .6; cursor: not-allowed; }

/* Thanh trượt danh sách gian hàng (horizontal shop slider) */
.thanh-truot-gian-hang-khung { position: relative; width: 100%; box-sizing: border-box; }
.thanh-truot-gian-hang-dau { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.thanh-truot-gian-hang-tieu-de { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: ${mau.chuChinh}; }
.thanh-truot-so-luong { display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px; padding: 0 7px; border-radius: 9999px; background: ${chuDao.nhatHon}; color: ${chuDao.chinh}; font-size: 12px; font-weight: 700; }
.thanh-truot-gian-hang-nut-nhom { display: flex; align-items: center; gap: 8px; }
.thanh-truot-nut-bam { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 50%; border: 1.5px solid ${mau.vienChip}; background: ${mau.nenThe}; color: ${mau.chuChinh}; cursor: pointer; transition: all .18s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: ${bong.nutChon}; }
.thanh-truot-nut-bam:hover:not(:disabled) { border-color: ${chuDao.chinh}; color: ${chuDao.chinh}; background: ${chuDao.nhatHon}; transform: scale(1.08); box-shadow: 0 4px 12px rgba(91, 75, 224, 0.18); }
.thanh-truot-nut-bam:active:not(:disabled) { transform: scale(0.96); }
.thanh-truot-nut-bam:disabled { opacity: 0.35; cursor: not-allowed; transform: none; box-shadow: none; }
.thanh-truot-gian-hang-chua { display: flex; gap: ${khoangCach.giuaThe}px; overflow-x: auto; scroll-behavior: smooth; scroll-snap-type: x mandatory; padding: 4px 2px 14px; box-sizing: border-box; scrollbar-width: thin; scrollbar-color: ${mau.vienChip} transparent; }
.thanh-truot-gian-hang-chua::-webkit-scrollbar { height: 6px; }
.thanh-truot-gian-hang-chua::-webkit-scrollbar-thumb { background: ${mau.vienChip}; border-radius: 9999px; }
.thanh-truot-gian-hang-chua::-webkit-scrollbar-thumb:hover { background: ${mau.vienChipHover}; }
.thanh-truot-gian-hang-chua::-webkit-scrollbar-track { background: transparent; }
.thanh-truot-gian-hang-item { flex: 0 0 295px; width: 295px; min-width: 295px; scroll-snap-align: start; box-sizing: border-box; }

.dang-nhap { min-height: 100vh; display: grid; grid-template-columns: 1.1fr 1fr; }
@media (max-width: 900px) { .dang-nhap { grid-template-columns: 1fr; } .dang-nhap-tranh { display: none !important; } }
@keyframes xoay { to { transform: rotate(360deg); } }
.xoay { width: 12px; height: 12px; border-radius: 50%; border: 2px solid currentColor; border-right-color: transparent; display: inline-block; animation: xoay .8s linear infinite; }
@keyframes khungXam { 0% { opacity: .55; } 50% { opacity: 1; } 100% { opacity: .55; } }
.khung-xam { background: ${mau.thanhNen}; border-radius: 8px; animation: khungXam 1.4s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .khung-xam, .xoay { animation: none; } * { transition: none !important; } }
`;
