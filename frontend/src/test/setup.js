// Thiết lập chung cho mọi test.
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { datCauHinhMock, datLaiMock } from '../api/mock/handlers.js';

// jsdom không có matchMedia; Ant Design và hook chuyển động đều hỏi đến nó.
if (!window.matchMedia) {
  window.matchMedia = (truyVan) => ({
    matches: false,
    media: truyVan,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
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
  // Mock không trễ và đồng bộ nhanh để test chạy nhanh.
  datLaiMock();
  datCauHinhMock({ doTre: 0, thoiGianDongBo: 50, llmLoi: false });
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
