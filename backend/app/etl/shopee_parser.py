"""Đọc file CSV Shopee → DataFrame cột chuẩn (SPEC §5.1) — đường nạp file dự phòng.

Luồng: đọc đúng 14 cột cần dùng → dựng cột sku theo chuỗi dự phòng → tính
từng cột chuẩn bằng các hàm có sẵn trong cleaners.py / status_mapper.py →
đếm 5 chỉ số chất lượng dữ liệu (§3.3).

Kết quả của parser này là "đáp án" cho test khứ hồi của đường API (§21.5), nên
mọi số liệu phải khớp §17 trước khi làm đường API.
"""

import pandas as pd

from app.etl import cleaners
from app.etl.loader import COT_CHUAN_SHOPEE
from app.etl.status_mapper import TRANG_THAI_KHONG_XAC_DINH, gom_nhom_trang_thai_file

# Chỉ đọc các cột này (usecols), vì 2 lý do:
# - File gốc có 14 cột thông tin cá nhân (§5.1). Không đọc thì PII không bao
#   giờ vào bộ nhớ, nên không có đường nào lọt xuống CSDL.
# - Tên viết ĐÚNG chính tả gốc, kể cả chữ hoa/thường. CẤM .lower() tên cột:
#   file có 2 cột "Tổng số tiền Người mua thanh toán" (cột 34, mức dòng) và
#   "Tổng số tiền người mua thanh toán" (cột 50, mức đơn), .lower() làm chúng
#   đè lên nhau mà không báo lỗi (§5.1 CẢNH BÁO 1). Parser không cần cột nào
#   trong 2 cột đó.
# KHÔNG đọc `NMV`, `NMV Sau Thuế`: công thức Lark sai ở dòng số lượng > 1 (§7.5).
COT_CAN_DOC = [
    "Mã đơn hàng",
    "Ngày đặt hàng",
    "Trạng Thái Đơn Hàng",
    "SKU sản phẩm",
    "SKU phân loại hàng",
    "Tên sản phẩm",
    "Tên phân loại hàng",
    "Số lượng",
    "Số lượng sản phẩm được hoàn trả",
    "Giá gốc",
    "Người bán trợ giá",
    "Nguồn Doanh Thu",
    "Tỉnh/Thành phố",
    "Khung Giờ Ra Đơn",
]

# Giá trị cuối của chuỗi dự phòng sku (§5.1), khi cả 2 cột SKU đều rỗng.
SKU_KHONG_XAC_DINH = "UNKNOWN"

# Nguồn doanh thu "shop tự bán" của Shopee. Giá trị khác (AFF_*) là affiliate;
# ô rỗng KHÔNG phải affiliate (§21.4).
NGUON_TU_BAN_SHOPEE = "ADS"


def doc_csv_shopee(duong_dan):
    """Đọc các cột cần dùng của file CSV Shopee.

    Nhận: đường dẫn file CSV xuất từ Seller Center (utf-8-sig).
    Trả: DataFrame chỉ gồm COT_CAN_DOC, mọi ô là chuỗi, ô rỗng là NaN.
    Cần hàm này để gom cách đọc file vào một chỗ: sai một tham số ở đây
    (đoán kiểu số, đổi tên cột) là sai toàn bộ số liệu phía sau.
    """
    # dtype=str: không để pandas tự đoán kiểu. Việc đổi số do cleaners làm,
    # có kiểm lỗi (§17.7c). Ô rỗng vẫn thành NaN — đúng kiểu cleaners chờ nhận.
    # Thiếu cột nào trong COT_CAN_DOC thì pandas báo ValueError ngay.
    return pd.read_csv(duong_dan, usecols=COT_CAN_DOC, dtype=str, encoding="utf-8-sig")


def lam_sach_o_sku(cot_sku):
    """Bỏ khoảng trắng hai đầu SKU, coi ô chỉ có khoảng trắng là rỗng.

    Nhận: Series SKU thô (cột `SKU sản phẩm` hoặc `SKU phân loại hàng`).
    Trả: Series SKU đã strip. Ô rỗng / chỉ có khoảng trắng → NaN.
    Cần hàm này vì chuỗi dự phòng chỉ chuyển sang cột kế khi ô rỗng thật. Ô
    "   " sau strip thành "" — không phải NaN nên sẽ lọt qua làm một SKU rỗng.
    API Shopee cũng trả "" khi chưa đặt SKU, nên 2 đường phải xử lý giống nhau.
    """
    sku_da_strip = cot_sku.str.strip()
    # mask(điều kiện) thay ô thỏa điều kiện bằng NaN; NaN vẫn giữ là NaN.
    return sku_da_strip.mask(sku_da_strip == "")


def dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai):
    """Dựng cột sku theo chuỗi dự phòng của SPEC §5.1.

    Nhận: 2 Series đã qua lam_sach_o_sku — `SKU sản phẩm`, `SKU phân loại hàng`.
    Trả: Series sku không còn NaN: lấy `SKU sản phẩm`; rỗng thì lấy
    `SKU phân loại hàng`; cả hai rỗng thì "UNKNOWN".
    Cần hàm này vì sku là khóa chống trùng và NOT NULL (§4.1). Dữ liệu thật có
    6 dòng `SKU sản phẩm` rỗng, cột dự phòng cho ra `M21 live`.
    """
    # Đây là CHỖ DUY NHẤT điền giá trị cho sku rỗng (§5.1 CẢNH BÁO 2). Trước
    # đây NaN phải còn là NaN: ép .astype(str) sớm thì pandas 2.2 biến NaN
    # thành chuỗi "nan", fillna không còn gì để điền và sinh 1 SKU giả (§17.7b).
    sku_sau_du_phong = sku_san_pham.fillna(sku_phan_loai)
    return sku_sau_du_phong.fillna(SKU_KHONG_XAC_DINH)


def tinh_nmv_shopee(gia_goc, so_luong, nguoi_ban_tro_gia):
    """Tính NMV mức dòng của Shopee: Giá gốc × Số lượng − Người bán trợ giá (§7.5).

    Nhận: 3 Series số cùng độ dài.
    Trả: Series NMV (VND).
    Cần hàm này vì KHÔNG dùng được cột `NMV` của file: Lark tính
    `Giá gốc − Người bán trợ giá`, trong khi `Giá gốc` là giá 1 sản phẩm còn
    `Người bán trợ giá` là tổng của cả dòng. Ở 22 dòng số lượng > 1, Lark ra
    số sai (ví dụ khách trả 2.800.000 nhưng NMV ghi 520.000).
    """
    gia_tri_theo_gia_goc = gia_goc * so_luong
    return gia_tri_theo_gia_goc - nguoi_ban_tro_gia


