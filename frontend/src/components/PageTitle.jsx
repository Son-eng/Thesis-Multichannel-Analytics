import { mau, coChu } from '../theme/tokens.js';

/**
 * Đầu trang: tiêu đề cỡ 24, dòng phụ, và vùng bên phải cho các ô chọn.
 * @param {string} tieuDe
 * @param {React.ReactNode} [dongPhu]
 * @param {React.ReactNode} [benPhai] các ô chọn, nút
 */
export default function PageTitle({ tieuDe, dongPhu, benPhai }) {
  return (
    <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: coChu.tieuDe, lineHeight: 1.2, fontWeight: 600, letterSpacing: '-0.015em' }}>{tieuDe}</h1>
        {dongPhu ? (
          <p className="so" style={{ margin: '4px 0 0', color: mau.chuNhan, fontSize: coChu.nho }}>
            {dongPhu}
          </p>
        ) : null}
      </div>
      {benPhai ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>{benPhai}</div> : null}
    </header>
  );
}
