"""Xuất báo cáo Excel (UC13, SPEC §12.1.4.4).

KHÔNG tính lại số liệu: mọi con số lấy từ `kpi_service` (cùng hàm mà dashboard dùng) nên file Excel và màn hình
luôn khớp nhau. Mỗi khối dashboard là một sheet. Quy tắc trình bày:
- Thiếu số liệu → ô để TRỐNG kèm chú thích ở cột "Ghi chú" ("Không có dữ liệu", …), không bao giờ ghi 0.
- Tiền là số nguyên (đồng); tỷ lệ và % thay đổi giữ đúng giá trị JSON (34.6 nghĩa là 34,6%), chỉ khác định dạng hiển thị.
- Dòng ghi chú cuối sheet "Tổng quan": doanh thu là NMV sau thuế, đã loại hủy và hoàn, chưa phải lợi nhuận.
"""

from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.services import kpi_service

TEN_SAN_HIEN_THI = {"shopee": "Shopee", "tiktok": "TikTok Shop"}
TEN_MUC = {"day": "Theo ngày", "month": "Theo tháng", "quarter": "Theo quý", "year": "Theo năm"}

SHEET_TONG_QUAN = "Tổng quan"
SHEET_DOANH_THU = "Doanh thu theo kỳ"
SHEET_SAN_PHAM = "Sản phẩm bán chạy"
SHEET_TINH = "Tỉnh thành"
SHEET_KHUNG_GIO = "Khung giờ"
SHEET_KENH_BAN = "Kênh bán"

GHI_CHU_KHONG_DU_LIEU = "Không có dữ liệu"
GHI_CHU_KHONG_DU_SO_SANH = "Không đủ dữ liệu để so sánh"
GHI_CHU_KY_TRUOC_BANG_0 = "Kỳ trước không có doanh thu"
GHI_CHU_KY_TRUOC_KHONG_DON = "Kỳ trước không có đơn"
GHI_CHU_NMV = ("Doanh thu là NMV sau thuế (đã chia 1,08 theo quy ước VAT 8%), đã loại đơn hủy và đơn hoàn; "
               "đây là doanh thu bán hàng, chưa phải lợi nhuận.")

DINH_DANG_TIEN = '#,##0'
DINH_DANG_PHAN_TRAM = '0.0"%"'
DINH_DANG_THAY_DOI = '+0.0"%";-0.0"%";0.0"%"'
DINH_DANG_DIEM = '+0.0" điểm %";-0.0" điểm %";0.0" điểm %"'

MAU_TIEU_DE = PatternFill("solid", start_color="E8EEF7", end_color="E8EEF7")

# Ký tự đầu khiến Excel/LibreOffice coi ô chuỗi là CÔNG THỨC (chèn công thức / CSV injection): = + - @ và tab, xuống dòng.
DAU_HIEU_CONG_THUC = ("=", "+", "-", "@", "\t", "\r", "\n")


def trung_hoa_cong_thuc(gia_tri):
    """Chuỗi bắt đầu bằng = + - @ (hoặc tab/xuống dòng) → thêm `'` ở đầu để Excel coi là văn bản, không chạy công thức.

    Chỉ đụng tới giá trị KIỂU CHUỖI. Số (kể cả số âm), None, ngày giữ nguyên.
    Cần vì tên gian hàng (tham số truy vấn, cột `Shop` của tệp TikTok), tên sản phẩm, tỉnh... do người dùng/dữ liệu ngoài
    quyết định, mà openpyxl ghi chuỗi bắt đầu bằng "=" thành CÔNG THỨC thật.
    """
    if isinstance(gia_tri, str) and gia_tri.startswith(DAU_HIEU_CONG_THUC):
        return "'" + gia_tri
    return gia_tri


