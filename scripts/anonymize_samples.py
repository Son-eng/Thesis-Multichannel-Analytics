"""Sinh hai file CSV ẩn danh từ file gốc: bỏ cột cá nhân, thay tên thương hiệu và tên gian hàng bằng tên giả, giữ nguyên dữ liệu bẩn.
Chạy tay một lần khi có tệp gốc mới (từ gốc project): backend\\.venv\\Scripts\\python scripts\\anonymize_samples.py
Cảnh báo: đọc dữ liệu khách hàng thật và scripts/ten_that.local.json; không commit, không dán nội dung ra ngoài.
"""

import json
import sys
from pathlib import Path

import pandas as pd

THU_MUC_MAU = Path(__file__).resolve().parent.parent / "data" / "samples"
DUONG_DAN_TEN_THAT = Path(__file__).resolve().parent / "ten_that.local.json"

MAU_FILE_TEN_THAT = """{
  "ten_thuong_hieu": "<tên thương hiệu thật>",
  "ten_gia_gian_hang_tiktok": {
    "<tên gian hàng thật thứ nhất>": "Shop A",
    "<tên gian hàng thật thứ hai>": "Shop B"
  }
}"""

# 14 cột cá nhân mỗi sàn.
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

CAU_HINH_TUNG_SAN = {
    "shopee": ("Shopee Tracking_Order.csv", "shopee_orders_anonymized.csv", COT_PII_SHOPEE),
    "tiktok": ("TikTok Tracking_Order.csv", "tiktok_orders_anonymized.csv", COT_PII_TIKTOK),
}

# Chỉ thay tên thương hiệu trong các cột chữ; mã SKU giữ nguyên vì là khóa chống trùng.
TEN_THUONG_HIEU_GIA = "BRAND"
COT_CO_TEN_THUONG_HIEU = {
    "shopee": ["Tên sản phẩm", "Tên phân loại hàng"],
    "tiktok": ["Product Name", "Variation"],
}

# Chỉ file TikTok có cột tên gian hàng.
COT_TEN_SHOP_TIKTOK = "Shop"


def doc_ten_that():
    """Tên thật không được nằm trong repo nên đọc từ file cục bộ; thiếu file thì trả None."""
    if not DUONG_DAN_TEN_THAT.exists():
        return None
    # Ghi rõ utf-8 vì open() trên Windows mặc định cp1252.
    with open(DUONG_DAN_TEN_THAT, encoding="utf-8") as file_json:
        return json.load(file_json)


def doc_csv_nguyen_van(duong_dan):
    """Giữ mọi ô đúng chuỗi gốc, để bản ẩn danh còn nguyên dữ liệu bẩn cho test."""
    return pd.read_csv(duong_dan, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def tim_cot_pii_thieu(bang, danh_sach_pii):
    cot_thieu = []
    for ten_cot in danh_sach_pii:
        if ten_cot not in bang.columns:
            cot_thieu.append(ten_cot)
    return cot_thieu


def tim_cot_pii_bi_trung_ten(bang, danh_sach_pii):
    """Pandas đổi tên cột trùng thành "Email.1", xóa "Email" thì cột kia vẫn lọt."""
    cot_trung = []
    for ten_cot in bang.columns:
        for ten_pii in danh_sach_pii:
            if ten_cot.startswith(ten_pii + "."):
                cot_trung.append(ten_cot)
    return cot_trung


def tim_ten_shop_chua_co_ten_gia(cot_shop, bang_ten_gia):
    """Gian hàng mới chưa có tên giả thì báo, không để tên thật lọt vào bản ẩn danh."""
    ten_chua_co = []
    for ten_shop in cot_shop.unique():
        if ten_shop not in bang_ten_gia:
            ten_chua_co.append(ten_shop)
    return ten_chua_co


def thay_ten_thuong_hieu(cot_chu, ten_thuong_hieu):
    # Dữ liệu thật có cả kiểu viết toàn chữ hoa nên so không phân biệt hoa thường.
    return cot_chu.str.replace(ten_thuong_hieu, TEN_THUONG_HIEU_GIA, case=False, regex=False)


def tim_cot_con_ten_that(bang, danh_sach_ten_that):
    """Kiểm lại mọi cột để tên thật không lọt ở cột ngoài danh sách đã biết."""
    cot_con_ten = []
    for ten_cot in bang.columns:
        for ten_that in danh_sach_ten_that:
            co_ten = bang[ten_cot].str.contains(ten_that, case=False, regex=False)
            if co_ten.any():
                cot_con_ten.append(ten_cot)
                break
    return cot_con_ten


def ghi_csv_an_danh(bang, duong_dan):
    """Ghi cùng định dạng với file gốc (bom, LF) để đọc được bằng đúng cách đọc file gốc."""
    bang.to_csv(duong_dan, index=False, encoding="utf-8-sig", lineterminator="\n")


def an_danh_mot_san(ten_san, ten_that):
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

    bang_an_danh = bang_goc.drop(columns=danh_sach_pii)

    for ten_cot in COT_CO_TEN_THUONG_HIEU[ten_san]:
        bang_an_danh[ten_cot] = thay_ten_thuong_hieu(bang_an_danh[ten_cot], ten_that["ten_thuong_hieu"])

    bang_ten_gia = ten_that["ten_gia_gian_hang_tiktok"]
    if ten_san == "tiktok":
        ten_shop_chua_co = tim_ten_shop_chua_co_ten_gia(bang_an_danh[COT_TEN_SHOP_TIKTOK], bang_ten_gia)
        if ten_shop_chua_co:
            # Không in tên gian hàng ra màn hình để log không lộ tên.
            print(f"DỪNG [{ten_san}]: có {len(ten_shop_chua_co)} gian hàng chưa có tên giả "
                  f"trong {DUONG_DAN_TEN_THAT.name}; KHÔNG ghi file ẩn danh.")
            return False
        # Tên gian hàng là cả ô nên thay cả ô.
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
