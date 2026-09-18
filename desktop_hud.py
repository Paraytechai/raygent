import sys
import os
import json
import urllib.request
from PySide6.QtCore import Qt, QUrl, QPoint, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

from hotkey_listener import WindowsGlobalHotkeyListener, HOTKEY_ID_RAYGENT

class RaygentHUDWindow(QMainWindow):
    def __init__(self, port=8765):
        super().__init__()
        self.port = port
        self.current_hud_mode = "full"
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(480, 720)

        # Position at bottom-right of screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 520, screen.height() - 780)

        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)

        # WebEngine settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        # Connect geometry change requests from JavaScript window.resizeTo
        self.web_view.page().geometryChangeRequested.connect(self.on_geometry_change)

        self.web_view.setUrl(QUrl(f"http://127.0.0.1:{self.port}"))

        self.drag_position = QPoint()

        # System tray icon
        self.tray = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(__file__), "static", "avatars", "ray_portrait.jpeg")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        
        tray_menu = QMenu()
        show_action = QAction("Show Raygent (Win+Shift+R)", self)
        show_action.triggered.connect(self.summon)
        tray_menu.addAction(show_action)

        mode_action = QAction("Toggle Mini / Full Widget (Alt+M)", self)
        mode_action.triggered.connect(self.toggle_mode_from_tray)
        tray_menu.addAction(mode_action)

        quit_action = QAction("Quit Raygent", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.show()

        # Global Hotkey Listener
        self.hotkey_listener = WindowsGlobalHotkeyListener(self.on_hotkey)
        self.hotkey_listener.start()

        # State poll timer for seamless resizing across web / desktop
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.poll_hud_state)
        self.state_timer.start(2500)

    def on_geometry_change(self, geom):
        new_w = geom.width()
        new_h = geom.height()
        self.resize(new_w, new_h)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - new_w - 40, screen.height() - new_h - 60)

    def poll_hud_state(self):
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/hud/state")
            with urllib.request.urlopen(req, timeout=0.25) as resp:
                data = json.loads(resp.read().decode())
                mode = data.get("mode", "full")
                if mode != self.current_hud_mode:
                    self.current_hud_mode = mode
                    target_w = data.get("width", 480)
                    target_h = data.get("height", 720)
                    self.resize(target_w, target_h)
                    screen = QApplication.primaryScreen().geometry()
                    self.move(screen.width() - target_w - 40, screen.height() - target_h - 60)
        except Exception:
            pass

    def toggle_mode_from_tray(self):
        new_mode = "mini" if self.current_hud_mode == "full" else "full"
        is_mini_js = "true" if new_mode == "mini" else "false"
        self.web_view.page().runJavaScript(f"setMiniMode({is_mini_js});")

    def on_hotkey(self, hotkey_id):
        # Triggered from background thread -> invoke summon
        self.summon()

    def summon(self):
        if self.isVisible():
            self.activateWindow()
            self.raise_()
        else:
            self.show()
            self.activateWindow()
            self.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

def run_hud(port=8765):
    app = QApplication(sys.argv)
    window = RaygentHUDWindow(port=port)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_hud()