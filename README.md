# Website phân tích dữ liệu bán hàng đa kênh (Shopee · TikTok Shop)

Khóa luận tốt nghiệp: hệ thống lấy đơn hàng của hai sàn qua API (có đường dự phòng nạp tệp CSV), chuẩn hóa về một quy tắc tính doanh thu, rồi hiển thị dashboard từng sàn, đối chiếu hai sàn, cảnh báo biến động, xuất Excel và nhận định tự động.

> Mọi khóa, token, mật khẩu trong kho mã này đều là **giá trị giả** để chạy thử. Không có dữ liệu khách hàng thật (hai tệp CSV mẫu đã được ẩn danh).

## 1. Cần cài sẵn

| Thành phần | Phiên bản | Dùng để |
|---|---|---|
| Docker Desktop | bản mới | chạy PostgreSQL 16.4 |
| Python | **3.12** (lệnh `py -3.12`) | backend, máy chủ giả lập sàn |
| Node.js | **24** (kèm npm) | giao diện |

Hướng dẫn dưới đây viết cho Windows (PowerShell). Chạy từ thư mục gốc của kho mã.

## 2. Chạy từ đầu trên máy mới

**Bước 1 — Cơ sở dữ liệu** (cổng 5434 trên máy; đổi được trong `docker-compose.yml`):

```powershell
docker compose up -d
docker compose ps          # đợi trạng thái "healthy"
```

**Bước 2 — Backend: cài thư viện, cấu hình, tạo bảng, nạp dữ liệu mẫu**

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `backend\.env`, đổi tối thiểu hai giá trị (đều đang là giá trị giả):

- `JWT_SECRET` — chuỗi ngẫu nhiên ≥ 32 ký tự. Sinh nhanh: `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `ADMIN_PASSWORD` — mật khẩu của tài khoản quản trị đầu tiên (≥ 8 ký tự).

Tùy chọn: `GEMINI_API_KEY` (khóa lấy ở Google AI Studio) để dùng nút "Sinh nhận định"; để trống thì chỉ nút đó báo lỗi, các phần khác vẫn chạy.

```powershell
.venv\Scripts\python -m alembic upgrade head          # tạo các bảng (orders, sync_runs, platform_tokens, users)
.venv\Scripts\python -m app.etl.nap_file shopee ..\data\samples\shopee_orders_anonymized.csv --shop "Shop C"
.venv\Scripts\python -m app.etl.nap_file tiktok ..\data\samples\tiktok_orders_anonymized.csv
```

Lệnh nạp in số dòng (Shopee 1.774 dòng, TikTok 7.540 dòng). Nạp lại cùng tệp bao nhiêu lần cũng không nhân đôi dữ liệu.

Với Shopee, `--shop "<tên gian hàng>"` là **bắt buộc** (tệp Shopee không có cột gian hàng, không có tên mặc định); thiếu thì lệnh báo lỗi và không nạp gì.

**Thả tệp để tự nạp:** tệp TikTok thả vào `data/inbox/tiktok/`. Tệp Shopee phải thả vào **ngăn của đúng gian hàng**: `data/inbox/shopee/<tên gian hàng>/` (ví dụ `data/inbox/shopee/Shop C/`). Hệ thống tự tạo ngăn cho mọi gian hàng Shopee đang có (thấy ngăn mới sau tối đa 30 giây khi thêm gian hàng). Tệp thả sai chỗ (thẳng ở `data/inbox/shopee/` hoặc ngăn không khớp gian hàng nào) bị chuyển sang `data/failed/shopee/` kèm tệp `.log` nói rõ lý do, và không dòng nào được nạp.

**Bước 3 — Máy chủ giả lập sàn** (cổng 8001; đóng vai Shopee và TikTok Shop, dữ liệu sinh từ chính hai tệp mẫu). Mở một cửa sổ PowerShell mới:

```powershell
cd mock_platform
Copy-Item .env.example .env
..\backend\.venv\Scripts\python -m uvicorn main:tao_ung_dung_tu_env --factory --port 8001
```

**Bước 4 — Backend** (cổng 8000). Cửa sổ PowerShell mới:

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Lúc khởi động backend tự tạo tài khoản `admin` (mật khẩu = `ADMIN_PASSWORD`) nếu bảng người dùng còn trống, và cứ 10 phút tự đồng bộ đơn từ máy chủ giả lập. Nếu không bật máy chủ giả lập (bước 3), đặt `SYNC_SCHEDULER_ENABLED=false` trong `backend\.env` để khỏi có lỗi đồng bộ trong log.

**Bước 5 — Giao diện** (cổng 5173). Cửa sổ PowerShell mới:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
```

