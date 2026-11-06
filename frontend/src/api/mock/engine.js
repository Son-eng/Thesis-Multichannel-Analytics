// Máy tính số liệu của mock: nhận cùng tham số như API thật (SPEC §12.1) và trả JSON đúng hợp đồng.
// Mọi số bắt nguồn từ dataset.js (số thật được ghim, số còn lại là minh họa).
// Quy tắc nghiệp vụ được giữ ĐÚNG như backend để giao diện chạy mock hay chạy thật đều không đổi:
// cắt cùng số ngày (§9.2), kỳ trước bằng 0 (§12.1.0.2), không tồn tại kỳ trước (§9.3b), null khác 0.

import { KHOANG_DU_LIEU, GIAN_HANG, MA_SAN_PHAM, NGUONG_CANH_BAO_PCT, DONG_UNKNOWN_SHOPEE, TONG_TOAN_BO } from './realFigures.js';
import { TY_TRONG_GIO, TY_TRONG_GIAN_HANG, DANH_SACH_TINH, TY_TRONG_KHAC, DONG_NMV_TAM_TINH } from './illustrativeFigures.js';
import { chiaTheoTrongSo, gopKhoang, doanhThuTheoMa } from './dataset.js';
import {
  MUC_THOI_GIAN,
  maKyChuaNgay,
  maKyHopLe,
  ngayDauKy,
  ngayCuoiKy,
  kyTruocCua,
  kyKeTiep,
  congNgay,
  demNgay,
} from '../../utils/period.js';

/** Lỗi giả lập: mang mã HTTP và `detail` đúng dạng FastAPI. */
export class LoiMock extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : detail.message);
    this.status = status;
    this.detail = detail;
  }
}

/** Tạo lỗi có mã riêng: {"detail": {"code", "message"}} (SPEC §12.1.0). */
export function loiCoMa(status, code, message, them = {}) {
  return new LoiMock(status, { code, message, ...them });
}

function lamTron1(x) {
  return Math.round(x * 10) / 10;
}

function phanTram(tu, mau) {
  if (!mau) {
    return null;
  }
  return lamTron1((tu / mau) * 100);
}

/** Kiểm tra tên sàn trong đường dẫn. */
export function kiemTraSan(san) {
  if (san !== 'shopee' && san !== 'tiktok') {
    throw new LoiMock(404, 'Không tìm thấy');
  }
}

/** Đọc và kiểm tra mức thời gian. */
function docMuc(q) {
  const muc = q.granularity || 'month';
  if (!MUC_THOI_GIAN.includes(muc)) {
    throw loiCoMa(422, 'invalid_granularity', 'Mức thời gian không hợp lệ');
  }
  return muc;
}

/**
 * Xác định kỳ hiện tại, kỳ trước (đã cắt cùng số ngày khi cần) của một sàn.
 * SPEC §9.2 (cắt), §9.3a (mức ngày không cắt), §12.1 "Cài đặt bước 13" (kỳ trước tồn tại khi ngày đầu >= ngày nhỏ nhất).
 */
export function xacDinhKy(san, muc, maKy) {
  const { min, max } = KHOANG_DU_LIEU[san];
  const ma = maKy || maKyChuaNgay(muc, max);
  if (!maKyHopLe(muc, ma)) {
    throw loiCoMa(422, 'invalid_period', `Mã kỳ "${ma}" sai định dạng của mức ${muc}`);
  }
  const dau = ngayDauKy(muc, ma);
  const cuoiLich = ngayCuoiKy(muc, ma);
  const dayDu = cuoiLich <= max;
  const den = dayDu ? cuoiLich : max;
  const maTruoc = kyTruocCua(muc, ma);
  const dauTruoc = ngayDauKy(muc, maTruoc);
  const cuoiTruocLich = ngayCuoiKy(muc, maTruoc);
  const coTruoc = dauTruoc >= min;
  let denTruoc = cuoiTruocLich;
  // Kỳ chưa đủ ngày: cắt kỳ trước về cùng số ngày (§9.2). Mức ngày không cắt (§9.3a).
  if (!dayDu && muc !== 'day' && den >= dau) {
    const soNgay = demNgay(dau, den);
    const denCat = congNgay(dauTruoc, soNgay - 1);
    denTruoc = denCat < cuoiTruocLich ? denCat : cuoiTruocLich;
  }
  return {
    muc,
    ma,
    dau,
    den,
    cuoiLich,
    dayDu,
    truoc: coTruoc ? { ma: maTruoc, dau: dauTruoc, den: denTruoc, cuoiLich: cuoiTruocLich } : null,
  };
}

