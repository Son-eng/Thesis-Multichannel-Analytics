import { nhanThayDoi, boGoc, coChu, kieu } from '../theme/tokens.js';

/** Chỉ vẽ nhãn; chữ và màu tốt/xấu do utils/delta.js quyết định. */
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
