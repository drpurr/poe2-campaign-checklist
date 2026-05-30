"""PoE2 Campaign Overlay — entry point.

A lightweight, always-on-top checklist overlay for Path of Exile 2. Pick the
act you're on, tick off objectives as you go, and customize the look from a
separate settings window. Everything is remembered between sessions.
"""

import sys

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon,
)
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from app_state import AppState
from overlay_window import OverlayWindow
from settings_window import SettingsWindow


def make_icon():
    """Build a small check-mark icon at runtime (no asset files needed)."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor("#1b1b24")))
    painter.setPen(QPen(QColor("#5cb85c"), 4))
    painter.drawRoundedRect(6, 6, 52, 52, 12, 12)
    pen = QPen(QColor("#5cb85c"), 7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygon([QPoint(19, 33), QPoint(29, 44), QPoint(46, 21)]))
    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PoE2 Campaign Overlay")
    # Closing the settings window should not quit the app — the tray icon does.
    app.setQuitOnLastWindowClosed(False)

    state = AppState()
    if not state.acts:
        QMessageBox.critical(
            None, "PoE2 Campaign Overlay",
            "No act files were found in the 'acts' folder next to the app.",
        )
        return 1

    icon = make_icon()
    app.setWindowIcon(icon)

    overlay = OverlayWindow(state)
    overlay.setWindowIcon(icon)
    settings = SettingsWindow(state, overlay)
    settings.setWindowIcon(icon)

    def open_settings():
        settings.show()
        settings.raise_()
        settings.activateWindow()

    overlay.on_open_settings = open_settings
    overlay.on_quit = app.quit
    overlay.on_act_changed = settings.sync_from_state
    overlay.apply_style()
    overlay.show()

    # System tray: always-available controls
    tray = QSystemTrayIcon(icon)
    tray.setToolTip("PoE2 Campaign Overlay")
    menu = QMenu()

    act_settings = QAction("Settings…", menu)
    act_settings.triggered.connect(open_settings)
    act_toggle = QAction("Show / hide overlay", menu)
    act_toggle.triggered.connect(lambda: overlay.setVisible(not overlay.isVisible()))
    act_reset_pos = QAction("Reset overlay position", menu)
    act_reset_pos.triggered.connect(overlay.reset_position)
    act_quit = QAction("Quit", menu)
    act_quit.triggered.connect(app.quit)

    menu.addAction(act_settings)
    menu.addAction(act_toggle)
    menu.addAction(act_reset_pos)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            open_settings()

    tray.activated.connect(on_tray_activated)
    tray.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
