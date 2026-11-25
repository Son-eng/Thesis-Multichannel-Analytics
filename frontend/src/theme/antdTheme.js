// Ánh xạ để các nút bấm, bảng biểu tự ăn theo bảng màu
import { tokenAntd } from './tokens.js';
import { chuyenDongDangTat } from './motion.js';

/** Là hàm vì "giảm chuyển động" của hệ điều hành phải đọc lúc dựng, không phải lúc nạp module. */
export function layAntdTheme() {
  return {
    token: { ...tokenAntd, motion: !chuyenDongDangTat() },
    components: {
      Layout: { bodyBg: tokenAntd.colorBgLayout },
    },
  };
}
