"""Test data_builder.py — đổi ngược CSV → khuôn API không làm mất hay sai số liệu (SPEC §19.4).

Số kỳ vọng tính THẲNG từ CSV bằng pandas ngay trong test, tức là một cách
đọc độc lập với code đang được kiểm. Thêm vào đó, đối chiếu với số đã chốt ở
SPEC §17.1 (1.774 / 7.540 dòng), §17.2 (1.761 / 7.526 đơn), §6.4 (769 dòng
Shopee COMPLETED), §3.2 (56 / 139 dòng hoàn).
"""

import ast
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

import data_builder

GIO_VN = timezone(timedelta(hours=7))


def doc_csv_doi_chieu(duong_dan):
    """Đọc CSV bằng pandas để tính số kỳ vọng — tên cột chuẩn hóa NFC như file gốc cần."""
    bang = pd.read_csv(duong_dan, dtype=str)
    bang.columns = [unicodedata.normalize("NFC", ten_cot) for ten_cot in bang.columns]
    return bang


def cot_so(bang, ten_cot):
    """Một cột tiền/số lượng của CSV dưới dạng số (xử lý cả "1,415,000" và "2.28e+06")."""
    return pd.to_numeric(bang[ten_cot].str.replace(",", ""))


@pytest.fixture(scope="module")
def shopee():
    return data_builder.dung_du_lieu_shopee()


@pytest.fixture(scope="module")
def tiktok():
    return data_builder.dung_du_lieu_tiktok()


@pytest.fixture(scope="module")
def csv_shopee():
    return doc_csv_doi_chieu(data_builder.FILE_SHOPEE)


@pytest.fixture(scope="module")
def csv_tiktok():
    return doc_csv_doi_chieu(data_builder.FILE_TIKTOK)


@pytest.fixture(scope="module")
def mat_hang_shopee(shopee):
    """Mọi phần tử item_list của mọi đơn, kèm order_sn và trạng thái đơn."""
    return [
        {**mat_hang, "order_sn": don["order_sn"], "order_status": don["order_status"]}
        for don in shopee["don_hang"].values()
        for mat_hang in don["item_list"]
    ]


@pytest.fixture(scope="module")
def don_tiktok(tiktok):
    """Mọi đơn TikTok của cả 2 shop, kèm tên shop."""
    return [
        {**don, "shop": ten_shop}
        for ten_shop, shop in tiktok.items()
        for don in shop["don_hang"].values()
    ]


# ---------- Hàm phụ ----------

def test_chia_deu_du_don_vao_phan_dau():
    assert data_builder.chia_deu(10, 3) == [4, 3, 3]
    assert data_builder.chia_deu(9, 3) == [3, 3, 3]
    assert data_builder.chia_deu(7, 1) == [7]


def test_so_nguyen_doc_ca_hai_dinh_dang():
    assert data_builder.so_nguyen("2.28e+06") == 2280000
    assert data_builder.so_nguyen("1,415,000") == 1415000
    with pytest.raises(ValueError):
        data_builder.so_nguyen("1.5")


def test_trang_thai_la_bao_loi():
    with pytest.raises(ValueError):
        data_builder.doi_trang_thai_shopee("Trạng thái lạ")
    with pytest.raises(ValueError):
        data_builder.doi_trang_thai_tiktok("Trạng thái lạ")


def test_khong_import_gi_tu_backend():
    """data_builder chỉ được dùng thư viện chuẩn và pandas (§19.4, bước 8 Phần C)."""
    ma_nguon = Path(data_builder.__file__).read_text(encoding="utf-8")
    cac_module = set()
    for nut in ast.walk(ast.parse(ma_nguon)):
        if isinstance(nut, ast.Import):
            cac_module.update(ten.name.split(".")[0] for ten in nut.names)
        elif isinstance(nut, ast.ImportFrom):
            cac_module.add(nut.module.split(".")[0])
    assert cac_module <= {"hashlib", "unicodedata", "datetime", "pathlib", "pandas"}


def test_sinh_hai_lan_ra_giong_het():
    assert data_builder.dung_du_lieu_shopee() == data_builder.dung_du_lieu_shopee()
    assert data_builder.dung_du_lieu_tiktok() == data_builder.dung_du_lieu_tiktok()


# ---------- Shopee ----------

