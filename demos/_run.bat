@echo off
:: =========================================================
:: 1S: ERP Free Edition  -  Demo runner
:: Usage: call _run.bat <script_name> <title>
:: =========================================================
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set "SCRIPT=%~1"
set "DEMO_TITLE=%~2"
set "ROOT=%~dp0.."

:: Find Python (check known paths, then PATH)
set "PY=python"
if exist "C:\Python314\python.exe"  set "PY=C:\Python314\python.exe"
if not "!PY!"=="C:\Python314\python.exe" (
    for %%P in (313 312 311 310) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%P\python.exe" (
            set "PY=%LOCALAPPDATA%\Programs\Python\Python%%P\python.exe"
            goto :found
        )
    )
)
:found

set "PYTHONPATH=!ROOT!"
cd /d "!ROOT!"
title 1S: ERP - !DEMO_TITLE!

echo.
echo =========================================================
echo  1S: ERP Free Edition  v0.3
echo  !DEMO_TITLE!
echo =========================================================
echo.
echo  Python: !PY!
echo  Script: examples\!SCRIPT!.1s
echo.

"!PY!" -X utf8 -m src.cli run "examples\!SCRIPT!.1s"
set "EC=!ERRORLEVEL!"

echo.
if !EC! == 0 (
    echo  [OK] Demo completed.
) else (
    echo  [ERR] Error code !EC!
    echo  Make sure Flask is installed: pip install flask
)
echo =========================================================
echo  Press any key to close...
pause >nul
endlocal
