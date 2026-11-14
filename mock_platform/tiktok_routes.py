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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import gay_loi
import signature
import tokens
import uy_quyen

router = APIRouter()

DUONG_DAN_ORDERS_SEARCH = "/order/202309/orders/search"
DUONG_DAN_FINANCE = "/finance/202501/orders/{order_id}/statement_transactions"
DUONG_DAN_REFRESH = "/api/v2/token/refresh"
DUONG_DAN_AFFILIATE = "/affiliate_seller/202410/orders/search"
# Ủy quyền gian hàng (chỉ dẫn 026). `/open/authorize`, `/api/v2/token/get`, `/authorization/202309/shops` theo
# Pipeline/Tiktok (tiktok_auth.py, Authorization/Get Authorized Shops.md); `/mock/...` là của riêng bản giả lập.
DUONG_DAN_TRANG_UY_QUYEN = "/open/authorize"
DUONG_DAN_QUYET_DINH = "/mock/tiktok/quyet-dinh"
DUONG_DAN_TOKEN_GET = "/api/v2/token/get"
DUONG_DAN_SHOPS = "/authorization/202309/shops"

# Tài liệu affiliate_seller/orders/search: "chỉ hỗ trợ tối đa 3 tháng dữ liệu cho
# mỗi yêu cầu". "3 tháng" không nói rõ số ngày → GIẢ ĐỊNH 93 ngày (§16 mục 10).
KHOANG_AFFILIATE_TOI_DA_GIAY = 93 * 24 * 60 * 60

# Mã quy ước của bản giả lập (§19.2). Dải 9990xxx để không trùng mã thật đã
# biết (36009002, 36009003) và nhìn là biết của bản giả lập.
MA_SAI_CHU_KY = 9990001
MA_LECH_THOI_GIAN = 9990002
MA_TOKEN_SAI = 9990003
MA_TOKEN_HET_HAN = 9990004
MA_THAM_SO_SAI = 9990005
MA_REFRESH_SAI = 9990006
MA_MA_UY_QUYEN_SAI = 9990007    # auth_code không có / đã dùng / hết hạn (GIẢ ĐỊNH: tài liệu không có mã riêng)
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


