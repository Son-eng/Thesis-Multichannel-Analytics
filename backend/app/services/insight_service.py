# Nhận định bằng AI Gemini 3.6

import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx2

from app.config import settings
from app.services import kpi_service

logger = logging.getLogger(__name__)

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
THOI_GIAN_CHO_GIAY = 45
# Đủ rộng để phần "suy nghĩ" của model không ăn hết phần trả lời.
SO_TOKEN_TOI_DA = 4096
SO_SAN_PHAM_GUI = 5
TEN_SAN_HIEN_THI = {"shopee": "Shopee", "tiktok": "TikTok Shop"}
GIO_VN = timezone(timedelta(hours=7))

CAU_LENH_HE_THONG = """Bạn là trợ lý viết nhận định ngắn cho người quản lý bán hàng trên sàn thương mại điện tử.
Bạn nhận một JSON số liệu đã được hệ thống tính sẵn và đã loại đơn hủy, đơn hoàn. Hãy viết nhận định bằng tiếng Việt.

QUY TẮC BẮT BUỘC:
- Chỉ diễn giải các số có trong JSON. KHÔNG tự tính số mới (không cộng, trừ, nhân, chia, không tính chênh lệch), KHÔNG làm tròn sang số không có trong dữ liệu, KHÔNG nhắc số nào ngoài JSON.
- KHÔNG suy đoán nguyên nhân (không nói "do khuyến mãi", "do mùa vụ", "do quảng cáo"...). Chỉ mô tả điều số liệu cho thấy.
- Nếu "period_complete" là false: nói rõ số liệu chỉ "tính đến ngày" trong "data_max_date" (dạng ngày/tháng), không nói như thể cả kỳ; kỳ so sánh đã được cắt cùng số ngày.
- Nếu "pct_change" là null: KHÔNG bình luận xu hướng tăng hay giảm. Nếu "previous_zero" là true: nói kỳ trước không có doanh thu.
- Nếu "alert_triggered" là true: nêu rằng doanh thu giảm đủ mạnh để cảnh báo.
- Cách viết số: tiền viết đủ có dấu chấm phân cách hàng nghìn (ví dụ 840.035.154 đồng) hoặc làm tròn theo triệu (ví dụ 840 triệu đồng); phần trăm dùng dấu phẩy thập phân (ví dụ 34,6%).
- Gọi sản phẩm bằng "product_code" đúng như trong JSON.
- Viết tối đa 5 câu, văn phong ngắn gọn, trung lập. Doanh thu ở đây là NMV sau thuế, chưa phải lợi nhuận.
- Chỉ trả về đoạn văn nhận định, không tiêu đề, không danh sách, không định dạng markdown."""


class LoiLLM(Exception):
    """Không sinh được nhận định; thong_diep an toàn để trả cho người dùng."""

    def __init__(self, thong_diep):
        self.thong_diep = thong_diep
        super().__init__(thong_diep)


def dung_du_lieu_gui(phien, san, muc, ma_ky):
    """Chỉ gửi số liệu tổng hợp từ kpi_service, không gửi dữ liệu dòng hay thông tin khách hàng."""
    kpi = kpi_service.kpi(phien, san, muc, ma_ky)
    metrics = kpi["metrics"]
    doanh_thu = metrics["revenue"]
    du_lieu = {
        "platform": TEN_SAN_HIEN_THI[san],
        "granularity": muc,
        "period": kpi["period"],
        "period_complete": kpi["period_complete"],
        "data_max_date": kpi["data_max_date"],
        "date_from": kpi["current"]["date_from"],
        "date_to": kpi["current"]["date_to"],
        "previous_period": None if kpi["previous"] is None else kpi["previous"]["period"],
        "previous_date_from": None if kpi["previous"] is None else kpi["previous"]["date_from"],
        "previous_date_to": None if kpi["previous"] is None else kpi["previous"]["date_to"],
        "revenue": doanh_thu["value"],
        "revenue_previous": doanh_thu["previous"],
        "pct_change": doanh_thu["pct_change"],
        "previous_zero": doanh_thu["previous_zero"],
        "alert_triggered": kpi["alert"]["triggered"],
        "order_count": metrics["order_count"]["value"],
        "order_count_previous": metrics["order_count"]["previous"],
        "quantity_sold": metrics["quantity_sold"]["value"],
        "aov": metrics["aov"]["value"],
        "aov_previous": metrics["aov"]["previous"],
        "top_products": [],
    }
    if kpi["status"] != "no_data":
        top = kpi_service.top_products(phien, san, muc, kpi["period"], SO_SAN_PHAM_GUI, "revenue")
        du_lieu["top_products"] = [
            {"product_code": m["product_code"], "revenue": m["revenue"], "change_pct": m["pct_change"]}
            for m in top["items"]]
    return du_lieu, kpi


