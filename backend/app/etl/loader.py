"""Ghi dữ liệu đã chuẩn hóa vào CSDL — chỗ hội tụ duy nhất của mọi đường (SPEC §4, §13).

File gồm 2 phần:
1. HỢP ĐỒNG ĐẦU RA: danh sách cột chuẩn của 2 bảng đơn hàng (COT_CHUAN_*).
2. upsert_don_hang(): ghi DataFrame cột chuẩn vào bảng bằng
   INSERT ... ON CONFLICT (order_id, sku) DO UPDATE.

Luồng của upsert_don_hang: kiểm cột và khóa trùng → đổi giá trị pandas/numpy
sang kiểu Python → chia lô 1.000 dòng → mỗi lô một lệnh upsert, đếm dòng thêm
mới / cập nhật từ RETURNING. Hàm KHÔNG commit — nơi gọi quyết định giao dịch.

Vì sao khai báo danh sách cột ở đây: có 4 module chuẩn hóa (2 parser CSV, 2
transform API) và chúng chỉ chung nhau đúng một thứ — DataFrame đầu ra phải có
đủ và đúng các cột này. Khai báo một lần ở nơi nhận dữ liệu thì cả 4 module
cùng nhìn vào một chỗ, và test khứ hồi (§21.5) so được từng cột giữa 2 đường.
Không cần lớp cơ sở cho parser (§13 "Không còn base_parser.py", §0.3).

Cột của bảng (§3.1, §3.2) KHÔNG có trong danh sách, vì module chuẩn hóa không
tạo ra chúng:
- `id`, `uploaded_at`, `updated_at`: CSDL tự sinh / upsert tự đặt (§4).
- `source_file`: tên file chỉ nơi gọi biết (thư mục quét, nút tải file);
  đường API không có. Để ngoài danh sách thì 2 đường vẫn so được từng cột.
"""

import pandas as pd
from sqlalchemy import func, literal_column
from sqlalchemy.dialects.postgresql import insert

from app.models.order_shopee import OrderShopee
from app.models.order_tiktok import OrderTiktok

# Thứ tự cột theo đúng thứ tự trong CREATE TABLE ở SPEC §3.1.
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

# Theo thứ tự CREATE TABLE ở SPEC §3.2. Khác Shopee 3 chỗ: có
# `sku_subtotal_after_discount` và `order_amount` (MỨC ĐƠN — CẤM SUM theo
# dòng, §7.4); không có `nmv_is_provisional` vì TikTok không có NMV tạm tính.
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


# Model và danh sách cột chuẩn của từng sàn.
BANG_THEO_SAN = {
    "shopee": (OrderShopee, COT_CHUAN_SHOPEE),
    "tiktok": (OrderTiktok, COT_CHUAN_TIKTOK),
}

# Hai cột tạo nên khóa chống trùng (§4). Không đưa vào SET của DO UPDATE:
# dòng đã khớp khóa thì 2 cột này vốn bằng nhau.
COT_KHOA = ["order_id", "sku"]

# Số dòng mỗi lệnh INSERT gửi xuống CSDL. PostgreSQL giới hạn 65.535 tham số
# trong một lệnh; mỗi dòng TikTok tốn 24 tham số (23 cột chuẩn + source_file),
# nên một lệnh chứa tối đa ~2.700 dòng. 1.000 dòng/lô (24.000 tham số) cách xa
# giới hạn đó, mà file mẫu lớn nhất (7.540 dòng) vẫn chỉ cần 8 lệnh. Lô quá nhỏ
# (vd 1 dòng) thì 7.540 lượt gửi qua mạng — chậm hẳn mà không được gì.
CO_LO_GHI = 1000


