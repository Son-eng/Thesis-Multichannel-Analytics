import { mau, coChu } from '../../theme/tokens.js';
import Icon from '../Icon.jsx';

export default function TieuDeKhoi({ bieuTuong, children, chuThich, vongTron = false }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
      <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8, fontSize: coChu.tieuDeThe, fontWeight: 500, color: mau.chuPhu }}>
        <Icon ten={bieuTuong} vongTron={vongTron} />
        {children}
      </h2>
      {chuThich ? <span style={{ fontSize: coChu.ratNho, color: mau.chuNhan }}>{chuThich}</span> : null}
    </div>
  );
}
