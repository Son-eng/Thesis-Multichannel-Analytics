import { useEffect } from 'react';
import { mau, canhBao, kieu, coChu } from '../theme/tokens.js';

/**
 * Hộp thoại giữa màn hình dùng cho xác nhận và nhập liệu ngắn (đổi vai trò, đặt lại mật khẩu, xóa tài khoản).
 * Đóng bằng phím Esc, bấm lớp phủ, hoặc nút Hủy.
 *
 * @param {string} tieuDe
 * @param {() => void} khiDong
 * @param {() => void} khiDongY chạy khi bấm nút xác nhận
 * @param {string} nhanDongY chữ nút xác nhận
 * @param {boolean} [nguyHiem] nút xác nhận màu đỏ (xóa)
 * @param {boolean} [khoaDongY] khóa nút xác nhận (dữ liệu chưa hợp lệ hoặc đang gửi)
 * @param {string} [loi] thông báo lỗi hiện trong hộp thoại
 */
export default function HopThoai({ tieuDe, khiDong, khiDongY, nhanDongY, nguyHiem = false, khoaDongY = false, loi = '', children }) {
  useEffect(() => {
    const khiBamPhim = (sk) => {
      if (sk.key === 'Escape') {
        khiDong();
      }
    };
    window.addEventListener('keydown', khiBamPhim);
    return () => window.removeEventListener('keydown', khiBamPhim);
  }, [khiDong]);

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: mau.phuNen, display: 'grid', placeItems: 'center', padding: 16, zIndex: 1000 }}
      onMouseDown={(sk) => {
        if (sk.target === sk.currentTarget) {
          khiDong();
        }
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-label={tieuDe}
        onSubmit={(sk) => {
          sk.preventDefault();
          if (!khoaDongY) {
            khiDongY();
          }
        }}
        style={{ ...kieu.the, width: '100%', maxWidth: 420, padding: 22, display: 'flex', flexDirection: 'column', gap: 14 }}
      >
        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>{tieuDe}</h2>
        {children}
        {loi ? (
          <div role="alert" style={{ fontSize: coChu.nho, color: canhBao.chuDam }}>
            {loi}
          </div>
        ) : null}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="button" className="nut" onClick={khiDong}>
            Hủy
          </button>
          <button type="submit" className={nguyHiem ? 'nut nut-nguy' : 'nut nut-chinh'} disabled={khoaDongY}>
            {nhanDongY}
          </button>
        </div>
      </form>
    </div>
  );
}
