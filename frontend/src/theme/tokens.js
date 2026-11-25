// Định nghĩa toàn bộ màu sắc, kích thước chữ, bán kính bo góc, đổ bóng
export const mau = {
  nenTrang: '#F3F4F8',
  nenThe: '#FFFFFF',
  nenTheKinh: 'rgba(255, 255, 255, 0.92)',
  nenPhu: '#FAFAFC',
  nenHang: '#F7F8FB',
  vienThe: '#E9EBF2',
  vienTrong: '#F0F1F6',
  vienChip: '#E1E4EC',
  vienChipHover: '#C9CDDA',
  chuChinh: '#1A1D29',
  chuPhu: '#3B4054',
  chuNhan: '#5D6378', // đạt tỷ lệ tương phản >= 4,5:1 trên nền trắng
  chuMo: '#6B7186',
  chuDonVi: '#8A90A3', // chỉ dùng cho đơn vị "đ" cạnh số lớn
  thanhNen: '#F1F2F7',
  cotXam: '#ECEEF5',
  phuNen: 'rgba(26,29,41,.45)',
  chuTrenNen: '#B9BED6',
};

/** Màu chủ đạo không đổi theo sàn. */
export const chuDao = {
  chinh: '#5B4BE0',
  dam: '#4535C4',
  nhat: '#F1F0FE',
  nhatHon: '#F3F2FE',
  sang: '#A79CF7',
  nenSlot: '#F6F5FF',
  nenAvatar: '#EEEBFE',
  nenBanner: '#F8F7FF',
  vienBanner: '#E4E0FB',
  nenIconBanner: '#ECE9FD',
  chonVan: '#E3DFFC',
  nutChinhHover: '#4C3CD3',
  thanhPhu: '#C9C2FA',
  thanhTinh: '#8E7FF5',
};

/** Màu sàn chỉ để phân biệt sàn, không dùng cho nút hay trạng thái. */
export const san = {
  shopee: { chinh: '#F26B4A', nhat: '#FEEDE8', chu: '#A3360F' },
  tiktok: { chinh: '#27C2B0', nhat: '#E3F7F4', chu: '#0B6B61' },
};

export const dangNhap = {
  duongA: '#FF6A3D',
  duongB: '#10B3A3',
};

/** Màu trang đăng nhập. */
export const tranhDangNhap = {
  nenTrang: '#F2F5FD',
  nenThe: '#FFFFFF',
  vienThe: '#2860E1',
  vienTheNhat: '#DCE5F7',
  bongThe: '0 24px 64px rgba(35, 80, 200, 0.12)',
  nutLogin: '#2B63E6',
  nutLoginHover: '#1D52D0',
  bongNut: '0 8px 24px rgba(43, 99, 230, 0.38)',
  chuTieuDe: '#1C2336',
  chuMo: '#8792A6',
  chuNhan: '#5F687A',
  duongKe: '#E2E8F4',
  duongKeHover: '#B9CBE8',
  duongKeFocus: '#2860E1',
  loiBg: '#FFF5F6',
  loiBorder: '#F7D3D8',
  loiChu: '#8E1B2E',
  mayA: '#DCE8FC',
  mayB: '#C5DCFA',
  mayC: '#ACCCF7',
  mayD: '#8EB6F2',
  mayE: '#6E9EE8',
  bangVien: '#BACFEF',
  bangNen: '#FFFFFF',
  bangDock: '#E7F0FA',
  bangCham: '#77A3EA',
  pieDam: '#3E6BC7',
  pieVua: '#78A2EC',
  pieNhat: '#BAD2F8',
  cotThanhA: '#588AE8',
  cotThanhB: '#8CB2F3',
  cotThanhNhat: '#D1E2FA',
  theMini: '#F2F6FD',
  theMiniVien: '#CFDEF5',
  toc: '#182136',
  aoQuan: '#4973C8',
  aoQuanDam: '#375EAD',
  aoQuanSang: '#6A92DC',
  giay: '#1A2338',
  da: '#FCE7DA',
  ho3D: '#1A2846',
  ho3DVien: '#293E6B',
  cot3DA: '#5C8CE8',
  cot3DB: '#4275D6',
  cot3DC: '#2A5CBE',
  cot3DSang: '#88ACF3',
  dongXuTop: '#B5D0F8',
  dongXuCanh: '#5684DF',
  dongXuDam: '#3765C4',
  bongMo: 'rgba(28, 48, 88, 0.12)',
  keSan: '#D5E3F7',
  nenBlobA: '#D4E3FB',
  nenBlobB: '#C2D7F8',
  glassNen: 'rgba(255, 255, 255, 0.85)',
  glassVien: '#FFFFFF',
  glassVienNgoai: '#D8E5F8',
  glassBong: '0 8px 24px rgba(160, 188, 232, 0.28), inset 0 2px 3px rgba(255, 255, 255, 0.95)',
  glassBongFocus: '0 8px 26px rgba(40, 96, 225, 0.32), inset 0 2px 3px rgba(255, 255, 255, 1)',
  iconO: '#64748B',
  iconOHover: '#2563EB',
  checkboxVien: '#CBD5E1',
  checkboxVienFocus: '#2563EB',
  linkQuenMk: '#2563EB',
  linkQuenMkHover: '#1D4ED8',
  popupOverlay: 'rgba(15, 23, 42, 0.45)',
  matBuonVang: '#FBBF24',
  matBuonVien: '#F59E0B',
  matBuonMat: '#78350F',
  matBuonNuocMat: '#60A5FA',
  nutPopup: '#2860E1',
  nutPopupHover: '#1C4DC2',
  muiTenNen: 'rgba(255, 255, 255, 0.22)',
};

