# Máy chủ giả lập API sàn (`mock_platform/`)

Ứng dụng FastAPI **riêng**, đóng vai Shopee và TikTok Shop ở cổng 8001. Dữ liệu sinh từ 2 file CSV ẩn danh trong `data/samples/` lúc khởi động. Backend chỉ nói chuyện với nó qua HTTP, như với sàn thật: đổi sang sàn thật chỉ cần sửa URL và khóa trong `backend/.env`.

Mọi khóa, token trong `.env.example` đều **giả**.

## Bật / tắt (PowerShell, từ thư mục `mock_platform/`)

Lần đầu: `Copy-Item .env.example .env`

```powershell
# Bật: in PID để tắt đúng tiến trình
$p = Start-Process -FilePath ..\backend\.venv\Scripts\python.exe `
     -ArgumentList "-m","uvicorn","main:tao_ung_dung_tu_env","--factory","--port","8001" `
     -PassThru -WindowStyle Hidden
"PID: $($p.Id)"

# Gọi thử (máy chủ đang chạy)
..\backend\.venv\Scripts\python.exe scripts\goi_thu.py            # mỗi endpoint một lần
..\backend\.venv\Scripts\python.exe scripts\goi_thu.py keo-du     # kéo hết, đối chiếu số CSV
..\backend\.venv\Scripts\python.exe scripts\goi_thu.py loi        # yêu cầu sai → mã lỗi
..\backend\.venv\Scripts\python.exe scripts\goi_thu.py lam-moi    # làm mới token 2 sàn
..\backend\.venv\Scripts\python.exe scripts\goi_thu.py dem-loi 300  # đếm tỷ lệ lỗi quá tải

# Tắt: launcher của .venv sinh thêm một tiến trình python con, nên tắt theo dòng lệnh
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*uvicorn*tao_ung_dung_tu_env*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

- **Không** bật bằng `... &` trong Git Bash: tắt shell không tắt uvicorn, để lại 3 tiến trình mồ côi.
- `lam-moi` dùng hết refresh_token Shopee trong `.env` (chỉ dùng 1 lần). Chạy lại trên cùng lượt máy chủ thì Shopee báo `error_auth` — đúng hành vi. Khởi động lại máy chủ để có lại token.
- Đổi biến môi trường cho một lượt chạy: đặt `$env:MOCK_FAULT_RATE = "0.3"` trước khi bật. Biến môi trường thắng giá trị trong `.env`.

## Chạy test

```powershell
..\backend\.venv\Scripts\python.exe -m pytest      # không cần Docker
```

Không thêm `-W error::DeprecationWarning`: `pytest.ini` đã biến DeprecationWarning thành lỗi, kèm một ngoại lệ cho cảnh báo nằm trong chính starlette.

## Biến `.env`

| Biến | Ý nghĩa |
|---|---|
| `SHOPEE_*`, `TIKTOK_*` | Khóa app và token ban đầu (giả). Backend dùng **cùng tên biến, cùng giá trị** |
| `MOCK_ESCROW_MODE` | `all` (mặc định): escrow cho mọi đơn, số liệu khớp số liệu chuẩn. `completed_only`: đơn khác COMPLETED bị báo lỗi → kiểm nhánh NMV tạm tính của backend |
| `MOCK_FAULT_RATE` | Tỷ lệ 0–1 yêu cầu bị trả lỗi quá tải: Shopee **HTTP 429** + `error_rate_limit`, TikTok HTTP 200 + `code 36009002`. 0 = tắt. Dùng để kiểm cơ chế thử lại |
| `MOCK_FAULT_SEED` | Số nguyên cố định chuỗi lỗi (tái lập được). Bỏ trống = ngẫu nhiên |
| `MOCK_SHOPEE_ACCESS_TTL_SECONDS`, `MOCK_TIKTOK_ACCESS_TTL_SECONDS` | Hạn sống access_token (giây). Mặc định như sàn thật (4 giờ / 7 ngày). Đặt `5` để thấy token hết hạn sau 5 giây |

## Các file

| File | Việc |
|---|---|
| `data_builder.py` | CSV ẩn danh → dữ liệu khuôn API trong bộ nhớ |
| `signature.py` | Chữ ký HMAC-SHA256 của 2 sàn, kiểm timestamp ±5 phút |
| `tokens.py` | Bảng token: hạn sống, làm mới, refresh Shopee dùng 1 lần |
| `gay_loi.py` | Lỗi quá tải có chủ đích (`MOCK_FAULT_RATE`) |
| `shopee_routes.py` | `get_order_list`, `get_order_detail`, `get_escrow_detail_batch`, `auth/access_token/get` |
| `tiktok_routes.py` | `orders/search`, Finance `statement_transactions`, `token/refresh` |
| `main.py`, `config.py` | Tạo app (`--factory`), đọc `.env` |
| `scripts/goi_thu.py` | Gọi thử máy chủ đang chạy; tự ký độc lập với `signature.py` |

## Giả định của bản giả lập (khác biệt có thể có với sàn thật)

Tài liệu đã lưu không mô tả những điểm dưới đây; bản giả lập tự chọn. Khóa luận phải nêu rõ.

| Điểm | Bản giả lập chọn |
|---|---|
| Finance với đơn chưa COMPLETED | `code 0`, `sku_transactions = []` |
| Lớp bọc của escrow lô; đơn không có escrow | `[{escrow_detail}]`; đơn lỗi `{order_sn, fail_error: "mock_escrow_not_available"}` + `warning` |
| Mã lỗi xác thực / tham số TikTok | Mã quy ước `9990001`–`9990006` |
| Khuôn `token/refresh` TikTok | Theo SDK mã nguồn mở EcomPHP; không trả trường hạn sống |
| Shopee: refresh_token đã dùng | `error_auth` |
| Mã HTTP | Lỗi trả HTTP 200 + mã trong body; riêng Shopee quá tải trả HTTP 429 |
| Cửa sổ thời gian | Shopee `[time_from, time_to]` cả hai đầu; TikTok `[_ge, _lt)` theo tài liệu |
| Trường mặc định `get_order_detail`; vị trí trường làm mới token Shopee | 4 trường mặc định; trường đặt trong `response` |
| `next_page_token` trang cuối TikTok; Finance mã đơn lạ | `""`; rỗng |

Ngoài ra máy chủ giả lập **không** tái hiện được giới hạn tần suất thật, độ trễ thật, hay lỗi nằm ngoài tài liệu.
