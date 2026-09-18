import os
import sys
import ctypes
import ctypes.wintypes
import threading
import time
import requests

# Windows Global Hotkey: Win + Shift + R
# MOD_WIN = 0x0008, MOD_SHIFT = 0x0004 -> 0x000C
MOD_WIN = 0x0008
MOD_SHIFT = 0x0004
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_R = 0x52
VK_SPACE = 0x20
HOTKEY_ID_RAYGENT = 1001

class WindowsGlobalHotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        user32 = ctypes.windll.user32
        # Register Win + Shift + R
        success1 = user32.RegisterHotKey(None, HOTKEY_ID_RAYGENT, MOD_WIN | MOD_SHIFT, VK_R)
        # Register Alt + Space as secondary convenience hotkey
        success2 = user32.RegisterHotKey(None, HOTKEY_ID_RAYGENT + 1, MOD_ALT, VK_SPACE)
        
        print(f"Global hotkeys registered: Win+Shift+R ({bool(success1)}), Alt+Space ({bool(success2)})")
        
        msg = ctypes.wintypes.MSG()
        while self.running:
            if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312: # WM_HOTKEY
                    try:
                        self.callback(msg.wParam)
                    except Exception as e:
                        print("Hotkey callback error:", e)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)

    def stop(self):
        self.running = False
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_RAYGENT)
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_RAYGENT + 1)

if __name__ == "__main__":
    def on_hotkey(hotkey_id):
        print(f"*** RAYGENT SUMMONED VIA HOTKEY ({hotkey_id}) ***")
        import webbrowser
        webbrowser.open("http://127.0.0.1:8765")

    listener = WindowsGlobalHotkeyListener(on_hotkey)
    listener.start()
    print("Raygent global hotkey listener running. Press Win+Shift+R or Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()