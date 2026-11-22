Markdown
# BatchClipboard
Copy multiple text snippets and Windows Snipping Tool screenshots at once, then paste everything together with Ctrl+V.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows)
![Release](https://img.shields.io/badge/Release-v1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**Copy multiple text snippets and Windows Snipping Tool screenshots in one session, then paste everything together at once with a single `Ctrl+V`.**

BatchClipboard hooks directly into native Windows shortcuts (`Ctrl+C`, `Win+Shift+S`, and `Ctrl+V`). Instead of switching back and forth between windows to copy and paste items one by one, toggle Batch Mode ON, capture everything you need in order, and drop the entire batch into your target app in one go.


https://github.com/user-attachments/assets/35bdf536-d0e3-4cd8-84f9-81cc8b79f52d


---

## Features

- **Native Windows Integration:** Works seamlessly with standard `Ctrl+C` text copies and Windows Snipping Tool (`Win+Shift+S`) screenshots—no modifications to system apps required.
- **Custom Paste Separators:** Switch separators on the fly from the Queue Inspector or `config.json`—choose **`Shift+Enter`** (default for **ChatGPT, Gemini, Discord, and WhatsApp** so images and text attach without submitting early), **`Newline`**, **`Double Newline`**, **`Tab`** (for **Excel / Google Sheets**), **`Comma (, )`**, or **`Bullet Points (- )`**.
- **Sticky Mode (`Sticky: ON/OFF`):** Pin your captured queue so it stays intact after `Ctrl+V`, letting you paste the same batch across multiple apps without re-copying.
- **System Tray Queue Inspector & Reorder:** Click the blue clipboard icon in your Windows system tray (or click the floating HUD pill) to preview text and screenshot thumbnails, reorder items (`↑` / `↓`), remove individual items (`✕`), or clear the queue.
- **Smart Deduplication:** Uses SHA-256 hashing so Windows Snipping Tool's double clipboard update is ignored (`1 snip = 1 screenshot`).
- **Lightweight & Configurable (~25–32 MB RAM):** Uses native Win32 tray APIs, compressed PNG storage in memory, and a local `config.json` for customizing hotkeys, delays, and HUD position.

---

## Keyboard Shortcuts & Controls

| Action / Shortcut | What It Does |
| :--- | :--- |
| **Double-tap `Ctrl`** *(or `Ctrl + Alt + B`)* | **Toggle Batch Mode ON / OFF.** Ignores `Ctrl+C` or other `Ctrl` combinations so normal shortcuts never misfire. |
| **`Ctrl + C`** | Works normally; while Batch Mode is ON, adds copied text to your queue. |
| **`Win + Shift + S`** | Takes a Snipping Tool screenshot normally and adds it to your queue. |
| **`Ctrl + V`** | Pastes all queued text and screenshots in order (clears queue unless **Sticky Mode** is ON). |
| **Click HUD `✕`** *(or press `Esc`)* | Cancels **only the current batch** and hides the HUD while keeping the background app active. |
| **Click System Tray Icon** *(or HUD text)* | Opens the live queue preview window (reorder items, switch separator, toggle Sticky Mode). |
| **`Ctrl + Alt + Shift + Q`** *(or **Quit App**)* | **Emergency Kill Switch:** Releases modifier keys, unhooks keyboard listeners, and exits completely. |

---

## Repository Structure
```text
BatchClipboard/
├── batch_clipboard/
│   ├── batch_clipboard.py   # Core clipboard listener, keyboard hooks, tray UI, and paste engine
│   ├── config.json          # User settings (hotkeys, separator, sticky mode, HUD offset, delays)
│   ├── install.bat          # One-click permanent Windows Startup installer
│   ├── install.py           # Copies to %LOCALAPPDATA%, adds Windows Startup entry, and launches silently
│   ├── run_once.bat         # One-click silent background run for current session (no Startup entry)
│   ├── uninstall.bat        # One-click complete uninstaller
│   └── uninstall.py         # Stops background process, cleans registry, and deletes installed files
├── .gitignore               # Excludes build artifacts, .exe binaries, cache, and runtime PID files
├── LICENSE                  # MIT License
├── README.md                # Project documentation
└── requirements.txt         # Python dependencies (pywin32, Pillow, keyboard)

```
Installation
Option 1: Easy Install — .exe Release (No Python Required)
Go to **[Releases](../../releases/latest)** and download BatchClipboard-Windows.zip.

Extract the ZIP folder anywhere on your PC.

Double-click install.exe to install to %LOCALAPPDATA%\BatchClipboard with Windows Startup enabled (or double-click BatchClipboard.exe to run once without installing).

Option 2: Run or Install from Source (Python)
Clone the repository and install dependencies:

DOS
git clone [https://github.com/Pi1233/BatchClipboard.git](https://github.com/Pi1233/BatchClipboard.git)
cd BatchClipboard
pip install -r requirements.txt
Run once in the background (no Windows Startup entry):
Double-click batch_clipboard\run_once.bat, or run:

DOS
batch_clipboard\run_once.bat
Integrate with Windows (Silent Background + Auto-Start):
Double-click batch_clipboard\install.bat, or run:

DOS
python batch_clipboard\install.py
(Whenever you update batch_clipboard.py, run install.bat or python batch_clipboard\install.py again to restart and update the background instance.)

Uninstallation
If installed via .exe: Double-click uninstall.exe from your extracted release folder.

If installed from Source: Double-click batch_clipboard\uninstall.bat or run:

DOS
python batch_clipboard\uninstall.py
Known Limitations
Administrator Windows: Due to Windows UIPI (User Interface Privilege Isolation), global keyboard hooks running as a standard user cannot intercept Ctrl+C or Ctrl+V inside elevated (Run as Administrator) terminals or apps.

License
Distributed under the MIT License. See LICENSE for details.
