"""Cảnh báo khi doanh thu giảm từ ngưỡng (mặc định 30%) trở lên so với kỳ trước; không cảnh báo khi không có kỳ trước, kỳ trước bằng 0 hoặc kỳ này trống."""

from datetime import timedelta

from sqlalchemy import text

from app.config import settings


def nguong_giam():
    return float(settings.ALERT_DROP_THRESHOLD_PCT)


def co_canh_bao(pct_tho, nguong=None):
    """So bằng pct_change chưa làm tròn: -29,96 làm tròn thành -30,0 sẽ cảnh báo oan."""
    nguong = nguong_giam() if nguong is None else float(nguong)
    return pct_tho is not None and pct_tho <= -nguong


def liet_ke_canh_bao(phien, san, muc, shop_name=None, product_code=None):
    """Mọi kỳ bị cảnh báo của sàn theo mức `muc`, trên toàn bộ dữ liệu (sắp theo kỳ tăng dần)."""
    # Import trong hàm vì kpi_service cũng import module này.
    from app.services import kpi_service as kpi

    nguong = nguong_giam()
    ket_qua = {"platform": san, "granularity": muc, "threshold_pct": -nguong, "items": []}
    ngay_min, ngay_max = kpi.khoang_du_lieu(phien, san)
    if ngay_max is None:
        return ket_qua

    loc, tham_so = kpi._loc(san, shop_name, product_code)
    cac_dong = phien.execute(text(f"""
        SELECT order_date, COUNT(*) AS so_dong,
               COALESCE(SUM(nmv_after_tax) FILTER (WHERE {kpi.HOP_LE}), 0) AS revenue
        FROM orders WHERE order_date BETWEEN :tu AND :den {loc} GROUP BY order_date
    """), {"tu": ngay_min, "den": ngay_max, **tham_so}).all()
    so_dong_ngay = {ngay: so for ngay, so, _ in cac_dong}
    doanh_thu_ngay = {ngay: int(tien) for ngay, _, tien in cac_dong}

    def tong(tu, den):
        so, tien, ngay = 0, 0, tu
        while ngay <= den:
            so += so_dong_ngay.get(ngay, 0)
            tien += doanh_thu_ngay.get(ngay, 0)
            ngay += timedelta(days=1)
        return so, tien

    dau = kpi.ky_chua_ngay(muc, ngay_min)[0]
    cuoi = kpi.ky_chua_ngay(muc, ngay_max)[0]
    while dau <= cuoi:
        ma_ky = kpi.ky_chua_ngay(muc, dau)[2]
        ky = kpi.xac_dinh_ky(muc, ma_ky, ngay_min, ngay_max)
        dau = kpi.ky_ke_tiep(muc, dau)
        if ky["truoc"] is None:
            continue
        so_dong, tien = tong(ky["dau"], ky["den"])
        _, tien_truoc = tong(ky["truoc"]["dau"], ky["truoc"]["den"])
        if so_dong == 0 or tien_truoc == 0:
            continue
        if co_canh_bao(kpi.thay_doi_phan_tram_tho(tien, tien_truoc), nguong):
            ket_qua["items"].append({
                "period": ky["ky"], "previous_period": ky["truoc"]["ky"],
                "revenue": tien, "revenue_previous": tien_truoc,
                "pct_change": kpi.thay_doi_phan_tram(tien, tien_truoc),
                "previous_zero": False, "period_complete": ky["day_du"]})
    return ket_qua
