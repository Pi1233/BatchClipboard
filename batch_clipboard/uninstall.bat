@echo off
echo Stopping BatchClipboard background process...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*BatchClipboard*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Removing Windows Startup entry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "BatchClipboard" /f >nul 2>&1

echo Deleting installed files...
rmdir /s /q "%LOCALAPPDATA%\BatchClipboard" >nul 2>&1
del /f /q "%TEMP%\batch_clipboard_tray.ico" >nul 2>&1

echo.
echo BatchClipboard has been completely removed from Windows.
pause
