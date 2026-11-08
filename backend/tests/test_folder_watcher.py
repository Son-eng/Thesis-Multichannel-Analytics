"""Test quét thư mục tự động `app/sync/folder_watcher.py` (SPEC §2.4, QUY_TRINH bước 12).

Thư mục `data/` thật được thay bằng thư mục tạm (tmp_path). Hai nhóm:
- hàm giả cho `nap_file` — kiểm quy tắc "kích thước không đổi qua hai lần quét", chuyển file;
- `nap_file` THẬT với CSDL thật (marker db, giao dịch rollback) — file tốt → processed/ và
  dòng sync_runs `file_auto`, file thiếu cột → failed/ kèm .log và không dòng đơn hàng nào.
"""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import text

from app.etl import nap_file
from app.sync import folder_watcher

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"
FILE_TIKTOK = THU_MUC_MAU / "tiktok_orders_anonymized.csv"


@pytest.fixture
def data(tmp_path):
    for nhom in ("inbox", "processed", "failed"):
        for san in ("shopee", "tiktok"):
            (tmp_path / nhom / san).mkdir(parents=True)
    (tmp_path / "inbox" / "shopee" / ".gitkeep").touch()           # file ẩn phải bị bỏ qua
    return tmp_path


def quet_hai_lan(data, ham_nap, trang_thai=None):
    """Quét lần 1 (ghi nhận kích thước) và lần 2 (kích thước không đổi → xử lý)."""
    kich_thuoc, kq1 = folder_watcher.quet_mot_lan(data, {}, ham_nap, trang_thai)
    kich_thuoc, kq2 = folder_watcher.quet_mot_lan(data, kich_thuoc, ham_nap, trang_thai)
    return kq1, kq2


def test_file_chi_duoc_xu_ly_o_lan_quet_thu_hai(data):
    (data / "inbox" / "tiktok" / "a.csv").write_text("x", encoding="utf-8")
    da_nap = []
    ham_nap = lambda san, duong_dan, ten_shop, nguon: da_nap.append((san, Path(duong_dan).name, ten_shop, nguon))
    kq1, kq2 = quet_hai_lan(data, ham_nap)
    assert kq1 == [("tiktok", "a.csv", "cho")] and da_nap == [("tiktok", "a.csv", None, "file_auto")]
    assert kq2 == [("tiktok", "a.csv", "processed")]
    assert not (data / "inbox" / "tiktok" / "a.csv").exists()
    assert [f.name for f in (data / "processed" / "tiktok").iterdir()][0].startswith("a__")
    assert (data / "inbox" / "shopee" / ".gitkeep").exists()           # .gitkeep không bị đụng


def test_file_dang_copy_do_kich_thuoc_con_doi_thi_chua_xu_ly(data):
    file = data / "inbox" / "tiktok" / "lon.csv"
    file.write_text("abc", encoding="utf-8")
    da_nap = []
    ham_nap = lambda *tham_so: da_nap.append(tham_so)
    kich_thuoc, _ = folder_watcher.quet_mot_lan(data, {}, ham_nap)
    file.write_text("abcdef", encoding="utf-8")                        # vẫn đang được ghi thêm
    kich_thuoc, kq = folder_watcher.quet_mot_lan(data, kich_thuoc, ham_nap)
    assert kq == [("tiktok", "lon.csv", "cho")] and da_nap == []
    _, kq = folder_watcher.quet_mot_lan(data, kich_thuoc, ham_nap)      # nay kích thước đã đứng yên
    assert kq == [("tiktok", "lon.csv", "processed")] and len(da_nap) == 1


def test_file_loi_vao_failed_kem_log_va_khong_chan_file_khac(data):
    (data / "inbox" / "shopee" / "hong.csv").write_text("x", encoding="utf-8")
    (data / "inbox" / "tiktok" / "tot.csv").write_text("x", encoding="utf-8")

    def ham_nap(san, duong_dan, ten_shop, nguon):
        if san == "shopee":
            raise ValueError("thiếu cột Mã đơn hàng")
        assert ten_shop is None
    _, kq = quet_hai_lan(data, ham_nap)
    assert sorted(kq) == [("shopee", "hong.csv", "failed"), ("tiktok", "tot.csv", "processed")]
    cac_file = sorted(f.name for f in (data / "failed" / "shopee").iterdir())
    assert len(cac_file) == 2 and cac_file[0].endswith(".csv") and cac_file[1].endswith(".log")
    noi_dung_log = next((data / "failed" / "shopee").glob("*.log")).read_text(encoding="utf-8")
    assert "ValueError" in noi_dung_log and "thiếu cột Mã đơn hàng" in noi_dung_log
    assert list((data / "inbox" / "shopee").glob("*.csv")) == []        # không còn tồn đọng trong inbox


