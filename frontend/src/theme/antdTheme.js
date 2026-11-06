import { tokenAntd } from './tokens.js';
import { chuyenDongDangTat } from './motion.js';

/**
 * Gói token cho ConfigProvider của Ant Design.
 * Tách riêng để App.jsx không phải biết chi tiết token.
 * Là hàm (không phải hằng) vì "giảm chuyển động" của hệ điều hành đọc lúc dựng, không phải lúc nạp module.
 * Bật giảm chuyển động hoặc cờ TAT_CHUYEN_DONG thì tắt luôn chuyển động của Ant Design (hộp thoại, thông báo).
 */
export function layAntdTheme() {
  return {
    token: { ...tokenAntd, motion: !chuyenDongDangTat() },
    components: {
      Layout: { bodyBg: tokenAntd.colorBgLayout },
    },
  };
}
