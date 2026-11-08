"""Ghi dữ liệu đã chuẩn hóa vào CSDL — chỗ hội tụ duy nhất của mọi đường (SPEC §4, §13).

File gồm 2 phần:
1. HỢP ĐỒNG ĐẦU RA: danh sách cột chuẩn mà mỗi bộ chuẩn hóa của từng sàn trả về
   (COT_CHUAN_*) và danh sách cột CHUNG của bảng `orders` (COT_CHUNG).
2. upsert_don_hang(): ghi DataFrame cột chuẩn của một sàn vào bảng `orders` bằng
   INSERT ... ON CONFLICT (platform, order_id, sku) DO UPDATE.

Từ 08/11/2026 (gộp CSDL theo yêu cầu GVHD, SPEC §3) hai bảng đơn hàng của hai sàn
là MỘT bảng `orders`. Bốn bộ chuẩn hóa không đổi: mỗi bộ vẫn trả DataFrame với
đúng cột của sàn mình; loader đưa về cột chung (cột riêng sàn khác để NULL,
`nmv_is_provisional` mặc định FALSE) và đặt `platform`.

Luồng của upsert_don_hang: kiểm cột và khóa trùng → đưa về cột chung → đổi giá trị
pandas/numpy sang kiểu Python → chia lô 1.000 dòng → mỗi lô một lệnh upsert, đếm
dòng thêm mới / cập nhật từ RETURNING. Hàm KHÔNG commit — nơi gọi quyết định giao dịch.

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

from app.models.order import Order

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


# Danh sách cột chuẩn của từng sàn (hợp đồng của bộ chuẩn hóa sàn đó).
COT_CHUAN_THEO_SAN = {
    "shopee": COT_CHUAN_SHOPEE,
    "tiktok": COT_CHUAN_TIKTOK,
}

# Cột CHUNG của bảng `orders`: hợp (union) của hai danh sách trên, theo thứ tự CREATE TABLE ở SPEC §3.1.
# Cột chỉ một sàn có (`sku_subtotal_after_discount`, `order_amount` của TikTok; `nmv_is_provisional` của Shopee)
# nằm ở đây; sàn không có thì nhận giá trị trong COT_MAC_DINH hoặc NULL.
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

# Giá trị cho cột NOT NULL mà sàn không có (TikTok không có NMV tạm tính → FALSE). Cột khác thiếu thì NULL.
COT_MAC_DINH = {"nmv_is_provisional": False}

# Khóa chống trùng trong CSDL (§4): gồm cả sàn, vì order_id của hai sàn thuộc hai hệ mã khác nhau. Không đưa vào
# SET của DO UPDATE: dòng đã khớp khóa thì các cột này vốn bằng nhau.
COT_KHOA = ["platform", "order_id", "sku"]
# Phần khóa mà DataFrame của MỘT sàn tự có (DataFrame không có cột `platform`): dùng kiểm trùng trong dữ liệu.
COT_KHOA_TRONG_BANG = ["order_id", "sku"]

# Số dòng mỗi lệnh INSERT gửi xuống CSDL. PostgreSQL giới hạn 65.535 tham số
# trong một lệnh; mỗi dòng tốn 26 tham số (24 cột chung + platform + source_file),
# nên một lệnh chứa tối đa ~2.500 dòng. 1.000 dòng/lô (26.000 tham số) cách xa
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

    dong_trung = bang_chuan.duplicated(COT_KHOA_TRONG_BANG, keep=False)
    if dong_trung.any():
        khoa_trung = bang_chuan.loc[dong_trung, COT_KHOA_TRONG_BANG].drop_duplicates()
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


def tao_lenh_upsert(model):
    """Dựng lệnh INSERT ... ON CONFLICT (platform, order_id, sku) DO UPDATE ... RETURNING.

    Nhận: model của bảng `orders`.
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
    for ten_cot in COT_CHUNG + ["source_file"]:
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


def dua_ve_cot_chung(bang_chuan):
    """Đưa DataFrame cột chuẩn của một sàn về đúng bộ cột chung của bảng `orders`.

    Nhận: DataFrame đã qua kiem_cot_va_khoa. Trả: DataFrame có đúng COT_CHUNG, theo thứ tự đó.
    Cột sàn không có: lấy giá trị trong COT_MAC_DINH nếu có (cột NOT NULL), không thì NULL.
    Cần hàm này vì bốn bộ chuẩn hóa chỉ biết cột của sàn mình; việc "bảng chung có thêm cột gì" là chuyện của nơi ghi.
    """
    bang = bang_chuan.reindex(columns=COT_CHUNG)
    for ten_cot, gia_tri in COT_MAC_DINH.items():
        if ten_cot not in bang_chuan.columns:
            bang[ten_cot] = gia_tri
    return bang


def upsert_don_hang(phien, san, bang_chuan, source_file):
    """Ghi DataFrame cột chuẩn của một sàn vào bảng chung `orders` bằng upsert (SPEC §4).

    Nhận: phien — Session SQLAlchemy đang mở; san — "shopee" hoặc "tiktok";
    bang_chuan — DataFrame ĐÚNG và ĐỦ COT_CHUAN_* của sàn; source_file — tên
    file nguồn, hoặc None (đường API).
    Trả: tuple (số dòng thêm mới, số dòng cập nhật).
    Cần hàm này vì mọi đường đưa dữ liệu vào (file, API) phải ghi theo cùng
    một quy tắc: trùng (platform, order_id, sku) thì CẬP NHẬT — trạng thái đơn đổi theo
    thời gian, DO NOTHING sẽ giữ trạng thái cũ mãi (§4).

    KHÔNG commit: nơi gọi bọc cả lượt (tạo sync_runs, parser, upsert, cập nhật
    sync_runs) trong MỘT giao dịch, lỗi ở đâu thì rollback hết.
    """
    kiem_cot_va_khoa(bang_chuan, COT_CHUAN_THEO_SAN[san])

    # Lượt đồng bộ định kỳ không có đơn nào đổi là trường hợp BÌNH THƯỜNG (§20.3):
    # không có gì để ghi. Bảng rỗng không có kiểu datetime nên đi tiếp sẽ lỗi
    # ở bước đổi kiểu (".dt accessor") — phát hiện ở bước 11 khi chạy lượt thứ 2
    # sau backfill. Đã kiểm cột ở trên, nên bảng rỗng SAI cột vẫn bị chặn.
    if bang_chuan.empty:
        return 0, 0

    cac_dong = doi_sang_dong_python(dua_ve_cot_chung(bang_chuan))
    for dong in cac_dong:
        dong["platform"] = san
        dong["source_file"] = source_file

    # insertmanyvalues_page_size: số dòng SQLAlchemy ghép vào MỘT câu INSERT
    # khi nhận cả danh sách dòng. Đặt bằng CO_LO_GHI để mỗi lô đúng một câu.
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
