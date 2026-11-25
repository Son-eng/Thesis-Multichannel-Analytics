# Điểm khởi động máy chủ FastAPI cổng 8001, mọi dữ liệu lưu trong app.state

import time

from fastapi import FastAPI

import config
import data_builder
import gay_loi
import shopee_routes
import tiktok_routes
import tokens
import uy_quyen


def tao_ung_dung(cau_hinh, dong_ho=time.time, du_lieu_shopee=None, du_lieu_tiktok=None):
    """dong_ho và dữ liệu dựng sẵn để test truyền vào, None thì tự dựng."""
    ung_dung = FastAPI(title="Máy chủ giả lập API sàn (bản demo khóa luận)")
    ung_dung.state.cau_hinh = cau_hinh
    ung_dung.state.dong_ho = dong_ho
    ung_dung.state.bo_sinh_ngau_nhien = gay_loi.tao_bo_sinh_ngau_nhien(cau_hinh.MOCK_FAULT_SEED)
    bay_gio = int(dong_ho())
    ung_dung.state.du_lieu_shopee = du_lieu_shopee or data_builder.dung_du_lieu_shopee()
    du_lieu_tiktok = du_lieu_tiktok or data_builder.dung_du_lieu_tiktok()
    # Yêu cầu TikTok chỉ mang shop_cipher nên tra dữ liệu theo cipher.
    ung_dung.state.du_lieu_tiktok_theo_cipher = {shop["shop_cipher"]: shop for shop in du_lieu_tiktok.values()}

    kho_shopee = tokens.KhoToken(
        cau_hinh.MOCK_SHOPEE_ACCESS_TTL_SECONDS, tokens.SHOPEE_HAN_REFRESH_GIAY, vo_hieu_refresh_cu=True
    )
    kho_shopee.nap_san(
        str(cau_hinh.SHOPEE_SHOP_ID), cau_hinh.SHOPEE_ACCESS_TOKEN, cau_hinh.SHOPEE_REFRESH_TOKEN, bay_gio
    )
    ung_dung.state.kho_token_shopee = kho_shopee

    # Refresh TikTok coi như không hết hạn và không vô hiệu token cũ.
    kho_tiktok = tokens.KhoToken(cau_hinh.MOCK_TIKTOK_ACCESS_TTL_SECONDS, None, vo_hieu_refresh_cu=False)
    token_ban_dau = {
        "Shop A": (cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN),
        "Shop B": (cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN),
    }
    for ten_shop, shop in du_lieu_tiktok.items():
        access_token, refresh_token = token_ban_dau[ten_shop]
        kho_tiktok.nap_san(shop["shop_cipher"], access_token, refresh_token, bay_gio)
    ung_dung.state.kho_token_tiktok = kho_tiktok

    # Thêm một shop mới chưa có đơn mỗi sàn; dữ liệu luôn rỗng nên không đổi số liệu Shop A/B/C.
    ten_shopee_moi, id_shopee_moi = uy_quyen.SHOP_SHOPEE_MOI
    ung_dung.state.cac_shop_shopee = {str(cau_hinh.SHOPEE_SHOP_ID): "Shop C", str(id_shopee_moi): ten_shopee_moi}
    ten_tiktok_moi, cipher_tiktok_moi = uy_quyen.SHOP_TIKTOK_MOI
    ung_dung.state.cac_shop_tiktok = {**data_builder.SHOP_CIPHER_TIKTOK, ten_tiktok_moi: cipher_tiktok_moi}
    ung_dung.state.du_lieu_tiktok_theo_cipher[cipher_tiktok_moi] = {
        "shop_cipher": cipher_tiktok_moi, "don_hang": {}, "finance": {}, "affiliate": {},
    }
    ung_dung.state.kho_phien_shopee = uy_quyen.KhoPhienUyQuyen()
    ung_dung.state.kho_ma_shopee = uy_quyen.KhoMaUyQuyen(uy_quyen.SHOPEE_HAN_MA_GIAY)
    ung_dung.state.kho_phien_tiktok = uy_quyen.KhoPhienUyQuyen()
    ung_dung.state.kho_ma_tiktok = uy_quyen.KhoMaUyQuyen(uy_quyen.TIKTOK_HAN_MA_GIAY)

    ung_dung.include_router(shopee_routes.router)
    ung_dung.include_router(tiktok_routes.router)
    ung_dung.add_exception_handler(shopee_routes.LoiShopee, shopee_routes.xu_ly_loi_shopee)
    ung_dung.add_exception_handler(tiktok_routes.LoiTikTok, tiktok_routes.xu_ly_loi_tiktok)
    return ung_dung


def tao_ung_dung_tu_env():
    return tao_ung_dung(config.doc_cau_hinh())
