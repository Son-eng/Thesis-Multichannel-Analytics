// Số thật đã kiểm chứng trên dữ liệu mẫu; số minh họa nằm ở illustrativeFigures.js.
// Tài khoản và dữ liệu trong mock đều là giả.

export const KHOANG_DU_LIEU = {
  shopee: { min: '2026-07-01', max: '2026-08-16' },
  tiktok: { min: '2026-01-01', max: '2026-08-23' },
};

export const GIAN_HANG = {
  shopee: ['Shop C'],
  tiktok: ['Shop A', 'Shop B'],
};

export const MA_SAN_PHAM = {
  shopee: ['BU01', 'M13', 'M15', 'M21', 'M24', 'M3 Plus', 'M5', 'M6 Pro', 'M8 AIR', 'M9 MAX'],
  tiktok: ['B3', 'BU01', 'M13', 'M15', 'M21', 'M22', 'M23', 'M24', 'M3 Plus', 'M5', 'M6 Pro', 'M8 AIR', 'M9 MAX'],
};

export const TONG_TOAN_BO = {
  shopee: {
    revenue: 1908961059,
    order_count: 1165, // số đơn hợp lệ
    order_count_all: 1761, // tổng số đơn
    quantity_sold: 1182,
    aov: 1638593,
  },
  tiktok: {
    revenue: 7538502584,
    order_count: 5211,
    order_count_all: 7526,
    quantity_sold: 5292,
    aov: 1446652,
  },
};

/** Doanh thu từng tháng, đã loại hủy và hoàn. */
export const DOANH_THU_THANG = {
  shopee: {
    '2026-07': 1068925905,
    '2026-08': 840035154, // đến 16/08
  },
  tiktok: {
    '2026-01': 963328583,
    '2026-02': 1056998596,
    '2026-03': 1459153482,
    '2026-04': 1014538449,
    '2026-05': 800122017,
    '2026-06': 566274001,
    '2026-07': 814595996,
    '2026-08': 863491460, // đến 23/08
  },
};

/** Doanh thu kỳ trước đã cắt cùng số ngày của tháng 8. */
export const KY_TRUOC_DA_CAT = {
  shopee: { period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-16', revenue: 624277755, pct_change: 34.6 },
  tiktok: { period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-23', revenue: 579379192, pct_change: 49.0 },
};

/** So nguyên tháng trước là cách sai, chỉ để minh họa. */
export const SO_VOI_NGUYEN_THANG = {
  shopee: { revenue: 1068925905, pct_change_if_used: -21.4 },
  tiktok: { revenue: 814595996, pct_change_if_used: 6.0 },
};

export const NGUONG_CANH_BAO_PCT = -30.0;

/** Cảnh báo duy nhất ở chế độ tháng: TikTok 2026-04. */
export const CANH_BAO_THANG_4_TIKTOK = {
  period: '2026-04',
  previous_period: '2026-03',
  revenue: 1014538449,
  revenue_previous: 1459153482,
  pct_change: -30.5,
};

/** TikTok giảm ba tháng liền T4, T5, T6 nhưng chỉ T4 vượt ngưỡng 30%. */
export const TIKTOK_T4_T5_T6 = [
  { period: '2026-04', revenue: 1014538449, previous: 1459153482, pct_change: -30.5 },
  { period: '2026-05', revenue: 800122017, previous: 1014538449, pct_change: -21.1 },
  { period: '2026-06', revenue: 566274001, previous: 800122017, pct_change: -29.2 },
];

/** Số liệu TikTok tháng 7/2026 dùng làm ví dụ cho nhận định LLM. */
export const TIKTOK_THANG_7 = {
  period: '2026-07',
  revenue: 814595996,
  revenue_previous: 566274001,
  pct_change: 43.9,
  order_count: 510,
  quantity_sold: 513,
  aov: 1597247,
  top5: [
    { product_code: 'M15', revenue: 328663138, pct_change: 26.8 },
    { product_code: 'BU01', revenue: 252093194, pct_change: 41.1 },
    { product_code: 'M5', revenue: 102675334, pct_change: 266.7 },
    { product_code: 'M6 Pro', revenue: 61734709, pct_change: 12.7 },
    { product_code: 'M3 Plus', revenue: 45314808, pct_change: 97.4 },
  ],
};

/** Năm bộ đếm chất lượng khi nạp tệp mẫu. */
export const CHAT_LUONG_TEP_MAU = {
  shopee: {
    rows_sku_fallback: 6,
    rows_sku_unknown: 0,
    rows_status_unknown: 19,
    rows_province_unmapped: 0,
    rows_product_unmapped: 0,
  },
  tiktok: {
    rows_sku_fallback: 0,
    rows_sku_unknown: 0,
    rows_status_unknown: 0,
    rows_province_unmapped: 0,
    rows_product_unmapped: 0,
  },
};

export const DONG_UNKNOWN_SHOPEE = { rows: 19, revenue: 29814813 };

export const DONG_HOAN_HANG = { shopee: 56, tiktok: 139 };

/** Tài khoản giả cho mock, mật khẩu demo123. */
export const TAI_KHOAN_GIA = [
  { id: 1, username: 'admin.vh', role: 'admin', password: 'demo123', created_at: '2026-08-01T09:00:00+07:00' },
  { id: 2, username: 'quanly.kd', role: 'user', password: 'demo123', created_at: '2026-08-03T10:30:00+07:00' },
];
