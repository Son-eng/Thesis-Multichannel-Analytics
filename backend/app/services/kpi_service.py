"""Tính KPI: doanh thu là SUM(nmv_after_tax) trên dòng không hủy, không hoàn; đếm đơn bằng COUNT(DISTINCT order_id)."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text

from app.services.alert_service import co_canh_bao, nguong_giam

# Mọi sàn chung một bảng orders nên truy vấn nào cũng phải lọc platform.
SAN_HOP_LE = ("shopee", "tiktok")

# Cột mức đơn lặp lại trên mọi dòng của đơn, không được SUM theo dòng.
ORDER_LEVEL_COLUMNS = {"shopee": [], "tiktok": ["order_amount"]}

HOP_LE = "order_status <> 'cancelled' AND is_returned = FALSE"
SO_MA_SAN_PHAM_TOP = 4


class KyKhongHopLe(ValueError):
    """(giữ một dòng)"""


def lam_tron_1(so):
    return float(Decimal(str(so)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def phan_tram(tu, mau):
    if tu is None or not mau:
        return None
    return lam_tron_1(Decimal(tu) * 100 / Decimal(mau))


def thay_doi_phan_tram(gia_tri, truoc):
    if gia_tri is None or truoc is None or truoc == 0:
        return None
    return lam_tron_1((Decimal(gia_tri) - Decimal(truoc)) * 100 / Decimal(truoc))


def thay_doi_phan_tram_tho(gia_tri, truoc):
    if gia_tri is None or truoc is None or truoc == 0:
        return None
    return float((Decimal(gia_tri) - Decimal(truoc)) * 100 / Decimal(truoc))


def _cong_thang(ngay, so_thang):
    thang_goc = ngay.year * 12 + (ngay.month - 1) + so_thang
    nam, thang = divmod(thang_goc, 12)
    return date(nam, thang + 1, 1)


def ky_chua_ngay(muc, ngay):
    if muc == "day":
        return ngay, ngay, ngay.isoformat()
    if muc == "month":
        dau = date(ngay.year, ngay.month, 1)
        return dau, _cong_thang(dau, 1) - timedelta(days=1), f"{ngay.year:04d}-{ngay.month:02d}"
    if muc == "quarter":
        quy = (ngay.month - 1) // 3
        dau = date(ngay.year, quy * 3 + 1, 1)
        return dau, _cong_thang(dau, 3) - timedelta(days=1), f"{ngay.year:04d}-Q{quy + 1}"
    return date(ngay.year, 1, 1), date(ngay.year, 12, 31), f"{ngay.year:04d}"


def doc_ma_ky(muc, ma_ky):
    try:
        if muc == "day":
            return date.fromisoformat(ma_ky)
        if muc == "month":
            nam, thang = ma_ky.split("-")
            if len(nam) != 4 or len(thang) != 2:
                raise ValueError
            return date(int(nam), int(thang), 1)
        if muc == "quarter":
            nam, quy = ma_ky.split("-Q")
            if len(nam) != 4 or quy not in ("1", "2", "3", "4"):
                raise ValueError
            return date(int(nam), (int(quy) - 1) * 3 + 1, 1)
        if len(ma_ky) != 4:
            raise ValueError
        return date(int(ma_ky), 1, 1)
    except ValueError:
        raise KyKhongHopLe(f"Mã kỳ '{ma_ky}' không đúng định dạng của mức '{muc}'") from None


def ky_truoc_cua(muc, dau_ky):
    if muc == "day":
        return dau_ky - timedelta(days=1)
    return _cong_thang(dau_ky, {"month": -1, "quarter": -3, "year": -12}[muc])


def ky_ke_tiep(muc, dau_ky):
    if muc == "day":
        return dau_ky + timedelta(days=1)
    return _cong_thang(dau_ky, {"month": 1, "quarter": 3, "year": 12}[muc])


def xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max):
    """Kỳ chưa đầy đủ thì cắt kỳ trước về cùng số ngày, mốc là MAX(order_date) của từng sàn chứ không dùng NOW()."""
    if ma_ky is None:
        dau, cuoi, ma_ky = ky_chua_ngay(muc, ngay_max)
    else:
        dau = doc_ma_ky(muc, ma_ky)
        dau, cuoi, ma_ky = ky_chua_ngay(muc, dau)
    # Mức ngày luôn đầy đủ, không cắt.
    day_du = True if muc == "day" else ngay_max >= cuoi
    den = cuoi if (day_du or ngay_max < dau) else ngay_max

    dau_truoc = ky_truoc_cua(muc, dau)
    _, cuoi_truoc, ma_truoc = ky_chua_ngay(muc, dau_truoc)
    truoc = None
    if dau_truoc >= ngay_min:
        den_truoc = cuoi_truoc if day_du else min(cuoi_truoc, dau_truoc + (den - dau))
        truoc = {"ky": ma_truoc, "dau": dau_truoc, "cuoi_day_du": cuoi_truoc, "den": den_truoc}
    return {"ky": ma_ky, "dau": dau, "cuoi": cuoi, "den": den, "day_du": day_du, "truoc": truoc}


def _loc(san, shop_name, product_code):
    menh_de, tham_so = " AND platform = :platform", {"platform": san}
    if shop_name:
        menh_de += " AND shop_name = :shop_name"
        tham_so["shop_name"] = shop_name
    if product_code:
        menh_de += " AND product_code = :product_code"
        tham_so["product_code"] = product_code
    return menh_de, tham_so


def khoang_du_lieu(phien, san):
    dong = phien.execute(text("SELECT MIN(order_date), MAX(order_date) FROM orders WHERE platform = :platform"),
                         {"platform": san}).one()
    return dong[0], dong[1]


def danh_sach_loc(phien, san):
    ngay_min, ngay_max = khoang_du_lieu(phien, san)
    cac_shop = phien.execute(text("SELECT DISTINCT shop_name FROM orders WHERE platform = :platform ORDER BY shop_name"),
                             {"platform": san}).scalars().all()
    cac_ma = phien.execute(text(
        "SELECT DISTINCT product_code FROM orders WHERE platform = :platform AND product_code IS NOT NULL ORDER BY product_code"),
        {"platform": san}).scalars().all()
    return {"platform": san, "shops": cac_shop, "product_codes": cac_ma,
            "data_min_date": ngay_min.isoformat() if ngay_min else None,
            "data_max_date": ngay_max.isoformat() if ngay_max else None}


def so_lieu_khoang(phien, san, tu_ngay, den_ngay, shop_name=None, product_code=None):
    """Các con số gốc của khoảng ngày [tu_ngay, den_ngay], tính bằng một câu SQL."""
    loc, tham_so = _loc(san, shop_name, product_code)
    cot_tam_tinh = ("COUNT(*) FILTER (WHERE nmv_is_provisional)" if san == "shopee" else "NULL")
    dong = phien.execute(text(f"""
        SELECT COUNT(*) AS so_dong,
               COALESCE(SUM(nmv_after_tax) FILTER (WHERE {HOP_LE}), 0) AS revenue,
               COUNT(DISTINCT order_id) FILTER (WHERE {HOP_LE}) AS order_count,
               COUNT(DISTINCT order_id) AS order_count_all,
               COALESCE(SUM(quantity) FILTER (WHERE {HOP_LE}), 0) AS quantity,
               COUNT(DISTINCT order_id) FILTER (WHERE order_status = 'cancelled') AS cancelled_orders,
               COUNT(DISTINCT order_id) FILTER (WHERE is_returned) AS returned_orders,
               COALESCE(SUM(nmv_after_tax) FILTER (WHERE {HOP_LE} AND is_affiliate), 0) AS affiliate_revenue,
               COUNT(*) FILTER (WHERE order_status = 'unknown') AS rows_unknown,
               COALESCE(SUM(nmv_after_tax) FILTER (WHERE {HOP_LE} AND order_status = 'unknown'), 0) AS revenue_unknown,
               {cot_tam_tinh} AS rows_provisional
        FROM orders
        WHERE order_date BETWEEN :tu AND :den {loc}
    """), {"tu": tu_ngay, "den": den_ngay, **tham_so}).mappings().one()
    ket_qua = dict(dong)
    for khoa in ("revenue", "affiliate_revenue", "revenue_unknown"):
        ket_qua[khoa] = int(ket_qua[khoa])
    return ket_qua


def chi_so_so(gia_tri, truoc, co_ky_truoc, truoc_khong_xac_dinh=False):
    if gia_tri is None:
        return {"value": None, "previous": truoc if co_ky_truoc else None, "pct_change": None, "previous_zero": False}
    if not co_ky_truoc:
        return {"value": gia_tri, "previous": None, "pct_change": None, "previous_zero": False}
    if truoc_khong_xac_dinh or truoc is None:
        return {"value": gia_tri, "previous": None, "pct_change": None, "previous_zero": True}
    if truoc == 0:
        return {"value": gia_tri, "previous": 0, "pct_change": None, "previous_zero": True}
    return {"value": gia_tri, "previous": truoc, "pct_change": thay_doi_phan_tram(gia_tri, truoc), "previous_zero": False}


def chi_so_ty_le(tu_nay, mau_nay, tu_truoc, mau_truoc, co_ky_truoc):
    gia_tri = phan_tram(tu_nay, mau_nay)
    truoc = phan_tram(tu_truoc, mau_truoc) if co_ky_truoc else None
    if gia_tri is None or truoc is None:
        return {"value": gia_tri, "previous": truoc, "change_pp": None}
    chenh = Decimal(tu_nay) * 100 / Decimal(mau_nay) - Decimal(tu_truoc) * 100 / Decimal(mau_truoc)
    return {"value": gia_tri, "previous": truoc, "change_pp": lam_tron_1(chenh)}


def _aov(so):
    return round(Decimal(so["revenue"]) / so["order_count"]) if so["order_count"] else None


def dung_metrics(hien_tai, truoc, co_du_lieu):
    co_truoc = truoc is not None

    def lay(khoa):
        return (hien_tai[khoa] if co_du_lieu else None), (truoc[khoa] if co_truoc else None)

    metrics = {}
    for ten, khoa in (("revenue", "revenue"), ("order_count", "order_count"),
                      ("order_count_all", "order_count_all"), ("quantity_sold", "quantity")):
        gia_tri, truoc_gt = lay(khoa)
        metrics[ten] = chi_so_so(gia_tri, truoc_gt, co_truoc)

    aov_nay = _aov(hien_tai) if co_du_lieu else None
    aov_truoc = _aov(truoc) if co_truoc else None
    metrics["aov"] = chi_so_so(aov_nay, aov_truoc, co_truoc,
                               truoc_khong_xac_dinh=co_truoc and aov_truoc is None)
    if aov_nay is None and co_du_lieu:                     # kỳ này có dòng nhưng không có đơn hợp lệ nên AOV không tính được
        metrics["aov"] = {"value": None, "previous": aov_truoc, "pct_change": None, "previous_zero": False}

    if not co_du_lieu:
        for ten in ("cancel_rate", "return_rate", "affiliate_share"):
            metrics[ten] = {"value": None, "previous": None, "change_pp": None}
        return metrics
    t = truoc or {}
    metrics["cancel_rate"] = chi_so_ty_le(hien_tai["cancelled_orders"], hien_tai["order_count_all"],
                                          t.get("cancelled_orders"), t.get("order_count_all"), co_truoc)
    metrics["return_rate"] = chi_so_ty_le(hien_tai["returned_orders"], hien_tai["order_count_all"],
                                          t.get("returned_orders"), t.get("order_count_all"), co_truoc)
    metrics["affiliate_share"] = chi_so_ty_le(hien_tai["affiliate_revenue"], hien_tai["revenue"],
                                              t.get("affiliate_revenue"), t.get("revenue"), co_truoc)
    return metrics


def doanh_thu_theo_ngay(phien, san, tu_ngay, den_ngay, shop_name=None, product_code=None):
    loc, tham_so = _loc(san, shop_name, product_code)
    cac_dong = phien.execute(text(f"""
        SELECT order_date, SUM(nmv_after_tax) FROM orders
        WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} {loc} GROUP BY order_date
    """), {"tu": tu_ngay, "den": den_ngay, **tham_so}).all()
    return {ngay: int(tien) for ngay, tien in cac_dong}


def dung_daily(phien, san, ky, shop_name, product_code):
    hien_tai = doanh_thu_theo_ngay(phien, san, ky["dau"], ky["den"], shop_name, product_code)
    truoc = ky["truoc"]
    truoc_theo_ngay = (doanh_thu_theo_ngay(phien, san, truoc["dau"], truoc["den"], shop_name, product_code)
                       if truoc else {})
    ket_qua = []
    so_ngay = (ky["den"] - ky["dau"]).days + 1
    for chi_so in range(so_ngay):
        ngay = ky["dau"] + timedelta(days=chi_so)
        ngay_truoc = None
        if truoc and truoc["dau"] + timedelta(days=chi_so) <= truoc["den"]:
            ngay_truoc = truoc["dau"] + timedelta(days=chi_so)
        ket_qua.append({
            "day_index": chi_so + 1, "date": ngay.isoformat(),
            "previous_date": ngay_truoc.isoformat() if ngay_truoc else None,
            "current": hien_tai.get(ngay, 0),
            # Ngày không có ở kỳ trước (kỳ trước ngắn hơn) là null, không phải 0.
            "previous": truoc_theo_ngay.get(ngay_truoc, 0) if ngay_truoc else None,
        })
    return ket_qua


def kpi(phien, san, muc, ma_ky, shop_name=None, product_code=None):
    ngay_min, ngay_max = khoang_du_lieu(phien, san)
    if ngay_max is None:
        ngay_min = ngay_max = date.today()
    ky = xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max)
    hien_tai = so_lieu_khoang(phien, san, ky["dau"], ky["den"], shop_name, product_code)
    co_du_lieu = hien_tai["so_dong"] > 0
    truoc_ky = ky["truoc"]
    truoc = so_lieu_khoang(phien, san, truoc_ky["dau"], truoc_ky["den"], shop_name, product_code) if truoc_ky else None

    if not co_du_lieu:
        trang_thai = "no_data"
    elif truoc_ky is None:
        trang_thai = "insufficient_data"
    else:
        trang_thai = "ok"

    metrics = dung_metrics(hien_tai, truoc, co_du_lieu)
    nguong = nguong_giam()
    pct_tho = (thay_doi_phan_tram_tho(hien_tai["revenue"], truoc["revenue"])
               if (co_du_lieu and truoc is not None) else None)

    ket_qua = {
        "platform": san, "granularity": muc, "period": ky["ky"], "status": trang_thai,
        "current": {"date_from": ky["dau"].isoformat(), "date_to": ky["den"].isoformat()},
        "previous": None if truoc_ky is None else {
            "period": truoc_ky["ky"], "date_from": truoc_ky["dau"].isoformat(), "date_to": truoc_ky["den"].isoformat()},
        "period_complete": ky["day_du"],
        "data_max_date": ngay_max.isoformat(),
        "metrics": metrics,
        "previous_full": None,
        "alert": {"triggered": co_canh_bao(pct_tho, nguong), "threshold_pct": -nguong},
        "data_quality": {
            "rows_status_unknown": hien_tai["rows_unknown"] if co_du_lieu else None,
            "revenue_status_unknown": hien_tai["revenue_unknown"] if co_du_lieu else None,
            "rows_nmv_provisional": hien_tai["rows_provisional"] if co_du_lieu else None,
        },
        "daily": None,
    }
    if not ky["day_du"] and truoc_ky is not None and co_du_lieu:
        # Doanh thu nguyên kỳ trước, chỉ để minh họa vì sao phải cắt cùng số ngày.
        nguyen = so_lieu_khoang(phien, san, truoc_ky["dau"], truoc_ky["cuoi_day_du"], shop_name, product_code)
        ket_qua["previous_full"] = {"period": truoc_ky["ky"], "revenue": nguyen["revenue"],
                                    "pct_change_if_used": thay_doi_phan_tram(hien_tai["revenue"], nguyen["revenue"])}
    if muc != "day":
        ket_qua["daily"] = dung_daily(phien, san, ky, shop_name, product_code) if co_du_lieu else None
    return ket_qua


def _trang_thai_don_gian(so_dong):
    return "ok" if so_dong else "no_data"


def revenue_trend(phien, san, muc, tu_ngay, den_ngay, shop_name=None, product_code=None):
    ngay_min, ngay_max = khoang_du_lieu(phien, san)
    if ngay_max is None:
        return {"platform": san, "granularity": muc, "top_product_codes": [], "items": []}
    tu_ngay = tu_ngay or ngay_min
    den_ngay = den_ngay or ngay_max
    loc, tham_so = _loc(san, shop_name, product_code)
    tham_so_khoang = {"tu": tu_ngay, "den": den_ngay, **tham_so}

    # Gộp theo (ngày, mã) rồi chia kỳ ở Python để mọi mức dùng cùng một cách chia.
    cac_dong = phien.execute(text(f"""
        SELECT order_date, product_code,
               COUNT(*) AS so_dong,
               COALESCE(SUM(nmv_after_tax) FILTER (WHERE {HOP_LE}), 0) AS revenue
        FROM orders WHERE order_date BETWEEN :tu AND :den {loc}
        GROUP BY order_date, product_code
    """), tham_so_khoang).all()
    don_hop_le = phien.execute(text(f"""
        SELECT order_date, COUNT(DISTINCT order_id) FROM orders
        WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} {loc} GROUP BY order_date
    """), tham_so_khoang).all()
    # Một đơn chỉ thuộc một ngày đặt nên cộng số đơn theo ngày vào kỳ là đúng.
    don_theo_ngay = {ngay: so for ngay, so in don_hop_le}

    tong_theo_ma = {}
    for _, ma, _, tien in cac_dong:
        if ma is not None:
            tong_theo_ma[ma] = tong_theo_ma.get(ma, 0) + int(tien)
    top = [ma for ma, _ in sorted(tong_theo_ma.items(), key=lambda kv: (-kv[1], kv[0]))[:SO_MA_SAN_PHAM_TOP]]

    cac_ky = {}
    dau = ky_chua_ngay(muc, tu_ngay)[0]
    cuoi = ky_chua_ngay(muc, den_ngay)[0]
    while dau <= cuoi:
        _, het, ma_ky = ky_chua_ngay(muc, dau)
        cac_ky[dau] = {"period": ma_ky, "rows": 0, "revenue": 0, "orders": 0, "by": {}, "cuoi": het}
        dau = ky_ke_tiep(muc, dau)
    for ngay, ma, so_dong, tien in cac_dong:
        ky = cac_ky[ky_chua_ngay(muc, ngay)[0]]
        ky["rows"] += so_dong
        ky["revenue"] += int(tien)
        ky["by"][ma] = ky["by"].get(ma, 0) + int(tien)
    for ngay, so in don_theo_ngay.items():
        cac_ky[ky_chua_ngay(muc, ngay)[0]]["orders"] += so

    items = []
    for ky in cac_ky.values():
        co_dong = ky["rows"] > 0
        by_product = None
        if co_dong:
            by_product = [{"product_code": ma, "revenue": ky["by"].get(ma, 0)} for ma in top]
            # Phần còn lại gồm mã ngoài top và dòng chưa có mã, để tổng bằng đúng doanh thu kỳ.
            by_product.append({"product_code": None, "revenue": ky["revenue"] - sum(p["revenue"] for p in by_product)})
        items.append({"period": ky["period"],
                      "revenue": ky["revenue"] if co_dong else None,
                      "order_count": ky["orders"] if co_dong else None,
                      "period_complete": True if muc == "day" else ngay_max >= ky["cuoi"],
                      "by_product": by_product})
    return {"platform": san, "granularity": muc, "top_product_codes": top, "items": items}


def top_products(phien, san, muc, ma_ky, limit, sort_by, shop_name=None, product_code=None):
    """Nhóm theo product_code, kèm % thay đổi so với kỳ trước đã cắt."""
    ngay_min, ngay_max = khoang_du_lieu(phien, san)
    if ngay_max is None:
        ngay_min = ngay_max = date.today()
    ky = xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max)
    loc, tham_so = _loc(san, shop_name, product_code)

    def theo_ma(tu, den):
        cac_dong = phien.execute(text(f"""
            SELECT product_code, SUM(nmv_after_tax) AS revenue, SUM(quantity) AS quantity FROM orders
            WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} {loc} GROUP BY product_code
        """), {"tu": tu, "den": den, **tham_so}).all()
        return {ma: (int(tien), int(sl)) for ma, tien, sl in cac_dong}

    so_dong = so_lieu_khoang(phien, san, ky["dau"], ky["den"], shop_name, product_code)["so_dong"]
    if so_dong == 0:
        trang_thai, hien_tai = "no_data", {}
    else:
        trang_thai = "ok" if ky["truoc"] else "insufficient_data"
        hien_tai = theo_ma(ky["dau"], ky["den"])
    truoc = theo_ma(ky["truoc"]["dau"], ky["truoc"]["den"]) if (ky["truoc"] and hien_tai) else None

    tong = sum(tien for tien, _ in hien_tai.values())
    cac_muc = []
    for ma, (tien, sl) in hien_tai.items():
        if truoc is None:
            pct, pz = None, False
        else:
            tien_truoc = truoc.get(ma, (0, 0))[0]
            pct, pz = (None, True) if tien_truoc == 0 else (thay_doi_phan_tram(tien, tien_truoc), False)
        cac_muc.append({"product_code": ma, "revenue": tien, "quantity": sl,
                        "share_pct": phan_tram(tien, tong), "pct_change": pct, "previous_zero": pz})
    if sort_by == "quantity":
        khoa_sap = lambda m: (-m["quantity"], -m["revenue"])
    else:
        khoa_sap = lambda m: (-m["revenue"], -m["quantity"])
    cac_muc.sort(key=lambda m: (khoa_sap(m), m["product_code"] is None, m["product_code"] or ""))
    return {"platform": san, "period": ky["ky"], "status": trang_thai, "items": cac_muc[:limit]}


def _ky_don_gian(phien, san, muc, ma_ky):
    ngay_min, ngay_max = khoang_du_lieu(phien, san)
    if ngay_max is None:
        ngay_min = ngay_max = date.today()
    return xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max), ngay_max


def by_affiliate(phien, san, muc, ma_ky, shop_name=None, product_code=None):
    """Doanh thu và số đơn hợp lệ của hai nhánh affiliate; tổng hai nhánh bằng doanh thu sàn."""
    ky, _ = _ky_don_gian(phien, san, muc, ma_ky)
    loc, tham_so = _loc(san, shop_name, product_code)
    so_dong = so_lieu_khoang(phien, san, ky["dau"], ky["den"], shop_name, product_code)["so_dong"]
    ket_qua = {"platform": san, "period": ky["ky"], "status": _trang_thai_don_gian(so_dong),
               "affiliate": None, "self_sold": None}
    if not so_dong:
        return ket_qua
    cac_dong = phien.execute(text(f"""
        SELECT is_affiliate, COALESCE(SUM(nmv_after_tax), 0), COUNT(DISTINCT order_id) FROM orders
        WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} {loc} GROUP BY is_affiliate
    """), {"tu": ky["dau"], "den": ky["den"], **tham_so}).all()
    theo_co = {co: (int(tien), so_don) for co, tien, so_don in cac_dong}
    tong = sum(tien for tien, _ in theo_co.values())
    for khoa, co in (("affiliate", True), ("self_sold", False)):
        tien, so_don = theo_co.get(co, (0, 0))
        ket_qua[khoa] = {"revenue": tien, "order_count": so_don, "share_pct": phan_tram(tien, tong)}
    return ket_qua


def thong_ke_theo_tinh(phien, san, ky, shop_name=None, product_code=None):
    loc, tham_so = _loc(san, shop_name, product_code)
    cac_dong = phien.execute(text(f"""
        SELECT COALESCE(province, 'Khác'), COUNT(DISTINCT order_id), SUM(nmv_after_tax) FROM orders
        WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} {loc} GROUP BY 1
    """), {"tu": ky["dau"], "den": ky["den"], **tham_so}).all()
    tong = sum(int(tien) for _, _, tien in cac_dong)
    cac_muc = [{"province": tinh, "order_count": so_don, "revenue": int(tien),
                "share_pct": phan_tram(int(tien), tong), "is_other": tinh == "Khác"}
               for tinh, so_don, tien in cac_dong]
    cac_muc.sort(key=lambda m: (m["is_other"], -m["revenue"], m["province"]))
    return cac_muc


def by_province(phien, san, muc, ma_ky, shop_name=None, product_code=None):
    ky, _ = _ky_don_gian(phien, san, muc, ma_ky)
    so_dong = so_lieu_khoang(phien, san, ky["dau"], ky["den"], shop_name, product_code)["so_dong"]
    if not so_dong:
        return {"platform": san, "period": ky["ky"], "status": "no_data", "province_count": None, "items": []}
    cac_muc = thong_ke_theo_tinh(phien, san, ky, shop_name, product_code)
    return {"platform": san, "period": ky["ky"], "status": "ok",
            "province_count": sum(1 for m in cac_muc if not m["is_other"]), "items": cac_muc}


def thong_ke_theo_gio(phien, san, ky, shop_name=None, product_code=None):
    """24 phần tử (giờ 0–23, kể cả giờ không có đơn) — dùng chung cho `/by-hour` và compare."""
    loc, tham_so = _loc(san, shop_name, product_code)
    cac_dong = phien.execute(text(f"""
        SELECT hour_bucket, COUNT(DISTINCT order_id), COALESCE(SUM(nmv_after_tax), 0) FROM orders
        WHERE order_date BETWEEN :tu AND :den AND {HOP_LE} AND hour_bucket IS NOT NULL {loc} GROUP BY hour_bucket
    """), {"tu": ky["dau"], "den": ky["den"], **tham_so}).all()
    theo_gio = {}
    for nhan, so_don, tien in cac_dong:
        theo_gio[int(nhan.split("H")[0])] = (nhan, so_don, int(tien))
    tong_don = sum(so_don for _, so_don, _ in theo_gio.values())
    ket_qua = []
    for gio in range(24):
        nhan, so_don, tien = theo_gio.get(gio, (f"{gio}H - {gio + 1}H", 0, 0))
        ket_qua.append({"hour": gio, "label": nhan, "order_count": so_don, "revenue": tien,
                        "share_pct": phan_tram(so_don, tong_don) if tong_don else 0.0})
    return ket_qua


def by_hour(phien, san, muc, ma_ky, shop_name=None, product_code=None):
    ky, _ = _ky_don_gian(phien, san, muc, ma_ky)
    so_dong = so_lieu_khoang(phien, san, ky["dau"], ky["den"], shop_name, product_code)["so_dong"]
    if not so_dong:
        return {"platform": san, "period": ky["ky"], "status": "no_data", "items": []}
    return {"platform": san, "period": ky["ky"], "status": "ok",
            "items": thong_ke_theo_gio(phien, san, ky, shop_name, product_code)}


def so_sanh_hai_san(phien, muc, ma_ky):
    """Không cộng gộp hai sàn; dùng kỳ chứa ngày dữ liệu mới nhất của cả hai sàn để so cùng một kỳ."""
    if ma_ky is None:
        ngay_moi_nhat = [khoang_du_lieu(phien, san)[1] for san in SAN_HOP_LE]
        ngay_moi_nhat = [n for n in ngay_moi_nhat if n]
        ma_ky = ky_chua_ngay(muc, max(ngay_moi_nhat))[2] if ngay_moi_nhat else None
    ket_qua = {"granularity": muc, "period": ma_ky}
    for san in ("shopee", "tiktok"):
        ngay_min, ngay_max = khoang_du_lieu(phien, san)
        if ngay_max is None:
            ket_qua[san] = {"status": "no_data", "data_max_date": None, "period_complete": False,
                            "current": None, "previous": None, "metrics": dung_metrics({}, None, False),
                            "by_hour": [], "by_product": [], "by_province_top": []}
            continue
        ky = xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max)
        hien_tai = so_lieu_khoang(phien, san, ky["dau"], ky["den"])
        co_du_lieu = hien_tai["so_dong"] > 0
        truoc_ky = ky["truoc"]
        truoc = so_lieu_khoang(phien, san, truoc_ky["dau"], truoc_ky["den"]) if truoc_ky else None
        trang_thai = "no_data" if not co_du_lieu else ("ok" if truoc_ky else "insufficient_data")
        khoi = {"status": trang_thai, "data_max_date": ngay_max.isoformat(), "period_complete": ky["day_du"],
                "current": {"date_from": ky["dau"].isoformat(), "date_to": ky["den"].isoformat()},
                "previous": None if truoc_ky is None else {
                    "period": truoc_ky["ky"], "date_from": truoc_ky["dau"].isoformat(),
                    "date_to": truoc_ky["den"].isoformat()},
                "metrics": dung_metrics(hien_tai, truoc, co_du_lieu),
                "by_hour": [], "by_product": [], "by_province_top": []}
        if co_du_lieu:
            khoi["by_hour"] = [{"hour": m["hour"], "label": m["label"], "order_count": m["order_count"],
                                "share_pct": m["share_pct"]} for m in thong_ke_theo_gio(phien, san, ky)]
            top = top_products(phien, san, muc, ky["ky"], 1000, "revenue")
            khoi["by_product"] = [{"product_code": m["product_code"], "revenue": m["revenue"], "quantity": m["quantity"]}
                                  for m in top["items"]]
            khoi["by_province_top"] = [{"province": m["province"], "revenue": m["revenue"], "share_pct": m["share_pct"]}
                                       for m in thong_ke_theo_tinh(phien, san, ky) if not m["is_other"]][:10]
        ket_qua[san] = khoi
    return ket_qua