def kiem_cot_va_khoa(bang_chuan, cot_chuan):
    """Kiểm DataFrame đúng hợp đồng trước khi ghi bất cứ gì.

    Nhận: DataFrame cột chuẩn; danh sách cột chuẩn của sàn (COT_CHUAN_*).
    Trả: không trả gì; sai thì raise ValueError nói rõ sai ở đâu.
    Cần hàm này vì 2 lỗi dưới đây, nếu để tới CSDL mới lộ, sẽ ra thông báo khó
    hiểu hoặc — tệ hơn — không ra lỗi nào:
    - Thiếu/thừa cột: cột thừa bị bỏ qua im lặng, cột thiếu thành NULL.
    - Trùng (order_id, sku) ngay trong DataFrame: PostgreSQL báo "ON CONFLICT
      DO UPDATE command cannot affect row a second time", không nói dòng nào.
    """
    cot_thieu = set(cot_chuan) - set(bang_chuan.columns)
    cot_thua = set(bang_chuan.columns) - set(cot_chuan)
    if cot_thieu or cot_thua:
        raise ValueError(
            f"DataFrame không đúng cột chuẩn — thiếu {sorted(cot_thieu)}, thừa {sorted(cot_thua)}. "
            "Không ghi dòng nào."
        )

    dong_trung = bang_chuan.duplicated(COT_KHOA, keep=False)
    if dong_trung.any():
        khoa_trung = bang_chuan.loc[dong_trung, COT_KHOA].drop_duplicates()
        raise ValueError(
            f"Có {len(khoa_trung)} cặp (order_id, sku) lặp lại trong cùng dữ liệu, ví dụ "
            f"{khoa_trung.head(3).values.tolist()}. Không ghi dòng nào."
        )


def doi_thoi_diem_sang_python(cot_thoi_diem):
    """Đổi cột datetime của pandas sang datetime của Python.

    Nhận: Series kiểu datetime64 (có thể có NaT).
    Trả: Series kiểu object gồm datetime.datetime hoặc None.
    Cần hàm này vì giá trị trong cột là pandas.Timestamp — một lớp con của
    datetime nhưng có thêm phần nano giây. Đổi tường minh thì biết chắc thứ
    gửi xuống CSDL là kiểu chuẩn của Python, không phụ thuộc thư viện kết nối
    có nhận lớp con hay không.
    """
    gia_tri_moi = []
    for thoi_diem in cot_thoi_diem:
        if pd.isna(thoi_diem):
            gia_tri_moi.append(None)
        else:
            gia_tri_moi.append(thoi_diem.to_pydatetime())
    return pd.Series(gia_tri_moi, index=cot_thoi_diem.index, dtype=object)


def doi_sang_dong_python(bang_chuan):
    """Đổi DataFrame cột chuẩn thành danh sách dict, mỗi dict một dòng, toàn kiểu Python.

    Nhận: DataFrame đã qua kiem_cot_va_khoa.
    Trả: list[dict] — số nguyên/thực/bool của Python, date, datetime, str; ô
    thiếu (NaN, NaT) thành None (NULL trong CSDL).
    Cần hàm này vì NaN của numpy là một SỐ: gửi thẳng xuống thì cột tiền nhận
    giá trị 'NaN' thay vì NULL, cột chữ lỗi kiểu. Đã kiểm: sau astype(object),
    số và bool thành kiểu Python, chỉ còn 2 cột thời gian là kiểu pandas.
    """
    bang_ghi = bang_chuan.astype(object)
    # Cột DATE của CSDL nhận datetime.date; parser giữ kiểu ngày-giờ lúc 0h.
    bang_ghi["order_date"] = bang_chuan["order_date"].dt.date
    bang_ghi["order_created_at"] = doi_thoi_diem_sang_python(bang_chuan["order_created_at"])
    # Ô nào thiếu ở bảng GỐC (NaN, NaT) thì thành None. Dùng điều kiện từ bảng
    # gốc vì sau khi đổi kiểu, một số ô thiếu đã đổi dạng (NaT → None ở trên).
    bang_ghi = bang_ghi.where(bang_chuan.notna(), None)
    return bang_ghi.to_dict("records")


