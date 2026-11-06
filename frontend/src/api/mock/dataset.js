// Bộ dữ liệu theo NGÀY của hai sàn, sinh một lần, cố định (không ngẫu nhiên).
// Vì sao theo ngày: mọi mức thời gian (ngày, tháng, quý, năm) và mọi phép cắt cùng-số-ngày
// (SPEC §9.2) đều tính được từ cùng một nguồn, nên các khối trên một trang luôn khớp nhau.
//
// Ràng buộc số thật (realFigures.js): doanh thu từng tháng, doanh thu kỳ trước đã cắt, tổng số đơn,
// số đơn tháng 7 TikTok... được giữ ĐÚNG. Cách chia thành từng ngày là minh họa.

import {
  KHOANG_DU_LIEU,
  DOANH_THU_THANG,
  KY_TRUOC_DA_CAT,
  TONG_TOAN_BO,
  TIKTOK_THANG_7,
  DONG_HOAN_HANG,
} from './realFigures.js';
import { DON_HOP_LE_THANG_SHOPEE, TY_TRONG_SAN_PHAM, M22_BAT_DAU, TY_TRONG_AFFILIATE } from './illustrativeFigures.js';
import { congNgay, demNgay, ngayCuoiKy } from '../../utils/period.js';

/**
 * Chia một số nguyên thành nhiều phần nguyên theo trọng số, tổng các phần BẰNG ĐÚNG số ban đầu
 * (phương pháp phần dư lớn nhất). Vì sao cần: tổng theo ngày phải bằng doanh thu tháng thật, không lệch 1 đồng.
 * @param {number} tong số nguyên cần chia
 * @param {number[]} trongSo trọng số không âm
 * @returns {number[]}
 */
export function chiaTheoTrongSo(tong, trongSo) {
  const tongTrongSo = trongSo.reduce((a, b) => a + b, 0);
  if (!(tongTrongSo > 0)) {
    return trongSo.map(() => 0);
  }
  const raw = trongSo.map((w) => (tong * w) / tongTrongSo);
  const nguyen = raw.map((r) => Math.floor(r));
  let du = tong - nguyen.reduce((a, b) => a + b, 0);
  const thuTu = raw
    .map((r, i) => ({ i, phan: r - Math.floor(r) }))
    .sort((a, b) => b.phan - a.phan || a.i - b.i);
  for (let k = 0; du > 0 && k < thuTu.length; k += 1) {
    nguyen[thuTu[k].i] += 1;
    du -= 1;
  }
  return nguyen;
}

/** Danh sách ngày liên tiếp từ `tu` đến `den` (gồm cả hai đầu). */
function lietKeNgay(tu, den) {
  const soNgay = demNgay(tu, den);
  const kq = [];
  for (let i = 0; i < soNgay; i += 1) {
    kq.push(congNgay(tu, i));
  }
  return kq;
}

/** Thứ trong tuần của một ngày ISO (0 = Chủ nhật). */
function thuTrongTuan(iso) {
  const [nam, thang, ngay] = iso.split('-').map(Number);
  return new Date(Date.UTC(nam, thang - 1, ngay)).getUTCDay();
}

/** Trọng số doanh thu của một ngày: dao động nhẹ, cuối tuần nhỉnh hơn. Minh họa. */
function trongSoNgay(iso, viTri, hat) {
  let w = 1 + 0.25 * Math.sin(viTri * 0.8 + hat) + 0.12 * Math.cos(viTri * 1.7 + hat * 2);
  const thu = thuTrongTuan(iso);
  if (thu === 0 || thu === 6) {
    w += 0.15;
  }
  return w;
}

/**
 * Chia mục tiêu theo tháng, cho phép ghim một số tháng ở giá trị thật.
 * @param {number} tong tổng toàn bộ
 * @param {number[]} trongSo trọng số từng tháng cho phần chưa ghim
 * @param {(number|null)[]} codinh giá trị ghim từng tháng (null = chưa ghim)
 */
function chiaCoGhim(tong, trongSo, codinh) {
  const daGhim = codinh.reduce((a, v) => a + (v === null ? 0 : v), 0);
  const trongSoConLai = trongSo.map((w, i) => (codinh[i] === null ? w : 0));
  const phan = chiaTheoTrongSo(tong - daGhim, trongSoConLai);
  return codinh.map((v, i) => (v === null ? phan[i] : v));
}

/**
 * Dựng danh sách đoạn doanh thu: mỗi tháng một đoạn, riêng tháng có kỳ trước đã cắt thì tách làm hai
 * đoạn để tổng 01 -> ngày cắt bằng ĐÚNG số thật (SPEC §9.4).
 */