/**
 * Lấy số liệu một khoảng ngày sau khi áp bộ lọc gian hàng và mã sản phẩm.
 * @param {{shop?: string, product?: string}} loc
 */
export function layKhoang(san, tu, den, loc = {}) {
  const gop = gopKhoang(san, tu, den);
  const rong = { coDuLieu: false, rev: 0, orders: 0, ordersAll: 0, returns: 0, qty: 0, affRev: 0, affOrders: 0, ngay: [], ma: {} };
  if (!gop.coDuLieu) {
    return rong;
  }
  const maGoc = doanhThuTheoMa(san, gop);
  let heSo = 1;
  let rev = gop.rev;
  if (loc.product) {
    const rSp = maGoc[loc.product] || 0;
    if (rSp === 0) {
      return rong;
    }
    heSo = rSp / gop.rev;
  }
  let heSoShop = 1;
  if (loc.shop) {
    heSoShop = TY_TRONG_GIAN_HANG[san][loc.shop] || 0;
    if (heSoShop === 0) {
      return rong;
    }
  }
  const he = heSo * heSoShop;
  rev = loc.product ? Math.round(maGoc[loc.product] * heSoShop) : Math.round(gop.rev * heSoShop);
  const nhan = (x) => Math.round(x * he);
  let ma;
  if (loc.product) {
    ma = { [loc.product]: rev };
  } else if (heSoShop === 1) {
    ma = maGoc;
  } else {
    const dsMa = Object.keys(maGoc);
    const phan = chiaTheoTrongSo(
      rev,
      dsMa.map((c) => maGoc[c]),
    );
    ma = {};
    dsMa.forEach((c, i) => {
      ma[c] = phan[i];
    });
  }
  return {
    coDuLieu: rev > 0,
    rev,
    orders: nhan(gop.orders),
    ordersAll: nhan(gop.ordersAll),
    returns: nhan(gop.returns),
    qty: nhan(gop.qty),
    affRev: nhan(gop.affRev),
    affOrders: nhan(gop.affOrders),
    ngay: gop.ngay.map((d) => ({ date: d.date, rev: Math.round(d.rev * he) })),
    ma,
  };
}

/** Đọc bộ lọc từ query. */
function docLoc(san, q) {
  const loc = {};
  if (q.shop_name) {
    loc.shop = q.shop_name;
  }
  if (q.product_code) {
    loc.product = q.product_code;
  }
  return loc;
}

// ----- Dựng chỉ số -----

/** Chỉ số số đếm / tiền: value, previous, pct_change, previous_zero (SPEC §12.1.0.2). */
function chiSoSo(giaTri, truoc, tinhTrang) {
  if (tinhTrang === 'no_data' || giaTri === null) {
    return { value: null, previous: null, pct_change: null, previous_zero: false };
  }
  if (tinhTrang === 'insufficient_data' || truoc === undefined) {
    return { value: giaTri, previous: null, pct_change: null, previous_zero: false };
  }
  if (truoc === null || truoc === 0) {
    return { value: giaTri, previous: truoc === null ? null : 0, pct_change: null, previous_zero: true };
  }
  return { value: giaTri, previous: truoc, pct_change: lamTron1(((giaTri - truoc) / truoc) * 100), previous_zero: false };
}

/** Chỉ số tỷ lệ: không có pct_change, thay bằng change_pp (điểm %). */
function chiSoTyLe(giaTri, truoc, tinhTrang) {
  if (tinhTrang === 'no_data' || giaTri === null) {
    return { value: null, previous: null, change_pp: null };
  }
  if (tinhTrang === 'insufficient_data' || truoc === null || truoc === undefined) {
    return { value: lamTron1(giaTri), previous: null, change_pp: null };
  }
  return { value: lamTron1(giaTri), previous: lamTron1(truoc), change_pp: lamTron1(giaTri - truoc) };
}

function aovCua(k) {
  if (!k || !k.coDuLieu || k.orders === 0) {
    return null;
  }
  return Math.round(k.rev / k.orders);
}

function tyLeHuy(k) {
  if (!k || !k.coDuLieu || k.ordersAll === 0) {
    return null;
  }
  const huy = Math.max(0, k.ordersAll - k.orders - k.returns);
  return (huy / k.ordersAll) * 100;
}

function tyLeHoan(k) {
  if (!k || !k.coDuLieu || k.ordersAll === 0) {
    return null;
  }
  return (k.returns / k.ordersAll) * 100;
}

