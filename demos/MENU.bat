@echo off
chcp 65001 >nul 2>&1
set PYTHONUTF8=1
set PYTHONPATH=%~dp0..
cd /d "%~dp0.."
title 1S: ERP Free Edition — Demo Menu

:MAIN
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║          1S: ERP Free Edition  v0.3  —  Demo Menu               ║
echo  ║          github.com/vftens/1s-compiler                          ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  ┌─ Украинский / Ukrainian ─────────────────────────────────────────┐
echo  │  [1]  ЗУП: Зарплата (UA)          [2]  Бухоблік: Повний цикл    │
echo  │  [3]  Workflow Dashboard (UA)     [4]  Cython: Швидкість         │
echo  │  [5]  4-Week Planning (UA)        [6]  Workflow Approval (UA)    │
echo  │  [7]  Chess Board (UA)            [8]  Excel Export (UA)         │
echo  └──────────────────────────────────────────────────────────────────┘
echo  ┌─ Русский / Russian ──────────────────────────────────────────────┐
echo  │  [A]  ЗУП: Зарплата (RU)          [B]  Бухучёт: Полный цикл     │
echo  │  [C]  Workflow Dashboard (RU)     [D]  Cython: Скорость          │
echo  └──────────────────────────────────────────────────────────────────┘
echo  ┌─ English ────────────────────────────────────────────────────────┐
echo  │  [E]  HRM: Payroll (EN)            [F]  Accounting full cycle    │
echo  │  [G]  Workflow Dashboard (EN)     [H]  Cython: Speed             │
echo  │  [I]  4-Week Planning (EN)        [J]  Workflow Approval (EN)    │
echo  │  [K]  Excel Export (EN)           [L]  Trial Balance + P^&L      │
echo  └──────────────────────────────────────────────────────────────────┘
echo  ┌─ All ────────────────────────────────────────────────────────────┐
echo  │  [R]  Run ALL demos sequentially   [W]  Launch Web UI            │
echo  │  [Q]  Quit                                                        │
echo  └──────────────────────────────────────────────────────────────────┘
echo.
set /p CHOICE=  Enter choice:

if /i "%CHOICE%"=="1" call "%~dp0_run.bat" demo_zup_uk          "ZUP: Зарплата UA"        & goto MAIN
if /i "%CHOICE%"=="2" call "%~dp0_run.bat" demo_accounting_uk   "Бухоблік UA"              & goto MAIN
if /i "%CHOICE%"=="3" call "%~dp0_run.bat" demo_workflow_graphics_uk "Workflow Dashboard UA" & goto MAIN
if /i "%CHOICE%"=="4" call "%~dp0_run.bat" demo_cython_uk       "Cython Speed UA"          & goto MAIN
if /i "%CHOICE%"=="5" call "%~dp0_run.bat" planning_uk          "4-Week Planning UA"       & goto MAIN
if /i "%CHOICE%"=="6" call "%~dp0_run.bat" workflow_uk          "Workflow Approval UA"     & goto MAIN
if /i "%CHOICE%"=="7" call "%~dp0_run.bat" chess_uk             "Chess Board UA"           & goto MAIN
if /i "%CHOICE%"=="8" call "%~dp0_run.bat" export_uk            "Excel Export UA"          & goto MAIN

if /i "%CHOICE%"=="A" call "%~dp0_run.bat" demo_zup_ru          "ЗУП: Зарплата RU"        & goto MAIN
if /i "%CHOICE%"=="B" call "%~dp0_run.bat" demo_accounting_ru   "Бухучёт RU"              & goto MAIN
if /i "%CHOICE%"=="C" call "%~dp0_run.bat" demo_workflow_graphics_ru "Workflow Dashboard RU" & goto MAIN
if /i "%CHOICE%"=="D" call "%~dp0_run.bat" demo_cython_ru       "Cython Speed RU"          & goto MAIN

if /i "%CHOICE%"=="E" call "%~dp0_run.bat" demo_zup_en          "HRM Payroll EN"           & goto MAIN
if /i "%CHOICE%"=="F" call "%~dp0_run.bat" demo_accounting_en   "Accounting EN"            & goto MAIN
if /i "%CHOICE%"=="G" call "%~dp0_run.bat" demo_workflow_graphics_en "Workflow Dashboard EN" & goto MAIN
if /i "%CHOICE%"=="H" call "%~dp0_run.bat" demo_cython_en       "Cython Speed EN"          & goto MAIN
if /i "%CHOICE%"=="I" call "%~dp0_run.bat" planning_en          "4-Week Planning EN"       & goto MAIN
if /i "%CHOICE%"=="J" call "%~dp0_run.bat" workflow_en          "Workflow Approval EN"     & goto MAIN
if /i "%CHOICE%"=="K" call "%~dp0_run.bat" export_en            "Excel Export EN"          & goto MAIN
if /i "%CHOICE%"=="L" call "%~dp0_run.bat" reports_en           "Trial Balance + P&L EN"   & goto MAIN

if /i "%CHOICE%"=="R" goto RUN_ALL
if /i "%CHOICE%"=="W" goto WEB_UI
if /i "%CHOICE%"=="Q" exit /b

echo  Invalid choice. Try again.
timeout /t 2 >nul
goto MAIN

:RUN_ALL
echo.
echo  Running all demos... (this will take a few minutes)
echo.
set PYTHONUTF8=1
for %%S in (demo_zup_uk demo_zup_ru demo_zup_en
            demo_accounting_uk demo_accounting_ru demo_accounting_en
            demo_cython_uk demo_cython_ru demo_cython_en
            demo_workflow_graphics_uk demo_workflow_graphics_ru demo_workflow_graphics_en) do (
    echo  --- %%S ---
    python -m src.cli run "examples\%%S.1s" 2>&1 | findstr /v "^$"
    echo.
)
echo  All demos completed.
pause
goto MAIN

:WEB_UI
echo.
echo  Starting 1S: ERP Web UI on http://127.0.0.1:5000/
echo  Login: admin / admin
echo.
start python -m src.cli serve --port 5000
timeout /t 2 >nul
start http://127.0.0.1:5000/
goto MAIN