function dungDoan(san) {
  const ngayMax = KHOANG_DU_LIEU[san].max;
  const doan = [];
  let hat = 0.7;
  Object.keys(DOANH_THU_THANG[san]).forEach((thang) => {
    const tongThang = DOANH_THU_THANG[san][thang];
    const dau = `${thang}-01`;
    const cuoi = ngayCuoiKy('month', thang) < ngayMax ? ngayCuoiKy('month', thang) : ngayMax;
    const cat = KY_TRUOC_DA_CAT[san];
    hat += 0.9;
    if (cat.period === thang) {
      doan.push({ tu: dau, den: cat.date_to, tong: cat.revenue, hat });
      doan.push({ tu: congNgay(cat.date_to, 1), den: cuoi, tong: tongThang - cat.revenue, hat: hat + 0.6 });
    } else {
      doan.push({ tu: dau, den: cuoi, tong: tongThang, hat });
    }
  });
  return doan;
}

/** Trọng số sản phẩm của một tháng (minh họa): tỷ trọng nền, lệch nhẹ theo tháng. */
function trongSoSanPhamThang(san, thang) {
  const ma = Object.keys(TY_TRONG_SAN_PHAM[san]);
  const soThang = Number(thang.slice(5, 7));
  return ma.map((code, i) => {
    let goc = TY_TRONG_SAN_PHAM[san][code];
    if (san === 'tiktok' && code === 'M22') {
      goc = thang >= M22_BAT_DAU.thang ? M22_BAT_DAU.tyTrong : 0;
    }
    const lech = 1 + 0.12 * Math.sin(soThang * 1.3 + i * 0.9);
    return { code, w: goc * lech };
  });
}

/**
 * Doanh thu từng mã của một tháng. Tổng các mã BẰNG doanh thu tháng.
 * TikTok tháng 7: năm mã đầu ghim ĐÚNG số thật (SPEC §10), phần còn lại chia cho các mã khác.
 * TikTok tháng 6: dựng ngược từ mức thay đổi thật (§10) để pct_change tính ra đúng 26,8; 41,1; 266,7; 12,7; 97,4.
 */
function doanhThuMaTrongThang(san, thang, tongThang) {
  const trongSo = trongSoSanPhamThang(san, thang);
  let ghim = {};
  if (san === 'tiktok' && thang === TIKTOK_THANG_7.period) {
    TIKTOK_THANG_7.top5.forEach((m) => {
      ghim[m.product_code] = m.revenue;
    });
  }
  if (san === 'tiktok' && thang === '2026-06') {
    TIKTOK_THANG_7.top5.forEach((m) => {
      ghim[m.product_code] = Math.round(m.revenue / (1 + m.pct_change / 100));
    });
  }
  const daGhim = Object.values(ghim).reduce((a, b) => a + b, 0);
  const conLai = trongSo.filter((m) => ghim[m.code] === undefined);
  const phan = chiaTheoTrongSo(
    tongThang - daGhim,
    conLai.map((m) => m.w),
  );
  const kq = { ...ghim };
  conLai.forEach((m, i) => {
    kq[m.code] = phan[i];
  });
  return kq;
}

const BO_NHO_DEM = {};

/**
 * Bộ dữ liệu theo ngày của một sàn. Dựng lần đầu rồi giữ lại.
 * @returns {{ngay: object[], ngayMin: string, ngayMax: string, thang: Object<string, {rev: number, ma: Object<string, number>}>}}
 *   mỗi ngày: {date, thang, rev, orders, ordersAll, returns, qty, affPct}
 */
