@echo off
:: Internal helper — called by all demo .bat files
:: Usage: call _run.bat <script_name> <window_title>
chcp 65001 >nul 2>&1
set PYTHONUTF8=1
set PYTHONPATH=%~dp0..
cd /d "%~dp0.."
title 1S: ERP — %~2
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  1S: ERP Free Edition  ·  %~2
echo  ╚══════════════════════════════════════════════════════════╝
echo.
python -m src.cli run "examples\%~1.1s"
echo.
echo  ═══════════════════════════════════════════════════════════
echo  Press any key to close...
pause >nul
