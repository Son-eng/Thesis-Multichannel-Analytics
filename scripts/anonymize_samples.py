"""Sinh 2 file CSV ẩn danh từ 2 file gốc trong data/samples/ (SPEC §15.1).

Vì sao cần: file gốc chứa thông tin cá nhân thật (họ tên, SĐT, địa chỉ cấp
phường/xã, tài khoản KOL) nên bị .gitignore chặn, không có trong repo. Nhưng
test và máy chủ giả lập (§19.4) cần dữ liệu thật để chạy. Bản ẩn danh = file
gốc bỏ đi các cột cá nhân, mọi thứ khác GIỮ Y NGUYÊN từng ký tự — kể cả dữ liệu
bẩn. Làm sạch luôn ở đây thì test của parser sẽ pass giả, vì không còn gì bẩn
để parser phải xử lý.

Ngoại lệ duy nhất: tên thương hiệu và tên gian hàng được thay bằng tên giả,
vì khóa luận (mục 1.3.2) cam kết không nêu tên doanh nghiệp, và repo sẽ nộp
cho khoa. Chỉ thay trong 5 cột chữ có chứa các tên đó; mã SKU giữ nguyên.
Tên thật KHÔNG viết trong file này mà đọc từ scripts/ten_that.local.json —
file chỉ có trên máy sinh viên, .gitignore chặn (mẫu nội dung: MAU_FILE_TEN_THAT).

CHẠY KHI NÀO: MỘT LẦN, khi có tệp gốc mới (hoặc cần sinh lại bản ẩn danh). KHÔNG phải một phần của luồng chạy
hệ thống: hệ thống chỉ dùng kết quả (data/samples/*_anonymized.csv), không bao giờ chạy script này.
Đầu vào: data/samples/Shopee Tracking_Order.csv và TikTok Tracking_Order.csv (gốc) + scripts/ten_that.local.json.
Đầu ra: data/samples/shopee_orders_anonymized.csv, tiktok_orders_anonymized.csv.
CẢNH BÁO: đọc DỮ LIỆU KHÁCH HÀNG THẬT và tên thật của doanh nghiệp. Tệp gốc và ten_that.local.json bị .gitignore
chặn — không commit, không đưa vào bài nộp, không dán nội dung ra nơi khác.

Cách chạy (từ gốc project):
    backend\\.venv\\Scripts\\python scripts\\anonymize_samples.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

THU_MUC_MAU = Path(__file__).resolve().parent.parent / "data" / "samples"
DUONG_DAN_TEN_THAT = Path(__file__).resolve().parent / "ten_that.local.json"

# In ra khi thiếu file tên thật, để người chạy biết phải tạo gì. Chỉ có tên giả.
MAU_FILE_TEN_THAT = """{
  "ten_thuong_hieu": "<tên thương hiệu thật>",
  "ten_gia_gian_hang_tiktok": {
    "<tên gian hàng thật thứ nhất>": "Shop A",
    "<tên gian hàng thật thứ hai>": "Shop B"
  }
}"""

# 14 cột cá nhân mỗi sàn — chép đúng chính tả từ SPEC §5.1 và §5.2.
COT_PII_SHOPEE = [
    "Người Mua",
    "Tên Người nhận",
    "Số điện thoại",
    "Địa chỉ nhận hàng",
    "Địa chỉ",
    "Email",
    "Họ & Tên",
    "Mã số thuế",
    "TP / Quận / Huyện",
    "Quận",
    "Ghi chú",
    "Nhận xét từ Người mua",
    "Mã vận đơn",
    "Mã Kiện Hàng",
]
COT_PII_TIKTOK = [
    "Buyer Username",
    "Recipient",
    "Phone #",
    "Detail Address",
    "Additional address information",
    "District",
    "Commune",
    "Buyer Message",
    "Seller Note",
    "Tracking ID",
    "Package ID",
    "Creator Handle",
    "Creator Username",
    "Checked Marked by",
]

# Mỗi sàn: (file gốc, file ẩn danh, danh sách cột cá nhân).
CAU_HINH_TUNG_SAN = {
    "shopee": ("Shopee Tracking_Order.csv", "shopee_orders_anonymized.csv", COT_PII_SHOPEE),
    "tiktok": ("TikTok Tracking_Order.csv", "tiktok_orders_anonymized.csv", COT_PII_TIKTOK),
}

# Tên thương hiệu nằm lẫn trong tên sản phẩm, ví dụ "Máy Massage Bàn Chân
# <thương hiệu> M15". Chỉ thay trong các cột chữ này; mã SKU (vd "M15") giữ
# nguyên vì là khóa chống trùng và là đầu vào của bảng product_map.json.
TEN_THUONG_HIEU_GIA = "BRAND"
COT_CO_TEN_THUONG_HIEU = {
    "shopee": ["Tên sản phẩm", "Tên phân loại hàng"],
    "tiktok": ["Product Name", "Variation"],
}

# Chỉ file TikTok có cột tên gian hàng. File Shopee không có cột này; tên giả
# "Shop C" của gian hàng Shopee do nơi gọi shopee_parser truyền vào lúc nạp.
COT_TEN_SHOP_TIKTOK = "Shop"


def doc_ten_that():
    """Đọc tên thương hiệu và bảng tên giả gian hàng từ file cục bộ.

    Nhận: không nhận gì; đọc DUONG_DAN_TEN_THAT.
    Trả: dict có 2 khóa "ten_thuong_hieu" (chuỗi) và
    "ten_gia_gian_hang_tiktok" ({tên thật: tên giả}); None nếu thiếu file.
    Cần hàm này vì tên thật không được nằm trong repo (khóa luận mục 1.3.2),
    nhưng script vẫn phải biết tên thật mới thay được.
    """
    if not DUONG_DAN_TEN_THAT.exists():
        return None
    # utf-8: open() mặc định trên Windows dùng cp1252, đọc hỏng chữ có dấu.
    with open(DUONG_DAN_TEN_THAT, encoding="utf-8") as file_json:
        return json.load(file_json)


def doc_csv_nguyen_van(duong_dan):
    """Đọc file CSV, giữ mọi ô đúng y nguyên chuỗi gốc.

    Nhận: đường dẫn file CSV (utf-8-sig).
    Trả: DataFrame mọi ô là chuỗi; ô rỗng là chuỗi rỗng "", không phải NaN.
    Cần hàm này vì cách đọc mặc định của pandas sửa dữ liệu mà không báo:
    đổi "2.28e+06" thành số 2280000.0, đổi ô rỗng và cả các chuỗi như "NA",
    "null" thành NaN. Bản ẩn danh phải giữ đúng dữ liệu bẩn để test có giá trị.
    """
    # dtype=str: không đoán kiểu số → "2.28e+06" vẫn là chuỗi đó.
    # keep_default_na=False: không biến ô rỗng / "NA" / "null" thành NaN.
    return pd.read_csv(duong_dan, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def tim_cot_pii_thieu(bang, danh_sach_pii):
    """Tìm các cột cá nhân có trong danh sách nhưng không có trong file.

    Nhận: DataFrame đã đọc, danh sách tên cột cá nhân.
    Trả: list tên cột bị thiếu — rỗng nghĩa là đủ.
    Cần hàm này vì thiếu cột thường có nghĩa là tên cột trong file đã đổi
    (sàn đổi tên, gõ sai chính tả). Khi đó cột cá nhân với tên mới vẫn nằm
    trong file và sẽ lọt ra ngoài nếu cứ lặng lẽ bỏ qua.
    """
    cot_thieu = []
    for ten_cot in danh_sach_pii:
        if ten_cot not in bang.columns:
            cot_thieu.append(ten_cot)
    return cot_thieu


def tim_cot_pii_bi_trung_ten(bang, danh_sach_pii):
    """Tìm cột cá nhân xuất hiện 2 lần trong file.

    Nhận: DataFrame đã đọc, danh sách tên cột cá nhân.
    Trả: list tên cột bị trùng — rỗng nghĩa là không có.
    Cần hàm này vì khi file có 2 cột cùng tên "Email", pandas tự đổi tên cột
    thứ hai thành "Email.1". Xóa "Email" thì "Email.1" vẫn còn, PII lọt ra
    ngoài mà không có lỗi nào.
    """
    cot_trung = []
    for ten_cot in bang.columns:
        for ten_pii in danh_sach_pii:
            if ten_cot.startswith(ten_pii + "."):
                cot_trung.append(ten_cot)
    return cot_trung


def tim_ten_shop_chua_co_ten_gia(cot_shop, bang_ten_gia):
    """Tìm tên gian hàng có trong file nhưng chưa có trong bảng tên giả.

    Nhận: Series cột `Shop` của file TikTok; bảng {tên thật: tên giả}.
    Trả: list tên gian hàng chưa có tên giả — rỗng nghĩa là đủ.
    Cần hàm này vì file xuất lần sau có thể có thêm gian hàng mới. Bỏ qua im
    lặng thì tên gian hàng thật nằm nguyên trong bản ẩn danh.
    """
    ten_chua_co = []
    for ten_shop in cot_shop.unique():
        if ten_shop not in bang_ten_gia:
            ten_chua_co.append(ten_shop)
    return ten_chua_co


def thay_ten_thuong_hieu(cot_chu, ten_thuong_hieu):
    """Thay tên thương hiệu bằng tên giả trong một cột chữ.

    Nhận: Series chuỗi, ví dụ cột `Tên sản phẩm`; tên thương hiệu thật.
    Trả: Series đã thay mọi chỗ có tên thương hiệu (không phân biệt hoa/thường)
    bằng "BRAND"; phần còn lại của chuỗi giữ nguyên.
    Cần hàm này vì khóa luận cam kết không nêu tên doanh nghiệp (mục 1.3.2).
    """
    # case=False: dữ liệu thật có 2 cách viết — toàn chữ hoa, và chỉ hoa chữ
    # cái đầu (87 lần trong `Tên sản phẩm` của Shopee).
    # regex=False: so đúng chuỗi chữ, không hiểu như biểu thức chính quy.
    return cot_chu.str.replace(ten_thuong_hieu, TEN_THUONG_HIEU_GIA, case=False, regex=False)


def tim_cot_con_ten_that(bang, danh_sach_ten_that):
    """Tìm các cột vẫn còn tên thật sau khi đã thay.

    Nhận: DataFrame đã ẩn danh; list tên thật (thương hiệu + gian hàng).
    Trả: list tên cột còn chứa ít nhất một tên thật (không phân biệt
    hoa/thường, tính cả chuỗi con) — rỗng nghĩa là sạch.
    Cần hàm này vì tên thật có thể xuất hiện ở một cột ngoài 5 cột đã biết
    (file xuất lần sau thêm cột). Kiểm lại toàn bộ thì không lọt.
    """
    cot_con_ten = []
    for ten_cot in bang.columns:
        for ten_that in danh_sach_ten_that:
            co_ten = bang[ten_cot].str.contains(ten_that, case=False, regex=False)
            if co_ten.any():
                cot_con_ten.append(ten_cot)
                break
    return cot_con_ten


def ghi_csv_an_danh(bang, duong_dan):
    """Ghi DataFrame ra file CSV cùng định dạng với file gốc.

    Nhận: DataFrame đã bỏ cột cá nhân, đường dẫn file đích.
    Trả: không trả gì; file được ghi đè nếu đã có.
    Cần hàm này để file ẩn danh đọc được bằng đúng cách đọc file gốc.
    """
    # utf-8-sig: giữ BOM như file gốc, Excel mở không lỗi font tiếng Việt.
    # lineterminator="\n": file gốc xuống dòng kiểu LF. Mặc định trên Windows
    # pandas ghi CRLF, làm file khác kiểu với file gốc.
    # index=False: không ghi thêm cột số thứ tự dòng.
    bang.to_csv(duong_dan, index=False, encoding="utf-8-sig", lineterminator="\n")


def an_danh_mot_san(ten_san, ten_that):
    """Ẩn danh file của một sàn: đọc, kiểm cột cá nhân, xóa, thay tên, ghi.

    Nhận: "shopee" hoặc "tiktok"; dict tên thật đọc bằng doc_ten_that().
    Trả: True nếu đã ghi file ẩn danh, False nếu phải dừng vì lỗi.
    Cần hàm này để 2 sàn chạy đúng một quy trình, chỉ khác cấu hình.
    """
    ten_file_goc, ten_file_an_danh, danh_sach_pii = CAU_HINH_TUNG_SAN[ten_san]
    bang_goc = doc_csv_nguyen_van(THU_MUC_MAU / ten_file_goc)

    cot_thieu = tim_cot_pii_thieu(bang_goc, danh_sach_pii)
    if cot_thieu:
        print(f"DỪNG [{ten_san}]: file thiếu cột cá nhân {cot_thieu}.")
        print("  Kiểm tra tên cột trong file có bị đổi không; KHÔNG ghi file ẩn danh.")
        return False

    cot_trung = tim_cot_pii_bi_trung_ten(bang_goc, danh_sach_pii)
    if cot_trung:
        print(f"DỪNG [{ten_san}]: cột cá nhân xuất hiện 2 lần {cot_trung}; KHÔNG ghi file ẩn danh.")
        return False

    # drop giữ nguyên thứ tự các cột còn lại.
    bang_an_danh = bang_goc.drop(columns=danh_sach_pii)

    for ten_cot in COT_CO_TEN_THUONG_HIEU[ten_san]:
        bang_an_danh[ten_cot] = thay_ten_thuong_hieu(bang_an_danh[ten_cot], ten_that["ten_thuong_hieu"])

    bang_ten_gia = ten_that["ten_gia_gian_hang_tiktok"]
    if ten_san == "tiktok":
        ten_shop_chua_co = tim_ten_shop_chua_co_ten_gia(bang_an_danh[COT_TEN_SHOP_TIKTOK], bang_ten_gia)
        if ten_shop_chua_co:
            # Không in tên gian hàng ra màn hình: log dán vào TRACKLOG sẽ lộ tên.
            print(f"DỪNG [{ten_san}]: có {len(ten_shop_chua_co)} gian hàng chưa có tên giả "
                  f"trong {DUONG_DAN_TEN_THAT.name}; KHÔNG ghi file ẩn danh.")
            return False
        # Thay cả ô bằng tên giả, không thay chuỗi con: tên gian hàng là cả ô.
        bang_an_danh[COT_TEN_SHOP_TIKTOK] = bang_an_danh[COT_TEN_SHOP_TIKTOK].map(bang_ten_gia)

    danh_sach_ten_that = [ten_that["ten_thuong_hieu"]] + list(bang_ten_gia)
    cot_con_ten = tim_cot_con_ten_that(bang_an_danh, danh_sach_ten_that)
    if cot_con_ten:
        print(f"DỪNG [{ten_san}]: cột {cot_con_ten} vẫn còn tên thật; KHÔNG ghi file ẩn danh.")
        return False

    ghi_csv_an_danh(bang_an_danh, THU_MUC_MAU / ten_file_an_danh)

    print(f"[{ten_san}] {ten_file_goc} -> {ten_file_an_danh}: "
          f"{len(bang_an_danh)} dòng, {len(bang_goc.columns)} -> {len(bang_an_danh.columns)} cột")
    return True


def main():
    """Ẩn danh cả 2 sàn. Thiếu file tên thật hoặc sàn nào lỗi thì thoát mã 1."""
    ten_that = doc_ten_that()
    if ten_that is None:
        print(f"DỪNG: thiếu file {DUONG_DAN_TEN_THAT}.")
        print("  Tạo file này (UTF-8) với nội dung theo mẫu, thay phần <...> bằng tên thật:")
        print(MAU_FILE_TEN_THAT)
        sys.exit(1)

    tat_ca_thanh_cong = True
    for ten_san in CAU_HINH_TUNG_SAN:
        if not an_danh_mot_san(ten_san, ten_that):
            tat_ca_thanh_cong = False
    if not tat_ca_thanh_cong:
        sys.exit(1)


if __name__ == "__main__":
    main()
