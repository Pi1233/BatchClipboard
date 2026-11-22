@echo off
setlocal
cd /d "%~dp0"

echo Checking Python packages...
python -c "import win32api, keyboard, PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    if exist "..\requirements.txt" (
        pip install -r "..\requirements.txt"
    ) else (
        pip install pywin32 keyboard Pillow
    )
)

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" /B pythonw "%~dp0batch_clipboard.py"
) else (
    start "" /B python "%~dp0batch_clipboard.py"
)

echo ====================================================
echo  BatchClipboard started for this session only!
echo ====================================================
echo  - Auto-start on boot : OFF (One-time run)
echo  - Toggle Batch Mode  : Double-tap Ctrl (or Ctrl+Alt+B)
echo  - Quit App           : Ctrl+Alt+Shift+Q or Tray Icon
echo ====================================================
timeout /t 4 >nul