Mở `frontend\.env`, đổi `VITE_USE_MOCK=true` thành `VITE_USE_MOCK=false` (true = dữ liệu giả ngay trong trình duyệt, không cần backend; false = gọi backend thật). Rồi:

```powershell
npm run dev
```

Mở http://localhost:5173 và đăng nhập `admin` cùng mật khẩu `ADMIN_PASSWORD` đã đặt ở bước 2. Muốn thử vai trò "Người dùng" (không thấy mục Quản trị): vào **Người dùng** → thêm tài khoản vai trò Người dùng → đăng xuất → đăng nhập bằng tài khoản đó.

**Chạy nhanh trên Windows (những lần sau):** double-click `chay.bat` ở thư mục gốc. Tệp này mở 3 cửa sổ: máy chủ giả lập 8001, backend 8000, giao diện 5173, rồi tự mở trình duyệt. Trước đó phải bật Docker (bước 1) và đã cài đặt xong theo các bước trên (`.venv`, `.env`, `npm ci`, tạo bảng và nạp dữ liệu mẫu). Tắt phần nào thì đóng cửa sổ đó.

### Thêm gian hàng mới (Kết nối gian hàng)

Admin vào **Đồng bộ dữ liệu** → **Kết nối gian hàng mới** → chọn sàn (Shopee thì nhập thêm tên hiển thị của gian hàng) → trình duyệt sang **trang ủy quyền của sàn**; chủ shop đăng nhập ở đó và bấm **Đồng ý** → hệ thống nhận kết quả, lưu quyền truy cập và tự đồng bộ gian hàng đó. Doanh nghiệp không bao giờ nhìn thấy khóa ứng dụng. **Kết nối lại** (khi quyền sắp hết hạn hoặc đã mất) dùng đúng luồng này, bấm ở thẻ của từng gian hàng. Cần chạy với backend thật (`VITE_USE_MOCK=false`).

Với máy chủ giả lập (bước 3), trang ủy quyền là trang giả do máy chủ giả lập dựng, có sẵn một gian hàng **mới chưa có đơn** để thử: Shopee `Shop D`, TikTok `Shop E`. Địa chỉ mặc định đã đúng cho máy chạy cục bộ; cần đổi khi chạy thật hoặc ở máy khác thì xem các biến `*_AUTH_PAGE_BASE_URL`, `PUBLIC_BACKEND_URL`, `FRONTEND_URL` ở cuối `backend\.env.example`. Gian hàng Shopee mới có ngăn thư mục riêng để thả tệp: `data/inbox/shopee/<tên gian hàng>/`.

## 3. Kiểm nhanh số liệu

Trên dữ liệu mẫu, các số sau phải khớp (đã chốt ở `docs/SPEC.md` §17):

- Tổng doanh thu: Shopee **1.908.961.059**, TikTok Shop **7.538.502.584**.
- Dashboard Shopee, tháng 8/2026 (kỳ chưa đủ ngày, đến 16/08): **840.035.154**, tăng **34,6%** so với 01–16/07 (624.277.755).
- Dashboard TikTok Shop, tháng 4/2026: doanh thu giảm **30,5%** và hiện dải cảnh báo; tháng khác không có cảnh báo.

## 4. Chạy kiểm thử

