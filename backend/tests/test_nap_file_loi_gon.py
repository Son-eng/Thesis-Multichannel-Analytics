"""Test `sync_runs.error_message` của lượt nạp tệp lỗi chỉ ghi dạng GỌN, không chép giá trị ô (chỉ dẫn 021, C.2).

Phần 1 thuần (không CSDL): `mo_ta_loi_gon`. Phần 2 (CSDL thật, rollback): tệp có ô chứa chuỗi giả nhạy cảm ở vị trí gây
lỗi → `error_message` trong CSDL không chứa chuỗi đó nhưng vẫn cho biết loại lỗi; chi tiết đầy đủ nằm ở log máy chủ.
"""

import logging
from pathlib import Path

import pandas.errors as loi_pandas
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from app.etl import nap_file

NHAY_CAM = "GIATRI-NHAY-CAM-999"
THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"
FILE_SHOPEE = THU_MUC_MAU / "shopee_orders_anonymized.csv"


# ---------------------------------------------------------------- thuần

@pytest.mark.parametrize("loi, mong_doi", [
    (ValueError(f'Unable to parse string "{NHAY_CAM}" at position 5'), "Giá trị không đọc được (ValueError) ở dòng dữ liệu thứ 6"),
    (loi_pandas.ParserError("Error tokenizing data. C error: Expected 5 fields in line 1234, saw 7"), "Lỗi đọc tệp (ParserError) ở dòng 1234"),
    (loi_pandas.ParserError("lỗi không rõ dòng"), "Lỗi đọc tệp (ParserError)"),
    (loi_pandas.EmptyDataError("No columns to parse from file"), "Tệp rỗng hoặc không có dòng tiêu đề (EmptyDataError)"),
    (UnicodeDecodeError("utf-8", b"\xff", 7, 8, "x"), "Tệp sai mã hóa ký tự (UnicodeDecodeError) ở byte 7"),
    (nap_file.ThieuCotBatBuoc(["Mã đơn hàng", "SKU sản phẩm"]), "Tệp thiếu cột bắt buộc: Mã đơn hàng, SKU sản phẩm"),
    (KeyError(NHAY_CAM), "Tệp thiếu cột hoặc sai tên cột (KeyError)"),
    (ValueError(f"giá trị lạ {NHAY_CAM}"), "Giá trị trong tệp không hợp lệ (ValueError)"),
    (ValueError("Có 3 cặp (order_id, sku) lặp lại trong cùng dữ liệu, ví dụ [['D1', 'K1']]. Không ghi dòng nào."),
     "Có 3 cặp (order_id, sku) lặp lại trong tệp (ValueError)"),
    (RuntimeError(f"chi tiết {NHAY_CAM}"), "Lỗi hệ thống khi nạp tệp (RuntimeError)"),
])
def test_mo_ta_loi_gon_dung_khuon_va_khong_chep_gia_tri(loi, mong_doi):
    ket_qua = nap_file.mo_ta_loi_gon(loi)
    assert ket_qua == mong_doi
    assert NHAY_CAM not in ket_qua and "D1" not in ket_qua


def test_mo_ta_loi_gon_cua_loi_csdl():
    assert nap_file.mo_ta_loi_gon(DataError("INSERT", {}, Exception(f"value too long {NHAY_CAM}"))) == \
        "Giá trị trong tệp không vừa kiểu dữ liệu của CSDL (DataError)"
    assert nap_file.mo_ta_loi_gon(OperationalError("SELECT 1", {}, Exception(NHAY_CAM))) == "Lỗi hệ thống khi nạp tệp (OperationalError)"
    assert nap_file.mo_ta_loi_gon(IntegrityError("INSERT", {}, Exception(NHAY_CAM))) == "Dòng trong tệp vi phạm ràng buộc của CSDL (IntegrityError)"


def test_loi_rang_buoc_ghi_ten_cot_vi_pham_nhung_khong_ghi_gia_tri():
    class Chan:                       # giả lập `orig.diag.column_name` của psycopg
        diag = type("Diag", (), {"column_name": "sku"})()
    loi = IntegrityError("INSERT", {}, Chan())
    assert nap_file.mo_ta_loi_gon(loi) == "Dòng trong tệp vi phạm ràng buộc của CSDL (IntegrityError) ở cột sku"


def test_loi_cot_chuan_van_giu_ten_cot_vi_chi_co_ten_cot():
    thong_diep = "DataFrame không đúng cột chuẩn — thiếu ['sku'], thừa []. Không ghi dòng nào."
    assert nap_file.mo_ta_loi_gon(ValueError(thong_diep)) == thong_diep


# ---------------------------------------------------------------- CSDL thật

@pytest.mark.db
def test_tep_co_o_nhay_cam_gay_loi_so_khong_lo_gia_tri_vao_sync_runs(tao_phien_test, monkeypatch, ket_noi_test, tmp_path, caplog):
    monkeypatch.setattr(nap_file, "SessionLocal", tao_phien_test)
    dong = FILE_SHOPEE.read_text(encoding="utf-8-sig").splitlines()
    tieu_de = dong[0].split(",")
    import csv
    import io
    doc = list(csv.reader(io.StringIO("\n".join(dong[:4]))))
    doc[2][tieu_de.index("Số lượng")] = NHAY_CAM                       # ô số chứa chữ → pd.to_numeric ném ValueError kèm giá trị ô
    ghi = io.StringIO()
    csv.writer(ghi).writerows(doc)
    tep = tmp_path / "o_hong.csv"
    tep.write_text(ghi.getvalue(), encoding="utf-8-sig")

    with caplog.at_level(logging.ERROR, logger="app.etl.nap_file"):
        with pytest.raises(ValueError):
            nap_file.nap_file("shopee", str(tep), "Shop C", "file_manual")

    thong_diep, trang_thai = ket_noi_test.execute(text("SELECT error_message, status FROM sync_runs ORDER BY id DESC LIMIT 1")).one()
    assert trang_thai == "failed"
    assert NHAY_CAM not in thong_diep                                  # KHÔNG có giá trị ô trong CSDL
    assert "ValueError" in thong_diep and "dòng dữ liệu thứ" in thong_diep   # vẫn cho biết loại lỗi và vị trí
    assert NHAY_CAM in caplog.text                                     # chi tiết đầy đủ ở log máy chủ
    assert ket_noi_test.execute(text("SELECT count(*) FROM orders")).scalar_one() == 0
