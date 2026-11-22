// Hệ giao diện: MỌI màu, cỡ chữ, bo góc, bóng, khoảng cách khai báo MỘT lần ở đây.
// Component chỉ đọc từ file này. Không viết mã màu hex ở file nào khác trong src/
// (có test quét; thư mục src/theme/ được miễn).
// Muốn đổi giao diện: sửa giá trị ở đây, mọi trang đổi theo.

/** Màu nền, viền, chữ. */
export const mau = {
  nenTrang: '#F3F4F8', // nền toàn trang (colorBgLayout)
  nenThe: '#FFFFFF', // nền thẻ, menu, thanh trên (colorBgContainer)
  nenTheKinh: 'rgba(255, 255, 255, 0.92)', // nền kính mờ cho thanh trên nổi
  nenPhu: '#FAFAFC', // nền ô phụ (ô đồng bộ ở chân menu)
  nenHang: '#F7F8FB', // nền hàng tiêu đề bảng, nền mục menu khi rê chuột
  vienThe: '#E9EBF2', // viền thẻ (colorBorder)
  vienTrong: '#F0F1F6', // đường kẻ trong thẻ (colorBorderSecondary)
  vienChip: '#E1E4EC', // viền ô chọn, nút
  vienChipHover: '#C9CDDA', // viền ô chọn khi rê chuột
  chuChinh: '#1A1D29', // chữ chính
  chuPhu: '#3B4054', // chữ phụ
  chuNhan: '#5D6378', // nhãn nhỏ, đạt tỷ lệ tương phản >= 4,5:1 trên nền trắng
  chuMo: '#6B7186', // nhãn nhóm, chú thích trục
  chuDonVi: '#8A90A3', // CHỈ dùng cho đơn vị "đ" cạnh số lớn
  thanhNen: '#F1F2F7', // nền thanh tỷ trọng, nền nhãn trung tính
  cotXam: '#ECEEF5', // cột biểu đồ không nổi bật
  phuNen: 'rgba(26,29,41,.45)', // lớp phủ mờ phía sau hộp thoại
  chuTrenNen: '#B9BED6', // chữ phụ trên nền tối (trang đăng nhập)
};

/** Màu chủ đạo của giao diện: KHÔNG đổi theo sàn. */
export const chuDao = {
  chinh: '#5B4BE0', // mục menu đang chọn, nút chính, cột nổi bật
  dam: '#4535C4',
  nhat: '#F1F0FE',
  nhatHon: '#F3F2FE', // nền biểu tượng trong thẻ chỉ số
  sang: '#A79CF7', // đầu sáng của dải chuyển sắc cột nổi bật
  nenSlot: '#F6F5FF', // nền nhạt phía sau tháng đang chọn
  nenAvatar: '#EEEBFE',
  nenBanner: '#F8F7FF',
  vienBanner: '#E4E0FB',
  nenIconBanner: '#ECE9FD',
  chonVan: '#E3DFFC', // màu bôi chọn chữ
  nutChinhHover: '#4C3CD3',
  thanhPhu: '#C9C2FA', // thanh "các tỉnh còn lại"
  thanhTinh: '#8E7FF5', // thanh tỉnh/thành
};

/** Màu nhận diện sàn: chỉ để phân biệt sàn, không dùng cho nút hay trạng thái. */
export const san = {
  shopee: { chinh: '#F26B4A', nhat: '#FEEDE8', chu: '#A3360F' },
  tiktok: { chinh: '#27C2B0', nhat: '#E3F7F4', chu: '#0B6B61' },
};

/** Hai đường minh họa ở trang đăng nhập (màu hai sàn, chỉ để trang trí). */
export const dangNhap = {
  duongA: '#FF6A3D',
  duongB: '#10B3A3',
};

