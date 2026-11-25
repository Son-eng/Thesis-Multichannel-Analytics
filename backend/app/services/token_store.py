"""Đọc, ghi platform_tokens: cầu nối giữa CSDL và connector, connector không biết CSDL."""

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.core.log_filter import dang_ky_bi_mat
from app.models.platform_token import PlatformToken

SAN_SHOPEE = "shopee"
SAN_TIKTOK = "tiktok"

# Shopee trả expire_in nên ưu tiên dùng; TikTok không trả nên dùng hằng số, refresh TikTok để NULL vì gần như không hết hạn.
HAN_ACCESS_SHOPEE = timedelta(hours=4)
HAN_REFRESH_SHOPEE = timedelta(days=30)
HAN_ACCESS_TIKTOK = timedelta(days=7)


class LoiGhiTokenSauLamMoi(Exception):
    """Sàn đã cấp token mới nhưng ghi CSDL thất bại; token_moi giữ trong bộ nhớ để thử ghi lại, không được ghi ra log."""

    def __init__(self, san, ten_shop, token_moi):
        super().__init__(
            f"Đã làm mới token {san}/{ten_shop} nhưng không ghi được vào platform_tokens. "
            "Token cũ có thể đã bị sàn vô hiệu — cần ghi lại token mới hoặc ủy quyền lại."
        )
        self.san = san
        self.ten_shop = ten_shop
        self.token_moi = token_moi


def tinh_han_token(san, ket_qua_lam_moi, bay_gio):
    if san == SAN_SHOPEE:
        han_access = timedelta(seconds=ket_qua_lam_moi["expire_in"]) if "expire_in" in ket_qua_lam_moi else HAN_ACCESS_SHOPEE
        return bay_gio + han_access, bay_gio + HAN_REFRESH_SHOPEE
    return bay_gio + HAN_ACCESS_TIKTOK, None


def cac_shop_tu_cau_hinh(cau_hinh):
    return [
        {"platform": SAN_SHOPEE, "shop_name": cau_hinh.SHOPEE_SHOP_NAME, "shop_ref": str(cau_hinh.SHOPEE_SHOP_ID),
         "access_token": cau_hinh.SHOPEE_ACCESS_TOKEN, "refresh_token": cau_hinh.SHOPEE_REFRESH_TOKEN},
        {"platform": SAN_TIKTOK, "shop_name": cau_hinh.TIKTOK_SHOP_A_NAME, "shop_ref": cau_hinh.TIKTOK_SHOP_A_CIPHER,
         "access_token": cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, "refresh_token": cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN},
        {"platform": SAN_TIKTOK, "shop_name": cau_hinh.TIKTOK_SHOP_B_NAME, "shop_ref": cau_hinh.TIKTOK_SHOP_B_CIPHER,
         "access_token": cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, "refresh_token": cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN},
    ]


def nap_san_tu_cau_hinh(cau_hinh, bay_gio=None):
    """Chỉ ghi cho shop chưa có dòng; đã có thì giữ nguyên vì token trong CSDL mới hơn token trong .env."""
    bay_gio = bay_gio or datetime.now().astimezone()
    cac_dong = []
    for shop in cac_shop_tu_cau_hinh(cau_hinh):
        han_access, han_refresh = tinh_han_token(shop["platform"], {}, bay_gio)
        cac_dong.append({**shop, "access_expires_at": han_access, "refresh_expires_at": han_refresh})

    # Đếm bằng RETURNING id vì rowcount qua Session.execute trả -1.
    cau_lenh = (
        insert(PlatformToken).values(cac_dong)
        .on_conflict_do_nothing(constraint="uq_token_shop")
        .returning(PlatformToken.id)
    )
    with SessionLocal() as phien:
        so_dong_moi = len(phien.execute(cau_lenh).all())
        phien.commit()
        return so_dong_moi


class TenGianHangDaDung(Exception):
    """Tên gian hàng đã thuộc một shop khác của cùng sàn, không ghi đè token của shop đó."""

    def __init__(self, san, ten_shop):
        super().__init__(f"Tên gian hàng '{ten_shop}' ({san}) đã dùng cho gian hàng khác")
        self.san = san
        self.ten_shop = ten_shop


