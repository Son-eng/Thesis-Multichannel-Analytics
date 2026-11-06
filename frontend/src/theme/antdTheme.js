import { tokenAntd } from './tokens.js';

// Gói token cho ConfigProvider của Ant Design.
// Tách riêng để App.jsx không phải biết chi tiết token.
export const antdTheme = {
  token: tokenAntd,
  components: {
    Layout: { bodyBg: tokenAntd.colorBgLayout },
  },
};