/** Bảng màu trang đăng nhập phong cách mới (khung thẻ viền xanh, tranh minh họa bảng phân tích). */
export const tranhDangNhap = {
  nenTrang: '#F2F5FD', // nền ngoài toàn trang
  nenThe: '#FFFFFF', // nền thẻ chính
  vienThe: '#2860E1', // viền xanh đậm bo quanh thẻ
  vienTheNhat: '#DCE5F7',
  bongThe: '0 24px 64px rgba(35, 80, 200, 0.12)',
  nutLogin: '#2B63E6', // nút xanh Login
  nutLoginHover: '#1D52D0',
  bongNut: '0 8px 24px rgba(43, 99, 230, 0.38)',
  chuTieuDe: '#1C2336', // chữ Login đậm
  chuMo: '#8792A6', // chữ phụ mờ
  chuNhan: '#5F687A', // nhãn input
  duongKe: '#E2E8F4', // gạch chân dưới input
  duongKeHover: '#B9CBE8',
  duongKeFocus: '#2860E1',
  loiBg: '#FFF5F6',
  loiBorder: '#F7D3D8',
  loiChu: '#8E1B2E',
  // Màu cho tranh minh họa dashboard
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
  // Nhân vật
  toc: '#182136',
  aoQuan: '#4973C8',
  aoQuanDam: '#375EAD',
  aoQuanSang: '#6A92DC',
  giay: '#1A2338',
  da: '#FCE7DA',
  // Khối 3D
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
  // Glassmorphism nổi cho 2 ô nhập liệu & các thành phần mới
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

/** Hai kênh bán trong bán nguyệt "Doanh thu theo kênh bán" (không phải màu sàn). */
export const kenhBan = {
  lienKet: '#5B4BE0', // tiếp thị liên kết
  tuBan: '#27C2B0', // shop tự bán
};

/** Dãy màu theo mã sản phẩm (4 mã đầu + "mã khác") và màu nền nhạt của ô mã. */
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

/** Nhãn tăng / giảm / trung tính (theo nghĩa tốt / xấu, không theo dấu). */
export const nhanThayDoi = {
  tot: { chu: '#0B7A68', nen: '#E3F7F2' },
  xau: { chu: '#B4233A', nen: '#FDECEE' },
  trungTinh: { chu: '#5D6378', nen: '#F1F2F7' },
};

/** Cảnh báo và trạng thái. */
export const canhBao = {
  chinh: '#D83A52',
  nen: '#FFF5F6',
  vien: '#F7D3D8',
  nenIcon: '#FDE3E7',
  chu: '#8E1B2E',
  chuDam: '#B4233A',
  vang: '#E59A1A', // chấm "có kỳ khác vượt ngưỡng"
  nenVang: '#FFF8EC',
  nenVangNhat: '#FFF1D6', // số đếm "sắp hết quyền" ở menu, ô bộ đếm chất lượng > 0
  chuVang: '#8A5300',
  xanh: '#1FA387', // chấm "không có cảnh báo"
  nenXanh: '#F2FBF8',
  nenOChay: '#E3F7F4', // ô đồng bộ ở chân menu
  chuOChay: '#0E7C6B',
};

/** Màu gạch chéo cho thanh "cả tháng trước" (minh họa vì sao phải cắt cùng số ngày). */
export const gachCheo = {
  dam: '#C9CDDA',
  nhat: '#EEF0F5',
};

/** Cỡ chữ (px). */
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

/** Bo góc (px): thẻ / ô trạng thái / nút, ô chọn / nhãn viên. */
export const boGoc = { the: 16, oTrangThai: 12, nut: 9, nhan: 6, navNoi: 20 };

/** Bóng thẻ dùng cho mọi thẻ. */
export const bong = {
  the: '0 1px 2px rgba(20,24,40,.04), 0 6px 18px rgba(20,24,40,.03)',
  nutChon: '0 1px 2px rgba(20,24,40,.12)',
  danhSachXo: '0 2px 4px rgba(20,24,40,.06), 0 12px 28px rgba(20,24,40,.12)', // danh sách xổ ra của ô chọn
  navNoi: '0 10px 32px -4px rgba(20, 24, 40, 0.08), 0 4px 12px -2px rgba(20, 24, 40, 0.04)', // bóng đổ nổi cho thanh điều hướng dock
  topbarNoi: '0 8px 24px -4px rgba(20, 24, 40, 0.06), 0 2px 8px -2px rgba(20, 24, 40, 0.03)', // bóng nổi cho thanh trên
  mucNavActive: '0 2px 8px rgba(91, 75, 224, 0.12)', // bóng nhẹ cho mục menu đang chọn
};

/** Khoảng cách (px). */
export const khoangCach = {
  leNgang: 28, // lề trái-phải vùng nội dung
  giuaThe: 16,
  giuaKhoi: 18,
  trongThe: '18px 20px',
  toiDaNoiDung: 1320,
  rongMenu: 248,
};

/** Font chữ. Số liệu luôn dùng tabular-nums (xem kieu.so). */
export const font = {
  chu: "'Be Vietnam Pro', system-ui, sans-serif",
};

/** Các mảng style dùng lại nhiều nơi. */
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

/** Token đưa vào ConfigProvider của Ant Design (xem antdTheme.js). */
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
  colorBgMask: mau.phuNen, // lớp phủ sau hộp thoại
  borderRadius: boGoc.nut,
  borderRadiusLG: boGoc.the,
  fontFamily: font.chu,
  fontSize: coChu.thuong,
};
