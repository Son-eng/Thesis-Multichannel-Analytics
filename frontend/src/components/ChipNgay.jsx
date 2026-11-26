import { DatePicker } from 'antd';
import dayjs from 'dayjs';
import Icon from './Icon.jsx';

const DINH_DANG_ISO = 'YYYY-MM-DD';

/** Ô chọn ngày dạng lịch, cùng khung với ChipChon; chỉ cho chọn ngày trong khoảng có dữ liệu. */
export default function ChipNgay({ nhan, giaTri, khiDoi, ngayMin, ngayMax }) {
  const ngayDangChon = giaTri ? dayjs(giaTri) : null;
  return (
    <div className="chip chip-ngay">
      <Icon ten="calendar" kichThuoc={15} />
      <DatePicker
        aria-label={nhan}
        value={ngayDangChon && ngayDangChon.isValid() ? ngayDangChon : null}
        format="DD/MM/YYYY"
        variant="borderless"
        allowClear={false}
        inputReadOnly
        showToday={false}
        minDate={dayjs(ngayMin)}
        maxDate={dayjs(ngayMax)}
        disabledDate={(ngay) => {
          const iso = ngay.format(DINH_DANG_ISO);
          return iso < ngayMin || iso > ngayMax;
        }}
        onChange={(ngay) => {
          if (ngay) {
            khiDoi(ngay.format(DINH_DANG_ISO));
          }
        }}
        classNames={{ popup: { root: 'lich-chon-ngay' } }}
        suffixIcon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            <path d="M3 4.5 6 7.5l3-3" />
          </svg>
        }
      />
    </div>
  );
}
