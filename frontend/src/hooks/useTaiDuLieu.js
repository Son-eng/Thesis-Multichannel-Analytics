import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Tải dữ liệu cho MỘT khối của trang, tự giữ trạng thái đang tải / lỗi / dữ liệu.
 *
 * Mỗi khối gọi hook riêng nên một khối lỗi không làm hỏng khối khác.
 * Khi đổi tham số, dữ liệu CŨ được giữ cho tới khi dữ liệu mới về: số chạy từ giá trị cũ sang giá trị mới
 * thay vì chạy lại từ đầu (yêu cầu chuyển động khi đổi kỳ). Khung xám chỉ hiện ở lần tải đầu tiên.
 *
 * @param {() => Promise<object>|null} hamTai hàm gọi API; trả null (hoặc không gọi) khi chưa đủ điều kiện tải
 * @param {any[]} phuThuoc danh sách phụ thuộc: đổi thì tải lại
 * @returns {{duLieu: object|null, loi: object|null, dangTai: boolean, thuLai: () => void}}
 */
export function useTaiDuLieu(hamTai, phuThuoc) {
  const [trangThai, setTrangThai] = useState({ duLieu: null, loi: null, dangTai: true });
  const [lanThu, setLanThu] = useState(0);
  const hamTaiMoiNhat = useRef(hamTai);
  hamTaiMoiNhat.current = hamTai;

  useEffect(() => {
    let daHuy = false;
    const lenhGoi = hamTaiMoiNhat.current();
    if (lenhGoi === null) {
      setTrangThai({ duLieu: null, loi: null, dangTai: true });
      return undefined;
    }
    setTrangThai((cu) => ({ ...cu, loi: null, dangTai: true }));
    lenhGoi
      .then((duLieu) => {
        if (!daHuy) {
          setTrangThai({ duLieu, loi: null, dangTai: false });
        }
      })
      .catch((e) => {
        if (!daHuy) {
          setTrangThai({ duLieu: null, loi: e, dangTai: false });
        }
      });
    return () => {
      daHuy = true;
    };
    // phuThuoc do nơi gọi truyền vào nên không thể kiểm tĩnh được.
  }, [...phuThuoc, lanThu]);

  const thuLai = useCallback(() => setLanThu((n) => n + 1), []);
  return { ...trangThai, thuLai };
}
