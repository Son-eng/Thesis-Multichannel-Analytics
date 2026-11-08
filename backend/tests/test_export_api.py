"""Test xuất Excel (UC13, SPEC §12.1.4.4): mở file sinh ra và kiểm số, tên sheet, ô thiếu số, tiêu đề tải về.

Dữ liệu mẫu đã nạp trong CSDL thật (chỉ đọc). Điểm cốt lõi: số trong Excel PHẢI bằng đúng JSON của dashboard
(file lấy số từ kpi_service, không tính lại) — nên ngoài số cố định của SPEC còn so từng ô với phản hồi của endpoint.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import text

from app.core.deps import yeu_cau_dang_nhap
from app.database import SessionLocal
from app.main import tao_ung_dung
from app.models.user import User
from app.services import export_service

pytestmark = pytest.mark.db

SO_DONG_MAU = {"shopee": 1774, "tiktok": 7540}
TEN_SHEET = ["Tổng quan", "Doanh thu theo kỳ", "Sản phẩm bán chạy", "Tỉnh thành", "Khung giờ", "Kênh bán"]


@pytest.fixture(scope="module")
def du_lieu_mau_da_nap():
    with SessionLocal() as phien:
        for bang, so_dong in SO_DONG_MAU.items():
            if phien.execute(text("SELECT count(*) FROM orders WHERE platform = :p"), {"p": bang}).scalar_one() != so_dong:
                pytest.skip(f"orders ({bang}) chưa nạp đủ {so_dong} dòng dữ liệu mẫu")


@pytest.fixture(scope="module")
def client(du_lieu_mau_da_nap):
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    ung_dung.dependency_overrides[yeu_cau_dang_nhap] = lambda: User(id=-1, username="nguoi_thu", role="user")
    with TestClient(ung_dung) as c:
        yield c


def tai(client, san="shopee", **tham_so):
    phan_hoi = client.get(f"/api/export/{san}/excel", params=tham_so)
    assert phan_hoi.status_code == 200, phan_hoi.text
    return phan_hoi, load_workbook(BytesIO(phan_hoi.content))


def hang_theo_nhan(sheet, nhan):
    """Hàng đầu tiên có ô cột A bằng `nhan` → dict {cột: ô}."""
    for hang in sheet.iter_rows():
        if hang[0].value == nhan:
            return {chr(65 + i): o for i, o in enumerate(hang)}
    raise AssertionError(f"Không thấy hàng '{nhan}' trong sheet {sheet.title}")


# ---------------------------------------------------------------- tệp tải về

def test_tieu_de_tai_ve_va_ten_sheet(client):
    phan_hoi, sổ = tai(client, "shopee", granularity="month", period="2026-08")
    assert phan_hoi.headers["content-type"] == export_service_media()
    assert phan_hoi.headers["content-disposition"] == 'attachment; filename="bao-cao-shopee-2026-08.xlsx"'
    assert sổ.sheetnames == TEN_SHEET
    assert phan_hoi.content[:2] == b"PK"                                           # xlsx là một tệp zip


def export_service_media():
    from app.api.export import KIEU_EXCEL
    return KIEU_EXCEL


def test_ten_tep_theo_san_va_ky(client):
    assert 'filename="bao-cao-tiktok-2026-Q3.xlsx"' in tai(client, "tiktok", granularity="quarter", period="2026-Q3")[0].headers["content-disposition"]
    assert 'filename="bao-cao-shopee-2026-08.xlsx"' in tai(client, "shopee")[0].headers["content-disposition"]   # mặc định: kỳ mới nhất


# ---------------------------------------------------------------- số trong sheet "Tổng quan" — số cố định §17 / §9.4

def test_shopee_2026_08_doanh_thu_ky_truoc_va_phan_tram_dung_o(client):
    _, sổ = tai(client, "shopee", granularity="month", period="2026-08")
    hang = hang_theo_nhan(sổ["Tổng quan"], "Doanh thu (đ)")
    assert hang["B"].value == 840035154                      # giá trị
    assert hang["C"].value == 624277755                      # kỳ trước đã cắt cùng số ngày (01–16/07)
    assert hang["D"].value == 34.6                           # +34,6%
    assert hang["B"].number_format == "#,##0" and hang["D"].number_format == '+0.0"%";-0.0"%";0.0"%"'
    assert hang["E"].value in (None, "")


def test_tong_quan_co_khoang_ngay_ky_truoc_da_cat_va_ghi_chu_ky_chua_day_du(client):
    _, sổ = tai(client, "shopee", granularity="month", period="2026-08")
    sheet = sổ["Tổng quan"]
    assert hang_theo_nhan(sheet, "Khoảng ngày kỳ này")["B"].value == "01/08/2026 – 16/08/2026"
    assert hang_theo_nhan(sheet, "Kỳ so sánh")["B"].value == "2026-07 (01/07/2026 – 16/07/2026)"
    assert hang_theo_nhan(sheet, "Dữ liệu đến ngày")["B"].value == "16/08/2026"
    assert "Chưa" in hang_theo_nhan(sheet, "Kỳ đầy đủ")["B"].value and "16/08/2026" in hang_theo_nhan(sheet, "Kỳ đầy đủ")["B"].value
    minh_hoa = hang_theo_nhan(sheet, "Nếu so nguyên kỳ trước (chỉ để minh họa)")
    assert (minh_hoa["C"].value, minh_hoa["D"].value) == (1068925905, -21.4)


def test_co_dong_ghi_chu_nmv_sau_thue_da_loai_huy_hoan_chua_phai_loi_nhuan(client):
    _, sổ = tai(client, "tiktok", granularity="month", period="2026-07")
    ghi_chu = hang_theo_nhan(sổ["Tổng quan"], "Lưu ý")["B"].value
    assert "NMV sau thuế" in ghi_chu and "đã loại đơn hủy và đơn hoàn" in ghi_chu and "chưa phải lợi nhuận" in ghi_chu


def test_tiktok_2026_08_va_canh_bao_thang_4(client):
    _, sổ = tai(client, "tiktok", granularity="month", period="2026-08")
    hang = hang_theo_nhan(sổ["Tổng quan"], "Doanh thu (đ)")
    assert (hang["B"].value, hang["C"].value, hang["D"].value) == (863491460, 579379192, 49.0)
    _, sổ4 = tai(client, "tiktok", granularity="month", period="2026-04")
    assert hang_theo_nhan(sổ4["Tổng quan"], "Cảnh báo biến động")["B"].value == "CÓ"
    assert hang_theo_nhan(sổ["Tổng quan"], "Cảnh báo biến động")["B"].value == "Không"


# ---------------------------------------------------------------- ô thiếu số để trống kèm chú thích, không ghi 0

def test_ky_khong_co_du_lieu_o_trong_kem_chu_thich_khong_ghi_0(client):
    _, sổ = tai(client, "shopee", granularity="month", period="2026-03")
    sheet = sổ["Tổng quan"]
    for nhan in ("Doanh thu (đ)", "Số đơn hợp lệ", "Tổng số đơn", "Số sản phẩm bán", "Giá trị đơn trung bình (đ)"):
        hang = hang_theo_nhan(sheet, nhan)
        assert hang["B"].value is None and hang["C"].value is None and hang["D"].value is None, nhan
        assert hang["E"].value == "Không có dữ liệu", nhan
    for nhan in ("Tỷ lệ hủy đơn (%)", "Tỷ lệ hoàn hàng (%)", "Tỷ trọng doanh thu affiliate (%)"):
        hang = hang_theo_nhan(sheet, nhan)
        assert hang["B"].value is None and hang["E"].value == "Không có dữ liệu", nhan
    assert hang_theo_nhan(sổ["Sản phẩm bán chạy"], "Mã sản phẩm")["F"].value == "Ghi chú"
    assert sổ["Sản phẩm bán chạy"]["F2"].value == "Không có dữ liệu" and sổ["Sản phẩm bán chạy"]["B2"].value is None
    assert sổ["Khung giờ"]["E2"].value == "Không có dữ liệu" and sổ["Khung giờ"].max_row == 2
    assert sổ["Kênh bán"]["B2"].value is None and sổ["Kênh bán"]["B3"].value is None


def test_khong_co_ky_truoc_o_so_sanh_trong_kem_chu_thich(client):
    _, sổ = tai(client, "shopee", granularity="year", period="2026")
    sheet = sổ["Tổng quan"]
    assert hang_theo_nhan(sheet, "Kỳ so sánh")["B"].value == "Không có kỳ trước"
    hang = hang_theo_nhan(sheet, "Doanh thu (đ)")
    assert hang["B"].value == 1908961059 and hang["C"].value is None and hang["D"].value is None
    assert hang["E"].value == "Không đủ dữ liệu để so sánh"


def test_ky_truoc_bang_0_ghi_chu_dung(client):
    """Shopee 2026-08, M9 MAX không bán ở kỳ trước: dòng sản phẩm để trống phần % và ghi 'Kỳ trước không bán'."""
    _, sổ = tai(client, "shopee", granularity="month", period="2026-08")
    hang = hang_theo_nhan(sổ["Sản phẩm bán chạy"], "M9 MAX")
    assert hang["E"].value is None and hang["F"].value == "Kỳ trước không bán" and hang["B"].value > 0


# ---------------------------------------------------------------- Excel khớp đúng JSON dashboard (không tính lại)

@pytest.mark.parametrize("san, muc, ky", [("shopee", "month", "2026-08"), ("tiktok", "month", "2026-07"),
                                          ("tiktok", "quarter", "2026-Q2"), ("shopee", "day", "2026-08-10")])
def test_cac_sheet_khop_json_cua_dashboard(client, san, muc, ky):
    _, sổ = tai(client, san, granularity=muc, period=ky)
    tham_so = {"granularity": muc, "period": ky}
    kpi = client.get(f"/api/{san}/kpi", params=tham_so).json()
    sheet = sổ["Tổng quan"]
    for nhan, khoa in (("Doanh thu (đ)", "revenue"), ("Số đơn hợp lệ", "order_count"), ("Tổng số đơn", "order_count_all"),
                       ("Số sản phẩm bán", "quantity_sold"), ("Giá trị đơn trung bình (đ)", "aov")):
        hang = hang_theo_nhan(sheet, nhan)
        chi_so = kpi["metrics"][khoa]
        assert (hang["B"].value, hang["C"].value, hang["D"].value) == (chi_so["value"], chi_so["previous"], chi_so["pct_change"]), nhan
    for nhan, khoa in (("Tỷ lệ hủy đơn (%)", "cancel_rate"), ("Tỷ lệ hoàn hàng (%)", "return_rate"),
                       ("Tỷ trọng doanh thu affiliate (%)", "affiliate_share")):
        hang = hang_theo_nhan(sheet, nhan)
        chi_so = kpi["metrics"][khoa]
        assert (hang["B"].value, hang["C"].value, hang["D"].value) == (chi_so["value"], chi_so["previous"], chi_so["change_pp"]), nhan

    san_pham = client.get(f"/api/{san}/top-products", params={**tham_so, "limit": 100}).json()["items"]
    sheet = sổ["Sản phẩm bán chạy"]
    assert [(r[0].value, r[1].value, r[2].value, r[3].value, r[4].value) for r in sheet.iter_rows(min_row=2, max_row=1 + len(san_pham))] == \
        [(m["product_code"], m["revenue"], m["quantity"], m["share_pct"], m["pct_change"]) for m in san_pham]

    tinh = client.get(f"/api/{san}/by-province", params=tham_so).json()["items"]
    assert [(r[0].value, r[1].value, r[2].value, r[3].value) for r in sổ["Tỉnh thành"].iter_rows(min_row=2, max_row=1 + len(tinh))] == \
        [(m["province"], m["order_count"], m["revenue"], m["share_pct"]) for m in tinh]

    gio = client.get(f"/api/{san}/by-hour", params=tham_so).json()["items"]
    assert len(gio) == 24 and sổ["Khung giờ"].max_row == 25
    assert [(r[0].value, r[1].value, r[2].value, r[3].value) for r in sổ["Khung giờ"].iter_rows(min_row=2, max_row=25)] == \
        [(m["label"], m["order_count"], m["revenue"], m["share_pct"]) for m in gio]

    kenh = client.get(f"/api/{san}/by-affiliate", params=tham_so).json()
    sheet = sổ["Kênh bán"]
    assert (sheet["B2"].value, sheet["C2"].value, sheet["D2"].value) == (kenh["affiliate"]["revenue"], kenh["affiliate"]["order_count"], kenh["affiliate"]["share_pct"])
    assert (sheet["B3"].value, sheet["C3"].value) == (kenh["self_sold"]["revenue"], kenh["self_sold"]["order_count"])


def test_sheet_doanh_thu_theo_ky_khop_revenue_trend_va_ky_trong_la_o_trong(client):
    _, sổ = tai(client, "tiktok", granularity="month", period="2026-08")
    xu_huong = client.get("/api/tiktok/revenue-trend", params={"granularity": "month"}).json()
    sheet = sổ["Doanh thu theo kỳ"]
    assert [(r[0].value, r[1].value, r[2].value) for r in sheet.iter_rows(min_row=2, max_row=1 + len(xu_huong["items"]))] == \
        [(m["period"], m["revenue"], m["order_count"]) for m in xu_huong["items"]]
    assert [c.value for c in sheet[1]][4:8] == [f"Doanh thu {ma} (đ)" for ma in xu_huong["top_product_codes"]]
    # Shopee: tháng 1–6 không có dữ liệu → khi xuất theo khoảng rộng, ô để trống (không phải 0) kèm ghi chú.
    from app.services import export_service as dv
    assert dv.GHI_CHU_KHONG_DU_LIEU == "Không có dữ liệu"


def test_loc_gian_hang_va_ma_san_pham_ap_dung_cho_ca_file(client):
    tong = hang_theo_nhan(tai(client, "tiktok", granularity="year", period="2026")[1]["Tổng quan"], "Doanh thu (đ)")["B"].value
    shop_a, shop_b = (hang_theo_nhan(tai(client, "tiktok", granularity="year", period="2026", shop_name=s)[1]["Tổng quan"],
                                     "Doanh thu (đ)")["B"].value for s in ("Shop A", "Shop B"))
    assert shop_a + shop_b == tong
    sheet = tai(client, "tiktok", granularity="year", period="2026", product_code="M15")[1]["Tổng quan"]
    assert hang_theo_nhan(sheet, "Mã sản phẩm")["B"].value == "M15"
    assert hang_theo_nhan(sheet, "Doanh thu (đ)")["B"].value < tong


# ---------------------------------------------------------------- lỗi, PDF, quyền

def test_pdf_tra_501_chua_ho_tro_trong_ban_demo(client):
    phan_hoi = client.get("/api/export/shopee/pdf")
    assert phan_hoi.status_code == 501
    assert phan_hoi.json() == {"detail": {"code": "not_supported", "message": "Chưa hỗ trợ trong bản demo"}}


@pytest.mark.parametrize("tham_so", [{"granularity": "month", "period": "2026-Q3"}, {"granularity": "year", "period": "abc"}])
def test_ky_sai_dinh_dang_422(client, tham_so):
    phan_hoi = client.get("/api/export/shopee/excel", params=tham_so)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_period"


def test_san_la_hoac_muc_la_422(client):
    assert client.get("/api/export/lazada/excel").status_code == 422
    assert client.get("/api/export/shopee/excel", params={"granularity": "week"}).status_code == 422


def test_phai_dang_nhap_moi_xuat_duoc(du_lieu_mau_da_nap):
    with TestClient(tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)) as khach:
        for duong_dan in ("/api/export/shopee/excel", "/api/export/shopee/pdf"):
            phan_hoi = khach.get(duong_dan)
            assert phan_hoi.status_code == 401 and phan_hoi.json()["detail"]["code"] == "not_authenticated"
