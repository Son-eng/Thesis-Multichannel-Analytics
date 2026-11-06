// SỐ THẬT ĐÃ KIỂM CHỨNG — chỉ chứa số có nguồn trong SPEC.
// Mỗi số kèm chú thích mục SPEC nguồn. Số minh họa nằm ở illustrativeFigures.js, KHÔNG để ở đây.
// Test src/api/mock/realFigures.test.js so từng số với giá trị chép tay từ SPEC.
// Tài khoản và dữ liệu trong mock đều là giả; không có token, khóa hay mật khẩu thật.

/** Khoảng dữ liệu của từng sàn. SPEC §17.1. */
export const KHOANG_DU_LIEU = {
  shopee: { min: '2026-07-01', max: '2026-08-16' }, // §17.1: 01/07/2026 – 16/08/2026
  tiktok: { min: '2026-01-01', max: '2026-08-23' }, // §17.1: 01/01/2026 – 23/08/2026
};

/** Danh sách gian hàng. SPEC §12.1.1.1 (Shop C của Shopee; Shop A, Shop B của TikTok). */
export const GIAN_HANG = {
  shopee: ['Shop C'],
  tiktok: ['Shop A', 'Shop B'],
};

/**
 * Danh sách product_code từng sàn, sắp theo bảng chữ cái.
 * Nguồn: backend/app/etl/mappings/product_map.json (chỉ đọc). SPEC §17.1: Shopee 10 mã, TikTok 13 mã.
 */
export const MA_SAN_PHAM = {
  shopee: ['BU01', 'M13', 'M15', 'M21', 'M24', 'M3 Plus', 'M5', 'M6 Pro', 'M8 AIR', 'M9 MAX'],
  tiktok: ['B3', 'BU01', 'M13', 'M15', 'M21', 'M22', 'M23', 'M24', 'M3 Plus', 'M5', 'M6 Pro', 'M8 AIR', 'M9 MAX'],
};

/** Mã chỉ bán trên TikTok. SPEC §12 (bảng "Chỉ so sánh các chỉ số CẢ 2 SÀN đều tính được"). */
export const MA_CHI_TIKTOK = ['B3', 'M22', 'M23'];

/** Tổng toàn bộ dữ liệu mỗi sàn. SPEC §17.2 (doanh thu, số đơn, AOV) và §17.1/§17.2 (tổng đơn, số sản phẩm). */
export const TONG_TOAN_BO = {
  shopee: {
    revenue: 1908961059, // §17.2
    order_count: 1165, // §17.2 (số đơn hợp lệ)
    order_count_all: 1761, // §17.2 (tổng số đơn)
    quantity_sold: 1182, // §17.2
    aov: 1638593, // §17.2
  },
  tiktok: {
    revenue: 7538502584, // §17.2
    order_count: 5211, // §17.2
    order_count_all: 7526, // §17.2
    quantity_sold: 5292, // §17.2
    aov: 1446652, // §17.2
  },
};

/** Doanh thu từng tháng (đã lọc hủy, hoàn). SPEC §17.3. */
export const DOANH_THU_THANG = {
  shopee: {
    '2026-07': 1068925905, // §17.3
    '2026-08': 840035154, // §17.3 (đến 16/08)
  },
  tiktok: {
    '2026-01': 963328583, // §17.3
    '2026-02': 1056998596, // §17.3
    '2026-03': 1459153482, // §17.3
    '2026-04': 1014538449, // §17.3
    '2026-05': 800122017, // §17.3
    '2026-06': 566274001, // §17.3
    '2026-07': 814595996, // §17.3
    '2026-08': 863491460, // §17.3 (đến 23/08)
  },
};

/**
 * Doanh thu kỳ trước đã cắt cùng số ngày của tháng 8. SPEC §9.4, §17.3 (bảng "Assertion cho quy tắc cắt cùng-số-ngày").
 */
