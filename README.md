# BatchClipboard
Copy multiple text snippets and Windows Snipping Tool screenshots at once, then paste everything together with Ctrl+V.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**Copy multiple text snippets and Windows Snipping Tool screenshots in one session, then paste everything together at once with a single `Ctrl+V`.**

BatchClipboard hooks directly into native Windows shortcuts (`Ctrl+C`, `Win+Shift+S`, and `Ctrl+V`). Instead of switching back and forth between windows to copy and paste items one by one, toggle Batch Mode ON, capture everything you need in order, and drop the entire batch into your target app in one go.

---

## Features

- **Native Windows Integration:** Works seamlessly with standard `Ctrl+C` text copies and Windows Snipping Tool (`Win+Shift+S`) screenshots—no modifications to system apps required.
- **Multi-Image & Text Pasting Everywhere:** Pastes queued text (`CF_UNICODETEXT`) and screenshots (`PNG` + `CF_DIB`) in exact capture order using `Shift+Enter` line breaks—so **ChatGPT, Gemini, WhatsApp, Discord, Google Docs, Word, and Paint** attach every image and paragraph without accidentally submitting early.
- **Smart Deduplication:** Uses SHA-256 hashing so Windows Snipping Tool's double clipboard update is ignored (`1 snip = 1 screenshot`).
- **System Tray Queue Inspector:** Click the blue clipboard icon in your Windows system tray (or click the floating HUD pill) to preview copied text and screenshot thumbnails, remove individual items, clear the queue, or quit the app.
- **Lightweight Footprint (~25–32 MB RAM):** Uses native Win32 tray APIs and compressed PNG storage in memory, immediately releasing RAM after pasting or cancelling.
- **Zero-Admin Background Install:** Integrates cleanly into Windows Startup (`HKCU\...\Run`) via `pythonw.exe` with no console window and a one-click uninstaller.

---

## Keyboard Shortcuts & Controls

| Action / Shortcut | What It Does |
| :--- | :--- |
| **Double-tap `Ctrl`** *(or `Ctrl + Alt + B`)* | **Toggle Batch Mode ON / OFF.** Ignores `Ctrl+C` or other `Ctrl` combinations so normal shortcuts never misfire. |
| **`Ctrl + C`** | Works normally; while Batch Mode is ON, adds copied text to your queue. |
| **`Win + Shift + S`** | Takes a Snipping Tool screenshot normally and adds it to your queue. |
| **`Ctrl + V`** | Pastes all queued text and screenshots in order, clears the queue, and turns Batch Mode OFF. |
| **Click HUD `✕`** *(or press `Esc`)* | Cancels **only the current batch** and hides the HUD while keeping the background script active. |
| **Click System Tray Icon** *(or HUD text)* | Opens the live queue preview window with screenshot thumbnails and item controls. |
| **`Ctrl + Alt + Shift + Q`** *(or **Quit App** in tray)* | **Emergency Kill Switch:** Releases modifier keys, unhooks keyboard listeners, and exits the app completely. |

---

## Repository Structure

```text
BatchClipboard/
├── batch_clipboard.py   # Core clipboard listener, keyboard hooks, tray preview UI, and paste engine
├── install.py           # Copies to %LOCALAPPDATA%, adds Windows Startup entry, and launches silently
├── uninstall.py         # Stops background process, cleans registry, and deletes installed files
├── uninstall.bat        # Standalone one-click uninstaller (works even without Python)
├── requirements.txt     # Python dependencies (pywin32, Pillow, keyboard)
├── .gitignore           # Excludes cache, runtime PID, and temporary files
├── LICENSE              # MIT License
└── README.md            # Project documentation
```

---

## Installation

### 1. Clone the Repository & Install Dependencies

```bash
git clone [https://github.com/](https://github.com/)<your-username>/BatchClipboard.git
cd BatchClipboard
pip install -r requirements.txt
```

### 2. Test Before Integrating (Optional)

Run the script directly from a terminal to try it out first:

```bash
python batch_clipboard.py
```

### 3. Integrate with Windows (Silent Background + Auto-Start)

Run the installer once to copy the app to `%LOCALAPPDATA%\BatchClipboard`, register it in Windows Startup (`Task Manager → Startup apps`), and start it silently in the background:

```bash
python install.py
```

*(Whenever you update `batch_clipboard.py`, run `python install.py` again to restart and update the background instance.)*

---

## Uninstallation

To stop the background process, remove the Windows Startup registry entry, and delete all installed files, run:

```bash
python uninstall.py
```

Alternatively, double-click **`uninstall.bat`** in File Explorer to remove everything completely.

---

## Known Limitations

- **Administrator Windows:** Due to Windows UIPI (User Interface Privilege Isolation), global keyboard hooks running as a standard user cannot intercept `Ctrl+C` or `Ctrl+V` inside elevated (Run as Administrator) terminals or apps.

---

## License

Distributed under the MIT License. See `LICENSE` for details.
