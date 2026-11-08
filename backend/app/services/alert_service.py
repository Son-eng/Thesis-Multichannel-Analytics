"""Cảnh báo biến động doanh thu (SPEC §9, §12.1.1.8).

Quy tắc: cảnh báo khi doanh thu kỳ hiện tại GIẢM từ `ALERT_DROP_THRESHOLD_PCT`% trở lên so với kỳ liền trước
(`pct_change <= −ngưỡng`). Ngưỡng đọc từ cấu hình, không hard-code. Ba trường hợp KHÔNG BAO GIỜ cảnh báo:
- không tồn tại kỳ trước (§9.3b);
- kỳ trước bằng 0 (§7.3, `previous_zero`) — không chia cho 0, không coi là "giảm 100%";
- kỳ này không có dòng nào (`no_data`) — kỳ trống không phải kỳ sụt giảm.
Kỳ chưa đầy đủ so với kỳ trước ĐÃ CẮT cùng số ngày (§9.2); mức ngày không cắt (§9.3a).

Quyết định dựa trên `pct_change` CHƯA làm tròn (−29,96 làm tròn thành −30,0 sẽ kích hoạt oan).
"""

from datetime import timedelta

from sqlalchemy import text

from app.config import settings


def nguong_giam():
    """Ngưỡng giảm (số dương, %) từ cấu hình — đọc mỗi lần gọi để test đổi được."""
    return float(settings.ALERT_DROP_THRESHOLD_PCT)


def co_canh_bao(pct_tho, nguong=None):
    """Cảnh báo khi `pct_tho` (% thay đổi, chưa làm tròn) ≤ −ngưỡng. `pct_tho` None → không bao giờ cảnh báo."""
    nguong = nguong_giam() if nguong is None else float(nguong)
    return pct_tho is not None and pct_tho <= -nguong


def liet_ke_canh_bao(phien, san, muc, shop_name=None, product_code=None):
    """Mọi kỳ bị cảnh báo của sàn theo mức `muc`, trên toàn bộ dữ liệu (sắp theo kỳ tăng dần).

    Trả: dict đúng khuôn §12.1.1.8 — platform, granularity, threshold_pct (âm), items[].
    """
    # Import trong hàm: kpi_service dùng `co_canh_bao` của module này nên import ở đầu file sẽ vòng.
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
        """(số dòng, doanh thu) của [tu, den]."""
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
        if ky["truoc"] is None:                                      # không có kỳ trước → không cảnh báo
            continue
        so_dong, tien = tong(ky["dau"], ky["den"])
        _, tien_truoc = tong(ky["truoc"]["dau"], ky["truoc"]["den"])
        if so_dong == 0 or tien_truoc == 0:                          # kỳ trống / kỳ trước bằng 0 → không cảnh báo
            continue
        if co_canh_bao(kpi.thay_doi_phan_tram_tho(tien, tien_truoc), nguong):
            ket_qua["items"].append({
                "period": ky["ky"], "previous_period": ky["truoc"]["ky"],
                "revenue": tien, "revenue_previous": tien_truoc,
                "pct_change": kpi.thay_doi_phan_tram(tien, tien_truoc),
                "previous_zero": False, "period_complete": ky["day_du"]})
    return ket_qua