MAU_SO = re.compile(r"\d+(?:[.,]\d+)*")
DON_VI = {"tỷ": 1e9, "tỉ": 1e9, "triệu": 1e6, "nghìn": 1e3, "ngàn": 1e3}


def doc_so(chuoi):
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", chuoi):
        phan_nguyen, _, thap_phan = chuoi.replace(".", "").partition(",")
    elif "," in chuoi:
        phan_nguyen, _, thap_phan = chuoi.partition(",")
        phan_nguyen = phan_nguyen.replace(".", "")
    elif re.fullmatch(r"\d+\.\d{1,2}", chuoi):
        phan_nguyen, _, thap_phan = chuoi.partition(".")
    else:
        phan_nguyen, thap_phan = chuoi.replace(".", ""), ""
    return float(f"{phan_nguyen}.{thap_phan}" if thap_phan else phan_nguyen), len(thap_phan)


def _gom_so_cho_phep(du_lieu):
    so = set()

    def duyet(gia_tri):
        if isinstance(gia_tri, bool) or gia_tri is None:
            return
        if isinstance(gia_tri, (int, float)):
            so.add(abs(float(gia_tri)))
        elif isinstance(gia_tri, str):
            for khop in MAU_SO.findall(gia_tri):
                so.add(float(khop.replace(",", ".")) if khop.count(".") + khop.count(",") <= 1 else float(re.sub(r"[.,]", "", khop)))
        elif isinstance(gia_tri, dict):
            for v in gia_tri.values():
                duyet(v)
        elif isinstance(gia_tri, (list, tuple)):
            for v in gia_tri:
                duyet(v)
    duyet(du_lieu)
    so.update(float(h) for h in range(1, len(du_lieu.get("top_products", [])) + 1))
    return so


def tim_so_la(van_ban, du_lieu):
    """Số trong văn bản không có trong dữ liệu đã gửi, có cho phép làm tròn hợp lý."""
    cho_phep = _gom_so_cho_phep(du_lieu)
    la = []
    for khop in MAU_SO.finditer(van_ban):
        gia_tri, chu_so_thap_phan = doc_so(khop.group())
        phan_sau = van_ban[khop.end():khop.end() + 8].strip().lower()
        he_so = next((hs for tu, hs in DON_VI.items() if phan_sau.startswith(tu)), 1.0)
        dung_sai = 0.5 * (10 ** -chu_so_thap_phan) * he_so + 1e-9
        gia_tri_dong = gia_tri * he_so
        if not any(abs(gia_tri_dong - v) <= dung_sai for v in cho_phep):
            la.append(khop.group())
    return la


def _thong_diep_loi_http(ma):
    if ma == 429:
        return "Đã hết hạn mức gọi Gemini, thử lại sau"
    if ma in (400, 401, 403):
        return "Khóa Gemini không hợp lệ hoặc chưa được cấp quyền"
    return "Gemini đang gặp sự cố, thử lại sau"


