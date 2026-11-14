import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Cấu hình Vite + Vitest dùng chung một file.
// jsdom: môi trường trình duyệt giả để test component.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    css: false,
    testTimeout: 30000,
    // Giới hạn số tiến trình chạy song song: máy yếu khởi động quá nhiều jsdom cùng lúc sẽ bị quá thời gian chờ.
    maxWorkers: 3,
    // Test luôn chạy với dữ liệu giả, KHÔNG phụ thuộc tệp frontend/.env của người chạy (ở máy thật thường đặt
    // VITE_USE_MOCK=false để gọi backend). Test nào cần chế độ máy chủ thật thì tự đặt bằng vi.stubEnv('VITE_USE_MOCK', 'false').
    env: { VITE_USE_MOCK: 'true' },
  },
})
