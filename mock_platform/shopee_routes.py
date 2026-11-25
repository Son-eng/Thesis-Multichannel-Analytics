# Chứa các endpoint của Shopee v2
import json
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import gay_loi
import signature
import tokens
import uy_quyen

router = APIRouter()

DUONG_DAN_ORDER_LIST = "/api/v2/order/get_order_list"
DUONG_DAN_ORDER_DETAIL = "/api/v2/order/get_order_detail"
DUONG_DAN_ESCROW_BATCH = "/api/v2/payment/get_escrow_detail_batch"
DUONG_DAN_REFRESH = "/api/v2/auth/access_token/get"
DUONG_DAN_CONVERSION = "/api/v2/ams/get_conversion_report"
DUONG_DAN_AUTH_PARTNER = "/api/v2/shop/auth_partner"
DUONG_DAN_TOKEN_GET = "/api/v2/auth/token/get"
DUONG_DAN_QUYET_DINH = "/mock/shopee/quyet-dinh"
LOI_MA_UY_QUYEN_SAI = "invalid_code"

CUA_SO_TOI_DA_GIAY = 15 * 24 * 60 * 60
PAGE_SIZE_TOI_THIEU = 1
PAGE_SIZE_TOI_DA = 100
SO_MA_DON_TOI_DA = 50
# Tài liệu không ghi giới hạn escrow, dùng 50.
SO_MA_DON_ESCROW_TOI_DA = 50

TRUONG_LOC_THOI_GIAN = {"create_time", "update_time"}
# Mặc định trả ít trường; item_list và recipient_address phải xin qua response_optional_fields.
TRUONG_DON_MAC_DINH = ["order_sn", "order_status", "create_time", "update_time"]
TRUONG_DON_TUY_CHON = ["item_list", "recipient_address"]

# fail_error có tiền tố "mock_" để không ai nhầm là mã thật.
LOI_ESCROW_KHONG_CO = "mock_escrow_not_available"


def du_lieu_cua_shop(trang_thai, shop_id):
    if str(shop_id) == str(trang_thai.cau_hinh.SHOPEE_SHOP_ID):
        return trang_thai.du_lieu_shopee
    return {"don_hang": {}, "escrow": {}, "affiliate": {}}


class LoiShopee(Exception):
    def __init__(self, ma_loi, thong_diep, ma_http=200):
        super().__init__(f"{ma_loi}: {thong_diep}")
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep
        self.ma_http = ma_http


async def xu_ly_loi_shopee(request, loi):
    # Đọc hết body trước khi trả lỗi, nếu không uvicorn đóng kết nối và client nhận "connection reset".
    await request.body()
    return JSONResponse(
        status_code=loi.ma_http,
        content={"request_id": secrets.token_hex(16), "error": loi.ma_loi, "message": loi.thong_diep},
    )


def tra_loi_thanh_cong(du_lieu, canh_bao=None):
    phan_hoi = {"request_id": secrets.token_hex(16), "error": "", "message": "", "response": du_lieu}
    if canh_bao:
        phan_hoi["warning"] = canh_bao
    return phan_hoi


def lay_tham_so(request, ten):
    gia_tri = request.query_params.get(ten, "")
    if gia_tri == "":
        raise LoiShopee("error_param", f"Thiếu tham số {ten}")
    return gia_tri


def lay_so_nguyen(request, ten):
    gia_tri = lay_tham_so(request, ten)
    try:
        return int(gia_tri)
    except ValueError:
        raise LoiShopee("error_param", f"{ten} phải là số nguyên") from None


def tach_danh_sach(chuoi):
    return [phan.strip() for phan in chuoi.split(",") if phan.strip()]


async def doc_body_json(request):
    try:
        than = json.loads(await request.body())
    except json.JSONDecodeError:
        raise LoiShopee("error_param", "Body không phải JSON hợp lệ") from None
    if not isinstance(than, dict):
        raise LoiShopee("error_param", "Body phải là một object JSON")
    return than


