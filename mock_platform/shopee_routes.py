"""4 endpoint Shopee của máy chủ giả lập (SPEC §19.2, §19.3).

Mỗi yêu cầu đi qua cùng một trình tự kiểm (`kiem_tham_so_chung`):
    đủ tham số chung → đúng partner_id → timestamp ±5 phút → đúng chữ ký
    → (Shop API) access_token còn hạn và thuộc đúng shop
rồi mới tới phần riêng của endpoint (giới hạn tham số, lấy dữ liệu).

Mã lỗi theo tài liệu tóm tắt Shopee (mục mã lỗi):
    error_param — thiếu/sai tham số, kể cả timestamp lệch
    error_sign  — sai chữ ký
    error_auth  — access_token / partner_id không hợp lệ
    refresh_token_expired — refresh_token quá 30 ngày
Refresh_token đã dùng / không tồn tại → error_auth: GIẢ ĐỊNH của bản giả lập,
tài liệu không có mã riêng (§16 mục 7).

Khuôn phản hồi theo mục 7 tài liệu: `request_id`, `error` ("" nếu thành
công), `message`, `warning` (khi lô có phần lỗi), `response` (dữ liệu).
"""

import json
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import signature
import tokens

router = APIRouter()

DUONG_DAN_ORDER_LIST = "/api/v2/order/get_order_list"
DUONG_DAN_ORDER_DETAIL = "/api/v2/order/get_order_detail"
DUONG_DAN_ESCROW_BATCH = "/api/v2/payment/get_escrow_detail_batch"
DUONG_DAN_REFRESH = "/api/v2/auth/access_token/get"

# Giới hạn tham số theo tài liệu (§19.2).
CUA_SO_TOI_DA_GIAY = 15 * 24 * 60 * 60
PAGE_SIZE_TOI_THIEU = 1
PAGE_SIZE_TOI_DA = 100
SO_MA_DON_TOI_DA = 50
# Escrow batch: tài liệu không ghi giới hạn; dùng 50 như Pipeline (§19.2).
SO_MA_DON_ESCROW_TOI_DA = 50

TRUONG_LOC_THOI_GIAN = {"create_time", "update_time"}
# get_order_detail: mặc định trả ít trường; item_list và recipient_address
# phải xin qua response_optional_fields (tài liệu, mục get_order_detail).
TRUONG_DON_MAC_DINH = ["order_sn", "order_status", "create_time", "update_time"]
TRUONG_DON_TUY_CHON = ["item_list", "recipient_address"]

# Đơn không trả được escrow trong lô. Giá trị `fail_error` do bản giả lập tự
# đặt, cố ý có tiền tố "mock_" để không ai nhầm là mã thật (§16 mục 6).
LOI_ESCROW_KHONG_CO = "mock_escrow_not_available"


class LoiShopee(Exception):
    """Yêu cầu bị từ chối. Được đổi thành phản hồi Shopee có `error` khác rỗng."""

    def __init__(self, ma_loi, thong_diep):
        super().__init__(f"{ma_loi}: {thong_diep}")
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep


async def xu_ly_loi_shopee(request, loi):
    """Đổi LoiShopee thành phản hồi lỗi theo khuôn mục 7 tài liệu.

    Trả HTTP 200: tài liệu chỉ mô tả lỗi qua trường `error`, không nói mã
    HTTP — GIẢ ĐỊNH của bản giả lập (§16 mục 8). Connector phải đọc `error`.
    """
    return JSONResponse(
        status_code=200,
        content={"request_id": secrets.token_hex(16), "error": loi.ma_loi, "message": loi.thong_diep},
    )


def tra_loi_thanh_cong(du_lieu, canh_bao=None):
    """Bọc dữ liệu vào khuôn phản hồi thành công (mục 7 tài liệu)."""
    phan_hoi = {"request_id": secrets.token_hex(16), "error": "", "message": "", "response": du_lieu}
    if canh_bao:
        phan_hoi["warning"] = canh_bao
    return phan_hoi


