"""Sinh backend/app/etl/mappings/product_map.json (SPEC §5.4).

Vì sao cần script này thay vì gõ tay file JSON: bảng TikTok (33 SKU → 13 mã)
được RÚT RA từ dữ liệu thật — cặp (`Seller SKU` đã làm sạch, `SKU Sản Phẩm`)
trong file CSV. Giữ script lại để truy vết được nguồn gốc từng dòng của bảng:
hội đồng hỏi "sao biết M3 pro thuộc M3 Plus" thì chạy lại là thấy.

Phần Shopee (19 SKU) chép từ bảng §5.4 vì Shopee không có cột mã sản phẩm để
rút ra. Gộp cả 2 phần vào đây để file JSON sinh lại được trọn vẹn từ một chỗ.

Chỉ đọc 2 cột SKU của file CSV, KHÔNG đọc cột nào chứa thông tin cá nhân.

CHẠY KHI NÀO: khi bảng SKU thay đổi (có sản phẩm mới) — hiếm. KHÔNG phải một phần của luồng chạy hệ thống:
hệ thống chỉ đọc kết quả (product_map.json).
Đầu vào: cột `Seller SKU` và `SKU Sản Phẩm` của CSV TikTok (mặc định bản ẩn danh trong data/samples/, hoặc đường dẫn truyền vào).
Đầu ra: backend/app/etl/mappings/product_map.json (GHI ĐÈ). Chạy xong chạy lại test (tests/test_mappings.py).
Cẩn thận: nếu truyền CSV GỐC thì đó là dữ liệu khách hàng thật — script chỉ đọc 2 cột SKU, nhưng không chép nội dung tệp ra ngoài.

Cách chạy (từ gốc project):
    backend\\.venv\\Scripts\\python scripts\\build_product_map.py [đường_dẫn_csv_tiktok]
"""

import json
import sys
from pathlib import Path

import pandas as pd

THU_MUC_GOC = Path(__file__).resolve().parent.parent

# Dùng chung hàm làm sạch SKU với hệ thống, không viết lại .strip().strip("'")
# ở đây: nếu sau này quy tắc làm sạch đổi thì bảng sinh ra vẫn khớp với cách
# hệ thống làm sạch SKU lúc tra bảng.
sys.path.insert(0, str(THU_MUC_GOC / "backend"))
from app.etl.cleaners import lam_sach_seller_sku_tiktok

DUONG_DAN_CSV_MAC_DINH = THU_MUC_GOC / "data" / "samples" / "TikTok Tracking_Order.csv"
DUONG_DAN_KET_QUA = THU_MUC_GOC / "backend" / "app" / "etl" / "mappings" / "product_map.json"

# Chép nguyên bảng SPEC §5.4. Combo lấy mã của sản phẩm đứng đầu.
BANG_SHOPEE = {
    "BU01": "BU01",
    "M13": "M13",
    "M15": "M15",
    "M21": "M21",
    "M21 VHL": "M21",
    "M21 live": "M21",
    "M24": "M24",
    "M24 LIVE": "M24",
    "M24 live": "M24",
    "M3 Plus": "M3 Plus",
    "M3 Plus + BU01": "M3 Plus",
    "M5_1C": "M5",
    "M5_2C + M15": "M5",
    "M6P_1C": "M6 Pro",
    "M6P_2C + M15": "M6 Pro",
    "M6P_2C + M5_2C": "M6 Pro",
    "M8 AIR": "M8 AIR",
    "M8 Air": "M8 AIR",
    "M9 MAX": "M9 MAX",
}

# 2 SKU TikTok có `SKU Sản Phẩm` rỗng ở mọi dòng — điền tay theo SPEC §5.4.
SKU_TIKTOK_DIEN_TAY = {
    "BU_01": "BU01",
    "M3Plus": "M3 Plus",
}


def doc_cap_sku_tiktok(duong_dan_csv):
    """Đọc các cặp (SKU đã làm sạch, mã sản phẩm) khác nhau trong file TikTok.

    Nhận: đường dẫn file CSV TikTok.
    Trả: DataFrame 2 cột `sku`, `product_code`, mỗi cặp một dòng. Mã có thể NaN.
    Cần hàm này để gom 7.540 dòng về vài chục cặp trước khi kiểm tra.
    """
    # usecols: chỉ nạp đúng 2 cột cần dùng. Vừa nhanh, vừa bảo đảm script
    # không bao giờ chạm vào cột thông tin cá nhân (SPEC §15).
    du_lieu = pd.read_csv(
        duong_dan_csv,
        encoding="utf-8-sig",
        usecols=["Seller SKU", "SKU Sản Phẩm"],
        dtype=str,
    )
    cap_sku = pd.DataFrame({
        "sku": lam_sach_seller_sku_tiktok(du_lieu["Seller SKU"]),
        "product_code": du_lieu["SKU Sản Phẩm"].str.strip(),
    })
    return cap_sku.drop_duplicates()


