import os
import shutil
import subprocess
import sys
import time
import winreg
from pathlib import Path

APP_NAME = "BatchClipboard"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
INSTALL_DIR = Path(os.environ["LOCALAPPDATA"]) / APP_NAME
BASE_DIR = Path(__file__).resolve().parent
SOURCE_SCRIPT = BASE_DIR / "batch_clipboard.py"
SOURCE_CONFIG = BASE_DIR / "config.json"


def get_pythonw_path() -> Path:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else exe


def stop_existing_instance():
    pid_file = INSTALL_DIR / "app.pid"
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text(encoding="utf-8").strip())
            subprocess.run(
                ["taskkill", "/F", "/PID", str(old_pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.3)
        except Exception:
            pass


def install():
    if not SOURCE_SCRIPT.exists():
        print(f"[Error] Could not find '{SOURCE_SCRIPT.name}' in this folder.")
        sys.exit(1)

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    stop_existing_instance()

    # 1. Copy main script & config to AppData
    target_script = INSTALL_DIR / "batch_clipboard.py"
    shutil.copy2(SOURCE_SCRIPT, target_script)

    target_config = INSTALL_DIR / "config.json"
    if SOURCE_CONFIG.exists() and not target_config.exists():
        shutil.copy2(SOURCE_CONFIG, target_config)

    # 2. Create silent launcher that tracks PID
    launcher_script = INSTALL_DIR / "launcher.pyw"
    launcher_code = f'''import os
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(r"{INSTALL_DIR}")
PID_FILE = APP_DIR / "app.pid"

if PID_FILE.exists():
    try:
        old_pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        if old_pid != os.getpid():
            subprocess.run(
                ["taskkill", "/F", "/PID", str(old_pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.2)
    except Exception:
        pass

PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

sys.path.insert(0, str(APP_DIR))
from batch_clipboard import BatchClipboardManager

if __name__ == "__main__":
    app = BatchClipboardManager()
    app.run()
'''
    launcher_script.write_text(launcher_code, encoding="utf-8")

    # 3. Register in Windows Startup
    pythonw_exe = get_pythonw_path()
    startup_cmd = f'"{pythonw_exe}" "{launcher_script}"'

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_cmd)

    # 4. Launch silently right now
    subprocess.Popen(
        [str(pythonw_exe), str(launcher_script)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    )

    print("====================================================")
    print(" BatchClipboard is now installed with Windows!")
    print("====================================================")
    print(f"• Installed to : {INSTALL_DIR}")
    print("• Auto-start   : Enabled (Task Manager -> Startup apps)")
    print("• Toggle Batch : Double-tap Ctrl (or Ctrl+Alt+B)")
    print("• Kill Switch  : Ctrl+Alt+Shift+Q")


if __name__ == "__main__":
    install()
