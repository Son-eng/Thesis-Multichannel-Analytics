import { mau, canhBao } from '../theme/tokens.js';
import { dinhDangSo } from '../utils/format.js';

export const COT_CHAT_LUONG = [
  { khoa: 'rows_sku_fallback', nhan: 'SKU dự phòng', nhanDai: 'Phải lấy SKU dự phòng', goiY: 'Dòng phải lấy SKU dự phòng' },
  { khoa: 'rows_sku_unknown', nhan: 'Thiếu SKU', nhanDai: 'Không xác định được SKU', goiY: 'Dòng không xác định được SKU' },
  { khoa: 'rows_status_unknown', nhan: 'Trạng thái lạ', nhanDai: 'Trạng thái đơn không xác định', goiY: 'Dòng có trạng thái đơn không xác định' },
  { khoa: 'rows_province_unmapped', nhan: 'Tỉnh chưa chuẩn hóa', nhanDai: 'Không chuẩn hóa được tỉnh/thành', goiY: 'Dòng không chuẩn hóa được tỉnh/thành' },
  { khoa: 'rows_product_unmapped', nhan: 'Chưa có mã SP', nhanDai: 'Không tìm được mã sản phẩm', goiY: 'Dòng không tìm được mã sản phẩm' },
];

/** Bộ đếm > 0 tô vàng (dòng cần xem lại), bằng 0 để mờ. */
export function OBoDem({ giaTri }) {
  const canXem = giaTri > 0;
  return (
    <span
      className="so"
      data-canh-bao={canXem ? 'true' : 'false'}
      style={{ display: 'inline-block', minWidth: 22, padding: '1px 7px', borderRadius: 6, fontWeight: canXem ? 600 : 400, background: canXem ? canhBao.nenVangNhat : 'transparent', color: canXem ? canhBao.chuVang : mau.chuMo }}
    >
      {dinhDangSo(giaTri)}
    </span>
  );
}
