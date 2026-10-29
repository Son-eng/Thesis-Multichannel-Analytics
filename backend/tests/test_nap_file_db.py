"""Test ghi CSDL thật: upsert của loader.py và lệnh nạp file nap_file.py (SPEC §4, §3.3, §17).

Marker `db`: cần PostgreSQL đang chạy, không kết nối được thì tự skip.
Mọi test chạy trong giao dịch bị rollback ở cuối (xem conftest.py) — tự dọn,
không làm mất dữ liệu đã nạp thật.

Số liệu chép NGUYÊN từ SPEC §17.2, §17.3, §3.3. Ở đây doanh thu tính bằng
SQL trên bảng thật — khác test_parsers.py (tính bằng pandas trên DataFrame):
khớp cả hai thì chắc chắn bước ghi không làm sai lệch số tiền nào.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.etl import loader, nap_file, shopee_parser

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"

# Công thức doanh thu §7.1, viết bằng SQL như kpi_service sẽ viết.
SQL_DOANH_THU = """
    SELECT SUM(nmv_after_tax) FROM {bang}
    WHERE order_status <> 'cancelled' AND is_returned = FALSE
"""
SQL_DOANH_THU_THEO_THANG = """
    SELECT to_char(order_date, 'YYYY-MM') AS thang, SUM(nmv_after_tax)
    FROM {bang}
    WHERE order_status <> 'cancelled' AND is_returned = FALSE
    GROUP BY thang ORDER BY thang
