"""Shared Catppuccin Mocha theme for the whole app.

A single source of truth for colours so the settings window, the overlay and the
incidental popups (message boxes, the tray menu, tooltips) all match. This is why
the app no longer depends on an external theme package: every surface we show is
styled from ``CAT`` here.

Palette: https://github.com/catppuccin/catppuccin — the dark "Mocha" flavour,
with Mauve as the accent.
"""

CAT = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "subtext0": "#a6adc8",
    "subtext1": "#bac2de",
    "text": "#cdd6f4",
    "accent": "#cba6f7",      # mauve
    "accent_dim": "#b4befe",  # lavender (hover/secondary)
    "red": "#f38ba8",
    "blue": "#89b4fa",
}

# App-wide QSS for the bits we don't hand-build: confirmation dialogs, the tray
# context menu and tooltips. Replaces qdarktheme — small on purpose, since the
# two main windows fully style themselves. ``.format(**CAT)`` splices colours in;
# literal QSS braces are doubled.
POPUP_QSS = """
QMessageBox, QMenu, QDialog {{
    background-color: {base};
    color: {text};
}}
QMessageBox QLabel {{ color: {text}; }}
QMenu::item {{ padding: 5px 22px; }}
QMenu::item:selected {{ background-color: {accent}; color: {crust}; }}
QMenu::separator {{ height: 1px; background: {surface1}; margin: 4px 8px; }}
QToolTip {{
    background-color: {mantle};
    color: {text};
    border: 1px solid {surface1};
    padding: 3px 6px;
}}
QPushButton {{
    background-color: {surface0};
    border: 1px solid {surface1};
    border-radius: 6px;
    padding: 5px 14px;
    color: {text};
}}
QPushButton:hover {{ border: 1px solid {accent}; background-color: {surface1}; }}
QPushButton:pressed {{ background-color: {mantle}; }}
""".format(**CAT)
