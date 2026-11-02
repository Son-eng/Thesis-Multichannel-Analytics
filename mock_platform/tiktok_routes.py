"""3 endpoint TikTok Shop của máy chủ giả lập (SPEC §19.2, §19.3, §19.4).

Hai endpoint của open-api (`orders/search`, Finance) đi qua cùng một trình tự
kiểm (`kiem_yeu_cau_open_api`):
    đủ tham số chung → đúng app_key → timestamp ±5 phút → đúng chữ ký
    → access_token (header `x-tts-access-token`) còn hạn và thuộc đúng shop_cipher
Endpoint làm mới token (`token/refresh`) thuộc máy chủ auth, không ký — chỉ
kiểm app_key, app_secret, refresh_token (theo SDK EcomPHP, §19.2).

Mã lỗi: tài liệu TikTok đã lưu chỉ có `36009003` (và `36009002` ở tài liệu
bàn giao). Mọi lỗi xác thực / tham số dưới đây dùng **mã quy ước dải 9990xxx**
— GIẢ ĐỊNH của bản giả lập (§16 mục 7, bảng ở §19.2). Backend không phụ thuộc
mã cụ thể: connector TikTok chỉ rẽ nhánh theo 36009002, 36009003 (§20.1).

Khuôn phản hồi theo tài liệu: `code` (0 = thành công), `message`,
`request_id`, `data`.
"""

import json
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import gay_loi
import signature
import tokens

router = APIRouter()

DUONG_DAN_ORDERS_SEARCH = "/order/202309/orders/search"
DUONG_DAN_FINANCE = "/finance/202501/orders/{order_id}/statement_transactions"
DUONG_DAN_REFRESH = "/api/v2/token/refresh"

# Mã quy ước của bản giả lập (§19.2). Dải 9990xxx để không trùng mã thật đã
# biết (36009002, 36009003) và nhìn là biết của bản giả lập.
MA_SAI_CHU_KY = 9990001
MA_LECH_THOI_GIAN = 9990002
MA_TOKEN_SAI = 9990003
MA_TOKEN_HET_HAN = 9990004
MA_THAM_SO_SAI = 9990005
MA_REFRESH_SAI = 9990006
# Mã THẬT (tài liệu bàn giao Pipeline): quá tải — dùng cho MOCK_FAULT_RATE.
MA_QUA_TAI = 36009002

PAGE_SIZE_TOI_THIEU = 1
PAGE_SIZE_TOI_DA = 100
TRUONG_SAP_XEP = {"create_time", "update_time"}
CHIEU_SAP_XEP = {"ASC", "DESC"}


class LoiTikTok(Exception):
    """Yêu cầu bị từ chối. Được đổi thành phản hồi TikTok có `code` khác 0."""

    def __init__(self, ma_loi, thong_diep):
        super().__init__(f"{ma_loi}: {thong_diep}")
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


async def xu_ly_loi_tiktok(request, loi):
    """Đổi LoiTikTok thành phản hồi lỗi. Luôn HTTP 200, kể cả quá tải 36009002 (§16 mục 9): lỗi báo qua `code`."""
    # Đọc cạn body trước khi trả lời — cùng lý do với xu_ly_loi_shopee.
    await request.body()
    return JSONResponse(
        status_code=200,
        content={"code": loi.ma_loi, "message": loi.thong_diep, "request_id": secrets.token_hex(16)},
    )


def tra_loi_thanh_cong(du_lieu):
    """Bọc dữ liệu vào khuôn phản hồi thành công của tài liệu."""
    return {"code": 0, "message": "Success", "request_id": secrets.token_hex(16), "data": du_lieu}


def kiem_qua_tai(request):
    """Lỗi quá tải có chủ đích (§19.3 mục 5): HTTP 200 + code 36009002 (§16 mục 9).

    Gọi ĐẦU TIÊN ở mọi route TikTok, trước mọi bước kiểm khác, để yêu cầu bị
    gây lỗi không chạm vào trạng thái (không tiêu refresh_token).
    36009002 là mã thật (tài liệu bàn giao), connector sẽ thử lại khi gặp (§20.1).
    """
    if gay_loi.nen_gay_loi(request.app.state):
        raise LoiTikTok(MA_QUA_TAI, "Too many requests (lỗi có chủ đích của bản giả lập)")


def lay_tham_so(request, ten):
    """Tham số query bắt buộc. Thiếu hoặc rỗng → MA_THAM_SO_SAI."""
    gia_tri = request.query_params.get(ten, "")
    if gia_tri == "":
        raise LoiTikTok(MA_THAM_SO_SAI, f"Thiếu tham số {ten}")
    return gia_tri