def test_shopee_so_don_so_dong(shopee, mat_hang_shopee, csv_shopee):
    assert len(shopee["don_hang"]) == csv_shopee["Mã đơn hàng"].nunique() == 1761
    assert len(mat_hang_shopee) == len(csv_shopee) == 1774
    assert list(shopee["escrow"]) == list(shopee["don_hang"])
    assert sum(len(e["order_income"]["items"]) for e in shopee["escrow"].values()) == 1774


def test_shopee_bao_toan_tien_va_so_luong(shopee, mat_hang_shopee, csv_shopee):
    so_luong = cot_so(csv_shopee, "Số lượng")
    assert sum(m["model_quantity_purchased"] for m in mat_hang_shopee) == so_luong.sum()
    assert (sum(m["model_original_price"] * m["model_quantity_purchased"] for m in mat_hang_shopee)
            == (cot_so(csv_shopee, "Giá gốc") * so_luong).sum())
    assert sum(m["model_discounted_price"] for m in mat_hang_shopee) == cot_so(csv_shopee, "Giá ưu đãi").sum()
    assert (sum(i["seller_discount"] for e in shopee["escrow"].values() for i in e["order_income"]["items"])
            == cot_so(csv_shopee, "Người bán trợ giá").sum())
    assert sum(m["returned_qty"] for m in mat_hang_shopee) == 56


def test_shopee_trang_thai(shopee, mat_hang_shopee, csv_shopee):
    so_dong = Counter(m["order_status"] for m in mat_hang_shopee)
    assert so_dong["COMPLETED"] == 769          # 750 + 19 dòng rỗng (§6.4)
    assert so_dong["CANCELLED"] == 544
    assert set(so_dong) == {"COMPLETED", "CANCELLED", "SHIPPED", "TO_CONFIRM_RECEIVE", "PROCESSED", "UNPAID"}
    don_rong = csv_shopee.loc[csv_shopee["Trạng Thái Đơn Hàng"].isna(), "Mã đơn hàng"]
    assert {shopee["don_hang"][ma]["order_status"] for ma in don_rong} == {"COMPLETED"}


def test_shopee_thoi_gian(shopee, csv_shopee):
    dong_dau = csv_shopee.drop_duplicates("Mã đơn hàng")
    for _, dong in dong_dau.iterrows():
        don = shopee["don_hang"][dong["Mã đơn hàng"]]
        gio_tao = datetime.fromtimestamp(don["create_time"], GIO_VN)
        assert gio_tao.strftime("%Y/%m/%d") == dong["Ngày đặt hàng"]
        assert f"{gio_tao.hour}H - {gio_tao.hour + 1}H" == dong["Khung Giờ Ra Đơn"]
        assert (gio_tao.minute, gio_tao.second) == (0, 0)
        assert don["update_time"] >= don["create_time"]

    # Đơn đầu tiên có giờ hoàn thành: update_time đúng bằng giờ đó.
    hoan_thanh = dong_dau[dong_dau["Thời gian hoàn thành đơn hàng"].str.strip() != ""].iloc[0]
    mong_doi = datetime.strptime(hoan_thanh["Thời gian hoàn thành đơn hàng"], "%Y-%m-%d %H:%M").replace(tzinfo=GIO_VN)
    assert shopee["don_hang"][hoan_thanh["Mã đơn hàng"]]["update_time"] == int(mong_doi.timestamp())


def test_shopee_id_gia_on_dinh_va_khop_escrow(shopee, mat_hang_shopee):
    # Trong một đơn, (item_id, model_id) không trùng — escrow ghép với item_list được.
    for don in shopee["don_hang"].values():
        cap_id = [(m["item_id"], m["model_id"]) for m in don["item_list"]]
        assert len(cap_id) == len(set(cap_id))
        cap_id_escrow = [(i["item_id"], i["model_id"]) for i in shopee["escrow"][don["order_sn"]]["order_income"]["items"]]
        assert cap_id_escrow == cap_id
    # Cùng SKU sản phẩm → cùng item_id ở mọi đơn.
    id_theo_sku = defaultdict(set)
    for m in mat_hang_shopee:
        if m["item_sku"]:
            id_theo_sku[m["item_sku"]].add(m["item_id"])
    assert all(len(cac_id) == 1 for cac_id in id_theo_sku.values())


