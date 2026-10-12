"""Sinh 2 file CSV ẩn danh từ 2 file gốc trong data/samples/ (SPEC §15.1).

Vì sao cần: file gốc chứa thông tin cá nhân thật (họ tên, SĐT, địa chỉ cấp
phường/xã, tài khoản KOL) nên bị .gitignore chặn, không có trong repo. Nhưng
test và máy chủ giả lập (§19.4) cần dữ liệu thật để chạy. Bản ẩn danh = file
gốc bỏ đi các cột cá nhân, mọi thứ khác GIỮ Y NGUYÊN từng ký tự — kể cả dữ liệu
bẩn. Làm sạch luôn ở đây thì test của parser sẽ pass giả, vì không còn gì bẩn
để parser phải xử lý.

Cách chạy (từ gốc project):
    backend\\.venv\\Scripts\\python scripts\\anonymize_samples.py
"""

import sys
from pathlib import Path

import pandas as pd

THU_MUC_MAU = Path(__file__).resolve().parent.parent / "data" / "samples"

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
    "shopee": ("Shopee Tracking_Order BOS (1).csv", "shopee_orders_anonymized.csv", COT_PII_SHOPEE),
    "tiktok": ("TikTok Tracking_Order.csv", "tiktok_orders_anonymized.csv", COT_PII_TIKTOK),
}


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


def an_danh_mot_san(ten_san):
    """Ẩn danh file của một sàn: đọc, kiểm cột cá nhân, xóa, ghi.

    Nhận: "shopee" hoặc "tiktok".
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
    ghi_csv_an_danh(bang_an_danh, THU_MUC_MAU / ten_file_an_danh)

    print(f"[{ten_san}] {ten_file_goc} -> {ten_file_an_danh}: "
          f"{len(bang_an_danh)} dòng, {len(bang_goc.columns)} -> {len(bang_an_danh.columns)} cột")
    return True


def main():
    """Ẩn danh cả 2 sàn. Sàn nào lỗi thì thoát mã 1 để người chạy biết."""
    tat_ca_thanh_cong = True
    for ten_san in CAU_HINH_TUNG_SAN:
        if not an_danh_mot_san(ten_san):
            tat_ca_thanh_cong = False
    if not tat_ca_thanh_cong:
        sys.exit(1)


if __name__ == "__main__":
    main()
