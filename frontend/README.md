# Frontend — Phân tích bán hàng đa kênh (Shopee · TikTok Shop)

React 18 + Vite + Ant Design 5 + React Router 6 + dayjs. JavaScript (không TypeScript). Biểu đồ vẽ bằng SVG/CSS trong `src/components/charts/`.

## Phiên bản đã dùng

- **Node 24.14.1**, npm 11.11.0 (yêu cầu tối thiểu Node 22 LTS).
- Mọi thư viện ghim phiên bản chính xác trong `package.json` (không `^`, không `~`), `package-lock.json` được commit.

## Cách chạy

```
cd frontend
npm install
npm run dev        # http://localhost:5173
npm test           # Vitest
npm run build      # ra thư mục dist/
```

## VITE_USE_MOCK

Sao `.env.example` thành `.env.local`.

| Biến | Ý nghĩa |
|---|---|
| `VITE_USE_MOCK=true` | Mọi lời gọi API đi vào `src/api/mock/`, trả JSON giả đúng hợp đồng `docs/SPEC.md §12.1`. Không cần backend, Docker hay CSDL. |
| `VITE_USE_MOCK=false` | Gọi backend thật tại `VITE_API_BASE_URL` (mặc định `http://localhost:8000`). Không phải sửa trang nào. |

Không đặt biến thì mock được bật.

**Tài khoản mock (GIẢ, chỉ để demo):** `admin.vh` (quản trị viên) và `quanly.kd` (người dùng), mật khẩu giả `demo123`. Đăng nhập bằng `quanly.kd` thì nhóm menu "QUẢN TRỊ" biến mất và các trang quản trị chuyển về dashboard.

## Cấu trúc

```
src/
  api/          MỘT cửa gọi API (client.js) + mỗi nhóm endpoint một file
    mock/       realFigures.js = số thật có nguồn SPEC; illustrativeFigures.js = số minh họa
  components/   Card, DeltaBadge, Sidebar, Topbar... ; charts/ chứa biểu đồ (nhận dữ liệu và màu qua props)
  context/      phiên đăng nhập
  hooks/        useDemSo (đếm số), useChuyenDong (trình tự mở trang)
  pages/        Login, Dashboard (dùng chung cho 2 sàn), ComparePlatforms, SyncStatus, Upload, Users
  theme/        tokens.js (màu, cỡ chữ...), motion.js (chuyển động), antdTheme.js, globalStyles.js
  utils/        quy tắc hiển thị: format.js, delta.js, period.js
```

Trang không bao giờ gọi `fetch` trực tiếp, chỉ import các hàm trong `src/api/`.

## Sửa giao diện

| Muốn đổi | Sửa file |
|---|---|
| Màu, cỡ chữ, bo góc, bóng thẻ, khoảng cách, font | `src/theme/tokens.js` (mỗi nhóm có chú thích dùng cho đâu) |
| Tốc độ, độ trễ, đường cong chuyển động | `src/theme/motion.js` (`thoiLuong`, `troGiup`, `duongCong`) |
| Tắt hết chuyển động | `src/theme/motion.js`, đặt `TAT_CHUYEN_DONG = true` |
| Giao diện thẻ (viền, bo góc, bóng) | `src/components/Card.jsx` đọc từ `tokens.js` |
| Nhãn tăng/giảm | `src/components/DeltaBadge.jsx`; chữ và màu quyết ở `src/utils/delta.js` |
| Màu và kiểu của ô chọn, nút, bảng | `src/theme/globalStyles.js` |

Không viết mã màu hex ở file nào khác trong `src/` (có test `src/test/khongMaHex.test.js` quét và báo lỗi). Khi hệ điều hành bật "giảm chuyển động" (`prefers-reduced-motion`), mọi thứ hiện ngay ở trạng thái cuối; nội dung không phụ thuộc chuyển động.

## Quy tắc hiển thị

Mười quy tắc (null không thành 0, `insufficient_data`, `previous_zero`, "điểm %", màu tốt/xấu, định dạng tiền...) nằm ở `src/utils/` và có test ở `src/utils/quyTacHienThi.test.js`.
