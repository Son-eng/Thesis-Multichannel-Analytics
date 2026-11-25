"""Ghi dữ liệu đã chuẩn hóa vào bảng orders bằng upsert; mọi đường nạp đều đi qua đây."""

import pandas as pd
from sqlalchemy import func, literal_column
from sqlalchemy.dialects.postgresql import insert

from app.models.order import Order

COT_CHUAN_SHOPEE = [
    "shop_name",
    "order_id",
    "sku",
    "product_code",
    "order_date",
    "order_created_at",
    "order_status_raw",
    "order_status",
    "is_returned",
    "product_name",
    "variation",
    "quantity",
    "returned_quantity",
    "unit_price",
    "nmv",
    "nmv_after_tax",
    "nmv_is_provisional",
    "is_affiliate",
    "province",
    "province_raw",
    "hour_bucket",
    "data_source",
]

# Khác Shopee: có order_amount là cột mức đơn, không được SUM theo dòng.
COT_CHUAN_TIKTOK = [
    "shop_name",
    "order_id",
    "sku",
    "product_code",
    "order_date",
    "order_created_at",
    "order_status_raw",
    "order_status",
    "is_returned",
    "product_name",
    "variation",
    "quantity",
    "returned_quantity",
    "unit_price",
    "sku_subtotal_after_discount",
    "nmv",
    "nmv_after_tax",
    "order_amount",
    "is_affiliate",
    "province",
    "province_raw",
    "hour_bucket",
    "data_source",
]


COT_CHUAN_THEO_SAN = {
    "shopee": COT_CHUAN_SHOPEE,
    "tiktok": COT_CHUAN_TIKTOK,
}

# Cột chung của bảng orders; sàn không có cột nào thì nhận giá trị mặc định hoặc NULL.
COT_CHUNG = [
    "shop_name",
    "order_id",
    "sku",
    "product_code",
    "order_date",
    "order_created_at",
    "order_status_raw",
    "order_status",
    "is_returned",
    "product_name",
    "variation",
    "quantity",
    "returned_quantity",
    "unit_price",
    "sku_subtotal_after_discount",
    "nmv",
    "nmv_after_tax",
    "order_amount",
    "nmv_is_provisional",
    "is_affiliate",
    "province",
    "province_raw",
    "hour_bucket",
    "data_source",
]

COT_MAC_DINH = {"nmv_is_provisional": False}

# Khóa chống trùng gồm cả sàn vì mã đơn hai sàn khác hệ.
COT_KHOA = ["platform", "order_id", "sku"]
COT_KHOA_TRONG_BANG = ["order_id", "sku"]

# PostgreSQL giới hạn 65.535 tham số mỗi lệnh; 1.000 dòng một lô là đủ xa giới hạn đó.
CO_LO_GHI = 1000


def kiem_cot_va_khoa(bang_chuan, cot_chuan):
    """Kiểm cột và khóa trùng trước khi ghi, vì để tới CSDL mới lộ thì lỗi khó hiểu hoặc không báo gì."""
    cot_thieu = set(cot_chuan) - set(bang_chuan.columns)
    cot_thua = set(bang_chuan.columns) - set(cot_chuan)
    if cot_thieu or cot_thua:
        raise ValueError(
            f"DataFrame không đúng cột chuẩn — thiếu {sorted(cot_thieu)}, thừa {sorted(cot_thua)}. "
            "Không ghi dòng nào."
        )

    dong_trung = bang_chuan.duplicated(COT_KHOA_TRONG_BANG, keep=False)
    if dong_trung.any():
        khoa_trung = bang_chuan.loc[dong_trung, COT_KHOA_TRONG_BANG].drop_duplicates()
        raise ValueError(
            f"Có {len(khoa_trung)} cặp (order_id, sku) lặp lại trong cùng dữ liệu, ví dụ "
            f"{khoa_trung.head(3).values.tolist()}. Không ghi dòng nào."
        )


def doi_thoi_diem_sang_python(cot_thoi_diem):
    gia_tri_moi = []
    for thoi_diem in cot_thoi_diem:
        if pd.isna(thoi_diem):
            gia_tri_moi.append(None)
        else:
            gia_tri_moi.append(thoi_diem.to_pydatetime())
    return pd.Series(gia_tri_moi, index=cot_thoi_diem.index, dtype=object)


def doi_sang_dong_python(bang_chuan):
    bang_ghi = bang_chuan.astype(object)
    bang_ghi["order_date"] = bang_chuan["order_date"].dt.date
    bang_ghi["order_created_at"] = doi_thoi_diem_sang_python(bang_chuan["order_created_at"])
    bang_ghi = bang_ghi.where(bang_chuan.notna(), None)
    return bang_ghi.to_dict("records")


def tao_lenh_upsert(model):
    """Dựng lệnh một lần và truyền dữ liệu lúc execute để SQLAlchemy không phải biên dịch lại mỗi lô."""
    lenh_insert = insert(model)

    # excluded là dòng vừa định chèn nhưng trùng khóa, tức giá trị mới đè lên giá trị cũ.
    cot_cap_nhat = {}
    for ten_cot in COT_CHUNG + ["source_file"]:
        if ten_cot not in COT_KHOA:
            cot_cap_nhat[ten_cot] = lenh_insert.excluded[ten_cot]
    # Không đặt id và uploaded_at để uploaded_at giữ nghĩa lần đầu xuất hiện.
    cot_cap_nhat["updated_at"] = func.now()

    lenh_upsert = lenh_insert.on_conflict_do_update(
        index_elements=COT_KHOA,
        set_=cot_cap_nhat,
    )
    # xmax = 0 là dòng vừa thêm mới, khác 0 là dòng cập nhật; đây là chi tiết riêng của PostgreSQL.
    la_dong_moi = literal_column("(xmax = 0)").label("la_dong_moi")
    return lenh_upsert.returning(la_dong_moi)


def dua_ve_cot_chung(bang_chuan):
    bang = bang_chuan.reindex(columns=COT_CHUNG)
    for ten_cot, gia_tri in COT_MAC_DINH.items():
        if ten_cot not in bang_chuan.columns:
            bang[ten_cot] = gia_tri
    return bang


def upsert_don_hang(phien, san, bang_chuan, source_file):
    """Trùng (platform, order_id, sku) thì cập nhật vì trạng thái đơn đổi theo thời gian; hàm không commit."""
    kiem_cot_va_khoa(bang_chuan, COT_CHUAN_THEO_SAN[san])

    # Lượt định kỳ không có đơn nào đổi là bình thường, bảng rỗng thì không có gì để ghi.
    if bang_chuan.empty:
        return 0, 0

    cac_dong = doi_sang_dong_python(dua_ve_cot_chung(bang_chuan))
    for dong in cac_dong:
        dong["platform"] = san
        dong["source_file"] = source_file

    # Mỗi lô ghép thành đúng một câu INSERT.
    lenh_upsert = tao_lenh_upsert(Order).execution_options(
        insertmanyvalues_page_size=CO_LO_GHI
    )

    so_dong_moi = 0
    so_dong_cap_nhat = 0
    for vi_tri_dau in range(0, len(cac_dong), CO_LO_GHI):
        lo_dong = cac_dong[vi_tri_dau:vi_tri_dau + CO_LO_GHI]
        ket_qua = phien.execute(lenh_upsert, lo_dong)
        for la_dong_moi in ket_qua.scalars():
            if la_dong_moi:
                so_dong_moi += 1
            else:
                so_dong_cap_nhat += 1
    return so_dong_moi, so_dong_cap_nhat
