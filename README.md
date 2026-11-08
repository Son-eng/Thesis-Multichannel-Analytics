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

## 5. Cấu trúc thư mục

```
backend/         FastAPI + SQLAlchemy: etl/ (đọc CSV, chuẩn hóa, ghi), connectors/ (gọi API sàn),
                 sync/ (đồng bộ, lịch, quét thư mục), services/ (KPI, cảnh báo, Excel, nhận định),
                 api/ (các endpoint), alembic/ (tạo bảng), tests/
mock_platform/   máy chủ giả lập API Shopee và TikTok Shop (cổng 8001), chạy độc lập với backend
frontend/        React + Vite + Ant Design: 6 màn hình (đăng nhập, dashboard từng sàn, đối chiếu,
                 đồng bộ, upload, người dùng)
data/            samples/ (hai tệp CSV mẫu đã ẩn danh); inbox/ processed/ failed/ (thư mục nạp tự động)
docs/            SPEC.md (đặc tả và mọi quyết định), QUY_TRINH.md (tiến độ), tracklog/ (nhật ký từng bước)
scripts/         công cụ ẩn danh dữ liệu mẫu
docker-compose.yml   PostgreSQL 16.4
```

## 6. Tài liệu

- `docs/SPEC.md` — đặc tả đầy đủ: công thức doanh thu (§7), cảnh báo (§9), hợp đồng JSON của mọi endpoint (§12.1), máy chủ giả lập (§19), số liệu chuẩn để kiểm (§17).
- `docs/QUY_TRINH.md` — các bước đã làm và kết quả kiểm chứng.
- `docs/tracklog/` — nhật ký chi tiết từng bước.

## 7. Phạm vi và hạn chế

Không làm trong bản này: xuất PDF (nút hiện "Chưa hỗ trợ trong bản demo") và ủy quyền lại token khi hết hạn. Sàn thật chưa được kiểm thử (chỉ máy chủ giả lập); Shopee thật cần thêm ứng dụng AMS riêng để lấy cờ affiliate. Chi tiết ở `docs/SPEC.md` §16.
