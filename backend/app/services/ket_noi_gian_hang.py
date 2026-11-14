"""Kết nối gian hàng bằng ủy quyền (OAuth) — chỉ dẫn 026, SPEC §22.

Luồng (mô hình của các phần mềm bên thứ ba thật): bên cung cấp giữ MỘT bộ khóa ứng dụng trên máy chủ; doanh nghiệp không
bao giờ thấy khóa.
    1. Admin bấm "Kết nối gian hàng" → `bat_dau_ket_noi` sinh `state`, trả địa chỉ trang ủy quyền của sàn.
    2. Trình duyệt sang trang ủy quyền; chủ shop đăng nhập TRÊN TRANG CỦA SÀN và bấm Đồng ý.
    3. Sàn chuyển trình duyệt về `/api/connections/<sàn>/callback` kèm mã ủy quyền → `xu_ly_callback` kiểm `state`,
       đổi mã lấy token (máy chủ-tới-máy chủ), ghi `platform_tokens` qua `token_store`.
    4. Trình duyệt được chuyển về giao diện, KHÔNG kèm token hay mã.

`state` giữ TRONG BỘ NHỚ tiến trình (không thêm bảng, chốt ở chỉ dẫn 026): khởi động lại máy chủ hoặc chạy nhiều tiến trình
thì yêu cầu đang chờ mất / không thấy nhau — cùng giả định một tiến trình như giới hạn tần suất ở chỉ dẫn 021.
Hết hạn 10 phút, dùng một lần; kiểm cả sàn khớp.

Mọi giá trị nhạy cảm (mã ủy quyền, token, state) được đăng ký cho bộ lọc log (`core/log_filter.py`) ngay khi nhận; thông điệp
trả cho người dùng và log chỉ có mã lỗi ngắn, không có giá trị của chúng.
"""

import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.config import settings
from app.connectors import http_retry, uy_quyen
from app.connectors.shopee_client import LoiApiShopee
from app.connectors.tiktok_client import LoiApiTikTok
from app.core.log_filter import dang_ky_bi_mat
from app.services import token_store
from app.sync.folder_watcher import ten_ngan_hop_le

logger = logging.getLogger(__name__)

SAN_HOP_LE = ("shopee", "tiktok")
DO_DAI_TEN_SHOP_TOI_DA = 50   # cột platform_tokens.shop_name

# Lý do kết nối không thành — mã ngắn đưa lên giao diện (`?ket_noi=loi&ly_do=…`).
LY_DO_STATE = "state_khong_hop_le"        # thiếu / hết hạn / đã dùng / giả mạo / sai sàn
LY_DO_TU_CHOI = "chu_shop_tu_choi"
LY_DO_THIEU_MA = "thieu_ma_uy_quyen"
LY_DO_LOI_SAN = "loi_san"                 # sàn từ chối đổi mã, hoặc không kết nối được sàn
LY_DO_TEN_TRUNG = "ten_trung"


class LoiYeuCauKetNoi(Exception):
    """Yêu cầu bắt đầu kết nối không hợp lệ (tên shop thiếu / sai). `ma` ngắn, `thong_diep` tiếng Việt cho người dùng."""

    def __init__(self, ma, thong_diep):
        super().__init__(thong_diep)
        self.ma = ma
        self.thong_diep = thong_diep


@dataclass
class YeuCauKetNoi:
    san: str
    nguoi_id: int
    ten_shop: str | None            # Shopee: tên do admin nhập; TikTok: None (tên lấy từ sàn)
    het_han: datetime


@dataclass
class KetQuaKetNoi:
    thanh_cong: bool
    ly_do: str | None = None                                  # khi lỗi
    cac_shop: list[str] = field(default_factory=list)         # tên gian hàng đã ghi (thành công)
    ket_noi_lai: bool = False
    nguoi_id: int | None = None                               # admin đã bắt đầu yêu cầu (để ghi lượt đồng bộ)