def lay_tham_so(request, ten):
    """Tham số query bắt buộc (chuỗi). Thiếu hoặc rỗng → error_param."""
    gia_tri = request.query_params.get(ten, "")
    if gia_tri == "":
        raise LoiShopee("error_param", f"Thiếu tham số {ten}")
    return gia_tri


def lay_so_nguyen(request, ten):
    """Tham số query bắt buộc kiểu số nguyên. Không phải số → error_param."""
    gia_tri = lay_tham_so(request, ten)
    try:
        return int(gia_tri)
    except ValueError:
        raise LoiShopee("error_param", f"{ten} phải là số nguyên") from None


def tach_danh_sach(chuoi):
    """"a, b,,c" → ["a", "b", "c"]: tài liệu nối các giá trị bằng dấu phẩy."""
    return [phan.strip() for phan in chuoi.split(",") if phan.strip()]


async def doc_body_json(request):
    """Body JSON dạng object của yêu cầu POST. Không đọc được → error_param."""
    try:
        than = json.loads(await request.body())
    except json.JSONDecodeError:
        raise LoiShopee("error_param", "Body không phải JSON hợp lệ") from None
    if not isinstance(than, dict):
        raise LoiShopee("error_param", "Body phải là một object JSON")
    return than


def kiem_tham_so_chung(request, duong_dan, la_shop_api):
    """Kiểm tham số chung, chữ ký, timestamp, (Shop API) access_token.

    Nhận: request; đường dẫn API (là một phần chuỗi ký); la_shop_api — True
    nếu cần access_token + shop_id, False với Public API (làm mới token).
    Trả: (shop_id dạng chuỗi — "" với Public API, bay_gio epoch giây).
    Ký trên đúng chuỗi client gửi lên, không đổi kiểu trước khi ký.
    """
    trang_thai = request.app.state
    cau_hinh = trang_thai.cau_hinh

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
    """Danh sách order_sn trong một khoảng thời gian ≤ 15 ngày, phân trang bằng cursor.

    Khoảng thời gian lấy CẢ HAI đầu [time_from, time_to] — tài liệu không nói,
    GIẢ ĐỊNH (§16 mục 8); bên gọi chia cửa sổ nối tiếp thì nên để cửa sổ sau
    bắt đầu từ time_to + 1. Thứ tự trả về: theo trường thời gian rồi order_sn,
    để phân trang ổn định giữa các lần gọi.
    """
    kiem_tham_so_chung(request, DUONG_DAN_ORDER_LIST, la_shop_api=True)

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

    # cursor là chuỗi "mờ" với bên gọi; ở đây chính là vị trí bắt đầu trang.
    cursor = request.query_params.get("cursor", "")
    if cursor != "" and not cursor.isdigit():
        raise LoiShopee("error_param", "cursor không hợp lệ")
    vi_tri = int(cursor or 0)

    loc_trang_thai = request.query_params.get("order_status")
    cac_don = [
        don for don in request.app.state.du_lieu_shopee["don_hang"].values()
        if tu_luc <= don[truong_thoi_gian] <= den_luc
        and (loc_trang_thai is None or don["order_status"] == loc_trang_thai)
    ]
    cac_don.sort(key=lambda don: (don[truong_thoi_gian], don["order_sn"]))

    trang = cac_don[vi_tri:vi_tri + so_moi_trang]
    con_nua = vi_tri + so_moi_trang < len(cac_don)
    # Tài liệu: mặc định chỉ trả order_sn; order_status khi xin qua response_optional_fields.
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
    """Chi tiết tối đa 50 đơn. item_list, recipient_address chỉ có khi xin qua response_optional_fields.

    Mã đơn không tồn tại thì bỏ qua, không báo lỗi — tài liệu không mô tả,
    GIẢ ĐỊNH (§16 mục 8). Backend chỉ hỏi mã vừa lấy từ get_order_list.
    """
    kiem_tham_so_chung(request, DUONG_DAN_ORDER_DETAIL, la_shop_api=True)

    cac_ma_don = tach_danh_sach(lay_tham_so(request, "order_sn_list"))
    if len(cac_ma_don) > SO_MA_DON_TOI_DA:
        raise LoiShopee("error_param", "order_sn_list vượt quá 50 mã")
    truong_xin_them = tach_danh_sach(request.query_params.get("response_optional_fields", ""))
    cac_truong = TRUONG_DON_MAC_DINH + [t for t in TRUONG_DON_TUY_CHON if t in truong_xin_them]

    du_lieu_don = request.app.state.du_lieu_shopee["don_hang"]
    danh_sach = [
        {truong: du_lieu_don[ma][truong] for truong in cac_truong}
        for ma in cac_ma_don
        if ma in du_lieu_don
    ]
    return tra_loi_thanh_cong({"order_list": danh_sach})


