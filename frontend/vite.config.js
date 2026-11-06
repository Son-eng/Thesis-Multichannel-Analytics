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
  },
})
