// Hệ giao diện: MỌI màu, cỡ chữ, bo góc, bóng, khoảng cách khai báo MỘT lần ở đây.
// Component chỉ đọc từ file này. Không viết mã màu hex ở file nào khác trong src/
// (có test quét; thư mục src/theme/ được miễn).
// Muốn đổi giao diện: sửa giá trị ở đây, mọi trang đổi theo.

/** Màu nền, viền, chữ. */
export const mau = {
  nenTrang: '#F3F4F8', // nền toàn trang (colorBgLayout)
  nenThe: '#FFFFFF', // nền thẻ, menu, thanh trên (colorBgContainer)
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
export const boGoc = { the: 16, oTrangThai: 12, nut: 9, nhan: 6 };

/** Bóng thẻ dùng cho mọi thẻ. */
export const bong = {
  the: '0 1px 2px rgba(20,24,40,.04), 0 6px 18px rgba(20,24,40,.03)',
  nutChon: '0 1px 2px rgba(20,24,40,.12)',
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