@router.post(DUONG_DAN_ESCROW_BATCH)
async def get_escrow_detail_batch(request: Request):
    """Escrow của tối đa 50 đơn. Công tắc MOCK_ESCROW_MODE (§19.2).

    Phần trong `escrow_detail` theo ESCROW_FIELD_REFERENCE.md
    (`order_sn`, `order_income.items[]`). Lớp bọc của bản batch và cách báo
    từng đơn lỗi là GIẢ ĐỊNH (§16 mục 6): đơn lỗi là phần tử
    {order_sn, fail_error, fail_message}, kèm `warning` ở cấp ngoài — tài liệu
    nói `warning` dùng khi "batch request có phần fail".
    """
    kiem_tham_so_chung(request, DUONG_DAN_ESCROW_BATCH, la_shop_api=True)

    than = await doc_body_json(request)
    cac_ma_don = than.get("order_sn_list")
    if not isinstance(cac_ma_don, list) or not cac_ma_don or not all(isinstance(ma, str) for ma in cac_ma_don):
        raise LoiShopee("error_param", "order_sn_list phải là danh sách mã đơn, không rỗng")
    if len(cac_ma_don) > SO_MA_DON_ESCROW_TOI_DA:
        raise LoiShopee("error_param", "order_sn_list vượt quá 50 mã")

    trang_thai = request.app.state
    chi_don_hoan_tat = trang_thai.cau_hinh.MOCK_ESCROW_MODE == "completed_only"
    du_lieu_don = trang_thai.du_lieu_shopee["don_hang"]
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
            ket_qua.append({"escrow_detail": trang_thai.du_lieu_shopee["escrow"][ma]})

    canh_bao = f"Không có escrow cho {len(ma_don_loi)} đơn: {', '.join(ma_don_loi)}" if ma_don_loi else None
    return tra_loi_thanh_cong(ket_qua, canh_bao)


@router.post(DUONG_DAN_REFRESH)
async def refresh_access_token(request: Request):
    """Đổi refresh_token lấy cặp token mới (Public API: chữ ký không có access_token, shop_id).

    Body: refresh_token, partner_id, shop_id (tài liệu). Refresh_token cũ bị
    vô hiệu sau khi dùng (§19.2). Trường trả về đặt trong `response` theo
    khuôn chung mục 7 tài liệu — tài liệu không nói riêng cho endpoint này,
    GIẢ ĐỊNH (§16 mục 8).
    """
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
        # GIẢ ĐỊNH (§16 mục 7): tài liệu không có mã riêng cho refresh_token
        # đã dùng / không tồn tại; error_auth là mã tài liệu dùng cho token không hợp lệ.
        raise LoiShopee("error_auth", "refresh_token không hợp lệ hoặc đã dùng") from None

    return tra_loi_thanh_cong({
        "access_token": access_moi,
        "refresh_token": refresh_moi,
        "expire_in": trang_thai.kho_token_shopee.han_access_giay,
    })
