import { mau, coChu } from '../theme/tokens.js';
import { docLoi } from '../api/client.js';
import { KHONG_CO_DU_LIEU } from '../utils/format.js';

/** Khung xám giữ chỗ khi đang tải (không dùng spinner). */
export function KhungXam({ cao = 120, style }) {
  return <div className="khung-xam" aria-hidden="true" style={{ height: cao, ...style }} />;
}

/** Chữ "Không có dữ liệu" khi khối trả status = no_data. */
export function KhongCoDuLieu({ cao = 80 }) {
  return (
    <div style={{ minHeight: cao, display: 'grid', placeItems: 'center', color: mau.chuNhan, fontSize: coChu.nho }}>
      {KHONG_CO_DU_LIEU}
    </div>
  );
}

/**
 * Bao một khối: tự xử lý đang tải (khung xám), lỗi và dữ liệu của CHÍNH khối đó.
 * Vì sao: một khối lỗi không được làm hỏng khối khác.
 *
 * @param {{duLieu: object|null, loi: object|null, dangTai: boolean, thuLai: Function}} tt kết quả useTaiDuLieu
 * @param {number} cao chiều cao khung xám giữ chỗ
 * @param {(duLieu: object) => React.ReactNode} children hàm vẽ khi đã có dữ liệu
 */
export default function KhoiDuLieu({ tt, cao = 120, children }) {
  if (tt.loi) {
    const { message } = docLoi(tt.loi);
    return (
      <div role="alert" style={{ minHeight: cao, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', gap: 8, color: mau.chuNhan, fontSize: coChu.nho }}>
        <span>Không tải được khối này: {message}</span>
        <button type="button" className="nut" onClick={tt.thuLai}>
          Thử lại
        </button>
      </div>
    );
  }
  if (tt.duLieu === null) {
    return <KhungXam cao={cao} />;
  }
  return children(tt.duLieu);
}
