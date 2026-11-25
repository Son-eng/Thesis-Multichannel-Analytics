from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.etl import loader, shopee_parser, tiktok_parser

pytestmark = pytest.mark.db

THU_MUC_MAU = Path(__file__).resolve().parents[2] / "data" / "samples"


@pytest.fixture(scope="module")
def mau():
    shopee = shopee_parser.chuan_hoa_file_shopee(THU_MUC_MAU / "shopee_orders_anonymized.csv", "Shop C")[0]
    tiktok = tiktok_parser.chuan_hoa_file_tiktok(THU_MUC_MAU / "tiktok_orders_anonymized.csv")[0]
    return shopee, tiktok


def mot_dong(bang, order_id="DON_TRUNG_MA", sku="SKU_TRUNG_MA"):
    dong = bang.head(1).copy()
    dong["order_id"] = order_id
    dong["sku"] = sku
    return dong.reset_index(drop=True)


def dem(ket_noi, **dieu_kien):
    mo_ta = " AND ".join(f"{k} = :{k}" for k in dieu_kien) or "TRUE"
    return ket_noi.execute(text(f"SELECT count(*) FROM orders WHERE {mo_ta}"), dieu_kien).scalar_one()


def test_cung_order_id_sku_khac_san_khong_bi_coi_la_trung(mau, phien_test, ket_noi_test):
    shopee, tiktok = mau
    them_s, cap_nhat_s = loader.upsert_don_hang(phien_test, "shopee", mot_dong(shopee), None)
    them_t, cap_nhat_t = loader.upsert_don_hang(phien_test, "tiktok", mot_dong(tiktok), None)
    assert (them_s, cap_nhat_s, them_t, cap_nhat_t) == (1, 0, 1, 0)
    assert dem(ket_noi_test, order_id="DON_TRUNG_MA", sku="SKU_TRUNG_MA") == 2
    assert dem(ket_noi_test, platform="shopee", order_id="DON_TRUNG_MA") == 1
    assert dem(ket_noi_test, platform="tiktok", order_id="DON_TRUNG_MA") == 1


def test_cung_san_cung_order_id_sku_thi_cap_nhat_khong_nhan_doi(mau, phien_test, ket_noi_test):
    shopee, _ = mau
    loader.upsert_don_hang(phien_test, "shopee", mot_dong(shopee), "lan_1.csv")
    dong_doi = mot_dong(shopee)
    dong_doi["order_status"] = "cancelled"
    them, cap_nhat = loader.upsert_don_hang(phien_test, "shopee", dong_doi, "lan_2.csv")
    assert (them, cap_nhat) == (0, 1)
    assert dem(ket_noi_test, platform="shopee", order_id="DON_TRUNG_MA") == 1
    assert ket_noi_test.execute(text("SELECT order_status FROM orders WHERE order_id = 'DON_TRUNG_MA'")).scalar_one() == "cancelled"


def test_cap_nhat_cua_mot_san_khong_dung_den_dong_cung_ma_cua_san_kia(mau, phien_test, ket_noi_test):
    shopee, tiktok = mau
    dong_shopee, dong_tiktok = mot_dong(shopee), mot_dong(tiktok)
    dong_shopee["order_status"] = dong_tiktok["order_status"] = "completed"
    loader.upsert_don_hang(phien_test, "shopee", dong_shopee, None)
    loader.upsert_don_hang(phien_test, "tiktok", dong_tiktok, None)
    dong_doi = dong_tiktok.copy()
    dong_doi["order_status"] = "cancelled"
    loader.upsert_don_hang(phien_test, "tiktok", dong_doi, None)
    trang_thai = dict(ket_noi_test.execute(text("SELECT platform, order_status FROM orders WHERE order_id = 'DON_TRUNG_MA'")).all())
    assert trang_thai == {"tiktok": "cancelled", "shopee": "completed"}


