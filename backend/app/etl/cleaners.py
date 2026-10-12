"""Các hàm làm sạch dùng chung cho mọi đường đưa dữ liệu vào (file CSV và API).

Vì sao gom vào một file: cùng một quy tắc làm sạch (đổi tiền, đọc ngày, chuẩn
hóa tỉnh...) phải cho ra cùng kết quả dù dữ liệu đến từ file hay từ API. Viết
một lần ở đây thì 4 module chuẩn hóa (2 parser CSV + 2 transform API) chỉ việc
gọi, không ai tự viết lại một bản hơi khác.

Mỗi hàm làm đúng một việc (SPEC §0.1). Hàm nào nhận/trả `pd.Series` là để chạy
trên cả cột một lượt; `normalize_province` nhận một chuỗi vì nó phải tra bảng
và ghi log cho từng giá trị lạ.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Thư mục chứa province_map.json, product_map.json. Tính theo vị trí file này,
# không dùng đường dẫn tương đối — cùng lý do với DUONG_DAN_FILE_ENV trong
# config.py: thư mục làm việc lúc chạy không cố định.
THU_MUC_BANG_ANH_XA = Path(__file__).resolve().parent / "mappings"

# Việt Nam dùng cố định UTC+7, không có giờ mùa hè (từ 1975 tới nay) nên cộng
# thẳng 7 giờ là đúng tuyệt đối, không cần thư viện múi giờ.
# Viết (7, unit="h") chứ không (hours=7): với numpy 2.5 đang cài, cách sau
# sinh DeprecationWarning bên trong pandas 2.2.3 (đã thử cả 3 cách viết).
LECH_GIO_VIET_NAM = pd.Timedelta(7, unit="h")

# Quy ước VAT 8% của công ty (SPEC §7.5).
HE_SO_VAT = 1.08

# Bước 1 của thuật toán chuẩn hóa tỉnh (SPEC §5.3). So khớp không phân biệt
# hoa/thường nên "Thành phố " và "Thành Phố " thực ra là một, vẫn liệt kê đủ cho
# khớp SPEC. "Tinh " và "Thanh pho " (không dấu) do sinh viên chốt thêm ngày
# 12/10/2026: dữ liệu TikTok thật có 154 dòng viết kiểu "Tinh An Giang",
# "Thanh pho Ha Noi"; thiếu 2 tiền tố này thì cả 154 dòng rơi vào "Khác".
# Không tỉnh nào có tên bắt đầu bằng các cụm này nên không bóc nhầm.
TIEN_TO_TINH = [
    "Tỉnh ",
    "Thành phố ",
    "Thành Phố ",
    "TP. ",
    "TP ",
    "Phố ",
    "Province de ",
    "Tinh ",
    "Thanh pho ",
]

# Bước 2 của thuật toán chuẩn hóa tỉnh: "Ho Chi Minh City", "Ha Noi City".
HAU_TO_TINH = [" City", " city"]

# Giá trị gán cho tỉnh không tra được (SPEC §5.3 bước 5).
TINH_KHONG_XAC_DINH = "Khác"


def doc_file_anh_xa(ten_file):
    """Đọc một bảng ánh xạ JSON trong thư mục mappings/.

    Nhận: tên file, ví dụ "province_map.json".
    Trả: dict đọc từ file.
    Cần hàm này vì cả 4 module chuẩn hóa (2 parser CSV, 2 transform API) đều
    cần bảng tỉnh và bảng sản phẩm; đọc ở một chỗ thì không ai trỏ nhầm file.
    """
    duong_dan = THU_MUC_BANG_ANH_XA / ten_file
    # Ghi rõ utf-8: trên Windows, open() mặc định dùng bảng mã cp1252 và sẽ
    # đọc hỏng tên tỉnh có dấu.
    with open(duong_dan, encoding="utf-8") as file_json:
        return json.load(file_json)


def doi_chuoi_tien_sang_so(cot_tien):
    """Đổi cột tiền dạng chuỗi sang số.

    Nhận: Series chứa số tiền, có thể là "1,415,000" (dấu phẩy ngăn nghìn),
    "2.28e+06" (ký hiệu khoa học), số sẵn, hoặc ô rỗng.
    Trả: Series số. Ô rỗng/NaN vẫn là NaN.
    Cần hàm này vì file Shopee/TikTok trộn cả 2 định dạng chuỗi (SPEC §2.3).
    """
    # Chỉ ép sang chuỗi ở ô CÓ giá trị. Ép cả cột bằng .astype(str) thì pandas
    # 2.2 biến NaN thành chuỗi "nan" (SPEC §17.7b). Ngược lại, bỏ qua bước ép
    # cũng sai: cột kiểu object lẫn số với chuỗi (pandas sinh ra khi đọc file
    # lớn theo từng khúc) thì .str.replace âm thầm biến các ô số thành NaN.
    co_gia_tri = cot_tien.notna()
    cot_dang_chuoi = cot_tien.astype(str).where(co_gia_tri)

    # Bỏ khoảng trắng trước: pd.to_numeric báo lỗi với " " nhưng hiểu "" là NaN.
    cot_bo_khoang_trang = cot_dang_chuoi.str.strip()
    cot_bo_dau_phay = cot_bo_khoang_trang.str.replace(",", "", regex=False)

    # pd.to_numeric hiểu cả "1415000" lẫn "2.28e+06". CẤM int(chuỗi) (lỗi với
    # "2.28e+06") và regex bóc chữ số (ra 228 thay vì 2280000) — SPEC §17.7c.
    # errors="raise": gặp chuỗi rác thì dừng ngay, không lặng lẽ thành NaN
    # rồi làm hụt doanh thu mà không ai biết.
    return pd.to_numeric(cot_bo_dau_phay, errors="raise")


def doc_ngay_shopee(cot_ngay):
    """Đọc cột ngày của file Shopee.

    Nhận: Series chuỗi dạng "YYYY/MM/DD" (cột `Ngày đặt hàng`).
    Trả: Series kiểu datetime. Ô rỗng thành NaT.
    Cần hàm này vì so sánh/lọc theo kỳ phải làm trên kiểu ngày, không phải
    trên chuỗi (SPEC §17.7a).
    """
    # Ghi rõ format thay vì để pandas tự đoán: tự đoán có thể đọc nhầm
    # ngày/tháng mà không báo lỗi.
    return pd.to_datetime(cot_ngay, format="%Y/%m/%d", errors="raise")


def doc_thoi_gian_tiktok(cot_thoi_gian):
    """Đọc cột thời gian tạo đơn của file TikTok.

    Nhận: Series chuỗi dạng "DD/MM/YYYY HH:MM:SS" (cột `Created Time`).
    Trả: Series kiểu datetime, giờ Việt Nam. Ô rỗng thành NaT.
    Cần hàm này vì từng có lỗi lấy min/max trên chuỗi: "31/07/2026" bị coi là
    lớn hơn "23/08/2026" (SPEC §17.7a).
    """
    return pd.to_datetime(cot_thoi_gian, format="%d/%m/%Y %H:%M:%S", errors="raise")


def doi_timestamp_api_sang_gio_vn(cot_timestamp):
    """Đổi unix timestamp (giây) của API sang thời gian theo giờ Việt Nam.

    Nhận: Series số giây tính từ 1970-01-01 UTC (trường `create_time`).
    Trả: Series datetime giờ Việt Nam, KHÔNG kèm thông tin múi giờ.
    Cần hàm này vì ngày đặt hàng phải tính theo GMT+7. Dùng UTC thì đơn tạo lúc
    0h–7h sáng giờ VN bị lùi sang ngày hôm trước — lỗi đã gặp ở Pipeline
    TikTok (SPEC §18.3).
    """
    # unit="s" cho ra giờ UTC dạng "trơn" (không kèm múi giờ).
    thoi_gian_utc = pd.to_datetime(cot_timestamp, unit="s")
    # Giữ dạng trơn sau khi cộng 7 giờ để cùng kiểu với đường file (CSV ghi giờ
    # VN không kèm múi giờ). Hai đường cùng kiểu thì test khứ hồi (SPEC §21.5)
    # mới so sánh trực tiếp được.
    return thoi_gian_utc + LECH_GIO_VIET_NAM


def tinh_khung_gio(cot_thoi_gian):
    """Tính khung giờ ra đơn từ thời điểm tạo đơn.

    Nhận: Series datetime theo giờ Việt Nam.
    Trả: Series chuỗi dạng "{h}H - {h+1}H", ví dụ "0H - 1H", "23H - 24H".
    Ô NaT thành NaN.
    Cần hàm này vì cột `Khung Giờ Ra Đơn` là công thức của Lark, API không trả
    về, hệ thống phải tự tính (SPEC §2.2). Định dạng giữ đúng 24 khung của file
    để 2 đường so sánh được.
    """
    co_thoi_gian = cot_thoi_gian.notna()
    # Nếu cột có NaT, .dt.hour ra số thực (7.0 thay vì 7) và chuỗi sẽ thành
    # "7.0H". Điền tạm 0 rồi ép int để định dạng đúng; các ô này bị trả về
    # NaN ở dòng cuối nên số 0 tạm không lọt ra ngoài.
    gio_bat_dau = cot_thoi_gian.dt.hour.fillna(0).astype(int)
    gio_ket_thuc = gio_bat_dau + 1

    phan_dau = gio_bat_dau.astype(str) + "H"
    phan_cuoi = gio_ket_thuc.astype(str) + "H"
    khung_gio = phan_dau + " - " + phan_cuoi
    return khung_gio.where(co_thoi_gian)


def lam_sach_seller_sku_tiktok(cot_seller_sku):
    """Làm sạch cột `Seller SKU` của TikTok.

    Nhận: Series SKU thô, có thể dính khoảng trắng và dấu nháy đơn ở hai đầu
    ("BU01'", "M15''").
    Trả: Series SKU đã bỏ khoảng trắng và dấu nháy ở HAI ĐẦU. Ô rỗng vẫn NaN.
    Cần hàm này vì `sku` là khóa chống trùng (SPEC §4): "BU01" và "BU01'" mà
    coi là 2 SKU thì cùng một dòng hàng bị đếm 2 lần.
    """
    sku_bo_khoang_trang = cot_seller_sku.str.strip()
    # Dùng strip("'") chứ KHÔNG dùng replace("'", ""), theo SPEC §5.2: còn 2
    # giá trị có nháy ở giữa ("BU01' + B3", "M15'_Live") nhưng sku chỉ là khóa
    # chống trùng, báo cáo dùng product_code. Giữ nháy ở giữa để sku bám sát
    # giá trị gốc, dễ truy vết.
    return sku_bo_khoang_trang.str.strip("'")


def bo_tien_to_tinh(ten_tinh):
    """Bỏ tiền tố hành chính ở đầu tên tỉnh (SPEC §5.3 bước 1).

    Nhận: chuỗi tên tỉnh, ví dụ "Tỉnh An Giang", "Province de Dong Thap".
    Trả: chuỗi đã bỏ tối đa một tiền tố, ví dụ "An Giang", "Dong Thap".
    Cần hàm này vì cùng một tỉnh được viết lúc có lúc không có tiền tố.
    """
    for tien_to in TIEN_TO_TINH:
        if ten_tinh.lower().startswith(tien_to.lower()):
            # Chỉ bỏ một tiền tố: tên kiểu "Tỉnh Thành phố X" không có trong
            # dữ liệu, bóc lặp lại chỉ thêm rủi ro cắt nhầm.
            return ten_tinh[len(tien_to):]
    return ten_tinh


def bo_hau_to_tinh(ten_tinh):
    """Bỏ hậu tố " City" ở cuối tên tỉnh (SPEC §5.3 bước 2).

    Nhận: chuỗi tên tỉnh, ví dụ "Ho Chi Minh City".
    Trả: chuỗi đã bỏ hậu tố, ví dụ "Ho Chi Minh".
    Cần hàm này vì TikTok có tên tỉnh viết theo kiểu tiếng Anh.
    """
    for hau_to in HAU_TO_TINH:
        if ten_tinh.endswith(hau_to):
            return ten_tinh[: -len(hau_to)]
    return ten_tinh


def tao_khoa_tra_tinh(ten_tinh):
    """Sinh khóa tra bảng tỉnh: bỏ dấu, viết thường, chỉ giữ chữ a-z (SPEC §5.3 bước 3).

    Nhận: chuỗi tên tỉnh đã qua bước 1-2.
    Trả: chuỗi khóa, ví dụ "Bà Rịa - Vũng Tàu" và "Ba Ria– Vung Tau" đều ra
    "bariavungtau". Tên không có chữ Latin (tiếng Nga/Hàn/Nhật) ra chuỗi rỗng.
    Cần hàm này vì bỏ dấu và ký tự lạ tự gộp được phần lớn cách viết khác nhau,
    nhờ đó bảng tra chỉ cần một khóa cho mỗi tỉnh.
    """
    # NFD tách chữ có dấu thành "chữ gốc + dấu" (ví dụ "ắ" → "a" + 2 dấu),
    # sau đó bỏ các ký tự dấu (nhóm Unicode "Mn").
    ten_tach_dau = unicodedata.normalize("NFD", ten_tinh)
    ky_tu_khong_dau = []
    for ky_tu in ten_tach_dau:
        if unicodedata.category(ky_tu) != "Mn":
            ky_tu_khong_dau.append(ky_tu)
    ten_khong_dau = "".join(ky_tu_khong_dau)

    # "đ" không phải "d" + dấu nên NFD không tách được, phải đổi tay.
    # Lưu ý: "Ð" (chữ Eth của tiếng Iceland, trông giống hệt "Đ") có trong dữ
    # liệu thật ("Ðắk Nông"). Nó KHÔNG được đổi ở đây mà bị bỏ ở bước lọc a-z,
    # ra khóa "aknong" — bảng tra có sẵn khóa này (SPEC §5.3).
    ten_doi_d = ten_khong_dau.replace("đ", "d").replace("Đ", "d")
    ten_viet_thuong = ten_doi_d.lower()
    return re.sub(r"[^a-z]", "", ten_viet_thuong)


def normalize_province(tinh_goc, bang_tinh):
    """Chuẩn hóa tên tỉnh/thành về tên chuẩn theo thuật toán 5 bước của SPEC §5.3.

    Nhận: tinh_goc — chuỗi tỉnh nguyên bản (có thể NaN); bang_tinh — dict
    {khóa: tên chuẩn} đọc từ province_map.json.
    Trả: tên tỉnh chuẩn, hoặc "Khác" nếu không tra được (có ghi log cảnh báo).
    Cần hàm này vì TikTok có 209 cách viết cho chưa tới 63 tỉnh. Không chuẩn hóa
    thì "Hồ Chí Minh" và "Ho Chi Minh City" thành 2 tỉnh trên dashboard.

    Tên hàm giữ tiếng Anh vì SPEC §5.3 đã đặt tên này. Bảng tra được truyền
    vào thay vì tự đọc file, để test được thuật toán bằng bảng nhỏ tự tạo.
    Việc giữ lại `province_raw` do nơi gọi làm (SPEC §5.3 "Bắt buộc").
    """
    if pd.isna(tinh_goc):
        logger.warning("Tỉnh rỗng, gán '%s'", TINH_KHONG_XAC_DINH)
        return TINH_KHONG_XAC_DINH

    # Đưa về dạng NFC (dạng dựng sẵn) trước khi so tiền tố: chuỗi chép từ web
    # hoặc Excel đôi khi ở dạng tách dấu, khi đó "Tỉnh " nhìn giống hệt nhưng
    # startswith so không khớp.
    tinh_nfc = unicodedata.normalize("NFC", tinh_goc.strip())
    tinh_bo_tien_to = bo_tien_to_tinh(tinh_nfc)
    tinh_bo_hau_to = bo_hau_to_tinh(tinh_bo_tien_to)
    khoa_tra = tao_khoa_tra_tinh(tinh_bo_hau_to)

    # Tên không có chữ Latin (3 dòng tiếng Nga/Hàn/Nhật) ra khóa rỗng. Bảng
    # tra lưu thẳng chuỗi gốc của chúng làm khóa, nên tra bằng chuỗi gốc.
    # Hai loại khóa không đè nhau được: khóa thường chỉ gồm chữ a-z.
    if khoa_tra == "":
        khoa_tra = tinh_nfc

    if khoa_tra in bang_tinh:
        return bang_tinh[khoa_tra]

    logger.warning("Không tra được tỉnh '%s' (khóa '%s'), gán '%s'",
                   tinh_goc, khoa_tra, TINH_KHONG_XAC_DINH)
    return TINH_KHONG_XAC_DINH


def tra_ma_san_pham(cot_sku, bang_san_pham):
    """Tra mã sản phẩm chuẩn `product_code` từ `sku` (SPEC §5.4).

    Nhận: cot_sku — Series SKU đã làm sạch; bang_san_pham — dict {sku: mã}
    của MỘT sàn (phần "shopee" hoặc "tiktok" trong product_map.json).
    Trả: Series product_code. SKU không có trong bảng → NaN (thành NULL trong
    CSDL), mỗi SKU lạ ghi một dòng log cảnh báo.
    Cần hàm này vì mọi báo cáo GROUP BY product_code, không GROUP BY sku: TikTok
    có 33 SKU nhưng chỉ 13 sản phẩm. SKU lạ không làm hỏng cả lượt nạp (§5.4).
    """
    ma_san_pham = cot_sku.map(bang_san_pham)

    # Log theo từng SKU lạ chứ không theo từng dòng: 1 SKU mới bán 500 dòng
    # thì 500 dòng log giống nhau chỉ che mất thông tin.
    sku_khong_tra_duoc = cot_sku[ma_san_pham.isna()].unique()
    for sku in sku_khong_tra_duoc:
        logger.warning("SKU '%s' không có trong product_map.json, product_code = NULL", sku)
    return ma_san_pham


def tinh_nmv_sau_thue(cot_nmv):
    """Tính NMV sau thuế: round(nmv / 1.08) (SPEC §7.5).

    Nhận: Series NMV (VND, số nguyên).
    Trả: Series NMV sau thuế đã làm tròn tới đơn vị đồng (kiểu số thực ".0",
    việc ép sang số nguyên làm ở bước nạp CSDL). NaN vẫn là NaN.
    Cần hàm này vì cột `NMV Sau Thuế` là công thức Lark, API không trả về.
    """
    nmv_chia_vat = cot_nmv / HE_SO_VAT
    # Làm tròn bằng Series.round(0), KHÔNG dùng int(): int() cắt bỏ phần lẻ,
    # ví dụ 1000 / 1.08 = 925,93 → int ra 925, đúng phải là 926. Cách này đã
    # khớp cột Lark 1.774/1.774 dòng Shopee và 7.540/7.540 dòng TikTok (§17.8).
    # Series.round làm tròn "nửa về số chẵn", nhưng với NMV nguyên thì
    # nmv / 1.08 không bao giờ rơi đúng vào ,5 nên không gặp ca biên đó.
    return nmv_chia_vat.round(0)