export const KY_TRUOC_DA_CAT = {
  shopee: { period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-16', revenue: 624277755, pct_change: 34.6 },
  tiktok: { period: '2026-07', date_from: '2026-07-01', date_to: '2026-07-23', revenue: 579379192, pct_change: 49.0 },
};

/** Nếu đem so NGUYÊN tháng trước (cách SAI, chỉ để minh họa). SPEC §9.4. */
export const SO_VOI_NGUYEN_THANG = {
  shopee: { revenue: 1068925905, pct_change_if_used: -21.4 },
  tiktok: { revenue: 814595996, pct_change_if_used: 6.0 },
};

/** Ngưỡng cảnh báo giảm doanh thu (%). SPEC §9.1 (ALERT_DROP_THRESHOLD_PCT = 30). */
export const NGUONG_CANH_BAO_PCT = -30.0;

/** Cảnh báo duy nhất ở chế độ tháng: TikTok 2026-04. SPEC §9.1, §17.3. */
export const CANH_BAO_THANG_4_TIKTOK = {
  period: '2026-04',
  previous_period: '2026-03',
  revenue: 1014538449, // §9.1
  revenue_previous: 1459153482, // §9.1
  pct_change: -30.5, // §9.1
};

/** Ba tháng TikTok giảm liên tiếp T4, T5, T6 (chỉ T4 vượt ngưỡng 30%). SPEC §9.1. */
export const TIKTOK_T4_T5_T6 = [
  { period: '2026-04', revenue: 1014538449, previous: 1459153482, pct_change: -30.5 },
  { period: '2026-05', revenue: 800122017, previous: 1014538449, pct_change: -21.1 },
  { period: '2026-06', revenue: 566274001, previous: 800122017, pct_change: -29.2 },
];

/**
 * Số liệu TikTok tháng 7/2026 trong ví dụ prompt LLM. SPEC §10.
 * top5 gồm doanh thu và mức thay đổi so với tháng 6 của từng mã.
 */
export const TIKTOK_THANG_7 = {
  period: '2026-07',
  revenue: 814595996, // §10
  revenue_previous: 566274001, // §10
  pct_change: 43.9, // §10
  order_count: 510, // §10
  quantity_sold: 513, // §10
  aov: 1597247, // §10
  top5: [
    { product_code: 'M15', revenue: 328663138, pct_change: 26.8 }, // §10
    { product_code: 'BU01', revenue: 252093194, pct_change: 41.1 }, // §10
    { product_code: 'M5', revenue: 102675334, pct_change: 266.7 }, // §10
    { product_code: 'M6 Pro', revenue: 61734709, pct_change: 12.7 }, // §10
    { product_code: 'M3 Plus', revenue: 45314808, pct_change: 97.4 }, // §10
  ],
};

/** Năm bộ đếm chất lượng khi nạp tệp mẫu. SPEC §3.3 (bảng "Giá trị mong đợi với 2 file mẫu"). */
export const CHAT_LUONG_TEP_MAU = {
  shopee: {
    rows_sku_fallback: 6, // §3.3
    rows_sku_unknown: 0, // §3.3
    rows_status_unknown: 19, // §3.3
    rows_province_unmapped: 0, // §3.3
    rows_product_unmapped: 0, // §3.3
  },
  tiktok: {
    rows_sku_fallback: 0,
    rows_sku_unknown: 0,
    rows_status_unknown: 0,
    rows_province_unmapped: 0,
    rows_product_unmapped: 0,
  },
};

/** Dòng trạng thái `unknown` của TOÀN BỘ dữ liệu Shopee. SPEC §17.2 và §12.1.1.2 (ghi chú dưới ví dụ). */
export const DONG_UNKNOWN_SHOPEE = { rows: 19, revenue: 29814813 };

/** Số dòng và số đơn hoàn/hủy toàn bộ dữ liệu. SPEC §17.1 (dòng hoàn hàng: Shopee 56, TikTok 139). */
export const DONG_HOAN_HANG = { shopee: 56, tiktok: 139 };

/** Số tỉnh chung của hai sàn. SPEC §12 (35 tỉnh chung = toàn bộ tỉnh của Shopee). */
export const SO_TINH_CHUNG = 35;

/** Các tài khoản GIẢ dùng cho mock. Mật khẩu giả `demo123`. Không phải tài khoản thật. */
export const TAI_KHOAN_GIA = [
  { id: 1, username: 'admin.vh', role: 'admin', password: 'demo123', created_at: '2026-08-01T09:00:00+07:00' }, // SPEC §12.1.4.1 (ví dụ admin.vh)
  { id: 2, username: 'quanly.kd', role: 'user', password: 'demo123', created_at: '2026-08-03T10:30:00+07:00' }, // SPEC §12.1.4.1 (v2: quanly.kd)
];
