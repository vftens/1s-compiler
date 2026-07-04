@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
set "PY=python"
if exist "C:\Python314\python.exe" set "PY=C:\Python314\python.exe"
if exist "C:\Python313\python.exe" set "PY=C:\Python313\python.exe"
echo.
echo ===== 1S: ERP - Full ERP Cycle (EN) =====
echo     Procurement | Warehouse | Logistics | Payroll | Maintenance
echo ==========================================
echo.
cd /d "%~dp0.."
"!PY!" -X utf8 -m src.cli run "examples\demo_erp_full_en.1s"
echo.
pause
