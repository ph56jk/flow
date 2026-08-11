@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_flow_worker_3170.ps1"
if errorlevel 1 (
  echo.
  echo Worker 3170 khoi dong that bai. Worker 3169 khong bi thay doi.
  pause
)
