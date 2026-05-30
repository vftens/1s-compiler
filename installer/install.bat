@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║    1S: ERP Free Edition  v0.3        ║
echo  ║    Установщик / Installer             ║
echo  ╚══════════════════════════════════════╝
echo.

:: Target directory
set INSTALL_DIR=%LOCALAPPDATA%\1S-ERP
set EXE_SRC=%~dp0..\dist\1S-ERP.exe

:: Check .exe exists
if not exist "%EXE_SRC%" (
    echo [ERROR] 1S-ERP.exe not found in dist\
    echo         Run first: python -m PyInstaller 1S-ERP.spec
    pause & exit /b 1
)

:: Create install dir
echo  [1/4] Creating directory: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul

:: Copy exe
echo  [2/4] Copying 1S-ERP.exe ...
copy /Y "%EXE_SRC%" "%INSTALL_DIR%\1S-ERP.exe" >nul
if errorlevel 1 ( echo [ERROR] Copy failed. & pause & exit /b 1 )

:: Desktop shortcut via PowerShell
echo  [3/4] Creating desktop shortcut ...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\1S-ERP.lnk'); ^
   $sc.TargetPath = '%INSTALL_DIR%\1S-ERP.exe'; ^
   $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
   $sc.Description = '1S: ERP Free Edition'; ^
   $sc.Save()"

:: Start Menu shortcut
echo  [4/4] Creating Start Menu shortcut ...
set SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs
mkdir "%SM%\1S-ERP" 2>nul
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%SM%\1S-ERP\1S ERP Free Edition.lnk'); ^
   $sc.TargetPath = '%INSTALL_DIR%\1S-ERP.exe'; ^
   $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
   $sc.Description = '1S: ERP Free Edition'; ^
   $sc.Save()"

echo.
echo  ✓ Установка завершена / Installation complete!
echo  ✓ Ярлык добавлен на рабочий стол / Shortcut added to Desktop
echo  ✓ Установлено в / Installed to: %INSTALL_DIR%
echo.
echo  Запуск: 1S-ERP на рабочем столе, или %INSTALL_DIR%\1S-ERP.exe
echo.
pause
