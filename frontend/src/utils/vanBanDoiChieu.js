import { dinhDangNgayNgan } from './format.js';
import { nhanKy, demNgay } from './period.js';

// Mọi ngày đọc từ API, frontend không tự tính khoảng ngày nào.

const TEN_SAN = { shopee: 'Shopee', tiktok: 'TikTok Shop' };

/** Dòng phụ nhắc tránh so trực tiếp tổng tiền khi hai sàn khác số ngày. */
export function dungBanner(muc, dl) {
  const kyChu = nhanKy(muc, dl.period);
  const canh = { shopee: dl.shopee, tiktok: dl.tiktok };
  const khongCo = ['shopee', 'tiktok'].filter((s) => canh[s].status === 'no_data');
  const choPhep = ['shopee', 'tiktok'].filter((s) => canh[s].status !== 'no_data');

  if (khongCo.length === 2) {
    return { chinh: `Cả hai sàn đều không có dữ liệu trong ${kyChu.toLowerCase()}.`, phu: '' };
  }
  if (khongCo.length === 1) {
    const thieu = TEN_SAN[khongCo[0]];
    const co = TEN_SAN[choPhep[0]];
    return {
      chinh: `${thieu} chưa có dữ liệu trong ${kyChu.toLowerCase()}, nên kỳ này chỉ ${co} có số liệu.`,
      phu: `Cánh ${thieu} ghi “Không có dữ liệu” thay vì 0 đồng: 0 đồng nghĩa là có bán mà không có doanh thu, còn ở đây hệ thống chưa có dữ liệu.`,
    };
  }

  const chuaDu = !dl.shopee.period_complete || !dl.tiktok.period_complete;
  const ngayDen = `Shopee đến ${dinhDangNgayNgan(dl.shopee.data_max_date)}, TikTok Shop đến ${dinhDangNgayNgan(dl.tiktok.data_max_date)}`;
  let chinh = `Cả hai sàn có đủ ngày của ${kyChu.toLowerCase()}.`;
  if (chuaDu) {
    chinh = `${kyChu} chưa kết thúc và hai sàn có dữ liệu đến ngày khác nhau: ${ngayDen}. Mỗi sàn được so với kỳ trước của chính nó, cắt về cùng số ngày.`;
  } else if (dl.shopee.data_max_date !== dl.tiktok.data_max_date) {
    chinh = `${kyChu} đã đủ ngày ở cả hai sàn (${ngayDen}). Mỗi sàn được so với kỳ trước của chính nó.`;
  }

  const thieuKyTruoc = choPhep.filter((s) => canh[s].status === 'insufficient_data').map((s) => TEN_SAN[s]);
  let phu = '';
  const soNgayShopee = demNgay(dl.shopee.current.date_from, dl.shopee.current.date_to);
  const soNgayTiktok = demNgay(dl.tiktok.current.date_from, dl.tiktok.current.date_to);
  if (soNgayShopee !== soNgayTiktok) {
    phu = `Vì hai sàn khác số ngày (${soNgayShopee} và ${soNgayTiktok} ngày), đừng so trực tiếp tổng doanh thu giữa hai sàn; hãy nhìn mức thay đổi và các tỷ lệ.`;
  }
  if (thieuKyTruoc.length > 0) {
    const them = `${thieuKyTruoc.join(' và ')} chưa có dữ liệu kỳ trước nên không có mức thay đổi.`;
    phu = phu ? `${phu} ${them}` : them;
  }
  return { chinh, phu };
}