def tao_lenh_upsert(model, cot_chuan):
    """Dựng lệnh INSERT ... ON CONFLICT (order_id, sku) DO UPDATE ... RETURNING.

    Nhận: model của bảng; danh sách cột chuẩn của sàn.
    Trả: lệnh SQLAlchemy chưa chạy, CHƯA gắn dữ liệu — dữ liệu truyền vào lúc
    execute.
    Cần hàm này để tách phần "viết SQL gì" khỏi phần "chạy theo lô", đọc riêng
    được từng nửa.

    Vì sao không gắn dữ liệu vào lệnh (.values(lô)): làm vậy thì mỗi lô là một
    câu SQL khác nhau 24.000 tham số, SQLAlchemy phải biên dịch lại từng lô.
    Đã đo trên file TikTok: ~15 giây/lần nạp, trong đó biên dịch ~0,7 giây/lô.
    Dựng lệnh một lần rồi truyền danh sách dòng lúc execute thì SQLAlchemy biên
    dịch một lần, tự ghép các dòng thành INSERT nhiều VALUES — ~4 giây/lần nạp.
    """
    lenh_insert = insert(model)

    # `excluded` là dòng VỪA ĐỊNH CHÈN nhưng bị trùng khóa — PostgreSQL đặt
    # sẵn tên này trong ON CONFLICT. SET cột = excluded.cột nghĩa là "lấy giá
    # trị mới từ file/API đè lên giá trị cũ".
    cot_cap_nhat = {}
    for ten_cot in cot_chuan + ["source_file"]:
        if ten_cot not in COT_KHOA:
            cot_cap_nhat[ten_cot] = lenh_insert.excluded[ten_cot]
    # Đánh dấu lần ghi gần nhất. KHÔNG đặt id và uploaded_at trong SET: id giữ
    # nguyên dòng cũ, uploaded_at giữ nghĩa "lần đầu xuất hiện" (§4).
    cot_cap_nhat["updated_at"] = func.now()

    lenh_upsert = lenh_insert.on_conflict_do_update(
        index_elements=COT_KHOA,
        set_=cot_cap_nhat,
    )
    # Đếm thêm mới / cập nhật bằng cột hệ thống ẩn `xmax` — chi tiết RIÊNG
    # của PostgreSQL, không phải SQL chuẩn (§4):
    # - Mỗi phiên bản dòng có xmax = mã giao dịch đã xóa hoặc khóa nó; 0 = chưa
    #   ai đụng tới. Dòng vừa INSERT mới tinh → xmax = 0.
    # - Nhánh DO UPDATE phải khóa dòng cũ trước khi sửa, nên phiên bản mới mang
    #   xmax = mã giao dịch hiện tại → khác 0.
    # Đây là mẹo dựa trên cách PostgreSQL cài đặt bên trong, được dùng rộng rãi
    # nhưng tài liệu chính thức không cam kết. Vẫn dùng vì ON CONFLICT không có
    # cách nào khác cho biết dòng nào thêm mới; test DB kiểm lại con số này.
    la_dong_moi = literal_column("(xmax = 0)").label("la_dong_moi")
    return lenh_upsert.returning(la_dong_moi)


def upsert_don_hang(phien, san, bang_chuan, source_file):
    """Ghi DataFrame cột chuẩn vào orders_shopee / orders_tiktok bằng upsert (SPEC §4).

    Nhận: phien — Session SQLAlchemy đang mở; san — "shopee" hoặc "tiktok";
    bang_chuan — DataFrame ĐÚNG và ĐỦ COT_CHUAN_* của sàn; source_file — tên
    file nguồn, hoặc None (đường API).
    Trả: tuple (số dòng thêm mới, số dòng cập nhật).
    Cần hàm này vì mọi đường đưa dữ liệu vào (file, API) phải ghi theo cùng
    một quy tắc: trùng (order_id, sku) thì CẬP NHẬT — trạng thái đơn đổi theo
    thời gian, DO NOTHING sẽ giữ trạng thái cũ mãi (§4).

    KHÔNG commit: nơi gọi bọc cả lượt (tạo sync_runs, parser, upsert, cập nhật
    sync_runs) trong MỘT giao dịch, lỗi ở đâu thì rollback hết.
    """
    model, cot_chuan = BANG_THEO_SAN[san]
    kiem_cot_va_khoa(bang_chuan, cot_chuan)

    cac_dong = doi_sang_dong_python(bang_chuan)
    for dong in cac_dong:
        dong["source_file"] = source_file

    # insertmanyvalues_page_size: số dòng SQLAlchemy ghép vào MỘT câu INSERT
    # khi nhận cả danh sách dòng. Đặt bằng CO_LO_GHI để mỗi lô đúng một câu.
    lenh_upsert = tao_lenh_upsert(model, cot_chuan).execution_options(
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