export function layBoDuLieu(san) {
  if (BO_NHO_DEM[san]) {
    return BO_NHO_DEM[san];
  }
  const { min, max } = KHOANG_DU_LIEU[san];
  const ngay = [];
  dungDoan(san).forEach((d) => {
    const dsNgay = lietKeNgay(d.tu, d.den);
    const w = dsNgay.map((iso, i) => trongSoNgay(iso, i, d.hat));
    const rev = chiaTheoTrongSo(d.tong, w);
    dsNgay.forEach((iso, i) => {
      ngay.push({ date: iso, thang: iso.slice(0, 7), rev: rev[i] });
    });
  });

  // Gom theo tháng.
  const dsThang = Object.keys(DOANH_THU_THANG[san]);
  const doanhThuThang = dsThang.map((t) => DOANH_THU_THANG[san][t]);
  const tong = TONG_TOAN_BO[san];

  // Đơn hợp lệ theo tháng: Shopee tách theo hằng minh họa; TikTok ghim tháng 7 = 510 (§10), còn lại chia theo doanh thu.
  let donHopLe;
  if (san === 'shopee') {
    donHopLe = dsThang.map((t) => DON_HOP_LE_THANG_SHOPEE[t]);
  } else {
    const codinh = dsThang.map((t) => (t === TIKTOK_THANG_7.period ? TIKTOK_THANG_7.order_count : null));
    donHopLe = chiaCoGhim(tong.order_count, doanhThuThang, codinh);
  }
  const tatCaDon = chiaTheoTrongSo(tong.order_count_all, donHopLe);
  const donHoan = chiaTheoTrongSo(DONG_HOAN_HANG[san], tatCaDon);
  let soLuong;
  if (san === 'tiktok') {
    const codinh = dsThang.map((t) => (t === TIKTOK_THANG_7.period ? TIKTOK_THANG_7.quantity_sold : null));
    soLuong = chiaCoGhim(tong.quantity_sold, donHopLe, codinh);
  } else {
    soLuong = chiaTheoTrongSo(tong.quantity_sold, donHopLe);
  }

  const thang = {};
  dsThang.forEach((t, k) => {
    const chiSoNgay = [];
    ngay.forEach((d, i) => {
      if (d.thang === t) {
        chiSoNgay.push(i);
      }
    });
    const w = chiSoNgay.map((i) => ngay[i].rev);
    const hopLe = chiaTheoTrongSo(donHopLe[k], w);
    const tatCa = chiaTheoTrongSo(tatCaDon[k], w);
    const hoan = chiaTheoTrongSo(donHoan[k], w);
    const sl = chiaTheoTrongSo(soLuong[k], w);
    chiSoNgay.forEach((i, j) => {
      ngay[i].orders = hopLe[j];
      ngay[i].ordersAll = Math.max(tatCa[j], hopLe[j] + hoan[j]);
      ngay[i].returns = hoan[j];
      ngay[i].qty = sl[j];
      ngay[i].affPct = TY_TRONG_AFFILIATE[san][t];
    });
    thang[t] = { rev: doanhThuThang[k], ma: doanhThuMaTrongThang(san, t, doanhThuThang[k]) };
  });

  BO_NHO_DEM[san] = { ngay, ngayMin: min, ngayMax: max, thang };
  return BO_NHO_DEM[san];
}

/**
 * Cộng dồn dữ liệu các ngày trong [tu, den], đã cắt theo khoảng dữ liệu của sàn.
 * @returns {object} coDuLieu = false khi không có ngày nào trong khoảng.
 */
export function gopKhoang(san, tu, den) {
  const bo = layBoDuLieu(san);
  const tuThuc = tu > bo.ngayMin ? tu : bo.ngayMin;
  const denThuc = den < bo.ngayMax ? den : bo.ngayMax;
  const kq = {
    coDuLieu: false,
    rev: 0,
    orders: 0,
    ordersAll: 0,
    returns: 0,
    qty: 0,
    affRev: 0,
    affOrders: 0,
    ngay: [],
    thangRev: {},
  };
  if (tuThuc > denThuc) {
    return kq;
  }
  kq.coDuLieu = true;
  const batDau = demNgay(bo.ngayMin, tuThuc) - 1;
  const ketThuc = demNgay(bo.ngayMin, denThuc) - 1;
  for (let i = batDau; i <= ketThuc; i += 1) {
    const d = bo.ngay[i];
    kq.rev += d.rev;
    kq.orders += d.orders;
    kq.ordersAll += d.ordersAll;
    kq.returns += d.returns;
    kq.qty += d.qty;
    kq.affRev += Math.round((d.rev * d.affPct) / 100);
    kq.affOrders += Math.round((d.orders * d.affPct) / 100);
    kq.thangRev[d.thang] = (kq.thangRev[d.thang] || 0) + d.rev;
    kq.ngay.push(d);
  }
  return kq;
}

/**
 * Doanh thu từng mã trong một khoảng đã gộp. Mỗi tháng đóng góp theo tỷ lệ doanh thu khoảng/tháng.
 * Tổng các mã BẰNG doanh thu khoảng; khoảng là nguyên một tháng thì trả đúng số của tháng.
 */
export function doanhThuTheoMa(san, gop) {
  const bo = layBoDuLieu(san);
  const trongSo = {};
  Object.keys(gop.thangRev).forEach((t) => {
    const ty = gop.thangRev[t] / bo.thang[t].rev;
    Object.keys(bo.thang[t].ma).forEach((code) => {
      trongSo[code] = (trongSo[code] || 0) + bo.thang[t].ma[code] * ty;
    });
  });
  const ma = Object.keys(trongSo);
  const phan = chiaTheoTrongSo(
    gop.rev,
    ma.map((c) => trongSo[c]),
  );
  const kq = {};
  ma.forEach((c, i) => {
    kq[c] = phan[i];
  });
  return kq;
}
