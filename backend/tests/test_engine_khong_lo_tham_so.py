import logging

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import database
from app.config import settings

pytestmark = pytest.mark.db

BI_MAT = "SECRET-TEST-123"
CAU_GHI = ("INSERT INTO platform_tokens (platform, shop_name, shop_ref, access_token, refresh_token, access_expires_at) "
           "VALUES ('shopee', 'ZZ_TEST_LOG', '1', :acc, :ref, now())")


@pytest.fixture
def engine_debug(engine_test):
    engine = database.tao_engine(settings.DATABASE_URL, True)
    yield engine
    engine.dispose()


def test_engine_cua_ung_dung_che_tham_so():
    assert database.engine.hide_parameters is True


def test_bat_debug_log_van_co_cau_sql_nhung_khong_co_gia_tri_tham_so(engine_debug, caplog, capsys):
    with caplog.at_level(logging.DEBUG, logger="sqlalchemy.engine"):
        with engine_debug.connect() as ket_noi:
            giao_dich = ket_noi.begin()
            ket_noi.execute(text(CAU_GHI), {"acc": BI_MAT + "-ACCESS", "ref": BI_MAT + "-REFRESH"})
            giao_dich.rollback()
    toan_bo_log = caplog.text + capsys.readouterr().out + capsys.readouterr().err
    assert "INSERT INTO platform_tokens" in caplog.text
    assert BI_MAT not in toan_bo_log


def test_thong_diep_loi_cua_sqlalchemy_khong_chua_tham_so(engine_debug):
    cau_loi = CAU_GHI.replace("'1', :acc", "NULL, :acc")
    with engine_debug.connect() as ket_noi:
        giao_dich = ket_noi.begin()
        with pytest.raises(DBAPIError) as loi:
            ket_noi.execute(text(cau_loi), {"acc": BI_MAT + "-ACCESS", "ref": BI_MAT + "-REFRESH"})
        giao_dich.rollback()
    thong_diep = str(loi.value)
    assert "[parameters:" not in thong_diep
    assert "hidden due to hide_parameters=True" in thong_diep
    phan_do_sqlalchemy = "\n".join(d for d in thong_diep.split("\n") if not d.startswith("DETAIL:"))
    assert BI_MAT not in phan_do_sqlalchemy


def test_phan_chi_tiet_do_postgresql_sinh_ra_van_duoc_lam_sach_o_duong_ghi_nhat_ky(engine_debug):
    from app.sync.sync_job import lam_sach_thong_diep
    cau_loi = CAU_GHI.replace("'1', :acc", "NULL, :acc")
    acc, ref = BI_MAT + "-ACCESS", BI_MAT + "-REFRESH"
    with engine_debug.connect() as ket_noi:
        giao_dich = ket_noi.begin()
        with pytest.raises(DBAPIError) as loi:
            ket_noi.execute(text(cau_loi), {"acc": acc, "ref": ref})
        giao_dich.rollback()
    thong_diep_tho = str(loi.value)
    assert acc in thong_diep_tho, "PostgreSQL không còn kèm cả dòng vi phạm vào thông điệp? Cập nhật ghi chú giới hạn trong báo cáo 021"
    sau_khi_lam_sach = lam_sach_thong_diep(thong_diep_tho, [acc, ref])
    assert acc not in sau_khi_lam_sach and ref not in sau_khi_lam_sach
