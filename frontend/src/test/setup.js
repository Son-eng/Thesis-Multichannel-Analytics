// Thiết lập chung cho mọi test.
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';
import { cleanup, configure } from '@testing-library/react';
import { datCauHinhMock, datLaiMock } from '../api/mock/handlers.js';

// jsdom không có matchMedia; Ant Design và hook chuyển động đều hỏi đến nó.
// Mặc định test coi như hệ điều hành bật "giảm chuyển động": mọi số hiện ngay giá trị cuối,
// nên test không phải chờ chuyển động. Test riêng của chuyển động tự đặt lại window.matchMedia.
// Máy Windows chạy jsdom chậm ở lần dựng đầu tiên (nạp mock, dựng dữ liệu theo ngày); 1 giây mặc định là quá ngặt.
configure({ asyncUtilTimeout: 15000 });

function matchMediaMacDinh(truyVan) {
  return {
    matches: truyVan.includes('prefers-reduced-motion'),
    media: truyVan,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  };
}

// jsdom thiếu ResizeObserver, Ant Design Table/Select dùng.
if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

beforeEach(() => {
  // Đặt lại mỗi ca: test chuyển động có thể đã thay window.matchMedia.
  window.matchMedia = matchMediaMacDinh;
  // Mock không trễ và đồng bộ nhanh để test chạy nhanh.
  datLaiMock();
  datCauHinhMock({ doTre: 0, thoiGianDongBo: 50, llmLoi: false });
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
