import ctypes
import os
import shutil
import subprocess
import time
import winreg
from pathlib import Path

APP_NAME = "BatchClipboard"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
INSTALL_DIR = Path(os.environ["LOCALAPPDATA"]) / APP_NAME


def release_modifier_keys():
    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    for vk in (0x11, 0x12, 0x10):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def stop_running_processes():
    pid_file = INSTALL_DIR / "app.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like '*batch_clipboard.py*' -or $_.CommandLine -like '*BatchClipboard*launcher.pyw*' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def remove_startup_entry():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False


def uninstall():
    print("Removing BatchClipboard from Windows...")

    release_modifier_keys()
    stop_running_processes()
    time.sleep(0.4)

    reg_removed = remove_startup_entry()

    dir_removed = False
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
        dir_removed = not INSTALL_DIR.exists()

    print("====================================================")
    print(" BatchClipboard has been completely uninstalled.")
    print("====================================================")
    print("• Background process : Stopped")
    print(f"• Startup registry   : {'Removed' if reg_removed else 'Already clean'}")
    print(f"• Installed files    : {'Deleted' if dir_removed else 'Already clean'}")


if __name__ == "__main__":
    uninstall()