def test_chi_nhan_csv_va_bo_qua_file_an_hoac_khac_duoi(data):
    (data / "inbox" / "shopee" / "ghi_chu.txt").write_text("x")
    (data / "inbox" / "shopee" / "~$tam.csv.tmp").write_text("x")
    da_nap = []
    quet_hai_lan(data, lambda *tham_so: da_nap.append(tham_so))
    assert da_nap == []


def test_hai_file_cung_ten_khong_de_nhau_o_processed(data):
    da_nap = []
    ham_nap = lambda *tham_so: da_nap.append(tham_so)
    for _ in range(2):
        (data / "inbox" / "tiktok" / "trung.csv").write_text("x", encoding="utf-8")
        quet_hai_lan(data, ham_nap)
    assert len(list((data / "processed" / "tiktok").glob("trung__*.csv"))) == 2


def test_trang_thai_quet_dem_file_cho_va_moc_quet(data):
    trang_thai = folder_watcher.TrangThaiQuet()
    assert trang_thai.last_scan_at is None
    (data / "inbox" / "shopee" / "a.csv").write_text("x", encoding="utf-8")
    folder_watcher.quet_mot_lan(data, {}, lambda *t: None, trang_thai)
    assert trang_thai.pending_files == 1 and trang_thai.last_scan_at is not None


# ---------- nap_file THẬT với CSDL thật ----------

@pytest.fixture
def nap_that(tao_phien_test, monkeypatch):
    monkeypatch.setattr(nap_file, "SessionLocal", tao_phien_test)
    return nap_file.nap_file


@pytest.mark.db
def test_file_tot_vao_processed_va_ghi_sync_run_file_auto(data, nap_that, ket_noi_test):
    shutil.copy(FILE_TIKTOK, data / "inbox" / "tiktok" / "TikTok_T8.csv")
    shutil.copy(FILE_SHOPEE, data / "inbox" / "shopee" / "Shopee_T8.csv")
    _, kq = quet_hai_lan(data, nap_that)
    assert sorted(kq) == [("shopee", "Shopee_T8.csv", "processed"), ("tiktok", "TikTok_T8.csv", "processed")]
    assert list((data / "inbox" / "shopee").glob("*.csv")) == [] and list((data / "inbox" / "tiktok").glob("*.csv")) == []
    assert len(list((data / "processed" / "shopee").glob("Shopee_T8__*.csv"))) == 1
    cac_dong = ket_noi_test.execute(text(
        "SELECT platform, shop_name, source, trigger_type, status, rows_total, rows_inserted FROM sync_runs ORDER BY platform")).all()
    assert cac_dong == [("shopee", "Shop C", "file_auto", "schedule", "success", 1774, 1774),
                        ("tiktok", None, "file_auto", "schedule", "success", 7540, 7540)]
    assert ket_noi_test.execute(text("SELECT SUM(nmv_after_tax) FROM orders WHERE platform = 'shopee' AND order_status <> 'cancelled' AND is_returned = FALSE")).scalar_one() == 1908961059


@pytest.mark.db
def test_file_thieu_cot_vao_failed_khong_ghi_don_nao(data, nap_that, ket_noi_test):
    dong_dau = FILE_SHOPEE.read_text(encoding="utf-8-sig").splitlines()[0]
    cot = dong_dau.split(",")
    file = data / "inbox" / "shopee" / "thieu_cot.csv"
    file.write_text(",".join(c for c in cot if c != "Mã đơn hàng") + "\n", encoding="utf-8-sig")
    _, kq = quet_hai_lan(data, nap_that)
    assert kq == [("shopee", "thieu_cot.csv", "failed")]
    assert ket_noi_test.execute(text("SELECT count(*) FROM orders WHERE platform = 'shopee'")).scalar_one() == 0
    dong = ket_noi_test.execute(text("SELECT source, status, error_message FROM sync_runs")).one()
    assert dong[0] == "file_auto" and dong[1] == "failed" and "Mã đơn hàng" in dong[2]
    assert next((data / "failed" / "shopee").glob("*.log")).read_text(encoding="utf-8").count("Mã đơn hàng") == 1


@pytest.mark.db
def test_nap_lai_cung_file_qua_thu_muc_khong_nhan_doi_du_lieu(data, nap_that, ket_noi_test):
    for _ in range(2):
        shutil.copy(FILE_TIKTOK, data / "inbox" / "tiktok" / "TikTok_T8.csv")
        quet_hai_lan(data, nap_that)
    assert ket_noi_test.execute(text("SELECT count(*) FROM orders WHERE platform = 'tiktok'")).scalar_one() == 7540
    cac_luot = ket_noi_test.execute(text("SELECT rows_inserted, rows_updated FROM sync_runs ORDER BY id")).all()
    assert cac_luot == [(7540, 0), (0, 7540)]
