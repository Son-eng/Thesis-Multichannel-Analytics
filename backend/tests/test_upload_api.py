"""Test POST /api/upload/{platform} và GET /api/watcher/status (SPEC §12.1.3.5–§12.1.3.6, QUY_TRINH bước 12).

CSDL thật trong giao dịch rollback: `nap_file.SessionLocal` và dependency `lay_phien_db`
cùng trỏ vào kết nối test. File mẫu ẩn danh ở data/samples/.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import lay_phien_db
from app.etl import nap_file
from app.main import tao_ung_dung

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"
MAU_GIO_VN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$")


@pytest.fixture
def client(phien_test, tao_phien_test, monkeypatch, tieu_de_admin):
    monkeypatch.setattr(nap_file, "SessionLocal", tao_phien_test)
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=False)
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung, headers=tieu_de_admin) as c:
        yield c


def dem(ket_noi, bang):
    """Đếm dòng: `bang` là "sync_runs" hoặc tên sàn ("shopee"/"tiktok") → đếm dòng của sàn đó trong `orders`."""
    if bang in ("shopee", "tiktok"):
        return ket_noi.execute(text("SELECT count(*) FROM orders WHERE platform = :p"), {"p": bang}).scalar_one()
    return ket_noi.execute(text(f"SELECT count(*) FROM {bang}")).scalar_one()


def tai_len(client, san, duong_dan, **form):
    with open(duong_dan, "rb") as f:
        return client.post(f"/api/upload/{san}", files={"file": (Path(duong_dan).name, f, "text/csv")}, data=form)


def test_tai_file_shopee_tra_dung_mot_sync_run_file_manual(client, ket_noi_test):
    phan_hoi = tai_len(client, "shopee", FILE_SHOPEE, shop_name="Shop C")
    assert phan_hoi.status_code == 200
    run = phan_hoi.json()
    assert (run["platform"], run["shop_name"], run["source"], run["trigger_type"], run["status"]) == \
           ("shopee", "Shop C", "file_manual", "manual", "success")
    assert run["file_name"] == "shopee_orders_anonymized.csv" and run["triggered_by"]["username"] == "admin_thu"
    assert (run["rows_total"], run["rows_inserted"], run["rows_updated"]) == (1774, 1774, 0)
    assert MAU_GIO_VN.match(run["started_at"]) and MAU_GIO_VN.match(run["finished_at"])
    assert set(run["quality"]) == {"rows_sku_fallback", "rows_sku_unknown", "rows_status_unknown",
                                    "rows_province_unmapped", "rows_product_unmapped"}
    assert dem(ket_noi_test, "shopee") == 1774 and dem(ket_noi_test, "sync_runs") == 1
    assert ket_noi_test.execute(text("SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'shopee' AND order_status <> 'cancelled' AND is_returned = FALSE")).scalar_one() == 1908961059


def test_tai_file_tiktok_khong_can_shop_name(client, ket_noi_test):
    phan_hoi = tai_len(client, "tiktok", FILE_TIKTOK)
    run = phan_hoi.json()
    assert phan_hoi.status_code == 200 and run["shop_name"] is None
    assert (run["rows_total"], run["rows_inserted"]) == (7540, 7540)
    assert ket_noi_test.execute(text("SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'tiktok' AND order_status <> 'cancelled' AND is_returned = FALSE")).scalar_one() == 7538502584


def test_shopee_thieu_shop_name_tra_400_shop_required_va_khong_ghi_gi(client, ket_noi_test):
    for form in ({}, {"shop_name": "  "}):
        phan_hoi = tai_len(client, "shopee", FILE_SHOPEE, **form)
        assert phan_hoi.status_code == 400
        assert phan_hoi.json() == {"detail": {"code": "shop_required", "message": "Tệp Shopee cần chọn gian hàng"}}
    assert dem(ket_noi_test, "shopee") == 0 and dem(ket_noi_test, "sync_runs") == 0


def test_tai_lai_cung_file_khong_nhan_doi_du_lieu(client, ket_noi_test):
    tai_len(client, "tiktok", FILE_TIKTOK)
    lan_hai = tai_len(client, "tiktok", FILE_TIKTOK).json()
    assert (lan_hai["rows_inserted"], lan_hai["rows_updated"]) == (0, 7540)
    assert dem(ket_noi_test, "tiktok") == 7540
    assert dem(ket_noi_test, "sync_runs") == 2


def test_file_thieu_cot_tra_422_missing_columns_va_khong_ghi_don_nao(client, ket_noi_test, tmp_path):
    cot = FILE_SHOPEE.read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    file_hong = tmp_path / "thieu_cot.csv"
    file_hong.write_text(",".join(c for c in cot if c != "Mã đơn hàng") + "\n", encoding="utf-8-sig")
    phan_hoi = tai_len(client, "shopee", file_hong, shop_name="Shop C")
    assert phan_hoi.status_code == 422
    assert phan_hoi.json() == {"detail": {"code": "missing_columns",
                                          "message": "Tệp thiếu cột bắt buộc, không dòng nào được ghi",
                                          "missing_columns": ["Mã đơn hàng"]}}
    assert dem(ket_noi_test, "shopee") == 0
    assert ket_noi_test.execute(text("SELECT status FROM sync_runs")).scalars().all() == ["failed"]   # lần nạp hỏng có dấu vết


def test_file_tiktok_thieu_cot_liet_ke_du_cac_cot_thieu(client, ket_noi_test, tmp_path):
    cot = FILE_TIKTOK.read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    cac_thieu = [c for c in cot[:3]]
    file_hong = tmp_path / "tt.csv"
    file_hong.write_text(",".join(c for c in cot if c not in cac_thieu) + "\n", encoding="utf-8-sig")
    phan_hoi = tai_len(client, "tiktok", file_hong)
    assert phan_hoi.status_code == 422
    thieu_bao_ve = set(phan_hoi.json()["detail"]["missing_columns"])
    from app.etl import tiktok_parser
    assert thieu_bao_ve == set(cac_thieu) & set(tiktok_parser.COT_CAN_DOC) and thieu_bao_ve
    assert dem(ket_noi_test, "tiktok") == 0


def test_file_khong_phai_csv_tra_422_invalid_file(client, ket_noi_test, tmp_path):
    rac = tmp_path / "rac.csv"
    rac.write_bytes(b"\x00\x01\x02 khong phai csv \xff\xfe")
    phan_hoi = tai_len(client, "tiktok", rac)
    assert phan_hoi.status_code == 422 and phan_hoi.json()["detail"]["code"] == "invalid_file"
    assert dem(ket_noi_test, "tiktok") == 0


def test_san_la_tra_422(client):
    assert tai_len(client, "lazada", FILE_TIKTOK).status_code == 422


def test_watcher_status_dung_khuon(client):
    du_lieu = client.get("/api/watcher/status").json()
    assert set(du_lieu) == {"interval_seconds", "last_scan_at", "pending_files"}
    assert du_lieu["interval_seconds"] == 30 and du_lieu["last_scan_at"] is None and du_lieu["pending_files"] == 0
    client.app.state.trang_thai_quet.pending_files = 2
    from datetime import datetime, timezone
    client.app.state.trang_thai_quet.last_scan_at = datetime(2026, 8, 23, 9, 52, 30, tzinfo=timezone.utc)
    du_lieu = client.get("/api/watcher/status").json()
    assert du_lieu == {"interval_seconds": 30, "last_scan_at": "2026-08-23T16:52:30+07:00", "pending_files": 2}


def test_lifespan_bat_watcher_quet_ngay_khi_khoi_dong_va_cap_nhat_trang_thai(phien_test, tmp_path, tieu_de_admin):
    (tmp_path / "inbox" / "tiktok").mkdir(parents=True)
    (tmp_path / "inbox" / "tiktok" / "cho.csv").write_text("x", encoding="utf-8")
    ung_dung = tao_ung_dung(chay_lich=False, khoi_dong_csdl=False, chay_watcher=True,
                            thu_muc_data=tmp_path, ham_nap=lambda *tham_so: None)
    ung_dung.dependency_overrides[lay_phien_db] = lambda: phien_test
    with TestClient(ung_dung, headers=tieu_de_admin) as c:
        for _ in range(100):                                  # vòng quét đầu chạy ở thread nền
            du_lieu = c.get("/api/watcher/status").json()
            if du_lieu["last_scan_at"]:
                break
            import time; time.sleep(0.1)
    assert MAU_GIO_VN.match(du_lieu["last_scan_at"]) and du_lieu["pending_files"] == 1   # lần quét đầu chỉ ghi kích thước
