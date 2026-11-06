// Bộ biểu tượng nét mảnh dùng trong menu, thẻ chỉ số, tiêu đề khối (theo bản thiết kế).
// Vẽ bằng stroke="currentColor" nên màu theo chữ xung quanh, không cần mã màu ở đây.

const DUONG_VE = {
  sync: 'M13.5 6.5A5.5 5.5 0 0 0 3 5M2.5 9.5A5.5 5.5 0 0 0 13 11M3 2v3h3M13 14v-3h-3',
  upload: 'M8 10V2M5 5l3-3 3 3M2.5 10v3.5h11V10',
  users: 'M1.5 13.5c.6-2.3 2.3-3.5 4.5-3.5s3.9 1.2 4.5 3.5M11 3.2a2.5 2.5 0 0 1 0 4.6M12.5 10.3c1 .5 1.7 1.6 2 3.2',
  compare: 'M2 5h10M9 2l3 3-3 3M14 11H4M7 8l-3 3 3 3',
  chart: 'M3 13V8M8 13V3M13 13V6',
  calendar: 'M2 6.5h12M5.5 1.5v3M10.5 1.5v3',
  filter: 'M2.5 4h11M4.5 8h7M6.5 12h3',
  download: 'M8 2v8M5 7l3 3 3-3M2.5 11v2.5h11V11',
  info: 'M8 7v4M8 5v.01',
  trend: 'M2.5 12.5 6 9l2.5 2.5L13.5 5M10 5h3.5v3.5',
  bag: 'M2.5 4h11l-1 7h-9l-1-7ZM5.5 4 6.5 2h3l1 2M6 14h.01M10 14h.01',
  card: 'M2 5.5h12v7H2v-7ZM2 8h12M5 11h2',
  cancel: 'M3 3l10 10M13 3 3 13',
  gauge: 'M2 12a6 6 0 0 1 12 0M8 12 11 7',
  box: 'M2.5 5 8 2l5.5 3v6L8 14l-5.5-3V5ZM2.5 5 8 8l5.5-3M8 8v6',
  clock: 'M8 4.5V8l2.5 1.5',
  pin: 'M8 14s4.5-4.2 4.5-7.5a4.5 4.5 0 0 0-9 0C3.5 9.8 8 14 8 14Z',
  bell: 'M4 11V7a4 4 0 0 1 8 0v4l1.5 1.5h-11L4 11ZM6.5 14h3',
  spark: 'M8 1.5v3M8 11.5v3M1.5 8h3M11.5 8h3M3.4 3.4l2 2M10.6 10.6l2 2M12.6 3.4l-2 2M5.4 10.6l-2 2',
  warn: 'M8 2.5 14.5 13.5h-13L8 2.5ZM8 6.5v3M8 11.5v.01',
  logout: 'M6 2.5H3v11h3M10 5l3 3-3 3M13 8H6',
  key: 'M10.5 6.5a3 3 0 1 1-2.1-2.9M8.4 6.6 2 13v1.5h2V13h1.5v-1.5H7',
  trash: 'M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.5 9h6l.5-9',
  plus: 'M8 3v10M3 8h10',
};

/**
 * Biểu tượng 16x16.
 * @param {string} ten khóa trong DUONG_VE
 * @param {number} [kichThuoc]
 * @param {boolean} [vongTron] vẽ thêm vòng tròn (dùng cho info, clock)
 */
export default function Icon({ ten, kichThuoc = 16, vongTron = false, doDay = 1.5 }) {
  return (
    <svg
      width={kichThuoc}
      height={kichThuoc}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={doDay}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {vongTron ? <circle cx="8" cy="8" r="6.5" /> : null}
      {ten === 'calendar' ? <rect x="2" y="3" width="12" height="11" rx="2" /> : null}
      {ten === 'users' ? <circle cx="6" cy="5.5" r="2.5" /> : null}
      <path d={DUONG_VE[ten]} />
    </svg>
  );
}