def ghi_ket_noi(san, ten_shop, shop_ref, ket_qua_token, bay_gio=None):
    """Kết nối lại nhận ra theo (sàn, shop_ref): giữ tên cũ, chỉ thay token và hạn."""
    bay_gio = bay_gio or datetime.now().astimezone()
    dang_ky_bi_mat(ket_qua_token["access_token"])
    dang_ky_bi_mat(ket_qua_token["refresh_token"])
    han_access, han_refresh = tinh_han_token(san, ket_qua_token, bay_gio)
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken).where(PlatformToken.platform == san, PlatformToken.shop_ref == shop_ref).with_for_update()
        ).scalar_one_or_none()
        la_ket_noi_lai = dong is not None
        if dong is None:
            trung_ten = phien.execute(
                select(PlatformToken.id).where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            ).first()
            if trung_ten is not None:
                raise TenGianHangDaDung(san, ten_shop)
            dong = PlatformToken(platform=san, shop_name=ten_shop, shop_ref=shop_ref,
                                 access_token=ket_qua_token["access_token"], refresh_token=ket_qua_token["refresh_token"],
                                 access_expires_at=han_access, refresh_expires_at=han_refresh)
            phien.add(dong)
        else:
            dong.access_token = ket_qua_token["access_token"]
            dong.refresh_token = ket_qua_token["refresh_token"]
            dong.access_expires_at = han_access
            dong.refresh_expires_at = han_refresh
            dong.updated_at = func.now()
        ten_da_ghi = dong.shop_name
        phien.commit()
        return ten_da_ghi, la_ket_noi_lai


def doc_token(san, ten_shop):
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken).where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
        ).scalar_one_or_none()
        if dong is not None:
            phien.expunge(dong)
            # Đăng ký token để bộ lọc log che nó ở mọi nơi.
            dang_ky_bi_mat(dong.access_token)
            dang_ky_bi_mat(dong.refresh_token)
        return dong


def ghi_token(san, ten_shop, token_moi):
    """Ghi lại cặp token mới trong một phiên CSDL mới, dùng khi gặp LoiGhiTokenSauLamMoi."""
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken)
            .where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            .with_for_update()
        ).scalar_one_or_none()
        if dong is None:
            raise LookupError(f"Chưa có token của {san}/{ten_shop} trong platform_tokens")
        dang_ky_bi_mat(token_moi["access_token"])
        dang_ky_bi_mat(token_moi["refresh_token"])
        dong.access_token = token_moi["access_token"]
        dong.refresh_token = token_moi["refresh_token"]
        dong.access_expires_at = token_moi["access_expires_at"]
        dong.refresh_expires_at = token_moi["refresh_expires_at"]
        dong.updated_at = func.now()
        phien.commit()


def danh_dau_het_quyen(san, ten_shop):
    """Đặt cả hai hạn về hiện tại để trang đồng bộ báo hết quyền; người dùng phải ủy quyền lại."""
    with SessionLocal() as phien:
        phien.execute(
            update(PlatformToken)
            .where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            .values(access_expires_at=func.now(), refresh_expires_at=func.now(), updated_at=func.now())
        )
        phien.commit()


def lam_moi_va_ghi(san, ten_shop, ham_lam_moi, bay_gio=None):
    """Khóa dòng FOR UPDATE suốt lúc gọi sàn để không có hai tiến trình cùng dùng một refresh_token Shopee."""
    bay_gio = bay_gio or datetime.now().astimezone()
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken)
            .where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            .with_for_update()
        ).scalar_one_or_none()
        if dong is None:
            raise LookupError(f"Chưa có token của {san}/{ten_shop} trong platform_tokens")

        # Lỗi ở đây thì rollback, dòng giữ nguyên token cũ.
        dang_ky_bi_mat(dong.access_token)
        dang_ky_bi_mat(dong.refresh_token)
        ket_qua = ham_lam_moi(dong.refresh_token, dong.shop_ref)
        # Đăng ký token mới trước khi ghi, để nếu commit lỗi thì thông điệp lỗi cũng đã được che.
        dang_ky_bi_mat(ket_qua.get("access_token"))
        dang_ky_bi_mat(ket_qua.get("refresh_token"))
        han_access, han_refresh = tinh_han_token(san, ket_qua, bay_gio)
        token_moi = {
            "access_token": ket_qua["access_token"],
            "refresh_token": ket_qua["refresh_token"],
            "access_expires_at": han_access,
            "refresh_expires_at": han_refresh,
        }
        dong.access_token = token_moi["access_token"]
        dong.refresh_token = token_moi["refresh_token"]
        dong.access_expires_at = han_access
        dong.refresh_expires_at = han_refresh
        dong.updated_at = func.now()
        try:
            phien.commit()
        except Exception as loi:
            # Sàn đã ghi nhận lần làm mới mà CSDL thì chưa, nên báo bằng lỗi riêng.
            raise LoiGhiTokenSauLamMoi(san, ten_shop, token_moi) from loi
        return token_moi
