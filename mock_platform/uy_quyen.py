"""Luồng ỦY QUYỀN gian hàng của máy chủ giả lập (chỉ dẫn 026, giai đoạn 2).

Đóng vai TRANG ỦY QUYỀN của sàn: chủ shop đăng nhập trên trang của sàn và bấm "Đồng ý", sàn chuyển trình duyệt về
địa chỉ của phần mềm kèm MÃ ỦY QUYỀN; phần mềm đổi mã lấy token ở máy chủ (khóa ứng dụng không bao giờ ra trình duyệt).

Hai kho trong bộ nhớ (mất khi tắt máy chủ, như bảng token):
- `KhoPhienUyQuyen`: một "lần mở trang ủy quyền" — nhớ redirect/state và các shop được chọn, dùng MỘT lần, hết hạn
  sau 10 phút. Có phiên này để nút Đồng ý không tin vào ô ẩn (không cho tự sửa địa chỉ chuyển về).
- `KhoMaUyQuyen`: mã ủy quyền sàn cấp sau khi bấm Đồng ý — dùng MỘT lần, hết hạn theo tài liệu từng sàn
  (Shopee 10 phút, TikTok 30 phút).

Mọi giá trị "giả" (shop D/E, mã, khóa) có tiền tố MOCK hoặc là số tự đặt, không phải của shop thật nào (QUY_TRINH §2.5).

Nguồn khuôn: báo cáo 026 mục (a) — các điểm "đã xác minh" lấy từ `Pipeline/` (Shopee: `shopee_auth.py`,
`shopeeapideveloperguidetomtat (1).md`; TikTok: `tiktok_auth.py`, `Authorization/Get Authorized Shops.md`);
điểm chưa xác minh được ghi rõ GIẢ ĐỊNH ở nơi dùng và ở SPEC §16.
"""

import html
import secrets
from urllib.parse import urlencode

HAN_PHIEN_GIAY = 10 * 60
SHOPEE_HAN_MA_GIAY = 10 * 60        # tài liệu tóm tắt Shopee: code "hết hạn sau 10 phút"
TIKTOK_HAN_MA_GIAY = 30 * 60        # tài liệu bàn giao TikTok: auth_code "hết hạn sau 30 phút"

# Shop MỚI chưa có đơn nào, để thử luồng "thêm gian hàng" (chỉ dẫn 026). Dữ liệu của chúng luôn RỖNG:
# không đụng dữ liệu Shop A/B/C (số bất biến).
SHOP_SHOPEE_MOI = ("Shop D", 200004)
SHOP_TIKTOK_MOI = ("Shop E", "MOCK_CIPHER_SHOP_E")
ID_TIKTOK_GIA = {"Shop A": "7000000000000000001", "Shop B": "7000000000000000002", "Shop E": "7000000000000000005"}


class PhienKhongHopLe(Exception):
    """Phiên ủy quyền không có / đã dùng / hết hạn."""


class MaKhongHopLe(Exception):
    """Mã ủy quyền không có / đã dùng / hết hạn — bên gọi đổi thành mã lỗi của từng sàn."""


class _KhoMotLan:
    """Kho giá trị dùng MỘT lần, có hạn. Lấy ra là xóa (kể cả khi hết hạn) nên không thử đi thử lại được."""

    def __init__(self, loi):
        self._du_lieu = {}
        self._loi = loi

    def cap(self, gia_tri, bay_gio, han_giay, do_dai_byte=16):
        ma = secrets.token_hex(do_dai_byte)
        self._du_lieu[ma] = (gia_tri, bay_gio + han_giay)
        return ma

    def xem(self, ma, bay_gio):
        """Đọc không xóa (để vẽ trang). Không hợp lệ → ném lỗi."""
        if ma not in self._du_lieu or bay_gio >= self._du_lieu[ma][1]:
            raise self._loi()
        return self._du_lieu[ma][0]

    def lay_mot_lan(self, ma, bay_gio):
        """Lấy giá trị và XÓA. Hết hạn hay không có → ném lỗi."""
        if ma not in self._du_lieu:
            raise self._loi()
        gia_tri, het_han = self._du_lieu.pop(ma)
        if bay_gio >= het_han:
            raise self._loi()
        return gia_tri


