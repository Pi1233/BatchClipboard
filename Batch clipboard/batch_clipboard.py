import ctypes
import gc
import hashlib
import io
import os
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import keyboard
import win32api
import win32clipboard
import win32con
import win32gui
from PIL import Image, ImageDraw, ImageGrab, ImageTk

user32 = ctypes.windll.user32
CF_PNG = win32clipboard.RegisterClipboardFormat("PNG")
WM_TRAY_CALLBACK = win32con.WM_USER + 20


@dataclass
class ClipItem:
    kind: str  # "text" or "image"
    digest: str
    text: Optional[str] = None
    png_bytes: Optional[bytes] = None
    dimensions: str = ""


class BatchClipboardManager:
    def __init__(self):
        self.batch_mode = False
        self.items: List[ClipItem] = []
        self.lock = threading.Lock()

        # Deduplication tracking (prevents Snipping Tool double-capture)
        self.last_digest = ""
        self.last_capture_time = 0.0

        # Flags to prevent self-triggering during paste
        self.ignore_clipboard_until = 0.0
        self.passing_paste = False

        # Double-tap Ctrl tracking (ignores Ctrl+C, Ctrl+Shift, etc.)
        self.ctrl_down = False
        self.other_key_during_ctrl = False
        self.last_pure_ctrl_up = 0.0

        # Tray & Preview state
        self.tray_hwnd = None
        self.preview_open = False
        self.preview_dirty = False
        self._thumb_refs: List[ImageTk.PhotoImage] = []

        # Setup UI
        self.root = tk.Tk()
        self._setup_hud()
        self._setup_preview_window()

    # ---------------------------------------------------------
    # 1. Floating Status HUD (Bottom-Right Pill)
    # ---------------------------------------------------------
    def _setup_hud(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)
        self.root.configure(bg="#1e1e2e")

        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack()

        self.label = tk.Label(
            container,
            text="",
            fg="#cdd6f4",
            bg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
        )
        self.label.pack(side=tk.LEFT)
        # Clicking the pill opens/closes the preview list
        self.label.bind("<Button-1>", lambda _e: self.toggle_preview_window())

        # Clicking ✕ cancels ONLY the current batch (keeps background script alive!)
        cancel_btn = tk.Button(
            container,
            text="✕",
            command=self.cancel_batch_mode,
            fg="#f38ba8",
            bg="#313244",
            activeforeground="#1e1e2e",
            activebackground="#f38ba8",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            cursor="hand2",
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=4)

        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"+{screen_w - 375}+{screen_h - 95}")
        self.root.withdraw()

    def update_hud(self):
        with self.lock:
            active = self.batch_mode
            text_count = sum(1 for i in self.items if i.kind == "text")
            img_count = sum(1 for i in self.items if i.kind == "image")
            dirty = self.preview_dirty
            if dirty:
                self.preview_dirty = False

        if active:
            self.label.config(
                text=f"Batch ON  |  {text_count} text, {img_count} snips  |  Ctrl+V"
            )
            self.root.deiconify()
        else:
            self.root.withdraw()

        if self.preview_open and dirty:
            self._render_preview_items()

        self.root.after(120, self.update_hud)

    # ---------------------------------------------------------
    # 2. Tray Click Preview Window (Inspect & Manage Queue)
    # ---------------------------------------------------------
    def _setup_preview_window(self):
        self.preview_win = tk.Toplevel(self.root)
        self.preview_win.overrideredirect(True)
        self.preview_win.attributes("-topmost", True)
        self.preview_win.attributes("-alpha", 0.96)
        self.preview_win.configure(bg="#181825", highlightbackground="#45475a", highlightthickness=1)

        # Top header bar
        header = tk.Frame(self.preview_win, bg="#11111b", padx=10, pady=8)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="BatchClipboard Queue",
            fg="#cdd6f4",
            bg="#11111b",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT)

        close_preview_btn = tk.Button(
            header,
            text="—",
            command=self.hide_preview_window,
            fg="#a6adc8",
            bg="#313244",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        close_preview_btn.pack(side=tk.RIGHT)

        self.mode_toggle_btn = tk.Button(
            header,
            text="Batch: OFF",
            command=self.toggle_batch_mode,
            fg="#11111b",
            bg="#a6e3a1",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.mode_toggle_btn.pack(side=tk.RIGHT, padx=(0, 8))

        # Scrollable list area
        list_wrapper = tk.Frame(self.preview_win, bg="#181825")
        list_wrapper.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.canvas = tk.Canvas(
            list_wrapper,
            bg="#181825",
            bd=0,
            highlightthickness=0,
            width=355,
            height=260,
        )
        scrollbar = tk.Scrollbar(
            list_wrapper, orient="vertical", command=self.canvas.yview
        )
        self.items_frame = tk.Frame(self.canvas, bg="#181825")

        self.items_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.items_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom action bar
        footer = tk.Frame(self.preview_win, bg="#11111b", padx=10, pady=8)
        footer.pack(fill=tk.X)

        tk.Button(
            footer,
            text="Clear Queue",
            command=self.clear_queue_only,
            fg="#cdd6f4",
            bg="#313244",
            bd=0,
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        tk.Button(
            footer,
            text="Quit App",
            command=self.emergency_exit,
            fg="#11111b",
            bg="#f38ba8",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        self.preview_win.withdraw()

    def toggle_preview_window(self):
        if self.preview_open:
            self.hide_preview_window()
        else:
            self.show_preview_window()

    def show_preview_window(self):
        self.preview_open = True
        self._render_preview_items()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.preview_win.geometry(f"385x355+{screen_w - 405}+{screen_h - 455}")
        self.preview_win.deiconify()
        self.preview_win.lift()

    def hide_preview_window(self):
        self.preview_open = False
        self._thumb_refs.clear()
        self.preview_win.withdraw()
        gc.collect()

    def _render_preview_items(self):
        for child in self.items_frame.winfo_children():
            child.destroy()
        self._thumb_refs.clear()

        with self.lock:
            active = self.batch_mode
            snapshot = list(self.items)

        if active:
            self.mode_toggle_btn.config(text="Batch: ON", bg="#a6e3a1", fg="#11111b")
        else:
            self.mode_toggle_btn.config(text="Batch: OFF", bg="#45475a", fg="#cdd6f4")

        if not snapshot:
            tk.Label(
                self.items_frame,
                text="Nothing copied yet.\n\nDouble-tap Ctrl to turn Batch ON,\nthen use Ctrl+C or Win+Shift+S.",
                fg="#a6adc8",
                bg="#181825",
                font=("Segoe UI", 9),
                justify=tk.CENTER,
                pady=65,
                padx=35,
            ).pack(fill=tk.X)
            return

        for idx, item in enumerate(snapshot):
            row = tk.Frame(self.items_frame, bg="#242436", padx=8, pady=6)
            row.pack(fill=tk.X, pady=3, padx=2)

            tk.Label(
                row,
                text=f"#{idx + 1}",
                fg="#89b4fa",
                bg="#242436",
                font=("Segoe UI", 9, "bold"),
                width=3,
                anchor="w",
            ).pack(side=tk.LEFT)

            if item.kind == "text" and item.text is not None:
                clean_line = " ".join(item.text.split())
                if len(clean_line) > 42:
                    clean_line = clean_line[:39] + "..."
                tk.Label(
                    row,
                    text=clean_line,
                    fg="#cdd6f4",
                    bg="#242436",
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

            elif item.kind == "image" and item.png_bytes is not None:
                try:
                    with Image.open(io.BytesIO(item.png_bytes)) as im:
                        im.thumbnail((72, 40))
                        photo = ImageTk.PhotoImage(im)
                        self._thumb_refs.append(photo)
                        tk.Label(row, image=photo, bg="#242436").pack(
                            side=tk.LEFT, padx=(4, 8)
                        )
                except Exception:
                    pass

                tk.Label(
                    row,
                    text=f"Snip ({item.dimensions})",
                    fg="#a6e3a1",
                    bg="#242436",
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Remove single item button
            tk.Button(
                row,
                text="✕",
                command=lambda i=idx: self.remove_item_at(i),
                fg="#f38ba8",
                bg="#313244",
                bd=0,
                font=("Segoe UI", 8, "bold"),
                padx=6,
                pady=2,
                cursor="hand2",
            ).pack(side=tk.RIGHT)

    def remove_item_at(self, index: int):
        with self.lock:
            if 0 <= index < len(self.items):
                self.items.pop(index)
                self.preview_dirty = True
        gc.collect()

    def clear_queue_only(self):
        with self.lock:
            self.items.clear()
            self.last_digest = ""
            self.preview_dirty = True
        gc.collect()

    # ---------------------------------------------------------
    # 3. Native Win32 System Tray Icon (Zero Extra Libraries)
    # ---------------------------------------------------------
    def start_tray_icon(self):
        threading.Thread(target=self._tray_thread_worker, daemon=True).start()

    def _create_tray_ico_file(self) -> Path:
        ico_path = Path(tempfile.gettempdir()) / "batch_clipboard_tray.ico"
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Rounded indigo badge + layered white clipboard cards
        draw.rounded_rectangle([2, 2, 30, 30], radius=7, fill="#89b4fa")
        draw.rectangle([8, 10, 20, 24], fill="#1e1e2e")
        draw.rectangle([12, 7, 24, 21], fill="#ffffff")
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32)])
        return ico_path

    def _tray_thread_worker(self):
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "BatchClipboardTrayClass"
        wc.lpfnWndProc = self._tray_wnd_proc
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        self.tray_hwnd = win32gui.CreateWindow(
            wc.lpszClassName, "BatchClipboardTray", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
        )

        try:
            ico_path = self._create_tray_ico_file()
            hicon = win32gui.LoadImage(
                0, str(ico_path), win32con.IMAGE_ICON, 16, 16, win32con.LR_LOADFROMFILE
            )
        except Exception:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.tray_hwnd, 1, flags, WM_TRAY_CALLBACK, hicon, "BatchClipboard (Click to inspect queue)")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        win32gui.PumpMessages()

    def _tray_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY_CALLBACK:
            if lparam in (win32con.WM_LBUTTONUP, win32con.WM_RBUTTONUP):
                self.root.after(0, self.toggle_preview_window)
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    # ---------------------------------------------------------
    # 4. Kill Switch & Batch Toggle Controls
    # ---------------------------------------------------------
    def emergency_exit(self):
        print("\n[Quit App] Removing tray icon, releasing hooks, and exiting...")
        try:
            if self.tray_hwnd:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.tray_hwnd, 1))
        except Exception:
            pass

        try:
            for vk in (win32con.VK_CONTROL, win32con.VK_MENU, win32con.VK_SHIFT):
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        os._exit(0)

    def start_hooks(self):
        keyboard.add_hotkey("ctrl+alt+shift+q", self.emergency_exit, suppress=True)
        keyboard.hook(self._on_passive_key, suppress=False)
        keyboard.add_hotkey("ctrl+v", self._on_ctrl_v, suppress=True)
        keyboard.add_hotkey("ctrl+alt+b", self.toggle_batch_mode, suppress=True)

    def _on_passive_key(self, event: keyboard.KeyboardEvent):
        name = (event.name or "").lower()
        is_ctrl = "ctrl" in name

        if event.event_type == keyboard.KEY_DOWN:
            if is_ctrl:
                if not self.ctrl_down:
                    self.ctrl_down = True
                    self.other_key_during_ctrl = False
            else:
                if self.ctrl_down:
                    self.other_key_during_ctrl = True

                if name == "esc" and self.batch_mode:
                    self.cancel_batch_mode()

        elif event.event_type == keyboard.KEY_UP and is_ctrl:
            self.ctrl_down = False
            if not self.other_key_during_ctrl:
                now = time.time()
                if now - self.last_pure_ctrl_up <= 0.40:
                    self.last_pure_ctrl_up = 0.0
                    self.toggle_batch_mode()
                else:
                    self.last_pure_ctrl_up = now

    def toggle_batch_mode(self):
        with self.lock:
            self.batch_mode = not self.batch_mode
            self.items.clear()
            self.last_digest = ""
            self.preview_dirty = True
            if self.batch_mode:
                self.ignore_clipboard_until = time.time() + 0.15
                print("[Batch Mode ON] Copy text (Ctrl+C) or Snip (Win+Shift+S)...")
            else:
                print("[Batch Mode OFF] Cleared queue.")
        gc.collect()

    def cancel_batch_mode(self):
        """Closes HUD and clears current batch WITHOUT killing background script."""
        with self.lock:
            self.batch_mode = False
            self.items.clear()
            self.last_digest = ""
            self.preview_dirty = True
        gc.collect()
        print("[Batch Cancelled] Double-tap Ctrl anytime to start a new batch.")

    # ---------------------------------------------------------
    # 5. Paste Worker (Browser & AI Chat Safe)
    # ---------------------------------------------------------
    def _on_ctrl_v(self):
        if self.passing_paste:
            return

        with self.lock:
            has_batch = self.batch_mode and len(self.items) > 0
            items_snapshot = list(self.items)
            if self.batch_mode:
                self.items.clear()
                self.batch_mode = False
                self.preview_dirty = True

        threading.Thread(
            target=self._paste_worker,
            args=(items_snapshot if has_batch else None,),
            daemon=True,
        ).start()

    def _paste_worker(self, items_snapshot: Optional[List[ClipItem]]):
        self.passing_paste = True
        self.ignore_clipboard_until = time.time() + 25.0

        try:
            deadline = time.time() + 0.30
            while time.time() < deadline:
                if (user32.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000) == 0:
                    break
                time.sleep(0.01)

            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            if not items_snapshot:
                self._send_ctrl_v()
                return

            for idx, item in enumerate(items_snapshot):
                if item.kind == "text" and item.text is not None:
                    self._set_clipboard_text(item.text)
                    time.sleep(0.05)
                    self._send_ctrl_v()
                    time.sleep(0.18)
                elif item.kind == "image" and item.png_bytes is not None:
                    # Convert PNG -> DIB on the fly to keep idle RAM minimal
                    dib_bytes = self._png_to_dib(item.png_bytes)
                    self._set_clipboard_image(item.png_bytes, dib_bytes)
                    del dib_bytes
                    time.sleep(0.06)
                    self._send_ctrl_v()
                    time.sleep(0.55)

                if idx < len(items_snapshot) - 1:
                    self._send_shift_enter()
                    time.sleep(0.06)

            items_snapshot.clear()
            gc.collect()
        finally:
            self.ignore_clipboard_until = time.time() + 0.35
            self.passing_paste = False

    def _png_to_dib(self, png_bytes: bytes) -> bytes:
        with Image.open(io.BytesIO(png_bytes)) as im:
            with io.BytesIO() as bmp_buf:
                im.convert("RGB").save(bmp_buf, format="BMP")
                return bmp_buf.getvalue()[14:]

    def _send_ctrl_v(self):
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        time.sleep(0.01)
        win32api.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.015)
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

    def _send_shift_enter(self):
        win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
        time.sleep(0.01)
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        time.sleep(0.015)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
        win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

    # ---------------------------------------------------------
    # 6. Clipboard Read / Write Helpers
    # ---------------------------------------------------------
    def _set_clipboard_text(self, text: str):
        for _ in range(6):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                finally:
                    win32clipboard.CloseClipboard()
                return
            except Exception:
                time.sleep(0.03)

    def _set_clipboard_image(self, png_bytes: bytes, dib_bytes: bytes):
        for _ in range(6):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(CF_PNG, png_bytes)
                    win32clipboard.SetClipboardData(win32con.CF_DIB, dib_bytes)
                finally:
                    win32clipboard.CloseClipboard()
                return
            except Exception:
                time.sleep(0.03)

    def start_clipboard_watcher(self):
        threading.Thread(target=self._watch_clipboard_loop, daemon=True).start()

    def _watch_clipboard_loop(self):
        last_seq = user32.GetClipboardSequenceNumber()

        while True:
            time.sleep(0.08)
            seq = user32.GetClipboardSequenceNumber()
            if seq == last_seq:
                continue

            time.sleep(0.14)
            last_seq = user32.GetClipboardSequenceNumber()

            if time.time() < self.ignore_clipboard_until:
                continue

            with self.lock:
                if not self.batch_mode:
                    continue

            captured = self._read_current_clipboard()
            if captured:
                now = time.time()
                with self.lock:
                    if not self.batch_mode:
                        continue
                    if (
                        captured.digest == self.last_digest
                        and (now - self.last_capture_time) < 2.5
                    ):
                        continue

                    self.last_digest = captured.digest
                    self.last_capture_time = now
                    self.items.append(captured)
                    self.preview_dirty = True
                    print(f"[Captured #{len(self.items)}] Type: {captured.kind}")

    def _read_current_clipboard(self) -> Optional[ClipItem]:
        for _ in range(5):
            try:
                win32clipboard.OpenClipboard()
                try:
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                        if text and text.strip():
                            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                            return ClipItem(kind="text", digest=digest, text=text)
                finally:
                    win32clipboard.CloseClipboard()
                break
            except Exception:
                time.sleep(0.03)

        try:
            grabbed = ImageGrab.grabclipboard()
            if isinstance(grabbed, Image.Image):
                w, h = grabbed.size
                with io.BytesIO() as png_buf:
                    grabbed.convert("RGB").save(png_buf, format="PNG", optimize=True)
                    png_bytes = png_buf.getvalue()
                grabbed.close()

                digest = hashlib.sha256(png_bytes).hexdigest()
                return ClipItem(
                    kind="image",
                    digest=digest,
                    png_bytes=png_bytes,
                    dimensions=f"{w}×{h}",
                )
        except Exception as exc:
            print(f"[Warning] Could not read clipboard image: {exc}")

        return None

    def run(self):
        self.start_tray_icon()
        self.start_hooks()
        self.start_clipboard_watcher()
        self.update_hud()
        self.root.mainloop()


if __name__ == "__main__":
    app = BatchClipboardManager()
    app.run()