def test_cot_rieng_tung_san(mau, phien_test, ket_noi_test):
    shopee, tiktok = mau
    loader.upsert_don_hang(phien_test, "shopee", shopee.head(5), None)
    loader.upsert_don_hang(phien_test, "tiktok", tiktok.head(5), None)
    cot = ("count(*) FILTER (WHERE order_amount IS NOT NULL), count(*) FILTER (WHERE sku_subtotal_after_discount IS NOT NULL), "
           "count(*) FILTER (WHERE nmv_is_provisional)")
    s = ket_noi_test.execute(text(f"SELECT {cot} FROM orders WHERE platform = 'shopee'")).one()
    t = ket_noi_test.execute(text(f"SELECT {cot} FROM orders WHERE platform = 'tiktok'")).one()
    assert tuple(s) == (0, 0, 0)
    assert t[0] == 5 and t[1] == 5 and t[2] == 0


def test_nmv_is_provisional_cua_shopee_duoc_giu_con_tiktok_luon_false(mau, phien_test, ket_noi_test):
    shopee, tiktok = mau
    dong = mot_dong(shopee, "DON_TAM_TINH", "SKU_TAM_TINH")
    dong["nmv_is_provisional"] = True
    loader.upsert_don_hang(phien_test, "shopee", dong, None)
    loader.upsert_don_hang(phien_test, "tiktok", mot_dong(tiktok, "DON_TIKTOK", "SKU_TIKTOK"), None)
    gia_tri = dict(ket_noi_test.execute(text("SELECT platform, nmv_is_provisional FROM orders WHERE order_id IN ('DON_TAM_TINH','DON_TIKTOK')")).all())
    assert gia_tri == {"shopee": True, "tiktok": False}


def test_platform_la_gia_tri_la_bi_check_chan(ket_noi_test):
    with pytest.raises(IntegrityError, match="ck_orders_platform"):
        ket_noi_test.execute(text(
            "INSERT INTO orders (platform, shop_name, order_id, sku, order_date, order_status, data_source) "
            "VALUES ('lazada', 'S', 'D1', 'K1', :d, 'completed', 'file')"), {"d": date(2026, 1, 1)})


def test_platform_null_bi_chan(ket_noi_test):
    with pytest.raises(IntegrityError, match="platform"):
        ket_noi_test.execute(text(
            "INSERT INTO orders (platform, shop_name, order_id, sku, order_date, order_status, data_source) "
            "VALUES (NULL, 'S', 'D1', 'K1', :d, 'completed', 'file')"), {"d": date(2026, 1, 1)})


def test_khoa_duy_nhat_bao_ve_ngay_o_csdl(ket_noi_test):
    cau = ("INSERT INTO orders (platform, shop_name, order_id, sku, order_date, order_status, data_source) "
           "VALUES ('shopee', 'S', 'D1', 'K1', :d, 'completed', 'file')")
    ket_noi_test.execute(text(cau), {"d": date(2026, 1, 1)})
    with pytest.raises(IntegrityError, match="uq_orders_platform_order_sku"):
        ket_noi_test.execute(text("SAVEPOINT s"))
        ket_noi_test.execute(text(cau), {"d": date(2026, 1, 1)})


def test_bang_cu_da_bi_xoa_va_chi_muc_deu_bat_dau_bang_platform(ket_noi_test):
    cac_bang = set(ket_noi_test.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
    assert "orders" in cac_bang and not ({"orders_shopee", "orders_tiktok"} & cac_bang)
    chi_muc = dict(ket_noi_test.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'orders' AND indexname LIKE 'idx_orders_%'")).all())
    assert set(chi_muc) == {f"idx_orders_platform_{t}" for t in ("date", "status", "shop", "sku", "product")}
    assert all("(platform, " in d for d in chi_muc.values())


def test_truy_van_mot_san_dung_chi_muc_co_platform(ket_noi_test):
    ket_noi_test.execute(text("SET LOCAL enable_seqscan = off"))
    ke_hoach = "\n".join(ket_noi_test.execute(text(
        "EXPLAIN SELECT sum(nmv_after_tax) FROM orders WHERE platform = 'tiktok' AND order_date BETWEEN '2026-08-01' AND '2026-08-23'"
    )).scalars())
    assert "idx_orders_platform_date" in ke_hoach or "uq_orders_platform_order_sku" in ke_hoach
