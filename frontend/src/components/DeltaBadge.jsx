import { nhanThayDoi, boGoc, coChu, kieu } from '../theme/tokens.js';

/**
 * Nhãn viên hiện mức thay đổi so với kỳ trước.
 * Nhận kết quả của taoNhanThayDoi() (utils/delta.js), nên không tự quyết quy tắc nào:
 * chữ, màu (tốt/xấu/trung tính) đều do utils quyết, nhãn chỉ vẽ.
 *
 * @param {{text: string, tone: 'tot'|'xau'|'trungTinh', laThongBao: boolean}} nhan
 */
export default function DeltaBadge({ nhan, style }) {
  const mau = nhanThayDoi[nhan.tone];
  return (
    <span
      className="so"
      data-tone={nhan.tone}
      style={{
        ...kieu.so,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 3,
        minHeight: 22,
        padding: '1px 7px',
        borderRadius: boGoc.nhan,
        fontSize: coChu.ratNho,
        fontWeight: nhan.laThongBao ? 500 : 600,
        background: mau.nen,
        color: mau.chu,
        ...style,
      }}
    >
      {nhan.text}
    </span>
  );
}