"""


@pytest.fixture
def nap(tao_phien_test, monkeypatch):
    """Hàm nạp file dùng Session của test (commit chỉ chốt SAVEPOINT)."""
    # nap_file.py mở phiên bằng SessionLocal; thay bằng khuôn phiên của test
    # để cả nhánh thành công lẫn nhánh ghi 'failed' đều nằm trong giao dịch test.
    monkeypatch.setattr(nap_file, "SessionLocal", tao_phien_test)

    def chay(san, duong_dan, ten_shop=None):
        return nap_file.nap_file(san, duong_dan, ten_shop, "file_manual")
    return chay


def gia_tri(ket_noi, cau_sql, **tham_so):
    """Chạy một câu SQL trả về đúng một giá trị."""
    return ket_noi.execute(text(cau_sql), tham_so).scalar_one()


# ---------- Nạp lần đầu + doanh thu SQL (§17.2, §17.3) + bộ đếm (§3.3) ----------

def test_nap_shopee(nap, ket_noi_test):
    ket_qua = nap("shopee", FILE_SHOPEE, "Shop C")

    assert ket_qua["rows_inserted"] == 1774
    assert ket_qua["rows_updated"] == 0
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee") == 1774
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_shopee")) == Decimal("1908961059")
    theo_thang = ket_noi_test.execute(text(SQL_DOANH_THU_THEO_THANG.format(bang="orders_shopee"))).all()
    assert dict(theo_thang) == {"2026-07": Decimal("1068925905"), "2026-08": Decimal("840035154")}

    dong_sync = ket_noi_test.execute(text("SELECT * FROM sync_runs")).mappings().one()
    assert dong_sync["platform"] == "shopee"
    assert dong_sync["shop_name"] == "Shop C"
    assert dong_sync["source"] == "file_manual"
    assert dong_sync["trigger_type"] == "manual"
    assert dong_sync["status"] == "success"
    assert dong_sync["file_name"] == "shopee_orders_anonymized.csv"
    assert dong_sync["finished_at"] is not None
    assert (dong_sync["rows_total"], dong_sync["rows_inserted"], dong_sync["rows_updated"]) == (1774, 1774, 0)
    bo_dem = (dong_sync["rows_sku_fallback"], dong_sync["rows_sku_unknown"], dong_sync["rows_status_unknown"],
              dong_sync["rows_province_unmapped"], dong_sync["rows_product_unmapped"])
    assert bo_dem == (6, 0, 19, 0, 0)


def test_nap_tiktok(nap, ket_noi_test):
    ket_qua = nap("tiktok", FILE_TIKTOK)

    assert (ket_qua["rows_inserted"], ket_qua["rows_updated"]) == (7540, 0)
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_tiktok")) == Decimal("7538502584")
    theo_thang = ket_noi_test.execute(text(SQL_DOANH_THU_THEO_THANG.format(bang="orders_tiktok"))).all()
    assert dict(theo_thang) == {
        "2026-01": Decimal("963328583"),
        "2026-02": Decimal("1056998596"),
        "2026-03": Decimal("1459153482"),
        "2026-04": Decimal("1014538449"),
        "2026-05": Decimal("800122017"),
        "2026-06": Decimal("566274001"),
        "2026-07": Decimal("814595996"),
        "2026-08": Decimal("863491460"),
    }

    dong_sync = ket_noi_test.execute(text("SELECT * FROM sync_runs")).mappings().one()
    # File TikTok chứa nhiều shop → shop_name NULL (§3.3).
    assert dong_sync["shop_name"] is None
    bo_dem = (dong_sync["rows_sku_fallback"], dong_sync["rows_sku_unknown"], dong_sync["rows_status_unknown"],
              dong_sync["rows_province_unmapped"], dong_sync["rows_product_unmapped"])
    assert bo_dem == (0, 0, 0, 0, 0)


# ---------- Lũy đẳng (§4) ----------

@pytest.mark.parametrize("san, duong_dan, ten_shop, so_dong, doanh_thu", [
    ("shopee", FILE_SHOPEE, "Shop C", 1774, Decimal("1908961059")),
    ("tiktok", FILE_TIKTOK, None, 7540, Decimal("7538502584")),
])
def test_nap_lai_cung_file_khong_doi_gi(nap, ket_noi_test, san, duong_dan, ten_shop, so_dong, doanh_thu):
    bang = f"orders_{san}"
    nap(san, duong_dan, ten_shop)
    ket_qua_lan_2 = nap(san, duong_dan, ten_shop)

    assert (ket_qua_lan_2["rows_inserted"], ket_qua_lan_2["rows_updated"]) == (0, so_dong)
    assert gia_tri(ket_noi_test, f"SELECT count(*) FROM {bang}") == so_dong
    assert gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang=bang)) == doanh_thu
    # 2 lần nạp → 2 dòng nhật ký, đều thành công.
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM sync_runs WHERE status = 'success'") == 2


# ---------- Cập nhật trạng thái (§4: lý do đổi DO NOTHING → DO UPDATE) ----------

def test_doi_trang_thai_mot_dong(phien_test, ket_noi_test):
    bang_chuan, _ = shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, "Shop C")
    loader.upsert_don_hang(phien_test, "shopee", bang_chuan, "lan_1.csv")
    phien_test.flush()

    # Cả lần nạp đầu và upsert sau nằm trong CÙNG giao dịch test, mà NOW() trả
    # giờ BẮT ĐẦU giao dịch → updated_at sẽ không đổi. Lùi tay 2 cột thời gian
    # về năm 2000 để giả lập "lần nạp trước diễn ra từ lâu".
    ket_noi_test.execute(text("UPDATE orders_shopee SET uploaded_at = '2000-01-01', updated_at = '2000-01-01'"))
    doanh_thu_truoc = gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_shopee"))

    # Chọn 1 dòng pending không hoàn hàng — dòng này đang được tính doanh thu.
    dong_doi = bang_chuan[(bang_chuan["order_status"] == "pending") & ~bang_chuan["is_returned"]].index[0]
    order_id = bang_chuan.at[dong_doi, "order_id"]
    sku = bang_chuan.at[dong_doi, "sku"]
    nmv_dong_doi = Decimal(str(bang_chuan.at[dong_doi, "nmv_after_tax"]))

    bang_moi = bang_chuan.copy()
    bang_moi.at[dong_doi, "order_status"] = "cancelled"
    so_dong_moi, so_dong_cap_nhat = loader.upsert_don_hang(phien_test, "shopee", bang_moi, "lan_2.csv")
    phien_test.flush()

    assert (so_dong_moi, so_dong_cap_nhat) == (0, 1774)
    dong = ket_noi_test.execute(
        text("SELECT order_status, uploaded_at, updated_at, source_file FROM orders_shopee "
             "WHERE order_id = :o AND sku = :s"), {"o": order_id, "s": sku}
    ).mappings().one()
    assert dong["order_status"] == "cancelled"
    assert dong["uploaded_at"].year == 2000          # giữ nghĩa "lần đầu xuất hiện"
    assert dong["updated_at"].year > 2000            # đánh dấu lần ghi mới
    assert dong["source_file"] == "lan_2.csv"        # dòng ghi sau thắng
    doanh_thu_sau = gia_tri(ket_noi_test, SQL_DOANH_THU.format(bang="orders_shopee"))
    assert doanh_thu_truoc - doanh_thu_sau == nmv_dong_doi


# ---------- Rollback khi lỗi giữa chừng ----------

def test_dong_hong_giua_chung_rollback_toan_bo(nap, ket_noi_test, monkeypatch):
    bang_chuan, bo_dem = shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, "Shop C")
    bang_hong = bang_chuan.copy()
    # Dòng 1.500 nằm ở LÔ THỨ HAI: lô đầu (dòng 0–999) đã ghi xong xuống CSDL
    # rồi mới gặp lỗi → chứng minh rollback xóa cả phần đã ghi, không chỉ lô lỗi.
    bang_hong.at[1500, "sku"] = None

    def parser_tra_dong_hong(duong_dan, ten_shop):
        return bang_hong, bo_dem
    monkeypatch.setattr(shopee_parser, "chuan_hoa_file_shopee", parser_tra_dong_hong)

    so_dong_truoc = gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee")
    moc_truoc_khi_nap = datetime.now().astimezone()
    with pytest.raises(IntegrityError, match="sku"):
        nap("shopee", FILE_SHOPEE, "Shop C")

    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee") == so_dong_truoc
    dong_sync = ket_noi_test.execute(text("SELECT * FROM sync_runs")).mappings().all()
    # Chỉ còn dòng 'failed' ghi riêng — dòng 'running' tạo đầu lượt đã rollback.
    assert len(dong_sync) == 1
    assert dong_sync[0]["status"] == "failed"
    assert "sku" in dong_sync[0]["error_message"]
    assert dong_sync[0]["finished_at"] is not None
    # started_at phải là lúc lần nạp bắt đầu thật. Bản cũ để now() mặc định:
    # trong test, now() là giờ bắt đầu giao dịch test — trước cả mốc này.
    # Đổi mốc sang cùng quy ước với cột (timestamp theo múi giờ phiên) bằng
    # chính CSDL, không tự giả định múi giờ phiên là gì.
    moc_theo_quy_uoc_cot = gia_tri(ket_noi_test, "SELECT CAST(:moc AS timestamp)", moc=moc_truoc_khi_nap)
    assert moc_theo_quy_uoc_cot <= dong_sync[0]["started_at"] <= dong_sync[0]["finished_at"]


def test_sai_cot_khong_ghi_gi(nap, ket_noi_test, monkeypatch):
    bang_chuan, bo_dem = shopee_parser.chuan_hoa_file_shopee(FILE_SHOPEE, "Shop C")

    def parser_thieu_cot(duong_dan, ten_shop):
        return bang_chuan.drop(columns=["nmv"]), bo_dem
    monkeypatch.setattr(shopee_parser, "chuan_hoa_file_shopee", parser_thieu_cot)

    with pytest.raises(ValueError, match="thiếu"):
        nap("shopee", FILE_SHOPEE, "Shop C")
    assert gia_tri(ket_noi_test, "SELECT count(*) FROM orders_shopee") == 0
    assert gia_tri(ket_noi_test, "SELECT status FROM sync_runs") == "failed"