def trung_hoa_toan_bo_o(so_lam_viec):
    """Áp `trung_hoa_cong_thuc` cho MỌI ô chuỗi của sổ làm việc, ngay trước khi lưu.

    Làm một lượt cuối thay vì rải ở từng chỗ ghi ô (hơn 60 chỗ) để chỗ ghi mới thêm sau này cũng tự được che; báo cáo này
    không bao giờ cố ý ghi công thức nên không có ô công thức hợp lệ nào bị phá. Ô đã bị openpyxl nhận là công thức
    (data_type 'f') cũng được trả về dạng văn bản.
    """
    for sheet in so_lam_viec.worksheets:
        for hang in sheet.iter_rows():
            for o in hang:
                if isinstance(o.value, str):
                    moi = trung_hoa_cong_thuc(o.value)
                    if moi != o.value:
                        o.value = moi
                        o.data_type = "s"


def _ngay_vn(chuoi_iso):
    """'2026-08-16' → '16/08/2026'."""
    return date.fromisoformat(chuoi_iso).strftime("%d/%m/%Y")


def _tieu_de(sheet, hang, cac_cot):
    for chi_so, nhan in enumerate(cac_cot, start=1):
        o = sheet.cell(row=hang, column=chi_so, value=nhan)
        o.font = Font(bold=True)
        o.fill = MAU_TIEU_DE
        o.alignment = Alignment(wrap_text=True, vertical="center")


def _chinh_do_rong(sheet, do_rong):
    for chi_so, rong in enumerate(do_rong, start=1):
        sheet.column_dimensions[get_column_letter(chi_so)].width = rong


def _ghi_chu_thay_doi(chi_so):
    """Chú thích cho một chỉ số có pct_change (khuôn §12.1.0.2); chuỗi rỗng nếu so sánh bình thường."""
    if chi_so["value"] is None:
        return GHI_CHU_KHONG_DU_LIEU
    if chi_so["pct_change"] is None and not chi_so["previous_zero"] and chi_so["previous"] is None:
        return GHI_CHU_KHONG_DU_SO_SANH
    if chi_so["previous_zero"]:
        return GHI_CHU_KY_TRUOC_KHONG_DON if chi_so["previous"] is None else GHI_CHU_KY_TRUOC_BANG_0
    return ""


def _ghi_chu_ty_le(chi_so):
    if chi_so["value"] is None:
        return GHI_CHU_KHONG_DU_LIEU
    if chi_so["previous"] is None:
        return GHI_CHU_KHONG_DU_SO_SANH
    return ""