class KhoPhienUyQuyen(_KhoMotLan):
    def __init__(self):
        super().__init__(PhienKhongHopLe)

    def mo(self, bay_gio, **thong_tin):
        return self.cap(thong_tin, bay_gio, HAN_PHIEN_GIAY)


class KhoMaUyQuyen(_KhoMotLan):
    def __init__(self, han_giay):
        super().__init__(MaKhongHopLe)
        self.han_giay = han_giay

    def cap_ma(self, bay_gio, **thong_tin):
        return self.cap(thong_tin, bay_gio, self.han_giay)


def noi_query(dia_chi, tham_so):
    """Nối tham số vào địa chỉ, giữ query đã có (`?state=…`): thêm bằng `&` nếu đã có `?`, nếu không thì `?`."""
    dau = "&" if "?" in dia_chi else "?"
    return dia_chi + dau + urlencode(tham_so)


def trang_uy_quyen(san, ten_ung_dung, cac_shop, phien, duong_dan_quyet_dinh, ten_o_chon):
    """HTML (tiếng Việt) của trang ủy quyền.

    Nhận: san ("Shopee"/"TikTok Shop"); ten_ung_dung; cac_shop — danh sách tên shop để chọn (ô đầu được chọn sẵn);
    phien — mã phiên (ô ẩn); duong_dan_quyet_dinh — nơi gửi biểu mẫu; ten_o_chon — tên trường ô chọn shop.
    Mọi chuỗi chèn vào trang đều qua html.escape.
    """
    cac_o = "\n".join(
        f'<label class="shop"><input type="radio" name="{html.escape(ten_o_chon)}" value="{html.escape(gia_tri)}"'
        f'{" checked" if i == 0 else ""}> <span>{html.escape(ten)}</span></label>'
        for i, (ten, gia_tri) in enumerate(cac_shop)
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ủy quyền gian hàng {html.escape(san)} (giả lập)</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f3f4f8; margin: 0; display: grid; place-items: center; min-height: 100vh; }}
  main {{ background: #fff; border: 1px solid #e1e4ec; border-radius: 14px; padding: 28px; width: min(440px, 92vw); }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  .gia {{ display: inline-block; font-size: 12px; color: #8a5300; background: #fff1d6; border-radius: 6px; padding: 2px 8px; margin-bottom: 14px; }}
  p {{ color: #3b4054; line-height: 1.5; }}
  .shop {{ display: flex; gap: 10px; align-items: center; border: 1px solid #e1e4ec; border-radius: 10px; padding: 10px 12px; margin: 8px 0; cursor: pointer; }}
  .nut {{ display: flex; gap: 10px; margin-top: 18px; }}
  button {{ flex: 1; padding: 11px; border-radius: 10px; border: 1px solid #c9cdda; background: #fff; font-size: 15px; cursor: pointer; }}
  button.chinh {{ background: #5b4be0; border-color: #5b4be0; color: #fff; }}
</style>
</head>
<body>
<main>
  <span class="gia">Trang giả lập của sàn {html.escape(san)} — không phải trang thật</span>
  <h1>{html.escape(ten_ung_dung)} xin quyền đọc đơn hàng của gian hàng</h1>
  <p>Ứng dụng chỉ <b>đọc</b> đơn hàng và số liệu đối soát. Bạn có thể thu hồi quyền bất cứ lúc nào. Chọn gian hàng cho phép:</p>
  <form method="post" action="{html.escape(duong_dan_quyet_dinh)}">
    <input type="hidden" name="phien" value="{html.escape(phien)}">
    {cac_o}
    <div class="nut">
      <button type="submit" name="quyet_dinh" value="tu_choi">Từ chối</button>
      <button type="submit" name="quyet_dinh" value="dong_y" class="chinh">Đồng ý</button>
    </div>
  </form>
</main>
</body>
</html>
"""
