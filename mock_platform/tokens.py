"""Bảng token trong bộ nhớ của máy chủ giả lập (PROMPT Phần C mục 3, SPEC §19.2–§19.3).

Bảng `platform_tokens` là của backend (phía "khách"). Máy chủ giả lập đóng vai
sàn, nên tự giữ một bảng riêng: token nào đang có hiệu lực, của shop nào, hết
hạn lúc nào. Hai bên chỉ biết token của nhau qua HTTP, như thật.

Hạn sống và hành vi làm mới theo tài liệu:
- Shopee: access_token 4 giờ, refresh_token 30 ngày và **chỉ dùng 1 lần** —
  làm mới xong thì refresh_token cũ bị vô hiệu
  (`shopeeapideveloperguidetomtat (1).md`, mục `refresh_access_token`).
- TikTok: access_token 7 ngày; refresh_token "sống tới năm 2123"
  (`Pipeline/Tiktok/Ban_Giao_TikTok.md`, `deploy/README_DEPLOY.md`) → coi như
  không hết hạn. Tài liệu KHÔNG nói refresh_token cũ bị vô hiệu → không vô hiệu.

Bảng chỉ báo LÝ DO từ chối (token sai / hết hạn). Đổi lý do thành mã lỗi của
từng sàn là việc của route (§19.3 mục 3).
"""

import secrets

LY_DO_TOKEN_SAI = "token_sai"          # không tồn tại, đã bị thay, hoặc của shop khác
LY_DO_TOKEN_HET_HAN = "token_het_han"

SHOPEE_HAN_ACCESS_GIAY = 4 * 60 * 60
SHOPEE_HAN_REFRESH_GIAY = 30 * 24 * 60 * 60
TIKTOK_HAN_ACCESS_GIAY = 7 * 24 * 60 * 60


class TokenKhongHopLe(Exception):
    """Token bị từ chối. Thuộc tính `ly_do` là LY_DO_TOKEN_SAI hoặc LY_DO_TOKEN_HET_HAN."""

    def __init__(self, ly_do):
        super().__init__(ly_do)
        self.ly_do = ly_do


class KhoToken:
    """Token đang có hiệu lực của MỘT sàn.

    Dùng lớp vì đây là trạng thái sống suốt thời gian máy chủ chạy và đổi
    theo từng lần làm mới; truyền dict qua lại giữa các hàm thì dễ quên cập
    nhật một chỗ. Mỗi sàn một đối tượng, khác nhau ở 3 tham số khởi tạo.
    """

    def __init__(self, han_access_giay, han_refresh_giay, vo_hieu_refresh_cu):
        """Nhận: hạn sống access (giây); hạn sống refresh (giây, None = không
        hết hạn); vo_hieu_refresh_cu — True nếu làm mới xong thì refresh_token
        cũ không dùng lại được (Shopee)."""
        self.han_access_giay = han_access_giay
        self.han_refresh_giay = han_refresh_giay
        self.vo_hieu_refresh_cu = vo_hieu_refresh_cu
        # token → (shop, thời điểm hết hạn epoch hoặc None)
        self._access = {}
        self._refresh = {}

    def _het_han_luc(self, bay_gio, han_giay):
        return None if han_giay is None else bay_gio + han_giay

    def nap_san(self, shop, access_token, refresh_token, bay_gio):
        """Nạp cặp token ban đầu của một shop, tính hạn từ bay_gio.

        Cần vì máy chủ giả lập không có bước đổi mã ủy quyền (§12.1.3.2):
        token ban đầu lấy từ .env, backend nạp sẵn cùng giá trị.
        """
        self._access[access_token] = (shop, self._het_han_luc(bay_gio, self.han_access_giay))
        self._refresh[refresh_token] = (shop, self._het_han_luc(bay_gio, self.han_refresh_giay))

    def _kiem(self, bang, token, shop, bay_gio):
        """Kiểm một token trong bảng (access hoặc refresh). Hỏng thì raise TokenKhongHopLe."""
        if token not in bang or bang[token][0] != shop:
            # Token của shop khác cũng là "sai": shop A không được đọc dữ liệu shop B.
            raise TokenKhongHopLe(LY_DO_TOKEN_SAI)
        het_han = bang[token][1]
        if het_han is not None and bay_gio >= het_han:
            raise TokenKhongHopLe(LY_DO_TOKEN_HET_HAN)

    def kiem_access_token(self, access_token, shop, bay_gio):
        """Kiểm access_token có hiệu lực cho shop này lúc bay_gio. Hỏng → TokenKhongHopLe."""
        self._kiem(self._access, access_token, shop, bay_gio)

    def lam_moi(self, refresh_token, shop, bay_gio):
        """Đổi refresh_token lấy cặp token mới.

        Nhận: refresh_token, shop, bay_gio (epoch giây).
        Trả: (access_token mới, refresh_token mới). Hỏng → TokenKhongHopLe.
        access_token cũ KHÔNG bị thu hồi: tài liệu không nói, nên để nó tự hết
        hạn như bình thường.
        """
        self._kiem(self._refresh, refresh_token, shop, bay_gio)
        if self.vo_hieu_refresh_cu:
            del self._refresh[refresh_token]
        access_moi = secrets.token_hex(16)
        refresh_moi = secrets.token_hex(16)
        self.nap_san(shop, access_moi, refresh_moi, bay_gio)
        return access_moi, refresh_moi