```powershell
cd backend
.venv\Scripts\python -m pytest              # cần Docker đang chạy (test ghi CSDL thật trong giao dịch rồi hoàn tác)
cd ..\mock_platform
..\backend\.venv\Scripts\python -m pytest
cd ..\frontend
npm test
npm run build
```

Backend có test chậm (đánh dấu `cham`, kéo toàn bộ dữ liệu qua máy chủ giả lập): thêm `-m "not cham"` để bỏ qua khi làm việc hằng ngày. Bộ đầy đủ chạy mất vài phút.

**Đọc kết quả test cho đúng — bật Docker TRƯỚC khi chạy `pytest`** (`docker compose up -d`, chờ `healthy`):

- Backend có **773 test**, trong đó 386 test cần PostgreSQL thật (đánh dấu `db`) và 43 test chậm (`cham`). Khi **đủ điều kiện** (Docker bật, đã nạp dữ liệu mẫu, máy có hai CSV gốc và `scripts/ten_that.local.json`) kết quả chuẩn là **`773 passed, 0 skipped`**; mock **176 passed**; frontend **222 passed** (tổng 1.171).
- **Docker tắt thì KHÔNG chỉ là "bỏ qua": kết quả lẫn skip và đỏ.** Đo bằng cách trỏ `DATABASE_URL` vào một cổng không có CSDL (không tắt container): `394 passed, 167 skipped, 4 failed, 178 errors` (đo khi backend còn 743 test, chưa đo lại), mất khoảng 24 phút vì chờ kết nối. Test nhóm `db` tự skip, nhưng nhiều test API (dashboard, cảnh báo, Excel, nhận định) báo `ERROR` ở bước dựng và vài test đồng bộ báo `FAILED`. Đừng chỉ nhìn màu: đọc dòng tổng kết `passed / skipped / failed / errors`.
- Muốn chạy phần không cần CSDL: `python -m pytest -m "not db"` → **387 passed** (386 test `db` bị loại), khoảng 2–3 phút, kết quả giống nhau dù Docker bật hay tắt.
- Trên máy **không có hai CSV gốc** hoặc `scripts/ten_that.local.json` (không nằm trong git vì chứa dữ liệu thật), 4 test đối chiếu với dữ liệu gốc (`test_du_lieu_mau.py`: `test_khong_cot_nao_con_ten_that` và `test_cot_khong_thay_ten_giong_het_file_goc`, mỗi test chạy cho 2 sàn) tự bỏ qua; tất cả test còn lại vẫn chạy trên hai tệp ẩn danh có trong git.
- Một số test API còn tự bỏ qua khi bảng `orders` chưa nạp đủ dữ liệu mẫu (xem mục 2: nạp hai tệp mẫu trước khi chạy test).
- Muốn biết vì sao từng test bị bỏ qua: `python -m pytest -rs` (kèm `-rsfE` để liệt kê cả test đỏ và lỗi).

## 5. Các thư mục trong dự án là gì

### Mã nguồn và tài liệu (là một phần của bài nộp)
| Thư mục / tệp | Là gì |
|---|---|
| `backend/` | Máy chủ FastAPI: `app/` (mã: `etl/` đọc CSV và chuẩn hóa, `connectors/` gọi API sàn, `sync/` đồng bộ + lịch + quét thư mục, `services/` KPI/cảnh báo/Excel/nhận định, `api/` các endpoint), `alembic/` (tạo bảng CSDL), `tests/`, `requirements.txt`, `.env.example` |
| `frontend/` | Giao diện React + Vite + Ant Design: `src/` (6 màn hình: đăng nhập, dashboard từng sàn, đối chiếu, đồng bộ, upload, người dùng), `package.json` |
| `mock_platform/` | **Máy chủ Shopee/TikTok GIẢ** (cổng 8001), chạy riêng, để demo và test đồng bộ mà không cần khóa sàn thật |
| `docker-compose.yml` | Chạy PostgreSQL 16.4 |
| `data/samples/` | Hai tệp CSV **đã ẩn danh** (`shopee_orders_anonymized.csv`, `tiktok_orders_anonymized.csv`): nạp dữ liệu mẫu và làm đáp án cho test |
| `data/inbox/`, `data/processed/`, `data/failed/` | Thư mục "thả tệp vào là tự nạp" (mỗi nơi có thư mục con `shopee/`, `tiktok/`; riêng Shopee thêm một ngăn cho mỗi gian hàng, tự tạo); trong git chỉ có tệp giữ chỗ `.gitkeep` |
| `docs/` | Tài liệu: xem `docs/README.md` (`SPEC.md` đặc tả, `QUY_TRINH.md` tiến độ, `TRACKLOG.md` nhật ký cũ đã đóng băng, `tracklog/` nhật ký mới) |
| `README.md` | Tệp này |

