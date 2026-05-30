@echo off
chcp 65001 >nul
echo.
echo  Удаление 1S: ERP Free Edition / Uninstall ...
echo.

set INSTALL_DIR=%LOCALAPPDATA%\1S-ERP
set SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs\1S-ERP
set DESK=%USERPROFILE%\Desktop\1S-ERP.lnk

echo  [1/3] Removing application files ...
if exist "%INSTALL_DIR%" ( rmdir /S /Q "%INSTALL_DIR%" )

echo  [2/3] Removing desktop shortcut ...
if exist "%DESK%" ( del /Q "%DESK%" )

echo  [3/3] Removing Start Menu entry ...
if exist "%SM%" ( rmdir /S /Q "%SM%" )

echo.
echo  ✓ 1S: ERP удалён / Uninstalled.
echo.
pause
