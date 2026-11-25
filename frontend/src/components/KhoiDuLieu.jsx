import { mau, coChu } from '../theme/tokens.js';
import { docLoi } from '../api/client.js';
import { KHONG_CO_DU_LIEU } from '../utils/format.js';

export function KhungXam({ cao = 120, style }) {
  return <div className="khung-xam" aria-hidden="true" style={{ height: cao, ...style }} />;
}

export function KhongCoDuLieu({ cao = 80 }) {
  return (
    <div style={{ minHeight: cao, display: 'grid', placeItems: 'center', color: mau.chuNhan, fontSize: coChu.nho }}>
      {KHONG_CO_DU_LIEU}
    </div>
  );
}

/** Mỗi khối tự xử lý đang tải, lỗi và dữ liệu của chính nó, để một khối lỗi không làm hỏng khối khác. */
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