class KhoYeuCau:
    """Các yêu cầu kết nối đang chờ sàn trả về, theo `state`. An toàn khi nhiều thread (endpoint sync chạy trong threadpool)."""

    def __init__(self):
        self._khoa = threading.Lock()
        self._yeu_cau = {}

    def tao(self, san, nguoi_id, ten_shop, bay_gio, han):
        state = secrets.token_urlsafe(24)
        with self._khoa:
            # Dọn các yêu cầu đã hết hạn để kho không phình ra mãi.
            for cu in [k for k, v in self._yeu_cau.items() if v.het_han <= bay_gio]:
                del self._yeu_cau[cu]
            self._yeu_cau[state] = YeuCauKetNoi(san, nguoi_id, ten_shop, bay_gio + han)
        return state

    def lay_mot_lan(self, state, san, bay_gio):
        """Lấy và XÓA yêu cầu theo state; None nếu không có / hết hạn / thuộc sàn khác (vẫn bị xóa: không thử lại được)."""
        with self._khoa:
            yeu_cau = self._yeu_cau.pop(state, None) if state else None
        if yeu_cau is None or yeu_cau.het_han <= bay_gio or yeu_cau.san != san:
            return None
        return yeu_cau

    def xoa_het(self):
        with self._khoa:
            self._yeu_cau.clear()


KHO_YEU_CAU = KhoYeuCau()


def _han():
    return timedelta(minutes=settings.CONNECT_STATE_MINUTES)


def url_callback(san, cau_hinh=settings):
    return f"{cau_hinh.PUBLIC_BACKEND_URL.rstrip('/')}/api/connections/{san}/callback"


def kiem_tra_ten_shop(ten_shop):
    ten = (ten_shop or "").strip()
    if not ten:
        raise LoiYeuCauKetNoi("shop_name_required", "Cần nhập tên hiển thị của gian hàng Shopee")
    if len(ten) > DO_DAI_TEN_SHOP_TOI_DA:
        raise LoiYeuCauKetNoi("shop_name_too_long", f"Tên gian hàng tối đa {DO_DAI_TEN_SHOP_TOI_DA} ký tự")
    if not ten_ngan_hop_le(ten):
        # Tên shop Shopee cũng là tên thư mục `data/inbox/shopee/<tên>/`.
        raise LoiYeuCauKetNoi("shop_name_invalid", 'Tên gian hàng không được chứa / \\ : * ? " < > | và không bắt đầu bằng dấu chấm')
    return ten


def bat_dau_ket_noi(san, nguoi_id, ten_shop=None, cau_hinh=settings, kho=None, bay_gio=None):
    """Bước 1: tạo yêu cầu chờ và trả địa chỉ trang ủy quyền của sàn (có chữ ký nếu sàn yêu cầu).

    Shopee cần tên hiển thị (tệp Shopee không có cột shop; tên này cũng là tên ngăn thư mục nạp tệp); TikTok lấy tên từ sàn.
    Với KẾT NỐI LẠI, giao diện gửi tên gian hàng đang có; ở bước callback, shop trùng (sàn, shop_ref) giữ tên cũ.
    """
    kho = kho or KHO_YEU_CAU
    bay_gio = bay_gio or datetime.now().astimezone()
    ten = kiem_tra_ten_shop(ten_shop) if san == "shopee" else None
    state = kho.tao(san, nguoi_id, ten, bay_gio, _han())
    if san == "shopee":
        # Shopee chỉ trả code + shop_id, không trả state (đã xác minh) nên gắn state vào chính `redirect`.
        # GIẢ ĐỊNH chưa xác minh với sàn thật: sàn giữ query có sẵn và nối `&code=…` (SPEC §16).
        return uy_quyen.tao_url_uy_quyen_shopee(cau_hinh, f"{url_callback(san, cau_hinh)}?state={state}")
    return uy_quyen.tao_url_uy_quyen_tiktok(cau_hinh, state)


def _ghi_shopee(yeu_cau, tham_so, cau_hinh, bay_gio):
    code, shop_id = tham_so.get("code"), tham_so.get("shop_id")
    if not code or not shop_id:
        return KetQuaKetNoi(False, LY_DO_THIEU_MA, nguoi_id=yeu_cau.nguoi_id)
    dang_ky_bi_mat(code)
    token = uy_quyen.doi_ma_shopee(cau_hinh, code, shop_id)
    ten, ket_noi_lai = token_store.ghi_ket_noi("shopee", yeu_cau.ten_shop, str(shop_id), token, bay_gio)
    return KetQuaKetNoi(True, cac_shop=[ten], ket_noi_lai=ket_noi_lai, nguoi_id=yeu_cau.nguoi_id)