function tyTrongAffiliate(k) {
  if (!k || !k.coDuLieu || k.rev === 0) {
    return null;
  }
  return (k.affRev / k.rev) * 100;
}

/** Khối `metrics` của §12.1.1.2, dùng chung cho kpi và compare. */
function dungMetrics(hienTai, truoc, tinhTrang) {
  const gt = (k, ten) => (k && k.coDuLieu ? k[ten] : null);
  const tr = (k, ten) => {
    if (!k) {
      return undefined;
    }
    return k.coDuLieu ? k[ten] : 0;
  };
  const aovTruoc = aovCua(truoc);
  return {
    revenue: chiSoSo(gt(hienTai, 'rev'), tr(truoc, 'rev'), tinhTrang),
    order_count: chiSoSo(gt(hienTai, 'orders'), tr(truoc, 'orders'), tinhTrang),
    order_count_all: chiSoSo(gt(hienTai, 'ordersAll'), tr(truoc, 'ordersAll'), tinhTrang),
    quantity_sold: chiSoSo(gt(hienTai, 'qty'), tr(truoc, 'qty'), tinhTrang),
    // AOV kỳ trước không xác định (không có đơn hợp lệ) -> previous = null, previous_zero = true (§12.1 "Cài đặt bước 13").
    aov: chiSoSo(aovCua(hienTai), truoc ? (aovTruoc === null ? null : aovTruoc) : undefined, tinhTrang),
    cancel_rate: chiSoTyLe(tyLeHuy(hienTai), tyLeHuy(truoc), tinhTrang),
    return_rate: chiSoTyLe(tyLeHoan(hienTai), tyLeHoan(truoc), tinhTrang),
    affiliate_share: chiSoTyLe(tyTrongAffiliate(hienTai), tyTrongAffiliate(truoc), tinhTrang),
  };
}

/** Tính hiện tại + trước cho một kỳ và trả trạng thái. Dùng chung kpi, top-products, compare, alerts. */
function tinhKyVoiTruoc(san, ky, loc) {
  const hienTai = layKhoang(san, ky.dau, ky.den, loc);
  const truoc = ky.truoc ? layKhoang(san, ky.truoc.dau, ky.truoc.den, loc) : null;
  let tinhTrang = 'ok';
  if (!hienTai.coDuLieu) {
    tinhTrang = 'no_data';
  } else if (!ky.truoc) {
    tinhTrang = 'insufficient_data';
  }
  return { hienTai, truoc, tinhTrang };
}

function khoangCua(ky) {
  return { date_from: ky.dau, date_to: ky.den };
}

// ----- Endpoint -----

export function filters(san) {
  return {
    platform: san,
    shops: GIAN_HANG[san].slice(),
    product_codes: MA_SAN_PHAM[san].slice(),
    data_min_date: KHOANG_DU_LIEU[san].min,
    data_max_date: KHOANG_DU_LIEU[san].max,
  };
}

