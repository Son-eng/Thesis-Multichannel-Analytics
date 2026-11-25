"""Trang ủy quyền giả của sàn; phiên và mã ủy quyền giữ trong bộ nhớ, dùng một lần và có hạn."""

import html
import secrets
from urllib.parse import urlencode

HAN_PHIEN_GIAY = 10 * 60
SHOPEE_HAN_MA_GIAY = 10 * 60
TIKTOK_HAN_MA_GIAY = 30 * 60

# Shop mới chưa có đơn để thử luồng thêm gian hàng; không đụng dữ liệu Shop A/B/C.
SHOP_SHOPEE_MOI = ("Shop D", 200004)
SHOP_TIKTOK_MOI = ("Shop E", "MOCK_CIPHER_SHOP_E")
ID_TIKTOK_GIA = {"Shop A": "7000000000000000001", "Shop B": "7000000000000000002", "Shop E": "7000000000000000005"}


class PhienKhongHopLe(Exception):
    """(giữ một dòng)"""


class MaKhongHopLe(Exception):
    """(giữ một dòng)"""


class _KhoMotLan:
    """Kho giá trị dùng một lần, có hạn."""

    def __init__(self, loi):
        self._du_lieu = {}
        self._loi = loi

    def cap(self, gia_tri, bay_gio, han_giay, do_dai_byte=16):
        ma = secrets.token_hex(do_dai_byte)
        self._du_lieu[ma] = (gia_tri, bay_gio + han_giay)
        return ma

    def xem(self, ma, bay_gio):
        if ma not in self._du_lieu or bay_gio >= self._du_lieu[ma][1]:
            raise self._loi()
        return self._du_lieu[ma][0]

    def lay_mot_lan(self, ma, bay_gio):
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
    dau = "&" if "?" in dia_chi else "?"
    return dia_chi + dau + urlencode(tham_so)


def trang_uy_quyen(san, ten_ung_dung, cac_shop, phien, duong_dan_quyet_dinh, ten_o_chon):
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