async def kiem_yeu_cau_open_api(request):
    """Kiểm tham số chung, chữ ký, timestamp, access_token của một yêu cầu open-api.

    Nhận: request.
    Trả: (dữ liệu của shop ứng với shop_cipher, body dạng chuỗi đúng như nhận).
    Chữ ký tính trên đường dẫn THỰC của yêu cầu (Finance có order_id trong
    đường dẫn) và body đúng từng byte đã nhận — không parse rồi serialize lại
    (bẫy §20.1).
    """
    kiem_qua_tai(request)
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh

    app_key = lay_tham_so(request, "app_key")
    timestamp = lay_tham_so(request, "timestamp")
    chu_ky = lay_tham_so(request, "sign")
    shop_cipher = lay_tham_so(request, "shop_cipher")
    if app_key != cau_hinh.TIKTOK_APP_KEY:
        raise LoiTikTok(MA_THAM_SO_SAI, "app_key không hợp lệ")

    bay_gio = int(trang_thai.dong_ho())
    if not signature.thoi_gian_hop_le(timestamp, bay_gio):
        raise LoiTikTok(MA_LECH_THOI_GIAN, "timestamp lệch quá 5 phút")

    than = (await request.body()).decode("utf-8")
    chu_ky_dung = signature.tinh_chu_ky_tiktok(
        cau_hinh.TIKTOK_APP_SECRET, request.url.path, dict(request.query_params), than
    )
    if not signature.chu_ky_khop(chu_ky, chu_ky_dung):
        raise LoiTikTok(MA_SAI_CHU_KY, "Sai chữ ký")

    access_token = request.headers.get("x-tts-access-token", "")
    try:
        trang_thai.kho_token_tiktok.kiem_access_token(access_token, shop_cipher, bay_gio)
    except tokens.TokenKhongHopLe as loi:
        if loi.ly_do == tokens.LY_DO_TOKEN_HET_HAN:
            raise LoiTikTok(MA_TOKEN_HET_HAN, "access_token đã hết hạn") from None
        raise LoiTikTok(MA_TOKEN_SAI, "access_token không hợp lệ") from None
    # Token đã khớp shop_cipher nên shop chắc chắn có trong dữ liệu.
    return trang_thai.du_lieu_tiktok_theo_cipher[shop_cipher], than


def doc_body_json(than):
    """Body JSON dạng object; body rỗng coi như {} (mọi trường lọc đều tùy chọn)."""
    if than.strip() == "":
        return {}
    try:
        du_lieu = json.loads(than)
    except json.JSONDecodeError:
        raise LoiTikTok(MA_THAM_SO_SAI, "Body không phải JSON hợp lệ") from None
    if not isinstance(du_lieu, dict):
        raise LoiTikTok(MA_THAM_SO_SAI, "Body phải là một object JSON")
    return du_lieu


def doc_moc_thoi_gian(than, ten):
    """Một mốc lọc trong body (`create_time_ge`…), None nếu không có. Sai kiểu → MA_THAM_SO_SAI."""
    gia_tri = than.get(ten)
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, int) or isinstance(gia_tri, bool):
        raise LoiTikTok(MA_THAM_SO_SAI, f"{ten} phải là số nguyên (Unix timestamp)")
    return gia_tri


def nam_trong_khoang(gia_tri, tu_moc, den_moc, bay_gio):
    """Lọc theo tài liệu: `_ge` lấy cả mốc, `_lt` không lấy mốc.

    Chỉ có `_ge` → `_lt` mặc định là bây giờ; chỉ có `_lt` → `_ge` mặc định là
    thời điểm sớm nhất. Không có cả hai → không lọc.
    """
    if tu_moc is None and den_moc is None:
        return True
    tu_moc = 0 if tu_moc is None else tu_moc
    den_moc = bay_gio if den_moc is None else den_moc
    return tu_moc <= gia_tri < den_moc