def _dung_tong_quan(sheet, kpi, bo_loc):
    metrics = kpi["metrics"]
    sheet["A1"] = f"Báo cáo {TEN_SAN_HIEN_THI[kpi['platform']]} — kỳ {kpi['period']}"
    sheet["A1"].font = Font(bold=True, size=14)
    thong_tin = [
        ("Mức xem", TEN_MUC[kpi["granularity"]]),
        ("Kỳ", kpi["period"]),
        ("Khoảng ngày kỳ này", f"{_ngay_vn(kpi['current']['date_from'])} – {_ngay_vn(kpi['current']['date_to'])}"),
        ("Kỳ so sánh", "Không có kỳ trước" if kpi["previous"] is None else
         f"{kpi['previous']['period']} ({_ngay_vn(kpi['previous']['date_from'])} – {_ngay_vn(kpi['previous']['date_to'])})"),
        ("Dữ liệu đến ngày", _ngay_vn(kpi["data_max_date"])),
        ("Kỳ đầy đủ", "Có" if kpi["period_complete"] else
         f"Chưa — tính đến {_ngay_vn(kpi['data_max_date'])}; kỳ so sánh đã cắt cùng số ngày"),
        ("Gian hàng", bo_loc.get("shop_name") or "Tất cả"),
        ("Mã sản phẩm", bo_loc.get("product_code") or "Tất cả"),
        ("Xuất lúc", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for chi_so, (nhan, gia_tri) in enumerate(thong_tin, start=3):
        sheet.cell(row=chi_so, column=1, value=nhan).font = Font(bold=True)
        sheet.cell(row=chi_so, column=2, value=gia_tri)
    hang = 3 + len(thong_tin) + 1

    _tieu_de(sheet, hang, ["Chỉ số", "Giá trị", "Kỳ trước", "Thay đổi", "Ghi chú"])
    hang += 1
    cac_so = [("Doanh thu (đ)", "revenue", DINH_DANG_TIEN), ("Số đơn hợp lệ", "order_count", DINH_DANG_TIEN),
              ("Tổng số đơn", "order_count_all", DINH_DANG_TIEN), ("Số sản phẩm bán", "quantity_sold", DINH_DANG_TIEN),
              ("Giá trị đơn trung bình (đ)", "aov", DINH_DANG_TIEN)]
    for nhan, khoa, dinh_dang in cac_so:
        chi_so = metrics[khoa]
        sheet.cell(row=hang, column=1, value=nhan)
        for cot, gia_tri, kieu in ((2, chi_so["value"], dinh_dang), (3, chi_so["previous"], dinh_dang),
                                   (4, chi_so["pct_change"], DINH_DANG_THAY_DOI)):
            o = sheet.cell(row=hang, column=cot, value=gia_tri)       # None → ô trống, không phải 0
            o.number_format = kieu
        sheet.cell(row=hang, column=5, value=_ghi_chu_thay_doi(chi_so))
        hang += 1
    for nhan, khoa in (("Tỷ lệ hủy đơn (%)", "cancel_rate"), ("Tỷ lệ hoàn hàng (%)", "return_rate"),
                       ("Tỷ trọng doanh thu affiliate (%)", "affiliate_share")):
        chi_so = metrics[khoa]
        sheet.cell(row=hang, column=1, value=nhan)
        sheet.cell(row=hang, column=2, value=chi_so["value"]).number_format = DINH_DANG_PHAN_TRAM
        sheet.cell(row=hang, column=3, value=chi_so["previous"]).number_format = DINH_DANG_PHAN_TRAM
        sheet.cell(row=hang, column=4, value=chi_so["change_pp"]).number_format = DINH_DANG_DIEM
        sheet.cell(row=hang, column=5, value=_ghi_chu_ty_le(chi_so))
        hang += 1

    hang += 1
    canh_bao = kpi["alert"]
    sheet.cell(row=hang, column=1, value="Cảnh báo biến động").font = Font(bold=True)
    sheet.cell(row=hang, column=2, value="CÓ" if canh_bao["triggered"] else "Không")
    sheet.cell(row=hang, column=5, value=f"Ngưỡng: giảm từ {abs(canh_bao['threshold_pct']):g}% trở lên so với kỳ trước")
    hang += 1
    if kpi["previous_full"] is not None:
        pf = kpi["previous_full"]
        sheet.cell(row=hang, column=1, value="Nếu so nguyên kỳ trước (chỉ để minh họa)").font = Font(bold=True)
        sheet.cell(row=hang, column=2, value=f"Doanh thu nguyên {pf['period']}").alignment = Alignment(wrap_text=True)
        sheet.cell(row=hang, column=3, value=pf["revenue"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=4, value=pf["pct_change_if_used"]).number_format = DINH_DANG_THAY_DOI
        sheet.cell(row=hang, column=5, value="KHÔNG dùng cho cảnh báo: so nguyên kỳ cho kết luận sai khi kỳ này chưa đủ ngày")
        hang += 1
    chat_luong = kpi["data_quality"]
    if chat_luong["rows_status_unknown"] is not None:
        sheet.cell(row=hang, column=1, value="Dòng trạng thái chưa xác định").font = Font(bold=True)
        sheet.cell(row=hang, column=2, value=chat_luong["rows_status_unknown"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=3, value=chat_luong["revenue_status_unknown"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=5, value="Số dòng và phần doanh thu (đ) đến từ dòng trạng thái chưa xác định — vẫn được tính vào doanh thu")
        hang += 1
        if chat_luong["rows_nmv_provisional"] is not None:
            sheet.cell(row=hang, column=1, value="Dòng NMV tạm tính").font = Font(bold=True)
            sheet.cell(row=hang, column=2, value=chat_luong["rows_nmv_provisional"]).number_format = DINH_DANG_TIEN
            hang += 1
    hang += 1
    sheet.cell(row=hang, column=1, value="Lưu ý").font = Font(bold=True)
    sheet.cell(row=hang, column=2, value=GHI_CHU_NMV)
    if kpi["status"] == "no_data":
        sheet.cell(row=hang + 1, column=2, value=f"Kỳ {kpi['period']}: {GHI_CHU_KHONG_DU_LIEU}")
    _chinh_do_rong(sheet, [34, 26, 18, 18, 70])


def _dung_doanh_thu(sheet, xu_huong):
    ma_top = xu_huong["top_product_codes"]
    cot = ["Kỳ", "Doanh thu (đ)", "Số đơn hợp lệ", "Kỳ đủ ngày"] + [f"Doanh thu {ma} (đ)" for ma in ma_top] + \
          ["Doanh thu mã khác (đ)", "Ghi chú"]
    _tieu_de(sheet, 1, cot)
    for hang, muc in enumerate(xu_huong["items"], start=2):
        sheet.cell(row=hang, column=1, value=muc["period"])
        sheet.cell(row=hang, column=2, value=muc["revenue"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=3, value=muc["order_count"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=4, value="Có" if muc["period_complete"] else "Chưa (kỳ đang chạy)")
        if muc["by_product"] is not None:
            for chi_so, phan in enumerate(muc["by_product"], start=5):
                sheet.cell(row=hang, column=chi_so, value=phan["revenue"]).number_format = DINH_DANG_TIEN
        else:
            sheet.cell(row=hang, column=len(cot), value=GHI_CHU_KHONG_DU_LIEU)
    _chinh_do_rong(sheet, [14, 18, 16, 20] + [20] * (len(ma_top) + 1) + [22])
    sheet.freeze_panes = "A2"


def _dung_san_pham(sheet, du_lieu):
    _tieu_de(sheet, 1, ["Mã sản phẩm", "Doanh thu (đ)", "Số lượng", "Tỷ trọng doanh thu (%)", "Thay đổi so kỳ trước (%)", "Ghi chú"])
    if not du_lieu["items"]:
        sheet.cell(row=2, column=6, value=GHI_CHU_KHONG_DU_LIEU)
    for hang, muc in enumerate(du_lieu["items"], start=2):
        sheet.cell(row=hang, column=1, value=muc["product_code"] if muc["product_code"] is not None else "Chưa phân loại")
        sheet.cell(row=hang, column=2, value=muc["revenue"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=3, value=muc["quantity"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=4, value=muc["share_pct"]).number_format = DINH_DANG_PHAN_TRAM
        sheet.cell(row=hang, column=5, value=muc["pct_change"]).number_format = DINH_DANG_THAY_DOI
        if muc["previous_zero"]:
            sheet.cell(row=hang, column=6, value="Kỳ trước không bán")
        elif muc["pct_change"] is None:
            sheet.cell(row=hang, column=6, value=GHI_CHU_KHONG_DU_SO_SANH)
    _chinh_do_rong(sheet, [18, 18, 12, 22, 24, 30])
    sheet.freeze_panes = "A2"


def _dung_tinh(sheet, du_lieu):
    _tieu_de(sheet, 1, ["Tỉnh/thành", "Số đơn hợp lệ", "Doanh thu (đ)", "Tỷ trọng doanh thu (%)", "Ghi chú"])
    if not du_lieu["items"]:
        sheet.cell(row=2, column=5, value=GHI_CHU_KHONG_DU_LIEU)
    for hang, muc in enumerate(du_lieu["items"], start=2):
        sheet.cell(row=hang, column=1, value=muc["province"])
        sheet.cell(row=hang, column=2, value=muc["order_count"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=3, value=muc["revenue"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=4, value=muc["share_pct"]).number_format = DINH_DANG_PHAN_TRAM
        if muc["is_other"]:
            sheet.cell(row=hang, column=5, value="Nhóm gom các tỉnh không nhận diện được")
    if du_lieu["province_count"] is not None:
        sheet.cell(row=len(du_lieu["items"]) + 3, column=1, value=f"{du_lieu['province_count']} tỉnh/thành có đơn")
    _chinh_do_rong(sheet, [26, 16, 18, 22, 40])
    sheet.freeze_panes = "A2"


def _dung_khung_gio(sheet, du_lieu):
    _tieu_de(sheet, 1, ["Khung giờ", "Số đơn hợp lệ", "Doanh thu (đ)", "Tỷ trọng số đơn (%)", "Ghi chú"])
    if not du_lieu["items"]:
        sheet.cell(row=2, column=5, value=GHI_CHU_KHONG_DU_LIEU)
    for hang, muc in enumerate(du_lieu["items"], start=2):
        sheet.cell(row=hang, column=1, value=muc["label"])
        sheet.cell(row=hang, column=2, value=muc["order_count"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=3, value=muc["revenue"]).number_format = DINH_DANG_TIEN
        sheet.cell(row=hang, column=4, value=muc["share_pct"]).number_format = DINH_DANG_PHAN_TRAM
    _chinh_do_rong(sheet, [16, 16, 18, 22, 30])
    sheet.freeze_panes = "A2"


def _dung_kenh_ban(sheet, du_lieu):
    _tieu_de(sheet, 1, ["Kênh bán", "Doanh thu (đ)", "Số đơn hợp lệ", "Tỷ trọng doanh thu (%)", "Ghi chú"])
    if du_lieu["affiliate"] is None:
        sheet.cell(row=2, column=5, value=GHI_CHU_KHONG_DU_LIEU)
    for hang, (nhan, khoa) in enumerate((("Affiliate", "affiliate"), ("Tự bán", "self_sold")), start=2):
        muc = du_lieu[khoa]
        sheet.cell(row=hang, column=1, value=nhan)
        if muc is not None:
            sheet.cell(row=hang, column=2, value=muc["revenue"]).number_format = DINH_DANG_TIEN
            sheet.cell(row=hang, column=3, value=muc["order_count"]).number_format = DINH_DANG_TIEN
            sheet.cell(row=hang, column=4, value=muc["share_pct"]).number_format = DINH_DANG_PHAN_TRAM
    _chinh_do_rong(sheet, [18, 18, 16, 22, 30])


def tao_bao_cao_excel(phien, san, muc, ma_ky, shop_name=None, product_code=None):
    """Dựng file Excel của một sàn, một kỳ. Trả (bytes, mã kỳ thực tế).

    Mọi số liệu gọi từ `kpi_service` với cùng tham số của dashboard. Mã kỳ sai định dạng → KyKhongHopLe.
    """
    kpi = kpi_service.kpi(phien, san, muc, ma_ky, shop_name, product_code)
    ky = kpi["period"]
    xu_huong = kpi_service.revenue_trend(phien, san, muc, None, None, shop_name, product_code)
    san_pham = kpi_service.top_products(phien, san, muc, ky, 100, "revenue", shop_name, product_code)
    tinh = kpi_service.by_province(phien, san, muc, ky, shop_name, product_code)
    gio = kpi_service.by_hour(phien, san, muc, ky, shop_name, product_code)
    kenh = kpi_service.by_affiliate(phien, san, muc, ky, shop_name, product_code)

    bang_tinh = Workbook()
    sheet = bang_tinh.active
    sheet.title = SHEET_TONG_QUAN
    _dung_tong_quan(sheet, kpi, {"shop_name": shop_name, "product_code": product_code})
    _dung_doanh_thu(bang_tinh.create_sheet(SHEET_DOANH_THU), xu_huong)
    _dung_san_pham(bang_tinh.create_sheet(SHEET_SAN_PHAM), san_pham)
    _dung_tinh(bang_tinh.create_sheet(SHEET_TINH), tinh)
    _dung_khung_gio(bang_tinh.create_sheet(SHEET_KHUNG_GIO), gio)
    _dung_kenh_ban(bang_tinh.create_sheet(SHEET_KENH_BAN), kenh)

    trung_hoa_toan_bo_o(bang_tinh)
    dem = BytesIO()
    bang_tinh.save(dem)
    return dem.getvalue(), ky