def kiem_tham_so_chung(request, duong_dan, la_shop_api):
    """Gọi đầu tiên ở mọi route Shopee; ký trên đúng chuỗi client gửi lên."""
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh

    if gay_loi.nen_gay_loi(trang_thai):
        raise LoiShopee("error_rate_limit", "Vượt giới hạn tần suất (lỗi có chủ đích của bản giả lập)", ma_http=429)

    partner_id = lay_tham_so(request, "partner_id")
    timestamp = lay_tham_so(request, "timestamp")
    chu_ky = lay_tham_so(request, "sign")
    access_token = lay_tham_so(request, "access_token") if la_shop_api else ""
    shop_id = lay_tham_so(request, "shop_id") if la_shop_api else ""

    if partner_id != str(cau_hinh.SHOPEE_PARTNER_ID):
        raise LoiShopee("error_auth", "partner_id không hợp lệ")
    bay_gio = int(trang_thai.dong_ho())
    if not signature.thoi_gian_hop_le(timestamp, bay_gio):
        raise LoiShopee("error_param", "timestamp lệch quá 5 phút")
    chu_ky_dung = signature.tinh_chu_ky_shopee(
        cau_hinh.SHOPEE_PARTNER_KEY, partner_id, duong_dan, timestamp, access_token, shop_id
    )
    if not signature.chu_ky_khop(chu_ky, chu_ky_dung):
        raise LoiShopee("error_sign", "Sai chữ ký")
    if la_shop_api:
        try:
            trang_thai.kho_token_shopee.kiem_access_token(access_token, shop_id, bay_gio)
        except tokens.TokenKhongHopLe as loi:
            raise LoiShopee("error_auth", f"access_token không hợp lệ ({loi.ly_do})") from None
    return shop_id, bay_gio


@router.get(DUONG_DAN_ORDER_LIST)
def get_order_list(request: Request):
    """Danh sách order_sn trong một khoảng thời gian ≤ 15 ngày, phân trang bằng cursor."""
    shop_id, _ = kiem_tham_so_chung(request, DUONG_DAN_ORDER_LIST, la_shop_api=True)

    truong_thoi_gian = lay_tham_so(request, "time_range_field")
    if truong_thoi_gian not in TRUONG_LOC_THOI_GIAN:
        raise LoiShopee("error_param", "time_range_field phải là create_time hoặc update_time")
    tu_luc = lay_so_nguyen(request, "time_from")
    den_luc = lay_so_nguyen(request, "time_to")
    if tu_luc > den_luc:
        raise LoiShopee("error_param", "time_from lớn hơn time_to")
    if den_luc - tu_luc > CUA_SO_TOI_DA_GIAY:
        raise LoiShopee("error_param", "Khoảng thời gian vượt quá 15 ngày")
    so_moi_trang = lay_so_nguyen(request, "page_size")
    if not PAGE_SIZE_TOI_THIEU <= so_moi_trang <= PAGE_SIZE_TOI_DA:
        raise LoiShopee("error_param", "page_size phải trong khoảng 1–100")

    # cursor là chuỗi mờ với bên gọi; ở đây chính là vị trí bắt đầu trang.
    cursor = request.query_params.get("cursor", "")
    if cursor != "" and not cursor.isdigit():
        raise LoiShopee("error_param", "cursor không hợp lệ")
    vi_tri = int(cursor or 0)

    loc_trang_thai = request.query_params.get("order_status")
    cac_don = [
        don for don in du_lieu_cua_shop(request.app.state, shop_id)["don_hang"].values()
        if tu_luc <= don[truong_thoi_gian] <= den_luc
        and (loc_trang_thai is None or don["order_status"] == loc_trang_thai)
    ]
    cac_don.sort(key=lambda don: (don[truong_thoi_gian], don["order_sn"]))

    trang = cac_don[vi_tri:vi_tri + so_moi_trang]
    con_nua = vi_tri + so_moi_trang < len(cac_don)
    tra_trang_thai = "order_status" in tach_danh_sach(request.query_params.get("response_optional_fields", ""))
    danh_sach = [
        {"order_sn": don["order_sn"], **({"order_status": don["order_status"]} if tra_trang_thai else {})}
        for don in trang
    ]
    return tra_loi_thanh_cong({
        "more": con_nua,
        "next_cursor": str(vi_tri + so_moi_trang) if con_nua else "",
        "order_list": danh_sach,
    })


@router.get(DUONG_DAN_ORDER_DETAIL)
def get_order_detail(request: Request):
    shop_id, _ = kiem_tham_so_chung(request, DUONG_DAN_ORDER_DETAIL, la_shop_api=True)

    cac_ma_don = tach_danh_sach(lay_tham_so(request, "order_sn_list"))
    if len(cac_ma_don) > SO_MA_DON_TOI_DA:
        raise LoiShopee("error_param", "order_sn_list vượt quá 50 mã")
    truong_xin_them = tach_danh_sach(request.query_params.get("response_optional_fields", ""))
    cac_truong = TRUONG_DON_MAC_DINH + [t for t in TRUONG_DON_TUY_CHON if t in truong_xin_them]

    du_lieu_don = du_lieu_cua_shop(request.app.state, shop_id)["don_hang"]
    danh_sach = [
        {truong: du_lieu_don[ma][truong] for truong in cac_truong}
        for ma in cac_ma_don
        if ma in du_lieu_don
    ]
    return tra_loi_thanh_cong({"order_list": danh_sach})


