@echo off
rem Khoi dong 3 phan cua he thong
rem Moi phan mo 1 cua so rieng; tat phan nao thi dong cua so do (hoac Ctrl+C).
rem Chay: double-click vao chay.bat, hoac "".\chay.bat" o terminal.

set "GOC=%~dp0"

start "1-May-chu-gia-lap-8001" /d "%GOC%mock_platform" cmd /k "..\backend\.venv\Scripts\python -m uvicorn main:tao_ung_dung_tu_env --factory --port 8001"
start "2-Backend-8000" /d "%GOC%backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --port 8000"
start "3-Giao-dien-5173" /d "%GOC%frontend" cmd /k "npm run dev"

rem Doi vai giay roi trinh duyet.
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