export function kpi(san, q) {
  const muc = docMuc(q);
  const loc = docLoc(san, q);
  const ky = xacDinhKy(san, muc, q.period);
  const { hienTai, truoc, tinhTrang } = tinhKyVoiTruoc(san, ky, loc);
  const dayDuTinhThuc = ky.dayDu;
  const metrics = dungMetrics(hienTai, truoc, tinhTrang);

  // previous_full: chỉ khi kỳ chưa đủ ngày và có kỳ trước (§12.1.1.2, bổ sung 29/10/2026).
  let truocNguyen = null;
  if (!dayDuTinhThuc && muc !== 'day' && ky.truoc && hienTai.coDuLieu) {
    const full = layKhoang(san, ky.truoc.dau, ky.truoc.cuoiLich, loc);
    if (full.coDuLieu && full.rev > 0) {
      truocNguyen = {
        period: ky.truoc.ma,
        revenue: full.rev,
        pct_change_if_used: lamTron1(((hienTai.rev - full.rev) / full.rev) * 100),
      };
    }
  }

  // Cảnh báo dùng pct_change CHƯA làm tròn (§12.1 "Cài đặt bước 13"): −29,96 không bị làm tròn thành −30,0.
  let kichHoat = false;
  if (tinhTrang === 'ok' && truoc && truoc.coDuLieu && truoc.rev > 0) {
    const thoCuaKyNay = ((hienTai.rev - truoc.rev) / truoc.rev) * 100;
    kichHoat = thoCuaKyNay <= NGUONG_CANH_BAO_PCT;
  }

  let chatLuong;
  if (!hienTai.coDuLieu) {
    chatLuong = { rows_status_unknown: null, revenue_status_unknown: null, rows_nmv_provisional: null };
  } else if (san === 'shopee') {
    const ty = hienTai.rev / TONG_TOAN_BO.shopee.revenue;
    chatLuong = {
      rows_status_unknown: Math.round(DONG_UNKNOWN_SHOPEE.rows * ty),
      revenue_status_unknown: Math.round(DONG_UNKNOWN_SHOPEE.revenue * ty),
      rows_nmv_provisional: DONG_NMV_TAM_TINH.shopee,
    };
  } else {
    chatLuong = { rows_status_unknown: 0, revenue_status_unknown: 0, rows_nmv_provisional: DONG_NMV_TAM_TINH.tiktok };
  }

  let daily = null;
  if (muc !== 'day') {
    daily = hienTai.ngay.map((d, i) => {
      const dTruoc = truoc && truoc.ngay[i] ? truoc.ngay[i] : null;
      return {
        day_index: i + 1,
        date: d.date,
        previous_date: dTruoc ? dTruoc.date : null,
        current: d.rev,
        previous: dTruoc ? dTruoc.rev : null,
      };
    });
  }

  return {
    platform: san,
    granularity: muc,
    period: ky.ma,
    status: tinhTrang,
    current: khoangCua(ky),
    previous: ky.truoc ? { period: ky.truoc.ma, date_from: ky.truoc.dau, date_to: ky.truoc.den } : null,
    period_complete: ky.dayDu,
    data_max_date: KHOANG_DU_LIEU[san].max,
    metrics,
    previous_full: truocNguyen,
    alert: { triggered: kichHoat, threshold_pct: NGUONG_CANH_BAO_PCT },
    data_quality: chatLuong,
    daily,
  };
}

export function revenueTrend(san, q) {
  const muc = docMuc(q);
  const loc = docLoc(san, q);
  const { min, max } = KHOANG_DU_LIEU[san];
  const tu = q.date_from || min;
  const den = q.date_to || max;
  const dsKy = [];
  let ma = maKyChuaNgay(muc, tu);
  const maCuoi = maKyChuaNgay(muc, den);
  for (let i = 0; i < 5000; i += 1) {
    dsKy.push(ma);
    if (ma === maCuoi) {
      break;
    }
    ma = kyKeTiep(muc, ma);
  }

  const items = dsKy.map((m) => {
    const dauKy = ngayDauKy(muc, m);
    const cuoiKy = ngayCuoiKy(muc, m);
    const k = layKhoang(san, dauKy > tu ? dauKy : tu, cuoiKy < den ? cuoiKy : den, loc);
    return { m, k };
  });

  // top_product_codes: tối đa 4 mã có doanh thu lớn nhất trên TOÀN khoảng trả về (§12.1.1.3).
  const tongTheoMa = {};
  items.forEach(({ k }) => {
    Object.keys(k.ma).forEach((c) => {
      tongTheoMa[c] = (tongTheoMa[c] || 0) + k.ma[c];
    });
  });
  const top = Object.keys(tongTheoMa)
    .filter((c) => tongTheoMa[c] > 0)
    .sort((a, b) => tongTheoMa[b] - tongTheoMa[a] || (a < b ? -1 : 1))
    .slice(0, 4);

  return {
    platform: san,
    granularity: muc,
    top_product_codes: top,
    items: items.map(({ m, k }) => {
      const hopLe = { period: m, revenue: null, order_count: null, period_complete: ngayCuoiKy(muc, m) <= max, by_product: null };
      if (!k.coDuLieu) {
        return hopLe;
      }
      const byProduct = top.map((c) => ({ product_code: c, revenue: k.ma[c] || 0 }));
      const tongTop = byProduct.reduce((a, b) => a + b.revenue, 0);
      byProduct.push({ product_code: null, revenue: k.rev - tongTop });
      return { ...hopLe, revenue: k.rev, order_count: k.orders, by_product: byProduct };
    }),
  };
}

