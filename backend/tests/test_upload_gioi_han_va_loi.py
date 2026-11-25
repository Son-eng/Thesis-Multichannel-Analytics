from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api import upload as api_upload
from app.database import lay_phien_db
from app.etl import nap_file
from app.main import tao_ung_dung

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"


@pytest.fixture
def ung_dung(phien_test, tao_phien_test, monkeypatch):
    monkeypatch.setattr(nap_file, "SessionLocal", tao_phien_test)
    app = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    app.dependency_overrides[lay_phien_db] = lambda: phien_test
    return app


@pytest.fixture
def client(ung_dung, tieu_de_admin):
    with TestClient(ung_dung, headers=tieu_de_admin) as c:
        yield c


def dem(ket_noi, bang):
    return ket_noi.execute(text(f"SELECT count(*) FROM {bang}")).scalar_one()


def tai_len(client, san, duong_dan, **form):
    with open(duong_dan, "rb") as f:
        return client.post(f"/api/upload/{san}", files={"file": (Path(duong_dan).name, f, "text/csv")}, data=form)


def test_tep_vuot_nguong_tra_413_dung_khuon_va_khong_tao_sync_run(client, ket_noi_test, monkeypatch):
    monkeypatch.setattr(api_upload, "GIOI_HAN_TAI_FILE_BYTE", 1000)
    phan_hoi = tai_len(client, "tiktok", FILE_TIKTOK)
    assert phan_hoi.status_code == 413
    chi_tiet = phan_hoi.json()["detail"]
    assert chi_tiet["code"] == "file_too_large" and chi_tiet["max_bytes"] == 1000 and "vượt quá" in chi_tiet["message"]
    assert dem(ket_noi_test, "sync_runs") == 0 and dem(ket_noi_test, "orders") == 0


def test_hang_so_gioi_han_la_50_mb_va_thong_diep_dung_chu():
    assert api_upload.GIOI_HAN_TAI_FILE_BYTE == 50 * 1024 * 1024 == 52428800


def test_thong_diep_413_ghi_dung_so_mb_theo_gioi_han_hien_hanh(client, monkeypatch):
    monkeypatch.setattr(api_upload, "GIOI_HAN_TAI_FILE_BYTE", 2 * 1024 * 1024)
    chi_tiet = tai_len(client, "tiktok", FILE_TIKTOK).json()["detail"]
    assert chi_tiet["message"] == "Tệp vượt quá 2 MB" and chi_tiet["max_bytes"] == 2 * 1024 * 1024


def test_tep_dung_bang_nguong_van_nap_duoc(client, monkeypatch, ket_noi_test):
    monkeypatch.setattr(api_upload, "GIOI_HAN_TAI_FILE_BYTE", FILE_TIKTOK.stat().st_size)
    phan_hoi = tai_len(client, "tiktok", FILE_TIKTOK)
    assert phan_hoi.status_code == 200 and phan_hoi.json()["rows_inserted"] == 7540


def test_tep_mau_hop_le_van_nap_nhu_cu(client, ket_noi_test):
    phan_hoi = tai_len(client, "shopee", FILE_SHOPEE, shop_name="Shop C")
    run = phan_hoi.json()
    assert phan_hoi.status_code == 200 and (run["rows_total"], run["rows_inserted"], run["rows_updated"]) == (1774, 1774, 0)
    assert ket_noi_test.execute(text(
        "SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'shopee' AND order_status <> 'cancelled' AND is_returned = FALSE"
    )).scalar_one() == 1908961059


def test_tep_rac_khong_phai_csv_van_422_invalid_file(client, tmp_path):
    rac = tmp_path / "rac.csv"
    rac.write_bytes(b"\x00\x01\x02 khong phai csv \xff\xfe")
    phan_hoi = tai_len(client, "tiktok", rac)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_file"


def test_tep_rong_van_422(client, tmp_path):
    rong = tmp_path / "rong.csv"
    rong.write_bytes(b"")
    assert tai_len(client, "shopee", rong, shop_name="Shop C").status_code == 422


def test_gia_tri_khong_vua_cot_csdl_la_422_khong_phai_500(client, tmp_path, ket_noi_test):
    dong = FILE_TIKTOK.read_text(encoding="utf-8-sig").splitlines()
    tieu_de = dong[0].split(",")
    tep = tmp_path / "sku_dai.csv"
    ban_sao = [dong[0], dong[1]]
    sku_cot = tieu_de.index("Seller SKU") if "Seller SKU" in tieu_de else None
    if sku_cot is None:
        pytest.skip("Tệp mẫu không có cột Seller SKU")
    import csv
    import io
    doc = list(csv.reader(io.StringIO("\n".join(ban_sao))))
    doc[1][sku_cot] = "X" * 300
    ghi = io.StringIO()
    csv.writer(ghi).writerows(doc)
    tep.write_text(ghi.getvalue(), encoding="utf-8-sig")
    phan_hoi = tai_len(client, "tiktok", tep)
    assert phan_hoi.status_code == 422, phan_hoi.text
    assert dem(ket_noi_test, "orders") == 0


def test_loi_ha_tang_la_500_khong_phai_422(ung_dung, tieu_de_admin, monkeypatch):
    def hong_csdl(*tham_so, **tu_khoa):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
    monkeypatch.setattr(nap_file, "nap_file", hong_csdl)
    with TestClient(ung_dung, headers=tieu_de_admin, raise_server_exceptions=False) as c:
        phan_hoi = tai_len(c, "tiktok", FILE_TIKTOK)
    assert phan_hoi.status_code == 500
    assert "invalid_file" not in phan_hoi.text


@pytest.mark.parametrize("loi", [RuntimeError("bo nho"), MemoryError(), OSError("o dia day")])
def test_cac_loi_khac_cung_la_500(ung_dung, tieu_de_admin, monkeypatch, loi):
    def hong(*tham_so, **tu_khoa):
        raise loi
    monkeypatch.setattr(nap_file, "nap_file", hong)
    with TestClient(ung_dung, headers=tieu_de_admin, raise_server_exceptions=False) as c:
        assert tai_len(c, "tiktok", FILE_TIKTOK).status_code == 500


def test_cac_lop_loi_noi_dung_tep_la_dung_nhung_lop_da_chon():
    ten = {c.__name__ for c in nap_file.LOI_NOI_DUNG_TEP}
    assert ten == {"ValueError", "KeyError", "ParserError", "EmptyDataError", "UnicodeDecodeError", "DataError", "IntegrityError"}
    assert not issubclass(OperationalError, nap_file.LOI_NOI_DUNG_TEP)
