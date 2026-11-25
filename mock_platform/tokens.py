"""Bảng token trong bộ nhớ của máy chủ giả lập; refresh Shopee chỉ dùng một lần, refresh TikTok coi như không hết hạn."""

import secrets

LY_DO_TOKEN_SAI = "token_sai"
LY_DO_TOKEN_HET_HAN = "token_het_han"

SHOPEE_HAN_ACCESS_GIAY = 4 * 60 * 60
SHOPEE_HAN_REFRESH_GIAY = 30 * 24 * 60 * 60
TIKTOK_HAN_ACCESS_GIAY = 7 * 24 * 60 * 60


class TokenKhongHopLe(Exception):
    def __init__(self, ly_do):
        super().__init__(ly_do)
        self.ly_do = ly_do


class KhoToken:
    """Token đang có hiệu lực của một sàn."""

    def __init__(self, han_access_giay, han_refresh_giay, vo_hieu_refresh_cu):
        self.han_access_giay = han_access_giay
        self.han_refresh_giay = han_refresh_giay
        self.vo_hieu_refresh_cu = vo_hieu_refresh_cu
        self._access = {}
        self._refresh = {}

    def _het_han_luc(self, bay_gio, han_giay):
        return None if han_giay is None else bay_gio + han_giay

    def nap_san(self, shop, access_token, refresh_token, bay_gio):
        """Token ban đầu lấy từ .env, backend nạp sẵn cùng giá trị."""
        self._access[access_token] = (shop, self._het_han_luc(bay_gio, self.han_access_giay))
        self._refresh[refresh_token] = (shop, self._het_han_luc(bay_gio, self.han_refresh_giay))

    def _kiem(self, bang, token, shop, bay_gio):
        if token not in bang or bang[token][0] != shop:
            # Token của shop khác cũng là sai: shop A không được đọc dữ liệu shop B.
            raise TokenKhongHopLe(LY_DO_TOKEN_SAI)
        het_han = bang[token][1]
        if het_han is not None and bay_gio >= het_han:
            raise TokenKhongHopLe(LY_DO_TOKEN_HET_HAN)

    def kiem_access_token(self, access_token, shop, bay_gio):
        self._kiem(self._access, access_token, shop, bay_gio)

    def shop_cua_access_token(self, access_token, bay_gio):
        if access_token not in self._access:
            raise TokenKhongHopLe(LY_DO_TOKEN_SAI)
        shop, het_han = self._access[access_token]
        if het_han is not None and bay_gio >= het_han:
            raise TokenKhongHopLe(LY_DO_TOKEN_HET_HAN)
        return shop

    def shop_cua_refresh_token(self, refresh_token):
        """Yêu cầu làm mới của TikTok chỉ gửi refresh_token, không gửi shop."""
        if refresh_token not in self._refresh:
            return None
        return self._refresh[refresh_token][0]

    def lam_moi(self, refresh_token, shop, bay_gio):
        """access_token cũ không bị thu hồi, để tự hết hạn."""
        self._kiem(self._refresh, refresh_token, shop, bay_gio)
        if self.vo_hieu_refresh_cu:
            del self._refresh[refresh_token]
        access_moi = secrets.token_hex(16)
        refresh_moi = secrets.token_hex(16)
        self.nap_san(shop, access_moi, refresh_moi, bay_gio)
        return access_moi, refresh_moi