export function topProducts(san, q) {
  const muc = docMuc(q);
  const loc = docLoc(san, q);
  const ky = xacDinhKy(san, muc, q.period);
  const { hienTai, truoc, tinhTrang } = tinhKyVoiTruoc(san, ky, loc);
  const gioiHan = Number(q.limit || 10);
  const sapTheo = q.sort_by === 'quantity' ? 'quantity' : 'revenue';
  const ketQua = { platform: san, period: ky.ma, status: tinhTrang, items: [] };
  if (tinhTrang === 'no_data') {
    return ketQua;
  }
  const dsMa = Object.keys(hienTai.ma).filter((c) => hienTai.ma[c] > 0);
  const soLuong = chiaTheoTrongSo(
    hienTai.qty,
    dsMa.map((c) => hienTai.ma[c]),
  );
  const items = dsMa.map((c, i) => {
    const r = hienTai.ma[c];
    const muc1 = { product_code: c, revenue: r, quantity: soLuong[i], share_pct: phanTram(r, hienTai.rev) };
    if (tinhTrang === 'insufficient_data') {
      return { ...muc1, pct_change: null, previous_zero: false };
    }
    const truocMa = truoc && truoc.coDuLieu ? truoc.ma[c] || 0 : 0;
    if (truocMa === 0) {
      return { ...muc1, pct_change: null, previous_zero: true };
    }
    return { ...muc1, pct_change: lamTron1(((r - truocMa) / truocMa) * 100), previous_zero: false };
  });
  items.sort((a, b) => b[sapTheo] - a[sapTheo] || (a.product_code < b.product_code ? -1 : 1));
  ketQua.items = items.slice(0, gioiHan);
  return ketQua;
}

function kyDonGian(san, q) {
  const muc = docMuc(q);
  const ky = xacDinhKy(san, muc, q.period);
  return ky;
}

export function byAffiliate(san, q) {
  const ky = kyDonGian(san, q);
  const k = layKhoang(san, ky.dau, ky.den, docLoc(san, q));
  if (!k.coDuLieu) {
    return { platform: san, period: ky.ma, status: 'no_data', affiliate: null, self_sold: null };
  }
  return {
    platform: san,
    period: ky.ma,
    status: 'ok',
    affiliate: { revenue: k.affRev, order_count: k.affOrders, share_pct: phanTram(k.affRev, k.rev) },
    self_sold: {
      revenue: k.rev - k.affRev,
      order_count: k.orders - k.affOrders,
      share_pct: phanTram(k.rev - k.affRev, k.rev),
    },
  };
}

/** Danh sách tỉnh đã sắp (nhóm "Khác" cuối), dùng chung cho by-province và compare. */
function thongKeTinh(san, k) {
  const ds = DANH_SACH_TINH[san].map(([ten, w]) => ({ ten, w, laKhac: false }));
  ds.push({ ten: 'Khác', w: TY_TRONG_KHAC, laKhac: true });
  const trongSo = ds.map((t) => t.w);
  const donTheoTinh = chiaTheoTrongSo(k.orders, trongSo);
  // Tỉnh không có đơn thì không có doanh thu: dùng đơn làm trọng số để hai số luôn nhất quán.
  const doanhThuTheoTinh = chiaTheoTrongSo(
    k.rev,
    donTheoTinh.map((d, i) => (d > 0 ? trongSo[i] : 0)),
  );
  const muc2 = [];
  ds.forEach((t, i) => {
    if (donTheoTinh[i] > 0 && doanhThuTheoTinh[i] > 0) {
      muc2.push({
        province: t.ten,
        order_count: donTheoTinh[i],
        revenue: doanhThuTheoTinh[i],
        share_pct: phanTram(doanhThuTheoTinh[i], k.rev),
        is_other: t.laKhac,
      });
    }
  });
  muc2.sort((a, b) => Number(a.is_other) - Number(b.is_other) || b.revenue - a.revenue);
  return muc2;
}

export function byProvince(san, q) {
  const ky = kyDonGian(san, q);
  const k = layKhoang(san, ky.dau, ky.den, docLoc(san, q));
  if (!k.coDuLieu) {
    return { platform: san, period: ky.ma, status: 'no_data', province_count: null, items: [] };
  }
  const items = thongKeTinh(san, k);
  return {
    platform: san,
    period: ky.ma,
    status: 'ok',
    province_count: items.filter((m) => !m.is_other).length,
    items,
  };
}

/** 24 phần tử giờ 0..23 (SPEC §12.1.1.7), dùng chung cho by-hour và compare. */
function thongKeGio(san, k) {
  const donTheoGio = chiaTheoTrongSo(k.orders, TY_TRONG_GIO[san]);
  const doanhThuTheoGio = chiaTheoTrongSo(k.rev, TY_TRONG_GIO[san]);
  return donTheoGio.map((d, gio) => ({
    hour: gio,
    label: `${gio}H - ${gio + 1}H`,
    order_count: d,
    revenue: doanhThuTheoGio[gio],
    share_pct: k.orders ? phanTram(d, k.orders) : 0,
  }));
}