@router.post(DUONG_DAN_ORDERS_SEARCH)
async def orders_search(request: Request):
    """Tìm đơn của một shop, phân trang bằng page_token (tài liệu `Get Order List.md`).

    Trả đơn đầy đủ (gồm line_items) như tài liệu — không cần gọi thêm endpoint
    chi tiết. Hết trang thì `next_page_token = ""` — tài liệu không nói giá trị
    trang cuối, GIẢ ĐỊNH (§16 mục 9).
    """
    shop, than_chuoi = await kiem_yeu_cau_open_api(request)
    than = doc_body_json(than_chuoi)

    try:
        so_moi_trang = int(lay_tham_so(request, "page_size"))
    except ValueError:
        raise LoiTikTok(MA_THAM_SO_SAI, "page_size phải là số nguyên") from None
    if not PAGE_SIZE_TOI_THIEU <= so_moi_trang <= PAGE_SIZE_TOI_DA:
        raise LoiTikTok(MA_THAM_SO_SAI, "page_size phải trong khoảng 1–100")
    truong_sap_xep = request.query_params.get("sort_field", "create_time")
    chieu_sap_xep = request.query_params.get("sort_order", "DESC")
    if truong_sap_xep not in TRUONG_SAP_XEP or chieu_sap_xep not in CHIEU_SAP_XEP:
        raise LoiTikTok(MA_THAM_SO_SAI, "sort_field / sort_order không hợp lệ")
    # page_token là chuỗi mờ với bên gọi; ở đây chính là vị trí bắt đầu trang.
    page_token = request.query_params.get("page_token", "")
    if page_token != "" and not page_token.isdigit():
        raise LoiTikTok(MA_THAM_SO_SAI, "page_token không hợp lệ")
    vi_tri = int(page_token or 0)

    bay_gio = int(request.app.state.dong_ho())
    tao_tu, tao_den = doc_moc_thoi_gian(than, "create_time_ge"), doc_moc_thoi_gian(than, "create_time_lt")
    sua_tu, sua_den = doc_moc_thoi_gian(than, "update_time_ge"), doc_moc_thoi_gian(than, "update_time_lt")
    loc_trang_thai = than.get("order_status")
    cac_don = [
        don for don in shop["don_hang"].values()
        if nam_trong_khoang(don["create_time"], tao_tu, tao_den, bay_gio)
        and nam_trong_khoang(don["update_time"], sua_tu, sua_den, bay_gio)
        and (loc_trang_thai is None or don["status"] == loc_trang_thai)
    ]
    # Thêm id vào khóa sắp xếp để thứ tự cố định khi 2 đơn trùng thời điểm.
    cac_don.sort(key=lambda don: (don[truong_sap_xep], don["id"]), reverse=chieu_sap_xep == "DESC")

    trang = cac_don[vi_tri:vi_tri + so_moi_trang]
    con_nua = vi_tri + so_moi_trang < len(cac_don)
    return tra_loi_thanh_cong({
        "orders": trang,
        "next_page_token": str(vi_tri + so_moi_trang) if con_nua else "",
        "total_count": len(cac_don),
    })


@router.get(DUONG_DAN_FINANCE)
async def statement_transactions(request: Request, order_id: str):
    """Giao dịch quyết toán theo SKU của một đơn (Finance, §19.2, chốt 13/10/2026).

    Đơn COMPLETED → `sku_transactions` sinh theo §19.4. Đơn khác, hoặc mã đơn
    không thuộc shop này → `code: 0`, `sku_transactions = []`, `total_count = 0`
    — giả định của bản giả lập, tài liệu không mô tả; backend không gọi nhánh
    này (§20.2, §16 mục 5).
    """
    shop, _ = await kiem_yeu_cau_open_api(request)
    giao_dich = shop["finance"].get(order_id, [])
    return tra_loi_thanh_cong({
        "order_id": order_id,
        "sku_transactions": giao_dich,
        "total_count": len(giao_dich),
    })


@router.get(DUONG_DAN_REFRESH)
def refresh_token(request: Request):
    """Đổi refresh_token lấy cặp token mới (máy chủ auth của TikTok).

    Khuôn theo SDK EcomPHP/tiktokshop-php (`src/Auth.php`, commit fbeedca,
    10/07/2026 — §19.2): query `app_key`, `app_secret`, `refresh_token`,
    `grant_type=refresh_token`, không ký; trả `data.access_token`,
    `data.refresh_token`. SDK không thể hiện trường hạn sống nào → không trả;
    backend tự tính hạn từ 7 ngày (§19.3 mục 3).
    refresh_token cũ KHÔNG bị vô hiệu (tài liệu không nói, §19.3 mục 3).
    """
    kiem_qua_tai(request)
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh
    app_key = lay_tham_so(request, "app_key")
    app_secret = lay_tham_so(request, "app_secret")
    refresh_cu = lay_tham_so(request, "refresh_token")
    if lay_tham_so(request, "grant_type") != "refresh_token":
        raise LoiTikTok(MA_THAM_SO_SAI, "grant_type phải là refresh_token")
    if app_key != cau_hinh.TIKTOK_APP_KEY or not signature.chu_ky_khop(app_secret, cau_hinh.TIKTOK_APP_SECRET):
        raise LoiTikTok(MA_REFRESH_SAI, "app_key / app_secret không hợp lệ")

    kho = trang_thai.kho_token_tiktok
    shop_cipher = kho.shop_cua_refresh_token(refresh_cu)
    if shop_cipher is None:
        raise LoiTikTok(MA_REFRESH_SAI, "refresh_token không hợp lệ")
    try:
        access_moi, refresh_moi = kho.lam_moi(refresh_cu, shop_cipher, int(trang_thai.dong_ho()))
    except tokens.TokenKhongHopLe:
        raise LoiTikTok(MA_REFRESH_SAI, "refresh_token không hợp lệ") from None
    return tra_loi_thanh_cong({"access_token": access_moi, "refresh_token": refresh_moi})