@router.post(DUONG_DAN_ESCROW_BATCH)
async def get_escrow_detail_batch(request: Request):
    shop_id, _ = kiem_tham_so_chung(request, DUONG_DAN_ESCROW_BATCH, la_shop_api=True)

    than = await doc_body_json(request)
    cac_ma_don = than.get("order_sn_list")
    if not isinstance(cac_ma_don, list) or not cac_ma_don or not all(isinstance(ma, str) for ma in cac_ma_don):
        raise LoiShopee("error_param", "order_sn_list phải là danh sách mã đơn, không rỗng")
    if len(cac_ma_don) > SO_MA_DON_ESCROW_TOI_DA:
        raise LoiShopee("error_param", "order_sn_list vượt quá 50 mã")

    trang_thai = request.app.state
    chi_don_hoan_tat = trang_thai.cau_hinh.MOCK_ESCROW_MODE == "completed_only"
    du_shop = du_lieu_cua_shop(trang_thai, shop_id)
    du_lieu_don = du_shop["don_hang"]
    ket_qua = []
    ma_don_loi = []
    for ma in cac_ma_don:
        khong_tra = ma not in du_lieu_don or (chi_don_hoan_tat and du_lieu_don[ma]["order_status"] != "COMPLETED")
        if khong_tra:
            ma_don_loi.append(ma)
            ket_qua.append({
                "order_sn": ma,
                "fail_error": LOI_ESCROW_KHONG_CO,
                "fail_message": "Đơn chưa có escrow (bản giả lập)",
            })
        else:
            ket_qua.append({"escrow_detail": du_shop["escrow"][ma]})

    canh_bao = f"Không có escrow cho {len(ma_don_loi)} đơn: {', '.join(ma_don_loi)}" if ma_don_loi else None
    return tra_loi_thanh_cong(ket_qua, canh_bao)


@router.get(DUONG_DAN_CONVERSION)
def get_conversion_report(request: Request):
    shop_id, _ = kiem_tham_so_chung(request, DUONG_DAN_CONVERSION, la_shop_api=True)

    tu_luc = lay_so_nguyen(request, "place_order_time_start")
    den_luc = lay_so_nguyen(request, "place_order_time_end")
    if tu_luc > den_luc:
        raise LoiShopee("error_param", "place_order_time_start lớn hơn place_order_time_end")
    so_trang = lay_so_nguyen(request, "page_no")
    if so_trang < 1:
        raise LoiShopee("error_param", "page_no bắt đầu từ 1")
    so_moi_trang = lay_so_nguyen(request, "page_size")
    if not PAGE_SIZE_TOI_THIEU <= so_moi_trang <= PAGE_SIZE_TOI_DA:
        raise LoiShopee("error_param", "page_size phải trong khoảng 1–100")

    cac_don = sorted(
        (thoi_diem_dat, ma) for ma, thoi_diem_dat in du_lieu_cua_shop(request.app.state, shop_id)["affiliate"].items()
        if tu_luc <= thoi_diem_dat <= den_luc
    )
    vi_tri = (so_trang - 1) * so_moi_trang
    trang = cac_don[vi_tri:vi_tri + so_moi_trang]
    return tra_loi_thanh_cong({
        "list": [{"order_sn": ma} for _, ma in trang],
        "has_more": vi_tri + so_moi_trang < len(cac_don),
    })


@router.post(DUONG_DAN_REFRESH)
async def refresh_access_token(request: Request):
    """Refresh_token cũ bị vô hiệu sau khi dùng."""
    _, bay_gio = kiem_tham_so_chung(request, DUONG_DAN_REFRESH, la_shop_api=False)

    than = await doc_body_json(request)
    for ten in ["refresh_token", "partner_id", "shop_id"]:
        if than.get(ten) in (None, ""):
            raise LoiShopee("error_param", f"Thiếu {ten} trong body")
    trang_thai = request.app.state
    if str(than["partner_id"]) != str(trang_thai.cau_hinh.SHOPEE_PARTNER_ID):
        raise LoiShopee("error_auth", "partner_id không hợp lệ")

    try:
        access_moi, refresh_moi = trang_thai.kho_token_shopee.lam_moi(
            str(than["refresh_token"]), str(than["shop_id"]), bay_gio
        )
    except tokens.TokenKhongHopLe as loi:
        if loi.ly_do == tokens.LY_DO_TOKEN_HET_HAN:
            raise LoiShopee("refresh_token_expired", "refresh_token đã quá 30 ngày") from None
        # Tài liệu không có mã riêng cho refresh_token đã dùng, nên dùng error_auth.
        raise LoiShopee("error_auth", "refresh_token không hợp lệ hoặc đã dùng") from None

    return tra_loi_thanh_cong({
        "access_token": access_moi,
        "refresh_token": refresh_moi,
        "expire_in": trang_thai.kho_token_shopee.han_access_giay,
    })