export function byHour(san, q) {
  const ky = kyDonGian(san, q);
  const k = layKhoang(san, ky.dau, ky.den, docLoc(san, q));
  if (!k.coDuLieu) {
    return { platform: san, period: ky.ma, status: 'no_data', items: [] };
  }
  return { platform: san, period: ky.ma, status: 'ok', items: thongKeGio(san, k) };
}

export function alerts(san, q) {
  const muc = docMuc(q);
  const loc = docLoc(san, q);
  const { min, max } = KHOANG_DU_LIEU[san];
  const items = [];
  let ma = maKyChuaNgay(muc, min);
  const maCuoi = maKyChuaNgay(muc, max);
  for (let i = 0; i < 5000; i += 1) {
    const ky = xacDinhKy(san, muc, ma);
    const { hienTai, truoc, tinhTrang } = tinhKyVoiTruoc(san, ky, loc);
    // Không bao giờ cảnh báo khi: không có kỳ trước, kỳ trước bằng 0, kỳ này không có dòng (SPEC §9.1 "Cài đặt").
    if (tinhTrang === 'ok' && truoc && truoc.coDuLieu && truoc.rev > 0) {
      const tho = ((hienTai.rev - truoc.rev) / truoc.rev) * 100;
      if (tho <= NGUONG_CANH_BAO_PCT) {
        items.push({
          period: ky.ma,
          previous_period: ky.truoc.ma,
          revenue: hienTai.rev,
          revenue_previous: truoc.rev,
          pct_change: lamTron1(tho),
          previous_zero: false,
          period_complete: ky.dayDu,
        });
      }
    }
    if (ma === maCuoi) {
      break;
    }
    ma = kyKeTiep(muc, ma);
  }
  return { platform: san, granularity: muc, threshold_pct: NGUONG_CANH_BAO_PCT, items };
}

/** Một cánh (một sàn) của trang đối chiếu (SPEC §12.1.2). */
function canhSoSanh(san, muc, maKy) {
  const ky = xacDinhKy(san, muc, maKy);
  const { hienTai, truoc, tinhTrang } = tinhKyVoiTruoc(san, ky, {});
  const khoi = {
    status: tinhTrang,
    data_max_date: KHOANG_DU_LIEU[san].max,
    period_complete: ky.dayDu,
    current: khoangCua(ky),
    previous: ky.truoc ? { period: ky.truoc.ma, date_from: ky.truoc.dau, date_to: ky.truoc.den } : null,
    metrics: dungMetrics(hienTai, truoc, tinhTrang),
    by_hour: [],
    by_product: [],
    by_province_top: [],
  };
  if (!hienTai.coDuLieu) {
    return khoi;
  }
  khoi.by_hour = thongKeGio(san, hienTai).map((g) => ({
    hour: g.hour,
    label: g.label,
    order_count: g.order_count,
    share_pct: g.share_pct,
  }));
  const tp = topProducts(san, { granularity: muc, period: ky.ma, limit: 1000 });
  khoi.by_product = tp.items.map((m) => ({ product_code: m.product_code, revenue: m.revenue, quantity: m.quantity }));
  khoi.by_province_top = thongKeTinh(san, hienTai)
    .filter((m) => !m.is_other)
    .slice(0, 10)
    .map((m) => ({ province: m.province, revenue: m.revenue, share_pct: m.share_pct }));
  return khoi;
}

/**
 * Đối chiếu hai sàn. Chỉ có hai khóa sàn, KHÔNG có `total` (SPEC §12, §12.1.2).
 * Không có `period`: dùng kỳ chứa ngày dữ liệu mới nhất của CẢ HAI sàn (§12.1 "Cài đặt bước 13").
 */
export function comparePlatforms(q) {
  const muc = docMuc(q);
  const ngayMoiNhat = KHOANG_DU_LIEU.shopee.max > KHOANG_DU_LIEU.tiktok.max ? KHOANG_DU_LIEU.shopee.max : KHOANG_DU_LIEU.tiktok.max;
  const ma = q.period || maKyChuaNgay(muc, ngayMoiNhat);
  return {
    granularity: muc,
    period: ma,
    shopee: canhSoSanh('shopee', muc, ma),
    tiktok: canhSoSanh('tiktok', muc, ma),
  };
}
