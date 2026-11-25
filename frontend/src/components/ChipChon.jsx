import Icon from './Icon.jsx';

/** Dùng thẻ select gốc để bàn phím và trình đọc màn hình hoạt động sẵn. */
export default function ChipChon({ nhan, bieuTuong, giaTri, khiDoi, luaChon, disabled = false }) {
  return (
    <label className="chip">
      {bieuTuong ? <Icon ten={bieuTuong} kichThuoc={15} /> : null}
      <span className="sr-only">{nhan}</span>
      <select aria-label={nhan} value={giaTri} onChange={(e) => khiDoi(e.target.value)} disabled={disabled}>
        {luaChon.map((l) => (
          <option key={l.value} value={l.value}>
            {l.label}
          </option>
        ))}
      </select>
      <svg style={{ position: 'absolute', right: 9, pointerEvents: 'none' }} width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <path d="M3 4.5 6 7.5l3-3" />
      </svg>
    </label>
  );
}