/** Hai kênh bán trong bán nguyệt, không phải màu sàn. */
export const kenhBan = {
  lienKet: '#5B4BE0',
  tuBan: '#27C2B0',
};

export const maSanPham = {
  day: ['#4F3FD1', '#8E7FF5', '#5C8DF6', '#27C2B0', '#A9E9E0'],
  theoMa: {
    M15: { dam: '#4F3FD1', nhat: '#EEEBFE' },
    BU01: { dam: '#8E7FF5', nhat: '#F3F1FE' },
    'M6 Pro': { dam: '#5C8DF6', nhat: '#EAF1FE' },
    M5: { dam: '#27C2B0', nhat: '#E3F7F4' },
  },
  macDinh: { dam: '#7FD8CC', nhat: '#EAF8F6' }, // mã không nằm trong 4 mã trên
};

/** Tăng, giảm theo nghĩa tốt hay xấu, không theo dấu. */
export const nhanThayDoi = {
  tot: { chu: '#0B7A68', nen: '#E3F7F2' },
  xau: { chu: '#B4233A', nen: '#FDECEE' },
  trungTinh: { chu: '#5D6378', nen: '#F1F2F7' },
};

export const canhBao = {
  chinh: '#D83A52',
  nen: '#FFF5F6',
  vien: '#F7D3D8',
  nenIcon: '#FDE3E7',
  chu: '#8E1B2E',
  chuDam: '#B4233A',
  vang: '#E59A1A',
  nenVang: '#FFF8EC',
  nenVangNhat: '#FFF1D6',
  chuVang: '#8A5300',
  xanh: '#1FA387',
  nenXanh: '#F2FBF8',
  nenOChay: '#E3F7F4',
  chuOChay: '#0E7C6B',
};

export const gachCheo = {
  dam: '#C9CDDA',
  nhat: '#EEF0F5',
};

export const coChu = {
  tieuDe: 24,
  soLon: 26,
  soLonNhat: 28,
  tieuDeThe: 14,
  thuong: 14,
  nho: 13,
  ratNho: 12,
  nhan: 11,
};

export const boGoc = { the: 16, oTrangThai: 12, nut: 9, nhan: 6, navNoi: 20 };

export const bong = {
  the: '0 1px 2px rgba(20,24,40,.04), 0 6px 18px rgba(20,24,40,.03)',
  nutChon: '0 1px 2px rgba(20,24,40,.12)',
  danhSachXo: '0 2px 4px rgba(20,24,40,.06), 0 12px 28px rgba(20,24,40,.12)',
  navNoi: '0 10px 32px -4px rgba(20, 24, 40, 0.08), 0 4px 12px -2px rgba(20, 24, 40, 0.04)',
  topbarNoi: '0 8px 24px -4px rgba(20, 24, 40, 0.06), 0 2px 8px -2px rgba(20, 24, 40, 0.03)',
  mucNavActive: '0 2px 8px rgba(91, 75, 224, 0.12)',
};

export const khoangCach = {
  leNgang: 28,
  giuaThe: 16,
  giuaKhoi: 18,
  trongThe: '18px 20px',
  toiDaNoiDung: 1320,
  rongMenu: 248,
};

/** Số liệu luôn dùng tabular-nums. */
export const font = {
  chu: "'Be Vietnam Pro', system-ui, sans-serif",
};

export const kieu = {
  so: { fontVariantNumeric: 'tabular-nums' },
  the: {
    background: mau.nenThe,
    border: `1px solid ${mau.vienThe}`,
    borderRadius: boGoc.the,
    boxShadow: bong.the,
    minWidth: 0,
    boxSizing: 'border-box',
  },
};

export const tokenAntd = {
  colorPrimary: chuDao.chinh,
  colorBgLayout: mau.nenTrang,
  colorBgContainer: mau.nenThe,
  colorBorder: mau.vienChip,
  colorBorderSecondary: mau.vienTrong,
  colorText: mau.chuChinh,
  colorTextSecondary: mau.chuPhu,
  colorTextTertiary: mau.chuNhan,
  colorError: canhBao.chinh,
  colorBgMask: mau.phuNen,
  borderRadius: boGoc.nut,
  borderRadiusLG: boGoc.the,
  fontFamily: font.chu,
  fontSize: coChu.thuong,
};