def test_shopee_sku_rong_va_tinh(shopee, mat_hang_shopee, csv_shopee):
    # 6 dòng rỗng `SKU sản phẩm` → item_sku "" (không phải "nan"), model_sku vẫn có.
    sku_rong = [m for m in mat_hang_shopee if m["item_sku"] == ""]
    assert len(sku_rong) == 6
    assert all(m["model_sku"] for m in sku_rong)
    tinh_csv = csv_shopee.drop_duplicates("Mã đơn hàng").set_index("Mã đơn hàng")["Tỉnh/Thành phố"]
    assert {ma: don["recipient_address"]["state"] for ma, don in shopee["don_hang"].items()} == tinh_csv.to_dict()


# ---------- TikTok ----------

def test_tiktok_so_don_theo_shop(tiktok, don_tiktok, csv_tiktok):
    assert len(don_tiktok) == csv_tiktok["Order ID"].nunique() == 7526
    so_don_csv = csv_tiktok.groupby("Shop")["Order ID"].nunique().to_dict()
    assert {ten: len(shop["don_hang"]) for ten, shop in tiktok.items()} == so_don_csv
    assert tiktok["Shop A"]["shop_cipher"] != tiktok["Shop B"]["shop_cipher"]


def test_tiktok_tach_line_item_bao_toan_tung_dong(don_tiktok, csv_tiktok):
    """Gộp lại các line item cùng (đơn, sku_id) phải ra đúng dòng CSV — cả 7.540 dòng."""
    gop = defaultdict(lambda: Counter())
    for don in don_tiktok:
        for li in don["line_items"]:
            khoa = (don["id"], li["sku_id"])
            gop[khoa]["so_luong"] += 1
            for truong in ["original_price", "seller_discount", "platform_discount", "sale_price"]:
                gop[khoa][truong] += int(li[truong])

    assert len(gop) == len(csv_tiktok) == 7540
    assert sum(g["so_luong"] for g in gop.values()) == cot_so(csv_tiktok, "Quantity").sum() == 7636
    cot_tuong_ung = {
        "so_luong": "Quantity",
        "original_price": "SKU Subtotal Before Discount",
        "seller_discount": "SKU Seller Discount",
        "platform_discount": "SKU Platform Discount",
        "sale_price": "SKU Subtotal After Discount",
    }
    for _, dong in csv_tiktok.iterrows():
        g = gop[(dong["Order ID"], dong["SKU ID"])]
        for truong, ten_cot in cot_tuong_ung.items():
            assert g[truong] == int(dong[ten_cot]), (dong["Order ID"], truong)


def test_tiktok_phan_du_don_vao_line_item_dau(don_tiktok, csv_tiktok):
    so_luong = cot_so(csv_tiktok, "Quantity")
    giam = cot_so(csv_tiktok, "SKU Seller Discount")
    dong_du = csv_tiktok[giam % so_luong != 0]
    assert len(dong_du) == 2                     # §17.8
    dong = dong_du.iloc[0]
    don = next(d for d in don_tiktok if d["id"] == dong["Order ID"])
    cac_phan = [int(li["seller_discount"]) for li in don["line_items"] if li["sku_id"] == dong["SKU ID"]]
    assert cac_phan[0] > cac_phan[1]
    assert len(set(cac_phan[1:])) == 1


def test_tiktok_truong_muc_don(don_tiktok, csv_tiktok):
    dong_dau = csv_tiktok.drop_duplicates("Order ID").set_index("Order ID")
    for don in don_tiktok:
        dong = dong_dau.loc[don["id"]]
        gio_tao = datetime.strptime(dong["Created Time"], "%d/%m/%Y %H:%M:%S").replace(tzinfo=GIO_VN)
        assert don["create_time"] == int(gio_tao.timestamp())
        assert don["update_time"] >= don["create_time"]
        assert don["payment"]["total_amount"] == dong["Order Amount"]
        assert don["recipient_address"]["district_info"] == [{"address_level": "L1", "address_name": dong["Province"]}]
    assert Counter(d["status"] for d in don_tiktok) == {
        "COMPLETED": dong_dau["Order Status"].eq("Đã hoàn tất").sum(),
        "CANCELLED": dong_dau["Order Status"].eq("Đã hủy").sum(),
        "IN_TRANSIT": dong_dau["Order Status"].eq("Đã vận chuyển").sum(),
        "AWAITING_SHIPMENT": dong_dau["Order Status"].eq("Cần vận chuyển").sum(),
    }


