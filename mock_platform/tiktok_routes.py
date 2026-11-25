"""Các endpoint TikTok của máy chủ giả lập; mã lỗi dải 9990xxx là mã quy ước của bản giả lập."""

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
DUONG_DAN_TRANG_UY_QUYEN = "/open/authorize"
DUONG_DAN_QUYET_DINH = "/mock/tiktok/quyet-dinh"
DUONG_DAN_TOKEN_GET = "/api/v2/token/get"
DUONG_DAN_SHOPS = "/authorization/202309/shops"

# "3 tháng" không rõ số ngày nên giả định 93 ngày.
KHOANG_AFFILIATE_TOI_DA_GIAY = 93 * 24 * 60 * 60

# Dải 9990xxx để không trùng mã thật và nhìn là biết của bản giả lập.
MA_SAI_CHU_KY = 9990001
MA_LECH_THOI_GIAN = 9990002
MA_TOKEN_SAI = 9990003
MA_TOKEN_HET_HAN = 9990004
MA_THAM_SO_SAI = 9990005
MA_REFRESH_SAI = 9990006
MA_MA_UY_QUYEN_SAI = 9990007
# Mã quá tải thật, dùng cho MOCK_FAULT_RATE.
MA_QUA_TAI = 36009002

PAGE_SIZE_TOI_THIEU = 1
PAGE_SIZE_TOI_DA = 100
TRUONG_SAP_XEP = {"create_time", "update_time"}
CHIEU_SAP_XEP = {"ASC", "DESC"}


class LoiTikTok(Exception):
    def __init__(self, ma_loi, thong_diep):
        super().__init__(f"{ma_loi}: {thong_diep}")
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


async def xu_ly_loi_tiktok(request, loi):
    await request.body()
    return JSONResponse(
        status_code=200,
        content={"code": loi.ma_loi, "message": loi.thong_diep, "request_id": secrets.token_hex(16)},
    )


def tra_loi_thanh_cong(du_lieu):
    return {"code": 0, "message": "Success", "request_id": secrets.token_hex(16), "data": du_lieu}


def kiem_qua_tai(request):
    """Gọi đầu tiên ở mọi route TikTok để yêu cầu bị gây lỗi không chạm vào trạng thái."""
    if gay_loi.nen_gay_loi(request.app.state):
        raise LoiTikTok(MA_QUA_TAI, "Too many requests (lỗi có chủ đích của bản giả lập)")


def lay_tham_so(request, ten):
    gia_tri = request.query_params.get(ten, "")
    if gia_tri == "":
        raise LoiTikTok(MA_THAM_SO_SAI, f"Thiếu tham số {ten}")
    return gia_tri


async def kiem_yeu_cau_open_api(request):
    """Chữ ký tính trên đúng đường dẫn và body từng byte đã nhận, không parse rồi serialize lại."""
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
    return trang_thai.du_lieu_tiktok_theo_cipher[shop_cipher], than


def doc_body_json(than):
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
    gia_tri = than.get(ten)
    if gia_tri is None:
        return None
    if not isinstance(gia_tri, int) or isinstance(gia_tri, bool):
        raise LoiTikTok(MA_THAM_SO_SAI, f"{ten} phải là số nguyên (Unix timestamp)")
    return gia_tri


def nam_trong_khoang(gia_tri, tu_moc, den_moc, bay_gio):
    if tu_moc is None and den_moc is None:
        return True
    tu_moc = 0 if tu_moc is None else tu_moc
    den_moc = bay_gio if den_moc is None else den_moc
    return tu_moc <= gia_tri < den_moc


@router.post(DUONG_DAN_ORDERS_SEARCH)
async def orders_search(request: Request):
    """Hết trang thì next_page_token = "" (giả định)."""
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
    # Thêm id vào khóa sắp xếp để thứ tự cố định khi trùng thời điểm.
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
    """Cặp (đơn, sku_id) có trong skus[] là affiliate; không sinh creator_username vì là tên tài khoản thật."""
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
        tu_moc = bay_gio - KHOANG_AFFILIATE_TOI_DA_GIAY
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
    """Đơn không phải COMPLETED trả danh sách rỗng (giả định, backend không gọi nhánh này)."""
    shop, _ = await kiem_yeu_cau_open_api(request)
    giao_dich = shop["finance"].get(order_id, [])
    return tra_loi_thanh_cong({
        "order_id": order_id,
        "sku_transactions": giao_dich,
        "total_count": len(giao_dich),
    })


@router.get(DUONG_DAN_REFRESH)
def refresh_token(request: Request):
    """Không ký, không trả hạn sống; refresh_token cũ không bị vô hiệu."""
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


def _trang_loi(thong_diep):
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><p>{thong_diep}</p>", status_code=400)


@router.get(DUONG_DAN_TRANG_UY_QUYEN)
def trang_uy_quyen(request: Request):
    """state không có trong tài liệu, ở đây nhận tùy chọn và trả lại nguyên vẹn (giả định)."""
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
    """TikTok không nhận địa chỉ chuyển về ở URL, dùng TIKTOK_REDIRECT_URL của cấu hình."""
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
    """grant_type là authorized_code, không phải authorization_code; mã dùng một lần, hết hạn sau 30 phút."""
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
    """Mỗi token của bản giả lập gắn với một shop nên danh sách có đúng một phần tử."""
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
