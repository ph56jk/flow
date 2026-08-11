@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\apply_rule_update.ps1" -Port 3169
if errorlevel 1 (
  echo.
  echo Cap nhat that bai. Code cu va du lieu van duoc giu nguyen.
) else (
  echo.
  echo Cap nhat rule thanh cong.
)
pause