def test_tiktok_moi_truong_tien_la_chuoi(don_tiktok):
    """Tài liệu TikTok ghi mọi trường tiền kiểu string (Get Order List.md)."""
    for don in don_tiktok:
        assert isinstance(don["payment"]["total_amount"], str)
        for li in don["line_items"]:
            assert all(isinstance(li[t], str) for t in ["original_price", "seller_discount", "platform_discount", "sale_price"])


def test_tiktok_finance_dung_139_dong_hoan(tiktok, don_tiktok, csv_tiktok):
    dong_hoan = csv_tiktok[csv_tiktok["Cancelation/Return Type"] == "Return/Refund"]
    mong_doi = {
        (dong["Order ID"], dong["SKU ID"]): str(-int(dong["SKU Subtotal Before Discount"]))
        for _, dong in dong_hoan.iterrows()
    }
    thuc_te = {}
    for shop in tiktok.values():
        for ma_don, giao_dich in shop["finance"].items():
            for gd in giao_dich:
                khoan_hoan = gd["revenue_breakdown"]["refund_subtotal_before_discount_amount"]
                assert isinstance(khoan_hoan, str)
                if khoan_hoan != "0":
                    thuc_te[(ma_don, gd["sku_id"])] = khoan_hoan
    assert len(thuc_te) == 139
    assert thuc_te == mong_doi


def test_tiktok_finance_chi_co_cho_don_completed(tiktok):
    for shop in tiktok.values():
        don_completed = {ma for ma, don in shop["don_hang"].items() if don["status"] == "COMPLETED"}
        assert set(shop["finance"]) == don_completed
        # Mỗi dòng CSV của đơn đó có đúng một giao dịch SKU.
        for ma_don, giao_dich in shop["finance"].items():
            sku_trong_don = {li["sku_id"] for li in shop["don_hang"][ma_don]["line_items"]}
            assert sorted(gd["sku_id"] for gd in giao_dich) == sorted(sku_trong_don)


# ---------- Affiliate (§21.4) ----------

def test_shopee_affiliate_dung_771_dong_764_don(shopee, csv_shopee):
    aff = csv_shopee["Nguồn Doanh Thu"].fillna("").str.strip()
    la_aff = (aff != "") & (aff != "ADS")
    dong_aff = csv_shopee[la_aff]
    assert len(dong_aff) == 771                                      # §17.8
    assert set(shopee["affiliate"]) == set(dong_aff["Mã đơn hàng"])
    assert len(shopee["affiliate"]) == 764
    # Cờ đồng nhất theo đơn: không đơn nào vừa có dòng affiliate vừa có dòng tự bán.
    assert csv_shopee.assign(aff=la_aff).groupby("Mã đơn hàng")["aff"].nunique().max() == 1
    # Mốc thời gian là create_time của chính đơn.
    assert all(shopee["don_hang"][ma]["create_time"] == tg for ma, tg in shopee["affiliate"].items())


def test_tiktok_affiliate_dung_4297_dong_theo_tung_shop(tiktok, csv_tiktok):
    aff = csv_tiktok["Nguồn Doanh Thu"].fillna("").str.strip()
    dong_aff = csv_tiktok[(aff != "") & (aff != "Inhouse")]
    mong_doi = {(dong["Order ID"], dong["SKU ID"]) for _, dong in dong_aff.iterrows()}
    thuc_te = {(ma, sku_id) for shop in tiktok.values() for ma, muc in shop["affiliate"].items() for sku_id in muc["skus"]}
    assert len(mong_doi) == len(thuc_te) == 4297
    assert thuc_te == mong_doi
    so_dong_theo_shop = {ten: sum(len(m["skus"]) for m in shop["affiliate"].values()) for ten, shop in tiktok.items()}
    assert so_dong_theo_shop == {"Shop A": 2763, "Shop B": 1534}
    # Đơn chỉ nằm ở shop của nó.
    for shop in tiktok.values():
        assert set(shop["affiliate"]) <= set(shop["don_hang"])


def test_nguon_tu_ban_va_o_rong_khong_phai_affiliate():
    assert not data_builder.la_dong_affiliate({"Nguồn Doanh Thu": ""}, "ADS")
    assert not data_builder.la_dong_affiliate({"Nguồn Doanh Thu": "ADS"}, "ADS")
    assert data_builder.la_dong_affiliate({"Nguồn Doanh Thu": "AFF_Video"}, "ADS")