@router.post(DUONG_DAN_AFFILIATE)
async def affiliate_orders_search(request: Request):
    """Các đơn affiliate của một shop theo ngày tạo, phân trang page_token (tài liệu `Search Seller Affiliate Orders.md`).

    Dùng để đánh `is_affiliate` (§21.4): cặp (đơn, sku_id) CÓ trong `skus[]` → True.
    Theo tài liệu: query `page_size` 1–100 (bắt buộc), `page_token`, `shop_cipher`;
    body `create_time_ge` (lấy mốc) / `create_time_lt` (không lấy mốc), mỗi yêu
    cầu tối đa 3 tháng; thiếu cả hai → mặc định 3 tháng gần nhất; chỉ có `_ge`
    thì `_lt` = bây giờ; chỉ có `_lt` thì `_ge` = sớm nhất.
    Trả `data.orders[]` {id, create_time, skus[]: {sku_id}}, `next_page_token`,
    `total_count`. Chỉ sinh các trường §21.4 dùng tới (không sinh
    `creator_username` — tên tài khoản KOL thật là PII, §5.2). `next_page_token`
    trang cuối là `""` (giả định, §16 mục 9). Mọi trạng thái đơn đều có mặt nếu
    nguồn doanh thu là AFF_* (giả định, §16 mục 10).
    """
    shop, than_chuoi = await kiem_yeu_cau_open_api(request)
    than = doc_body_json(than_chuoi)

    try:
        so_moi_trang = int(lay_tham_so(request, "page_size"))
    except ValueError:
        raise LoiTikTok(MA_THAM_SO_SAI, "page_size phải là số nguyên") from None
    if not PAGE_SIZE_TOI_THIEU <= so_moi_trang <= PAGE_SIZE_TOI_DA:
        raise LoiTikTok(MA_THAM_SO_SAI, "page_size phải trong khoảng 1–100")
    page_token = request.query_params.get("page_token", "")
    if page_token != "" and not page_token.isdigit():
        raise LoiTikTok(MA_THAM_SO_SAI, "page_token không hợp lệ")
    vi_tri = int(page_token or 0)

    bay_gio = int(request.app.state.dong_ho())
    tu_moc, den_moc = doc_moc_thoi_gian(than, "create_time_ge"), doc_moc_thoi_gian(than, "create_time_lt")
    if tu_moc is None and den_moc is None:
        tu_moc = bay_gio - KHOANG_AFFILIATE_TOI_DA_GIAY       # mặc định: 3 tháng gần nhất
    tu_thuc = 0 if tu_moc is None else tu_moc
    den_thuc = bay_gio if den_moc is None else den_moc
    if den_thuc - tu_thuc > KHOANG_AFFILIATE_TOI_DA_GIAY:
        raise LoiTikTok(MA_THAM_SO_SAI, "Mỗi yêu cầu chỉ hỗ trợ tối đa 3 tháng dữ liệu")

    cac_don = sorted(
        (muc["create_time"], ma, muc["skus"]) for ma, muc in shop["affiliate"].items()
        if tu_thuc <= muc["create_time"] < den_thuc
    )
    trang = cac_don[vi_tri:vi_tri + so_moi_trang]
    con_nua = vi_tri + so_moi_trang < len(cac_don)
    return tra_loi_thanh_cong({
        "orders": [
            {"id": ma, "create_time": thoi_diem_tao, "skus": [{"sku_id": sku_id} for sku_id in cac_sku]}
            for thoi_diem_tao, ma, cac_sku in trang
        ],
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


# ---------------------------------------------------------------- ủy quyền gian hàng (chỉ dẫn 026)

def _trang_loi(thong_diep):
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><p>{thong_diep}</p>", status_code=400)


@router.get(DUONG_DAN_TRANG_UY_QUYEN)
def trang_uy_quyen(request: Request):
    """Trang ủy quyền gian hàng (HTML): `?service_id=…` — không ký (đã xác minh, tiktok_auth.py:92-99).

    `state` KHÔNG có trong tài liệu luồng Shop; ở đây nhận `state` tùy chọn và trả lại nguyên vẹn khi chuyển về
    (GIẢ ĐỊNH, ghi ở SPEC §16) để phần mềm chống giả mạo yêu cầu.
    """
    trang_thai = request.app.state
    if request.query_params.get("service_id", "") != trang_thai.cau_hinh.TIKTOK_SERVICE_ID:
        return _trang_loi("service_id không hợp lệ.")
    phien = trang_thai.kho_phien_tiktok.mo(
        int(trang_thai.dong_ho()), state=request.query_params.get("state", ""))
    cac_shop = [(ten, ten) for ten in trang_thai.cac_shop_tiktok]
    return HTMLResponse(uy_quyen.trang_uy_quyen(
        "TikTok Shop", "Hệ thống Đa Kênh", cac_shop, phien, DUONG_DAN_QUYET_DINH, "shop"))


@router.post(DUONG_DAN_QUYET_DINH)
async def quyet_dinh_uy_quyen(request: Request):
    """Đồng ý → về Redirect URL ĐÃ ĐĂNG KÝ kèm `code` (+ `state` nếu có); từ chối → kèm `error=access_denied` (GIẢ ĐỊNH).

    TikTok không nhận địa chỉ chuyển về ở URL: dùng `TIKTOK_REDIRECT_URL` của cấu hình (như Redirect URL ở Partner Center).
    """
    trang_thai = request.app.state
    bay_gio = int(trang_thai.dong_ho())
    form = await request.form()
    phien = str(form.get("phien", ""))
    try:
        thong_tin = trang_thai.kho_phien_tiktok.xem(phien, bay_gio)
    except uy_quyen.PhienKhongHopLe:
        return _trang_loi("Phiên ủy quyền không hợp lệ, đã dùng hoặc đã hết hạn. Hãy mở lại trang ủy quyền.")
    dich = trang_thai.cau_hinh.TIKTOK_REDIRECT_URL
    them = {"state": thong_tin["state"]} if thong_tin["state"] else {}
    quyet_dinh = str(form.get("quyet_dinh", ""))
    if quyet_dinh == "tu_choi":
        trang_thai.kho_phien_tiktok.lay_mot_lan(phien, bay_gio)
        return RedirectResponse(uy_quyen.noi_query(dich, {"error": "access_denied", **them}), status_code=303)
    ten_shop = str(form.get("shop", ""))
    if quyet_dinh != "dong_y" or ten_shop not in trang_thai.cac_shop_tiktok:
        return _trang_loi("Chưa chọn gian hàng hợp lệ.")
    trang_thai.kho_phien_tiktok.lay_mot_lan(phien, bay_gio)
    ma = trang_thai.kho_ma_tiktok.cap_ma(bay_gio, shop_cipher=trang_thai.cac_shop_tiktok[ten_shop])
    return RedirectResponse(uy_quyen.noi_query(dich, {"code": ma, **them}), status_code=303)


@router.get(DUONG_DAN_TOKEN_GET)
def doi_ma_lay_token(request: Request):
    """Đổi `auth_code` lấy cặp token (máy chủ auth, không ký) — đã xác minh (tiktok_auth.py:406-417).

    Query: app_key, app_secret, auth_code, `grant_type=authorized_code` (KHÔNG phải `authorization_code` như OAuth chuẩn).
    auth_code dùng MỘT lần, hết hạn sau 30 phút (tài liệu bàn giao); khóa ứng dụng / grant_type sai thì KHÔNG tiêu mã.
    Trường trả về: chỉ `access_token`, `refresh_token` như endpoint làm mới. Ủy quyền lại một shop đang có: cấp cặp token
    MỚI, token cũ vẫn dùng tới hạn (GIẢ ĐỊNH, §16).
    """
    kiem_qua_tai(request)
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh
    app_key = lay_tham_so(request, "app_key")
    app_secret = lay_tham_so(request, "app_secret")
    auth_code = lay_tham_so(request, "auth_code")
    if lay_tham_so(request, "grant_type") != "authorized_code":
        raise LoiTikTok(MA_THAM_SO_SAI, "grant_type phải là authorized_code")
    if app_key != cau_hinh.TIKTOK_APP_KEY or not signature.chu_ky_khop(app_secret, cau_hinh.TIKTOK_APP_SECRET):
        raise LoiTikTok(MA_REFRESH_SAI, "app_key / app_secret không hợp lệ")

    bay_gio = int(trang_thai.dong_ho())
    try:
        thong_tin = trang_thai.kho_ma_tiktok.lay_mot_lan(auth_code, bay_gio)
    except uy_quyen.MaKhongHopLe:
        raise LoiTikTok(MA_MA_UY_QUYEN_SAI, "auth_code không hợp lệ, đã dùng hoặc đã hết hạn") from None
    access_moi, refresh_moi = secrets.token_hex(16), secrets.token_hex(16)
    trang_thai.kho_token_tiktok.nap_san(thong_tin["shop_cipher"], access_moi, refresh_moi, bay_gio)
    return tra_loi_thanh_cong({"access_token": access_moi, "refresh_token": refresh_moi})


@router.get(DUONG_DAN_SHOPS)
async def danh_sach_shop_da_uy_quyen(request: Request):
    """Danh sách shop mà token này được ủy quyền (đã xác minh: `Authorization/Get Authorized Shops.md`).

    Query chỉ có app_key, timestamp, sign (KHÔNG có shop_cipher — đó là việc endpoint này làm: cấp `cipher`); header
    `x-tts-access-token`. Trả `data.shops[]` gồm id, name, region, seller_type, cipher, code. Mỗi token của bản giả lập
    gắn với MỘT shop nên danh sách có đúng một phần tử.
    """
    kiem_qua_tai(request)
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh
    app_key = lay_tham_so(request, "app_key")
    timestamp = lay_tham_so(request, "timestamp")
    chu_ky = lay_tham_so(request, "sign")
    if app_key != cau_hinh.TIKTOK_APP_KEY:
        raise LoiTikTok(MA_THAM_SO_SAI, "app_key không hợp lệ")
    bay_gio = int(trang_thai.dong_ho())
    if not signature.thoi_gian_hop_le(timestamp, bay_gio):
        raise LoiTikTok(MA_LECH_THOI_GIAN, "timestamp lệch quá 5 phút")
    than = (await request.body()).decode("utf-8")
    chu_ky_dung = signature.tinh_chu_ky_tiktok(cau_hinh.TIKTOK_APP_SECRET, request.url.path, dict(request.query_params), than)
    if not signature.chu_ky_khop(chu_ky, chu_ky_dung):
        raise LoiTikTok(MA_SAI_CHU_KY, "Sai chữ ký")

    try:
        shop_cipher = trang_thai.kho_token_tiktok.shop_cua_access_token(request.headers.get("x-tts-access-token", ""), bay_gio)
    except tokens.TokenKhongHopLe as loi:
        if loi.ly_do == tokens.LY_DO_TOKEN_HET_HAN:
            raise LoiTikTok(MA_TOKEN_HET_HAN, "access_token đã hết hạn") from None
        raise LoiTikTok(MA_TOKEN_SAI, "access_token không hợp lệ") from None
    ten_shop = next(ten for ten, cipher in trang_thai.cac_shop_tiktok.items() if cipher == shop_cipher)
    return tra_loi_thanh_cong({"shops": [{
        "id": uy_quyen.ID_TIKTOK_GIA[ten_shop], "name": ten_shop, "region": "VN", "seller_type": "LOCAL",
        "cipher": shop_cipher, "code": "MOCK" + ten_shop[-1],
    }]})