def goi_gemini(client, noi_dung_nguoi_dung):
    """Khóa API chỉ đi trong header x-goog-api-key, không vào URL hay log."""
    khoa = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY is not None else ""
    if not khoa:
        raise LoiLLM("Chưa cấu hình GEMINI_API_KEY")
    body = {
        "systemInstruction": {"parts": [{"text": CAU_LENH_HE_THONG}]},
        "contents": [{"role": "user", "parts": [{"text": noi_dung_nguoi_dung}]}],
        "generationConfig": {"maxOutputTokens": SO_TOKEN_TOI_DA},
    }
    if settings.GEMINI_THINKING_LEVEL:
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": settings.GEMINI_THINKING_LEVEL}
    try:
        phan_hoi = client.post(URL_GEMINI.format(model=settings.GEMINI_MODEL), json=body,
                               headers={"x-goog-api-key": khoa})
    except httpx2.HTTPError as loi:
        # Chỉ ghi loại lỗi vì thông điệp của thư viện có thể chứa URL, header.
        logger.warning("Gọi Gemini lỗi mạng: %s", type(loi).__name__)
        raise LoiLLM("Không kết nối được Gemini") from None
    if phan_hoi.status_code != 200:
        logger.warning("Gemini trả mã HTTP %s", phan_hoi.status_code)
        raise LoiLLM(_thong_diep_loi_http(phan_hoi.status_code))
    try:
        ung_vien = phan_hoi.json()["candidates"][0]
        van_ban = "".join(p.get("text", "") for p in ung_vien["content"]["parts"]).strip()
        ly_do_dung = ung_vien.get("finishReason", "STOP")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        logger.warning("Gemini trả phản hồi không đúng khuôn")
        raise LoiLLM("Gemini trả phản hồi không đọc được") from None
    if ly_do_dung != "STOP" or not van_ban:
        logger.warning("Gemini dừng với finishReason=%s", ly_do_dung)
        raise LoiLLM("Gemini không trả về văn bản hoàn chỉnh")
    return van_ban


def sinh_nhan_dinh(phien, san, muc, ma_ky, transport=None):
    """transport chỉ test truyền vào để không gọi Gemini thật."""
    du_lieu, kpi = dung_du_lieu_gui(phien, san, muc, ma_ky)
    ket_qua = {"generated_at": datetime.now(GIO_VN).isoformat(timespec="seconds"),
               "period_complete": kpi["period_complete"], "data_max_date": kpi["data_max_date"]}
    if kpi["status"] == "no_data":
        # Không có số để diễn giải thì không gọi LLM, trả câu cố định.
        ket_qua["text"] = f"Kỳ {kpi['period']} của {TEN_SAN_HIEN_THI[san]} chưa có dữ liệu nên chưa thể nhận định."
        return ket_qua

    json_gui = json.dumps(du_lieu, ensure_ascii=False, indent=2)
    noi_dung = f"Số liệu:\n{json_gui}\n\nHãy viết nhận định theo đúng quy tắc."
    so_lan_bi_chan = 0
    with httpx2.Client(timeout=THOI_GIAN_CHO_GIAY, transport=transport) as client:
        for lan in range(2):
            van_ban = goi_gemini(client, noi_dung)
            so_la = tim_so_la(van_ban, du_lieu)
            if not so_la:
                if so_lan_bi_chan:
                    logger.warning("Nhận định đạt sau %d lần bị chặn vì số lạ", so_lan_bi_chan)
                ket_qua["text"] = van_ban
                return ket_qua
            so_lan_bi_chan += 1
            logger.warning("Nhận định bị chặn vì số không có trong dữ liệu (lần %d, %d số lạ)", lan + 1, len(so_la))
            noi_dung = (f"Số liệu:\n{json_gui}\n\nLần viết trước chứa số KHÔNG có trong số liệu: {', '.join(so_la)}. "
                        "Viết lại, chỉ dùng đúng các số có trong số liệu, không tự tính số mới.")
    raise LoiLLM("Nhận định chứa số không có trong dữ liệu")
