"""Test nội dung 2 bảng ánh xạ thật: province_map.json (SPEC §5.3), product_map.json (§5.4).

Không đọc file CSV gốc ở đây: file đó chứa PII nên không có trong repo, test
phải chạy được trên máy hội đồng. Việc đối chiếu toàn bộ giá trị trong CSV thật
được ghi ở TRACKLOG (bước 3c).
"""

import pytest

from app.etl import cleaners

BANG_TINH = cleaners.doc_file_anh_xa("province_map.json")
BANG_SAN_PHAM = cleaners.doc_file_anh_xa("product_map.json")


# ---------- province_map.json ----------

@pytest.mark.parametrize(
    "tinh_goc, tinh_chuan",
    [
        # Các dạng bẩn liệt kê ở SPEC §5.3
        ("Hồ Chí Minh", "Hồ Chí Minh"),
        ("Ho Chi Minh", "Hồ Chí Minh"),
        ("Ho Chi Minh City", "Hồ Chí Minh"),
        ("Thành phố Hồ Chí Minh", "Hồ Chí Minh"),
        ("TP. Hồ Chí Minh", "Hồ Chí Minh"),
        ("Saigon", "Hồ Chí Minh"),
        ("Hà Nội", "Hà Nội"),
        ("Ha Noi", "Hà Nội"),
        ("Ha Noi City", "Hà Nội"),
        ("Thành phố Hà Nội", "Hà Nội"),
        ("Phố Hà Nội", "Hà Nội"),
        ("An Giang", "An Giang"),
        ("Tỉnh An Giang", "An Giang"),
        ("Đắk Lắk", "Đắk Lắk"),
        ("Tỉnh Daclak", "Đắk Lắk"),
        ("Tỉnh Đắc Lắk", "Đắk Lắk"),       # cách viết có thật trong dữ liệu
        ("Tỉnh Đắk Lắk", "Đắk Lắk"),
        ("Bà Rịa - Vũng Tàu", "Bà Rịa - Vũng Tàu"),
        ("Bà Rịa-Vũng Tàu", "Bà Rịa - Vũng Tàu"),
        ("Ba Ria– Vung Tau", "Bà Rịa - Vũng Tàu"),
        ("Province de Dong Thap", "Đồng Tháp"),
        # Các cặp đặc biệt trong bảng §5.3
        ("Ðắk Nông", "Đắk Nông"),           # "Ð" Iceland → khóa "aknong"
        ("Đắk Nông", "Đắk Nông"),
        ("Tỉnh Ðiện Biên", "Điện Biên"),    # "Ð" Iceland → khóa "ienbien"
        ("Điện Biên", "Điện Biên"),
        ("Huế", "Huế"),
        ("Thành phố Huế", "Huế"),
        ("Thừa Thiên Huế", "Huế"),
        ("Tỉnh Thừa Thiên-Huế", "Huế"),
        # Tiền tố không dấu (chốt 12/10/2026)
        ("Tinh An Giang", "An Giang"),
        ("Thanh pho Ha Noi", "Hà Nội"),
        ("Thanh pho Ho Chi Minh", "Hồ Chí Minh"),
        ("Tinh Thua Thien Hue", "Huế"),
        # Dấu thanh kiểu cũ/mới gộp về một tên
        ("Tỉnh Khánh Hoà", "Khánh Hòa"),
        ("Tỉnh Thanh Hoá", "Thanh Hóa"),
        ("Hoà Bình", "Hòa Bình"),
    ],
)
def test_tinh_bien_the_ve_ten_chuan(tinh_goc, tinh_chuan):
    assert cleaners.normalize_province(tinh_goc, BANG_TINH) == tinh_chuan


@pytest.mark.parametrize(
    "tinh_goc, tinh_chuan",
    [
        ("Город Ханой", "Hà Nội"),   # tiếng Nga
        ("호찌민 시", "Hồ Chí Minh"),  # tiếng Hàn
        ("ハノイ市", "Hà Nội"),        # tiếng Nhật
    ],
)
def test_tinh_3_dong_tieng_nuoc_ngoai(tinh_goc, tinh_chuan):
    assert cleaners.normalize_province(tinh_goc, BANG_TINH) == tinh_chuan


@pytest.mark.parametrize("tinh_la", ["Atlantis", "Tỉnh Không Có", "12345", ""])
def test_tinh_la_ve_khac(tinh_la):
    assert cleaners.normalize_province(tinh_la, BANG_TINH) == "Khác"


def test_bang_tinh_gom_ve_63_tinh():
    # Dữ liệu dùng tên tỉnh trước sáp nhập 2025 (SPEC §5.3, lưu ý cho khóa
    # luận): 63 tỉnh cũ. Số này lệch nghĩa là bảng có tên chuẩn gõ sai, ví dụ
    # "Hoà Bình" và "Hòa Bình" thành 2 tỉnh.
    assert len(set(BANG_TINH.values())) == 63


def test_bang_tinh_khoa_latin_dung_dang_da_normalize():
    # Khóa Latin phải đúng dạng bước 3 sinh ra, không thì không bao giờ tra trúng.
    for khoa in BANG_TINH:
        if khoa.isascii():
            assert cleaners.tao_khoa_tra_tinh(khoa) == khoa


# ---------- product_map.json ----------

MA_SAN_PHAM_CHUNG = {"BU01", "M13", "M15", "M21", "M24", "M3 Plus", "M5", "M6 Pro", "M8 AIR", "M9 MAX"}


def test_san_pham_shopee_19_sku_ra_10_ma():
    bang_shopee = BANG_SAN_PHAM["shopee"]
    assert len(bang_shopee) == 19
    assert set(bang_shopee.values()) == MA_SAN_PHAM_CHUNG


def test_san_pham_shopee_co_sku_tu_chuoi_du_phong():
    # "M21 live" là giá trị đến từ chuỗi dự phòng SKU (§5.1), phải có trong bảng.
    assert BANG_SAN_PHAM["shopee"]["M21 live"] == "M21"


def test_san_pham_tiktok_33_sku_ra_13_ma():
    bang_tiktok = BANG_SAN_PHAM["tiktok"]
    assert len(bang_tiktok) == 33
    assert set(bang_tiktok.values()) == MA_SAN_PHAM_CHUNG | {"B3", "M22", "M23"}


def test_san_pham_tiktok_2_dong_dien_tay():
    assert BANG_SAN_PHAM["tiktok"]["BU_01"] == "BU01"
    assert BANG_SAN_PHAM["tiktok"]["M3Plus"] == "M3 Plus"


@pytest.mark.parametrize(
    "sku, ma",
    [
        ("M3 pro", "M3 Plus"),
        ("m3pro", "M3 Plus"),
        ("M6P_2C + M5_2C", "M6 Pro"),   # combo lấy mã sản phẩm đứng đầu
        ("BU01' + B3", "BU01"),         # nháy ở giữa được giữ trong sku (§5.2)
        ("M15'_Live", "M15"),
    ],
)
def test_san_pham_tiktok_bien_the(sku, ma):
    assert BANG_SAN_PHAM["tiktok"][sku] == ma


def test_san_pham_tiktok_khoa_da_lam_sach():
    # Bảng được tra bằng SKU ĐÃ làm sạch; khóa còn nháy/khoảng trắng ở 2 đầu
    # thì không bao giờ tra trúng.
    for sku in BANG_SAN_PHAM["tiktok"]:
        assert sku == sku.strip().strip("'")
