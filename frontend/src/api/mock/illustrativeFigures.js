// Số minh họa, chỉ để giao diện có dữ liệu; số đã kiểm chứng nằm ở realFigures.js.

/** M22 của TikTok bằng 0 trước tháng 8 để có ví dụ previous_zero. */
export const TY_TRONG_SAN_PHAM = {
  shopee: {
    M15: 0.32,
    BU01: 0.235,
    'M6 Pro': 0.125,
    M5: 0.105,
    'M3 Plus': 0.075,
    M13: 0.05,
    'M9 MAX': 0.03,
    'M8 AIR': 0.027,
    M21: 0.017,
    M24: 0.011,
  },
  tiktok: {
    M15: 0.395,
    BU01: 0.29,
    M5: 0.095,
    'M6 Pro': 0.075,
    'M3 Plus': 0.045,
    M13: 0.03,
    'M9 MAX': 0.018,
    'M8 AIR': 0.016,
    M21: 0.013,
    M24: 0.009,
    B3: 0.008,
    M23: 0.004,
    M22: 0.0,
  },
};

export const M22_BAT_DAU = { thang: '2026-08', tyTrong: 0.04 };

/** Tổng 1.165 là số thật, tách theo tháng là minh họa. */
export const DON_HOP_LE_THANG_SHOPEE = { '2026-07': 653, '2026-08': 512 };

export const TY_TRONG_GIO = {
  shopee: [1.2, 0.6, 0.4, 0.2, 0.2, 0.5, 1.4, 2.8, 4.3, 5.6, 6.4, 6.9, 7.4, 6.2, 5.3, 4.9, 5.1, 5.5, 5.9, 6.6, 7.8, 8.1, 5.8, 2.9],
  tiktok: [2.1, 1.2, 0.7, 0.4, 0.3, 0.4, 1.0, 2.0, 3.1, 4.0, 4.6, 5.0, 5.6, 4.7, 4.1, 3.9, 4.2, 4.9, 5.8, 7.0, 8.6, 9.6, 8.4, 4.4],
};

export const TY_TRONG_AFFILIATE = {
  shopee: { '2026-07': 22.1, '2026-08': 23.6 },
  tiktok: {
    '2026-01': 57.8,
    '2026-02': 58.5,
    '2026-03': 59.2,
    '2026-04': 59.8,
    '2026-05': 60.1,
    '2026-06': 59.6,
    '2026-07': 60.4,
    '2026-08': 61.8,
  },
};

export const TY_TRONG_GIAN_HANG = {
  shopee: { 'Shop C': 1 },
  tiktok: { 'Shop A': 0.64, 'Shop B': 0.36 },
};

const TINH_CHUNG = [
  ['TP. Hồ Chí Minh', 24.1],
  ['Hà Nội', 20.6],
  ['Hải Phòng', 5.2],
  ['Đà Nẵng', 4.4],
  ['Đồng Nai', 3.9],
  ['Bình Dương', 3.6],
  ['Cần Thơ', 3.0],
  ['Quảng Ninh', 2.6],
  ['Thanh Hóa', 2.4],
  ['Nghệ An', 2.2],
  ['Khánh Hòa', 2.0],
  ['Lâm Đồng', 1.8],
  ['Bắc Ninh', 1.7],
  ['Hưng Yên', 1.6],
  ['Thái Nguyên', 1.5],
  ['Hải Dương', 1.4],
  ['Long An', 1.3],
  ['Bà Rịa - Vũng Tàu', 1.2],
  ['Thừa Thiên Huế', 1.1],
  ['Vĩnh Phúc', 1.0],
  ['Nam Định', 0.9],
  ['Thái Bình', 0.9],
  ['Phú Thọ', 0.8],
  ['Bình Định', 0.8],
  ['Quảng Nam', 0.7],
  ['Đắk Lắk', 0.7],
  ['Tiền Giang', 0.6],
  ['An Giang', 0.6],
  ['Kiên Giang', 0.5],
  ['Hà Tĩnh', 0.5],
  ['Quảng Bình', 0.4],
  ['Lạng Sơn', 0.4],
  ['Ninh Bình', 0.3],
  ['Bắc Giang', 0.3],
  ['Cà Mau', 0.2],
];

const TINH_THEM_TIKTOK = [
  ['Gia Lai', 0.2],
  ['Tây Ninh', 0.2],
  ['Hòa Bình', 0.15],
  ['Sơn La', 0.1],
  ['Lào Cai', 0.1],
  ['Cao Bằng', 0.05],
];

export const TY_TRONG_KHAC = 0.4;

export const DANH_SACH_TINH = {
  shopee: TINH_CHUNG,
  tiktok: TINH_CHUNG.concat(TINH_THEM_TIKTOK),
};

export const DONG_NMV_TAM_TINH = { shopee: 0, tiktok: null };

export const TOKEN_GIA = [
  {
    platform: 'shopee',
    shop_name: 'Shop C',
    last_success_at: '2026-08-23T16:40:07+07:00',
    access_expires_at: '2026-08-23T20:40:00+07:00',
    refresh_expires_at: '2026-08-28T10:00:00+07:00', // còn 5 ngày nên là "expiring" (ngưỡng 7 ngày)
    token_status: 'expiring',
  },
  {
    platform: 'tiktok',
    shop_name: 'Shop A',
    last_success_at: '2026-08-23T16:40:12+07:00',
    access_expires_at: '2026-08-30T16:40:12+07:00',
    refresh_expires_at: null, // TikTok không có hạn refresh_token
    token_status: 'ok',
  },
  {
    platform: 'tiktok',
    shop_name: 'Shop B',
    last_success_at: '2026-08-23T16:40:15+07:00',
    access_expires_at: '2026-08-30T16:40:15+07:00',
    refresh_expires_at: null,
    token_status: 'ok',
  },
];

export const CHU_KY_DONG_BO_PHUT = 10;
export const THOI_DIEM_HIEN_TAI = '2026-08-23T16:50:00+07:00';