### Ba thư mục `scripts` — KHÔNG phải một phần của luồng chạy hệ thống
Hệ thống chạy bình thường mà không cần bất kỳ tệp nào dưới đây; đây là công cụ chạy tay.
| Thư mục | Dùng để làm gì |
|---|---|
| `scripts/` (ở gốc) | Chạy **một lần**: `anonymize_samples.py` (ẩn danh CSV gốc → `data/samples/*_anonymized.csv`), `build_product_map.py` (sinh bảng mã sản phẩm). Đọc dữ liệu khách hàng thật nên chỉ chạy được trên máy có CSV gốc |
| `backend/scripts/` | `thu_nhan_dinh.py`: chạy tay thử Gemini **thật** (tốn hạn mức, cần `GEMINI_API_KEY`) |
| `mock_platform/scripts/` | `goi_thu.py`: chạy tay thử máy chủ giả đang chạy |

### Thư mục tự sinh, xóa được bất cứ lúc nào (nằm ngoài git, sẽ tự tạo lại)
| Thư mục | Là gì |
|---|---|
| `__pycache__/` (nhiều nơi trong `backend/`, `mock_platform/`, `scripts/`) | Python tự đặt bản biên dịch |
| `backend/.pytest_cache/` | pytest tự đặt |
| `frontend/dist/` | Kết quả của `npm run build` |

### KHÔNG nộp (nặng, chứa khóa hoặc dữ liệu thật)
| Thư mục / tệp | Vì sao |
|---|---|
| `backend/.venv/`, `frontend/node_modules/` | Thư viện đã cài, rất nặng; tạo lại theo mục 2 |
| `backend/.env`, `mock_platform/.env`, `frontend/.env` | Cấu hình riêng của máy (có khóa, mật khẩu); chỉ nộp các tệp `.env.example` |
| `data/samples/Shopee Tracking_Order.csv`, `data/samples/TikTok Tracking_Order.csv` | CSV **gốc có dữ liệu khách hàng thật** |
| `scripts/ten_that.local.json` | Bảng tên thật, chỉ có trên máy sinh viên |
| `prompts/` | Chỉ dẫn và báo cáo trao đổi với chat chính (ngoài git); không phải mã nguồn |

## 6. Tài liệu

- `docs/README.md` — chỉ đường: tệp nào trong `docs/` là gì, tệp nào đã đóng băng.
- `docs/SPEC.md` — đặc tả đầy đủ: công thức doanh thu (§7), cảnh báo (§9), hợp đồng JSON của mọi endpoint (§12.1), máy chủ giả lập (§19), số liệu chuẩn để kiểm (§17).
- `docs/QUY_TRINH.md` — các bước đã làm và kết quả kiểm chứng.
- `docs/tracklog/` — nhật ký chi tiết từng bước.

## 7. Phạm vi và hạn chế

Không làm trong bản này: xuất PDF (nút hiện "Chưa hỗ trợ trong bản demo") và ủy quyền lại token khi hết hạn. Sàn thật chưa được kiểm thử (chỉ máy chủ giả lập); Shopee thật cần thêm ứng dụng AMS riêng để lấy cờ affiliate. Chi tiết ở `docs/SPEC.md` §16.