def tao_bang_chuan(bang_goc, sku, ten_shop):
    """Tính toàn bộ cột chuẩn của bảng orders_shopee từ các cột đã đọc.

    Nhận: bang_goc — kết quả doc_csv_shopee; sku — kết quả chuỗi dự phòng;
    ten_shop — tên gian hàng (file Shopee không có cột shop).
    Trả: DataFrame đúng và đủ các cột COT_CHUAN_SHOPEE, theo đúng thứ tự đó,
    cùng chỉ số dòng với file (dòng i của kết quả là dòng i của file).
    Cần hàm này để mọi quy tắc ánh xạ cột của §5.1 nằm ở một chỗ, đọc từ trên
    xuống là thấy cột nào lấy từ đâu.
    """
    bang_san_pham = cleaners.doc_file_anh_xa("product_map.json")["shopee"]
    bang_tinh = cleaners.doc_file_anh_xa("province_map.json")

    so_luong = pd.to_numeric(bang_goc["Số lượng"], errors="raise")
    so_luong_hoan = pd.to_numeric(bang_goc["Số lượng sản phẩm được hoàn trả"], errors="raise")
    # `Giá gốc` ghi bằng ký hiệu khoa học ở 100% dòng ("2.28e+06") — §5.1.
    gia_goc = cleaners.doi_chuoi_tien_sang_so(bang_goc["Giá gốc"])
    nguoi_ban_tro_gia = cleaners.doi_chuoi_tien_sang_so(bang_goc["Người bán trợ giá"])
    nmv = tinh_nmv_shopee(gia_goc, so_luong, nguoi_ban_tro_gia)

    bang_chuan = pd.DataFrame(index=bang_goc.index)
    bang_chuan["shop_name"] = ten_shop
    bang_chuan["order_id"] = bang_goc["Mã đơn hàng"]
    bang_chuan["sku"] = sku
    bang_chuan["product_code"] = cleaners.tra_ma_san_pham(sku, bang_san_pham)
    bang_chuan["order_date"] = cleaners.doc_ngay_shopee(bang_goc["Ngày đặt hàng"])
    # File Shopee chỉ có ngày, không có giờ tạo đơn → NULL (§3 bổ sung 11/10).
    bang_chuan["order_created_at"] = pd.Series(pd.NaT, index=bang_goc.index, dtype="datetime64[ns]")
    bang_chuan["order_status_raw"] = bang_goc["Trạng Thái Đơn Hàng"]
    bang_chuan["order_status"] = bang_goc["Trạng Thái Đơn Hàng"].apply(
        gom_nhom_trang_thai_file, args=("shopee",)
    )
    # Shopee: số lượng hoàn > 0 khớp đúng 56/56 dòng hoàn (§3.2), dùng được.
    bang_chuan["is_returned"] = so_luong_hoan > 0
    bang_chuan["product_name"] = bang_goc["Tên sản phẩm"]
    bang_chuan["variation"] = bang_goc["Tên phân loại hàng"]
    bang_chuan["quantity"] = so_luong
    bang_chuan["returned_quantity"] = so_luong_hoan
    bang_chuan["unit_price"] = gia_goc
    bang_chuan["nmv"] = nmv
    bang_chuan["nmv_after_tax"] = cleaners.tinh_nmv_sau_thue(nmv)
    # Đường file có đủ `Người bán trợ giá` nên NMV là số chính xác, không tạm
    # tính. Chỉ đường API mới có trường hợp chưa có escrow (§7.5).
    bang_chuan["nmv_is_provisional"] = False
    bang_chuan["is_affiliate"] = cleaners.xac_dinh_affiliate(bang_goc["Nguồn Doanh Thu"], NGUON_TU_BAN_SHOPEE)
    bang_chuan["province"] = bang_goc["Tỉnh/Thành phố"].apply(
        cleaners.normalize_province, args=(bang_tinh,)
    )
    # Giữ bản gốc để truy vết khi bảng tỉnh tra sai (§5.3 "Bắt buộc").
    bang_chuan["province_raw"] = bang_goc["Tỉnh/Thành phố"]
    # Không có giờ tạo đơn để tự tính, nên lấy thẳng cột của file. Cột này
    # khớp giờ `create_time` của API thật ở 275/275 dòng (§17.8).
    bang_chuan["hour_bucket"] = bang_goc["Khung Giờ Ra Đơn"]
    bang_chuan["data_source"] = "file"

    return bang_chuan[COT_CHUAN_SHOPEE]


def chuan_hoa_file_shopee(duong_dan, ten_shop):
    """Chuẩn hóa một file CSV Shopee thành dữ liệu sẵn sàng nạp CSDL.

    Nhận: duong_dan — đường dẫn file CSV; ten_shop — tên gian hàng, do nơi
    gọi truyền vào vì file Shopee không có cột shop (mặc định khi nạp file
    là "Shop C", §5.1).
    Trả: tuple (DataFrame cột chuẩn COT_CHUAN_SHOPEE, dict 5 bộ đếm chất
    lượng của §3.3 — khóa trùng tên cột của bảng sync_runs).
    Cần hàm này làm cửa vào duy nhất của đường file Shopee: thư mục quét và
    nút tải file (§2.4) đều gọi hàm này.
    """
    bang_goc = doc_csv_shopee(duong_dan)

    sku_san_pham = lam_sach_o_sku(bang_goc["SKU sản phẩm"])
    sku_phan_loai = lam_sach_o_sku(bang_goc["SKU phân loại hàng"])
    sku = dien_sku_theo_chuoi_du_phong(sku_san_pham, sku_phan_loai)

    bang_chuan = tao_bang_chuan(bang_goc, sku, ten_shop)

    # Các quy tắc §5–§6 sửa dữ liệu bẩn âm thầm (điền dự phòng, gán "Khác",
    # gán "unknown"). Đếm lại ở đây để lỗi dữ liệu không bị che mất (§3.3).
    dung_sku_du_phong = sku_san_pham.isna() & sku_phan_loai.notna()
    khong_co_sku = sku_san_pham.isna() & sku_phan_loai.isna()
    bo_dem = {
        "rows_sku_fallback": int(dung_sku_du_phong.sum()),
        "rows_sku_unknown": int(khong_co_sku.sum()),
        "rows_status_unknown": int((bang_chuan["order_status"] == TRANG_THAI_KHONG_XAC_DINH).sum()),
        "rows_province_unmapped": int((bang_chuan["province"] == cleaners.TINH_KHONG_XAC_DINH).sum()),
        "rows_product_unmapped": int(bang_chuan["product_code"].isna().sum()),
    }
    return bang_chuan, bo_dem