def _ghi_tiktok(yeu_cau, tham_so, cau_hinh, bay_gio):
    code = tham_so.get("code")
    if not code:
        return KetQuaKetNoi(False, LY_DO_THIEU_MA, nguoi_id=yeu_cau.nguoi_id)
    dang_ky_bi_mat(code)
    token = uy_quyen.doi_ma_tiktok(cau_hinh, code)
    dang_ky_bi_mat(token.get("access_token"))
    dang_ky_bi_mat(token.get("refresh_token"))
    cac_shop_san = uy_quyen.lay_shop_tiktok(cau_hinh, token["access_token"])
    cac_ten, ket_noi_lai, ten_trung = [], False, False
    for shop in cac_shop_san:
        try:
            ten, lai = token_store.ghi_ket_noi("tiktok", shop["name"], shop["cipher"], token, bay_gio)
        except token_store.TenGianHangDaDung:
            ten_trung = True
            continue
        cac_ten.append(ten)
        ket_noi_lai = ket_noi_lai or lai
    if not cac_ten:
        return KetQuaKetNoi(False, LY_DO_TEN_TRUNG if ten_trung else LY_DO_LOI_SAN, nguoi_id=yeu_cau.nguoi_id)
    return KetQuaKetNoi(True, cac_shop=cac_ten, ket_noi_lai=ket_noi_lai, nguoi_id=yeu_cau.nguoi_id)


def xu_ly_callback(san, tham_so, cau_hinh=settings, kho=None, bay_gio=None):
    """Bước 3: nhận kết quả từ sàn. `tham_so` là query của lần chuyển về (dict chuỗi). KHÔNG ném lỗi: trả KetQuaKetNoi.

    Xác thực bằng `state` (không có JWT: trình duyệt do sàn chuyển về): thiếu / hết hạn / đã dùng / khác sàn → không làm gì.
    """
    kho = kho or KHO_YEU_CAU
    bay_gio = bay_gio or datetime.now().astimezone()
    state = tham_so.get("state") or ""
    dang_ky_bi_mat(state)
    yeu_cau = kho.lay_mot_lan(state, san, bay_gio)
    if yeu_cau is None:
        logger.warning("Kết nối gian hàng %s: state không hợp lệ", san)
        return KetQuaKetNoi(False, LY_DO_STATE)
    if tham_so.get("error"):
        logger.info("Kết nối gian hàng %s: chủ shop từ chối ủy quyền", san)
        return KetQuaKetNoi(False, LY_DO_TU_CHOI, nguoi_id=yeu_cau.nguoi_id)
    try:
        ghi = _ghi_shopee if san == "shopee" else _ghi_tiktok
        ket_qua = ghi(yeu_cau, tham_so, cau_hinh, bay_gio)
    except token_store.TenGianHangDaDung:
        return KetQuaKetNoi(False, LY_DO_TEN_TRUNG, nguoi_id=yeu_cau.nguoi_id)
    except (LoiApiShopee, LoiApiTikTok) as loi:
        # Chỉ ghi tên lỗi của sàn (ví dụ invalid_code), không ghi thông điệp hay giá trị nào khác.
        logger.warning("Kết nối gian hàng %s: sàn từ chối (%s)", san, getattr(loi, "ma_loi", "?"))
        return KetQuaKetNoi(False, LY_DO_LOI_SAN, nguoi_id=yeu_cau.nguoi_id)
    except Exception as loi:   # mạng, hết lần thử lại, CSDL… — mọi lỗi đều phải về giao diện thành thông báo, không phải trang lỗi
        logger.warning("Kết nối gian hàng %s thất bại: %s", san, type(loi).__name__)
        return KetQuaKetNoi(False, LY_DO_LOI_SAN, nguoi_id=yeu_cau.nguoi_id)
    if ket_qua.thanh_cong:
        logger.info("Kết nối gian hàng %s thành công (%s)", san, "kết nối lại" if ket_qua.ket_noi_lai else "gian hàng mới")
    return ket_qua


def url_ve_giao_dien(ket_qua, cau_hinh=settings):
    """Địa chỉ giao diện để chuyển trình duyệt về. KHÔNG bao giờ có token, mã ủy quyền hay state."""
    goc = f"{cau_hinh.FRONTEND_URL.rstrip('/')}/admin/sync"
    if ket_qua.thanh_cong:
        return goc + "?" + urlencode({"ket_noi": "thanh_cong", "shop": ",".join(ket_qua.cac_shop),
                                      "lai": "1" if ket_qua.ket_noi_lai else "0"})
    return goc + "?" + urlencode({"ket_noi": "loi", "ly_do": ket_qua.ly_do})
