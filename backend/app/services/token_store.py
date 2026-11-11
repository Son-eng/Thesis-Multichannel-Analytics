"""Đọc / ghi bảng `platform_tokens` — token API của từng gian hàng (SPEC §3.3, §12.1.3.2, §20.1).

Vì sao đặt ở services/ chứ không ở connectors/: connector chỉ nói chuyện HTTP,
không biết CSDL (§20.1) — nhờ vậy test connector không cần PostgreSQL. Module
này là cầu nối: lấy token trong CSDL đưa cho connector, và ghi token mới mà
connector nhận được từ sàn.

Hai việc chính:
1. `nap_san_tu_cau_hinh()` — lần đầu chạy, bảng chưa có token của shop nào thì
   lấy token ban đầu trong .env (§20.4) ghi vào. Đã có dòng thì KHÔNG ghi đè:
   token trong CSDL là token mới nhất, token trong .env có thể đã bị dùng.
2. `lam_moi_va_ghi()` — làm mới token và ghi token mới trong CÙNG MỘT giao
   dịch, có khóa dòng. Lý do: refresh_token Shopee chỉ dùng được 1 lần (§3.3).

Thời điểm truyền vào đều là datetime CÓ múi giờ; cột kiểu timestamp không múi
giờ, PostgreSQL tự đổi về múi giờ phiên — cùng quy ước với nap_file.py (bước 8 Phần A).
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.core.log_filter import dang_ky_bi_mat
from app.models.platform_token import PlatformToken

SAN_SHOPEE = "shopee"
SAN_TIKTOK = "tiktok"

# Hạn sống theo tài liệu (§19.3 mục 3). Shopee trả `expire_in` khi làm mới
# nên ưu tiên dùng số đó; TikTok không trả trường hạn nào (§19.2) nên bắt buộc
# dùng hằng số; refresh TikTok "sống tới năm 2123" → để NULL (§12.1.3.2).
HAN_ACCESS_SHOPEE = timedelta(hours=4)
HAN_REFRESH_SHOPEE = timedelta(days=30)
HAN_ACCESS_TIKTOK = timedelta(days=7)


class LoiGhiTokenSauLamMoi(Exception):
    """Sàn ĐÃ cấp token mới nhưng ghi xuống CSDL thất bại.

    Hậu quả với Shopee: refresh_token cũ đã bị sàn vô hiệu, còn token mới chưa
    được lưu → lần làm mới sau sẽ bị từ chối (error_auth), phải ủy quyền lại.
    Thuộc tính `token_moi` giữ cặp token mới TRONG BỘ NHỚ để nơi gọi (sync_job,
    bước 11) thử ghi lại; KHÔNG được in ra log. Thông báo lỗi không chứa token.
    """

    def __init__(self, san, ten_shop, token_moi):
        super().__init__(
            f"Đã làm mới token {san}/{ten_shop} nhưng không ghi được vào platform_tokens. "
            "Token cũ có thể đã bị sàn vô hiệu — cần ghi lại token mới hoặc ủy quyền lại."
        )
        self.san = san
        self.ten_shop = ten_shop
        self.token_moi = token_moi


def tinh_han_token(san, ket_qua_lam_moi, bay_gio):
    """Thời điểm hết hạn (access, refresh) của cặp token vừa cấp.

    Nhận: sàn; ket_qua_lam_moi — dict connector trả về (có thể có `expire_in`
    giây, như phản hồi Shopee); bay_gio — datetime có múi giờ.
    Trả: (access_expires_at, refresh_expires_at hoặc None).
    """
    if san == SAN_SHOPEE:
        han_access = timedelta(seconds=ket_qua_lam_moi["expire_in"]) if "expire_in" in ket_qua_lam_moi else HAN_ACCESS_SHOPEE
        return bay_gio + han_access, bay_gio + HAN_REFRESH_SHOPEE
    return bay_gio + HAN_ACCESS_TIKTOK, None


def cac_shop_tu_cau_hinh(cau_hinh):
    """3 gian hàng và token ban đầu khai trong .env (§20.4), dạng dict sẵn để ghi bảng.

    Shopee: shop_ref = shop_id; TikTok: shop_ref = shop_cipher (§3.3).
    """
    return [
        {"platform": SAN_SHOPEE, "shop_name": cau_hinh.SHOPEE_SHOP_NAME, "shop_ref": str(cau_hinh.SHOPEE_SHOP_ID),
         "access_token": cau_hinh.SHOPEE_ACCESS_TOKEN, "refresh_token": cau_hinh.SHOPEE_REFRESH_TOKEN},
        {"platform": SAN_TIKTOK, "shop_name": cau_hinh.TIKTOK_SHOP_A_NAME, "shop_ref": cau_hinh.TIKTOK_SHOP_A_CIPHER,
         "access_token": cau_hinh.TIKTOK_SHOP_A_ACCESS_TOKEN, "refresh_token": cau_hinh.TIKTOK_SHOP_A_REFRESH_TOKEN},
        {"platform": SAN_TIKTOK, "shop_name": cau_hinh.TIKTOK_SHOP_B_NAME, "shop_ref": cau_hinh.TIKTOK_SHOP_B_CIPHER,
         "access_token": cau_hinh.TIKTOK_SHOP_B_ACCESS_TOKEN, "refresh_token": cau_hinh.TIKTOK_SHOP_B_REFRESH_TOKEN},
    ]


def nap_san_tu_cau_hinh(cau_hinh, bay_gio=None):
    """Ghi token ban đầu từ .env cho shop nào CHƯA có dòng trong platform_tokens.

    Nhận: cau_hinh (app.config.settings); bay_gio — datetime có múi giờ,
    mặc định là lúc gọi.
    Trả: số dòng vừa thêm (0 nếu cả 3 shop đã có).
    Hạn tính như token vừa được cấp lúc nạp — GIẢ ĐỊNH: .env không cho biết
    token được cấp lúc nào. Với máy chủ giả lập thì đúng (nó cấp token ban
    đầu lúc khởi động); với sàn thật, nếu token đã cũ thì lượt đồng bộ đầu
    gặp token hết hạn → làm mới (§18.2 bước 3).
    ON CONFLICT DO NOTHING trên (platform, shop_name): đã có dòng thì giữ
    nguyên, không ghi đè token mới nhất bằng token cũ trong .env.
    """
    bay_gio = bay_gio or datetime.now().astimezone()
    cac_dong = []
    for shop in cac_shop_tu_cau_hinh(cau_hinh):
        han_access, han_refresh = tinh_han_token(shop["platform"], {}, bay_gio)
        cac_dong.append({**shop, "access_expires_at": han_access, "refresh_expires_at": han_refresh})

    # RETURNING id: chỉ dòng THẬT SỰ được thêm mới mới trả về (dòng bị DO NOTHING
    # bỏ qua thì không) → đếm là ra số dòng thêm. Không dùng rowcount: chạy qua
    # Session.execute thì rowcount ra -1 (đã gặp ở bước 9a).
    cau_lenh = (
        insert(PlatformToken).values(cac_dong)
        .on_conflict_do_nothing(constraint="uq_token_shop")
        .returning(PlatformToken.id)
    )
    with SessionLocal() as phien:
        so_dong_moi = len(phien.execute(cau_lenh).all())
        phien.commit()
        return so_dong_moi


def doc_token(san, ten_shop):
    """Dòng token của một shop (đối tượng PlatformToken đã tách khỏi phiên), hoặc None."""
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken).where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
        ).scalar_one_or_none()
        if dong is not None:
            phien.expunge(dong)
            # Từ đây token của shop này nằm trong bộ nhớ: đăng ký để bộ lọc log che nó ở mọi nơi nó có thể lọt vào.
            dang_ky_bi_mat(dong.access_token)
            dang_ky_bi_mat(dong.refresh_token)
        return dong


def ghi_token(san, ten_shop, token_moi):
    """Ghi lại cặp token mới trong một phiên CSDL MỚI (dùng khi `LoiGhiTokenSauLamMoi`).

    Nhận: token_moi — dict `LoiGhiTokenSauLamMoi.token_moi` (access_token,
    refresh_token, access_expires_at, refresh_expires_at).
    Lỗi: LookupError nếu không có dòng của shop; lỗi CSDL thì ném nguyên.
    """
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
    """Đánh dấu shop hết quyền: đặt cả 2 hạn về BÂY GIỜ → token_status = "expired" (§12.1.3.2).

    Dùng khi sàn đã vô hiệu refresh_token cũ mà không ghi lại được token mới:
    người dùng phải ủy quyền lại. Đặt `refresh_expires_at` cả với TikTok (vốn
    NULL = "ok") để trang đồng bộ báo đúng. Không đổi giá trị token.
    """
    with SessionLocal() as phien:
        phien.execute(
            update(PlatformToken)
            .where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            .values(access_expires_at=func.now(), refresh_expires_at=func.now(), updated_at=func.now())
        )
        phien.commit()


def lam_moi_va_ghi(san, ten_shop, ham_lam_moi, bay_gio=None):
    """Làm mới token của một shop và ghi token mới — trong MỘT giao dịch, có khóa dòng.

    Nhận:
        san, ten_shop — dòng cần làm mới.
        ham_lam_moi(refresh_token, shop_ref) — do connector cung cấp: gọi sàn,
            trả dict {access_token, refresh_token[, expire_in]}; lỗi thì ném.
        bay_gio — datetime có múi giờ, mặc định lúc gọi.
    Trả: dict cặp token mới kèm 2 thời điểm hết hạn.
    Lỗi:
        LookupError — chưa có dòng token của shop (chưa nạp sẵn).
        Lỗi của ham_lam_moi — ném nguyên; CSDL không đổi gì (rollback).
        LoiGhiTokenSauLamMoi — sàn đã cấp token mới nhưng commit thất bại.

    Trình tự trong giao dịch:
        SELECT … FOR UPDATE → gọi sàn → UPDATE dòng → COMMIT.
    Khóa dòng (FOR UPDATE) giữ suốt lúc gọi sàn: tiến trình khác muốn làm mới
    cùng shop phải đợi, rồi đọc được refresh_token MỚI — không bao giờ có 2
    tiến trình cùng dùng một refresh_token Shopee (lần thứ 2 sẽ bị từ chối).
    """
    bay_gio = bay_gio or datetime.now().astimezone()
    with SessionLocal() as phien:
        dong = phien.execute(
            select(PlatformToken)
            .where(PlatformToken.platform == san, PlatformToken.shop_name == ten_shop)
            .with_for_update()
        ).scalar_one_or_none()
        if dong is None:
            raise LookupError(f"Chưa có token của {san}/{ten_shop} trong platform_tokens")

        # Lỗi ở đây (sàn từ chối, hết lần thử lại…) → thoát khối `with` chưa
        # commit → rollback, nhả khóa, dòng giữ nguyên token cũ.
        dang_ky_bi_mat(dong.access_token)
        dang_ky_bi_mat(dong.refresh_token)
        ket_qua = ham_lam_moi(dong.refresh_token, dong.shop_ref)
        # Đăng ký token MỚI ngay khi nhận từ sàn, TRƯỚC khi ghi: nếu commit lỗi và PostgreSQL chép cả dòng vào thông điệp
        # lỗi thì chuỗi đó đã nằm trong tập bị che.
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
            # Từ đây sàn đã ghi nhận lần làm mới mà CSDL thì không: phải báo
            # bằng lỗi riêng, nơi gọi mới phân biệt được với "sàn từ chối".
            raise LoiGhiTokenSauLamMoi(san, ten_shop, token_moi) from loi
        return token_moi