def tim_sku_mau_thuan(cap_sku):
    """Tìm các SKU ứng với hơn 1 mã sản phẩm.

    Nhận: DataFrame cặp (sku, product_code) từ doc_cap_sku_tiktok.
    Trả: dict {sku: [các mã]} — rỗng nếu mọi SKU chỉ ứng 1 mã.
    Cần hàm này vì bảng tra chỉ đúng khi 1 SKU ↔ 1 mã. Gặp mâu thuẫn thì
    người phải quyết, script không được tự chọn một mã.
    """
    cap_co_ma = cap_sku.dropna(subset=["product_code"])
    so_ma_moi_sku = cap_co_ma.groupby("sku")["product_code"].nunique()
    sku_nhieu_ma = so_ma_moi_sku[so_ma_moi_sku > 1].index

    mau_thuan = {}
    for sku in sku_nhieu_ma:
        cac_ma = cap_co_ma.loc[cap_co_ma["sku"] == sku, "product_code"]
        mau_thuan[sku] = sorted(cac_ma)
    return mau_thuan


def lap_bang_tiktok(cap_sku):
    """Lập bảng {sku: mã sản phẩm} cho TikTok, gồm cả 2 dòng điền tay.

    Nhận: DataFrame cặp (sku, product_code) đã kiểm không mâu thuẫn.
    Trả: (bảng, danh sách lỗi). Danh sách lỗi rỗng thì bảng dùng được.
    Cần hàm này để mọi SKU xuất hiện trong dữ liệu đều có mã, không sót.
    """
    bang_tiktok = {}
    for dong in cap_sku.dropna(subset=["product_code"]).itertuples():
        bang_tiktok[dong.sku] = dong.product_code

    loi = []
    for sku, ma in SKU_TIKTOK_DIEN_TAY.items():
        # Nếu dữ liệu đã có mã cho SKU này thì dòng điền tay là thừa hoặc sai.
        if sku in bang_tiktok and bang_tiktok[sku] != ma:
            loi.append(f"SKU '{sku}': điền tay '{ma}' nhưng dữ liệu ghi '{bang_tiktok[sku]}'")
        bang_tiktok[sku] = ma

    tat_ca_sku = set(cap_sku["sku"].dropna())
    for sku in sorted(tat_ca_sku - set(bang_tiktok)):
        loi.append(f"SKU '{sku}': không có mã trong dữ liệu và không có trong bảng điền tay")
    return bang_tiktok, loi


def main():
    """Đọc CSV, kiểm tra, ghi product_map.json. Có lỗi thì dừng, không ghi file."""
    if len(sys.argv) > 1:
        duong_dan_csv = Path(sys.argv[1])
    else:
        duong_dan_csv = DUONG_DAN_CSV_MAC_DINH

    cap_sku = doc_cap_sku_tiktok(duong_dan_csv)

    mau_thuan = tim_sku_mau_thuan(cap_sku)
    if mau_thuan:
        print("DỪNG: có SKU ứng với nhiều mã sản phẩm — cần người quyết:")
        for sku, cac_ma in mau_thuan.items():
            print(f"  {sku!r}: {cac_ma}")
        sys.exit(1)

    bang_tiktok, loi = lap_bang_tiktok(cap_sku)
    if loi:
        print("DỪNG: bảng TikTok chưa đầy đủ:")
        for dong_loi in loi:
            print(f"  {dong_loi}")
        sys.exit(1)

    # sort_keys: file sinh lại ra đúng thứ tự cũ, git diff chỉ hiện dòng đổi thật.
    bang_san_pham = {"shopee": BANG_SHOPEE, "tiktok": bang_tiktok}
    with open(DUONG_DAN_KET_QUA, "w", encoding="utf-8", newline="\n") as file_json:
        json.dump(bang_san_pham, file_json, ensure_ascii=False, indent=2, sort_keys=True)
        file_json.write("\n")

    print(f"Đã ghi {DUONG_DAN_KET_QUA.relative_to(THU_MUC_GOC)}")
    print(f"  Shopee: {len(BANG_SHOPEE)} SKU -> {len(set(BANG_SHOPEE.values()))} mã")
    print(f"  TikTok: {len(bang_tiktok)} SKU -> {len(set(bang_tiktok.values()))} mã")


if __name__ == "__main__":
    main()