def _trang_loi(thong_diep, ma_http=400):
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><p>{thong_diep}</p>", status_code=ma_http)


@router.get(DUONG_DAN_AUTH_PARTNER)
def trang_uy_quyen(request: Request):
    _, bay_gio = kiem_tham_so_chung(request, DUONG_DAN_AUTH_PARTNER, la_shop_api=False)
    redirect = lay_tham_so(request, "redirect")
    trang_thai = request.app.state
    phien = trang_thai.kho_phien_shopee.mo(bay_gio, redirect=redirect)
    cac_shop = [(ten, shop_id) for shop_id, ten in trang_thai.cac_shop_shopee.items()]
    return HTMLResponse(uy_quyen.trang_uy_quyen(
        "Shopee", "Hệ thống Đa Kênh", cac_shop, phien, DUONG_DAN_QUYET_DINH, "shop_id"))


@router.post(DUONG_DAN_QUYET_DINH)
async def quyet_dinh_uy_quyen(request: Request):
    """Shopee chỉ trả code và shop_id, không trả state; query có sẵn trong redirect được giữ."""
    trang_thai = request.app.state
    bay_gio = int(trang_thai.dong_ho())
    form = await request.form()
    phien = str(form.get("phien", ""))
    quyet_dinh = str(form.get("quyet_dinh", ""))
    try:
        thong_tin = trang_thai.kho_phien_shopee.xem(phien, bay_gio)
    except uy_quyen.PhienKhongHopLe:
        return _trang_loi("Phiên ủy quyền không hợp lệ, đã dùng hoặc đã hết hạn. Hãy mở lại trang ủy quyền.")
    redirect = thong_tin["redirect"]
    if quyet_dinh == "tu_choi":
        trang_thai.kho_phien_shopee.lay_mot_lan(phien, bay_gio)
        return RedirectResponse(uy_quyen.noi_query(redirect, {"error": "access_denied"}), status_code=303)
    shop_id = str(form.get("shop_id", ""))
    if quyet_dinh != "dong_y" or shop_id not in trang_thai.cac_shop_shopee:
        return _trang_loi("Chưa chọn gian hàng hợp lệ.")
    trang_thai.kho_phien_shopee.lay_mot_lan(phien, bay_gio)
    ma = trang_thai.kho_ma_shopee.cap_ma(bay_gio, shop_id=shop_id)
    return RedirectResponse(uy_quyen.noi_query(redirect, {"code": ma, "shop_id": shop_id}), status_code=303)


@router.post(DUONG_DAN_TOKEN_GET)
async def doi_ma_lay_token(request: Request):
    """code dùng một lần, hết hạn sau 10 phút; chữ ký sai thì không tiêu mã."""
    _, bay_gio = kiem_tham_so_chung(request, DUONG_DAN_TOKEN_GET, la_shop_api=False)
    than = await doc_body_json(request)
    for ten in ["code", "partner_id"]:
        if than.get(ten) in (None, ""):
            raise LoiShopee("error_param", f"Thiếu {ten} trong body")
    trang_thai = request.app.state
    if str(than["partner_id"]) != str(trang_thai.cau_hinh.SHOPEE_PARTNER_ID):
        raise LoiShopee("error_auth", "partner_id không hợp lệ")

    ma = str(than["code"])
    try:
        thong_tin = trang_thai.kho_ma_shopee.xem(ma, bay_gio)
        if than.get("shop_id") not in (None, "") and str(than["shop_id"]) != thong_tin["shop_id"]:
            raise uy_quyen.MaKhongHopLe()
        trang_thai.kho_ma_shopee.lay_mot_lan(ma, bay_gio)
    except uy_quyen.MaKhongHopLe:
        raise LoiShopee(LOI_MA_UY_QUYEN_SAI, "code không hợp lệ, đã dùng hoặc đã hết hạn") from None

    access_moi, refresh_moi = secrets.token_hex(16), secrets.token_hex(16)
    trang_thai.kho_token_shopee.nap_san(thong_tin["shop_id"], access_moi, refresh_moi, bay_gio)
    return tra_loi_thanh_cong({
        "access_token": access_moi,
        "refresh_token": refresh_moi,
        "expire_in": trang_thai.kho_token_shopee.han_access_giay,
        "shop_id_list": [int(thong_tin["shop_id"])],
    })
