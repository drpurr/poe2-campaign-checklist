"""The separate settings window for customizing the overlay.

The window is a **fixed size**: it is sized to its content once at construction
and cannot be resized. A resizable window let Qt distribute slack space inside
the layouts, which pulled labels and controls out of alignment; pinning the size
removes that class of problem.

Alignment is the other priority. Every row label is **left-aligned** inside a
fixed-width label column, so all labels in a section sit on a single vertical
guide (and, because both sections share the same left margin, the two sections
line up with each other too). Controls live in a stretching middle column and
numeric spin boxes in a fixed right-hand column, so combos/sliders share a left
edge and the spin boxes share a right edge.

Styling is a warm "Path of Exile" gold-on-dark QSS layered over the app-wide
dark theme from ``main.py``.
"""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox,
    QSlider, QSpinBox, QPushButton, QLabel, QGroupBox, QSizePolicy,
    QMessageBox, QCheckBox,
)

from act_icons import make_act_icon
from app_state import DEFAULT_CONFIG
from google_fonts import GOOGLE_FONTS, ensure_font
from theme import CAT

# Fixed window width. Height is locked to the natural content height once built.
WINDOW_WIDTH = 480

NUMERIC_COL_WIDTH = 84       # right-hand spin-box column width
APPEARANCE_LABEL_COL = 78    # left label column in the Appearance section
ACT_ICON_COL = 40            # emblem column in the Act Reward Choices section
SECTION_SPACING = 12

# Painted ornate frame geometry.
FRAME_MARGIN = 5             # frame inset from the window edge
FRAME_RADIUS = 12

# Catppuccin Mocha styling. Kept as a plain string (not an f-string) so the QSS
# braces need no escaping; palette values are spliced in once via .format below.
# The root is transparent because the base fill + frame are painted in
# paintEvent (a frameless, translucent top-level window).
_QSS = """
QWidget#SettingsRoot {{ background: transparent; }}

QLabel#TitleText {{
    color: {text}; font-size: 14px; font-weight: 700; letter-spacing: 3px;
}}
QLabel#TitleGear {{ color: {accent}; font-size: 16px; }}
QPushButton#CloseX {{
    background: transparent; border: 1px solid {surface1}; border-radius: 5px;
    color: {subtext0}; font-size: 13px; font-weight: 700; padding: 0;
}}
QPushButton#CloseX:hover {{ border: 1px solid {red}; color: {red}; }}

QGroupBox {{
    border: 1px solid {surface1};
    border-radius: 8px;
    margin-top: 16px;
    padding: 10px 4px 4px 4px;
    background-color: {mantle};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 2px 8px;
    color: {accent};
    font-size: 12px;
    font-weight: 700;
}}

QLabel#RowLabel {{ color: {text}; font-size: 13px; }}
QLabel#Caption  {{ color: {subtext0}; font-size: 11px; }}
QCheckBox       {{ color: {text}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {surface2}; background: {surface0};
}}
QCheckBox::indicator:checked {{
    background: {accent}; border: 1px solid {accent};
}}

QComboBox, QSpinBox {{
    background-color: {surface0};
    border: 1px solid {surface1};
    border-radius: 5px;
    padding: 4px 6px;
    color: {text};
    selection-background-color: {accent};
    selection-color: {crust};
}}
QComboBox:hover, QSpinBox:hover {{ border: 1px solid {surface2}; }}
QComboBox:focus, QSpinBox:focus {{ border: 1px solid {accent}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background-color: {surface0};
    border: 1px solid {surface1};
    color: {text};
    selection-background-color: {accent};
    selection-color: {crust};
    outline: none;
}}

QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: {surface1}; }}
QSlider::sub-page:horizontal {{ height: 6px; border-radius: 3px; background: {accent}; }}
QSlider::handle:horizontal {{
    width: 16px; margin: -6px 0; border-radius: 8px;
    background: {accent}; border: 1px solid {crust};
}}
QSlider::handle:horizontal:hover {{ background: {accent_dim}; }}

QPushButton {{
    background-color: {surface0};
    border: 1px solid {surface1};
    border-radius: 6px;
    padding: 6px 14px;
    color: {text};
}}
QPushButton:hover  {{ border: 1px solid {accent}; background-color: {surface1}; }}
QPushButton:pressed {{ background-color: {mantle}; }}
QPushButton#PrimaryBtn {{
    background-color: {accent}; border: 1px solid {accent};
    color: {crust}; font-weight: 700;
}}
QPushButton#PrimaryBtn:hover {{ background-color: {accent_dim}; }}
""".format(**CAT)


class _TitleBar(QWidget):
    """Frameless title bar: gear glyph + title, with drag-to-move and close.

    The window is frameless (so it can wear the painted gold frame), which means
    it loses the OS title bar — this re-implements the essentials: a draggable
    strip and a close button wired to the window.
    """

    def __init__(self, window, title):
        super().__init__(window)
        self._win = window
        self._press_offset = None
        self.setFixedHeight(34)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 0, 4, 0)
        row.setSpacing(8)
        gear = QLabel("⚙")           # ⚙
        gear.setObjectName("TitleGear")
        name = QLabel(title)
        name.setObjectName("TitleText")
        close = QPushButton("✕")      # ✕
        close.setObjectName("CloseX")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setFixedSize(26, 24)
        close.setToolTip("Close")
        close.clicked.connect(window.close)
        row.addWidget(gear)
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(close)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = (
                event.globalPosition().toPoint()
                - self._win.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (self._press_offset is not None
                and event.buttons() & Qt.MouseButton.LeftButton):
            self._win.move(event.globalPosition().toPoint() - self._press_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._press_offset = None


class SettingsWindow(QWidget):
    def __init__(self, state, overlay):
        super().__init__()
        self.state = state
        self.overlay = overlay
        # Start "loading" so widget signals that fire during construction
        # (e.g. setRange/addItem emitting valueChanged/currentIndexChanged)
        # are ignored until _load_from_config has populated everything.
        self._loading = True

        self.setObjectName("SettingsRoot")
        self.setWindowTitle("Settings")
        # Frameless + translucent so the window can wear a painted gold frame
        # with rounded corners (see paintEvent); the title bar is re-added below.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(_QSS)

        # Outer margins leave room for the painted frame; the title bar sits just
        # inside it, then the content with its own breathing room.
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 14)
        root.setSpacing(SECTION_SPACING)

        root.addWidget(_TitleBar(self, "SETTINGS"))
        root.addWidget(self._build_appearance_group())
        choices = self._build_choices_group()
        if choices is not None:
            root.addWidget(choices)
        root.addStretch(1)
        root.addLayout(self._build_buttons())

        self._load_from_config()

        # Lock the size to the natural content height at the fixed width, so the
        # window cannot be resized and nothing can drift out of alignment.
        self.setFixedWidth(WINDOW_WIDTH)
        self.setFixedHeight(self.sizeHint().height())

    def paintEvent(self, _event):
        """Paint the Catppuccin base fill and the double-rule accent frame."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(
            FRAME_MARGIN, FRAME_MARGIN, -FRAME_MARGIN, -FRAME_MARGIN
        )
        outer = QPainterPath()
        outer.addRoundedRect(rect, FRAME_RADIUS, FRAME_RADIUS)
        painter.fillPath(outer, QColor(CAT["base"]))
        inner = QRectF(rect).adjusted(4, 4, -4, -4)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, FRAME_RADIUS - 3, FRAME_RADIUS - 3)
        painter.setPen(QPen(QColor(CAT["surface0"]), 1))
        painter.drawPath(inner_path)
        painter.setPen(QPen(QColor(CAT["accent"]), 2))
        painter.drawPath(outer)
        painter.end()

    # ----- construction --------------------------------------------------
    def _row_label(self, text):
        """A LEFT-aligned label for a grid's first column.

        Left alignment is what puts every label's left edge on one vertical
        guide; the fixed column width then keeps the controls lined up too.
        """
        lbl = QLabel(text)
        lbl.setObjectName("RowLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _build_appearance_group(self):
        """Appearance: font + size, opacity, border + icon size.

        3 columns: left label (fixed) | control (stretch) | numeric (fixed).
        Colours are fixed by the app theme, so there are no colour pickers.
        """
        group = QGroupBox("APPEARANCE")
        grid = QGridLayout(group)
        grid.setContentsMargins(16, 16, 16, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, APPEARANCE_LABEL_COL)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(2, NUMERIC_COL_WIDTH)

        # Row 0 — Font family (control) + size (numeric).
        self.font_combo = QComboBox()
        self.font_combo.addItems(GOOGLE_FONTS)
        self._make_combo_compact(self.font_combo)
        self.font_combo.currentIndexChanged.connect(self._on_font_changed)
        self.font_size = self._numeric_spin(8, 40, "")
        self.font_size.valueChanged.connect(self._on_style_changed)
        grid.addWidget(self._row_label("Font"), 0, 0)
        grid.addWidget(self.font_combo, 0, 1)
        grid.addWidget(self.font_size, 0, 2)

        # Row 1 — Opacity slider (control) + percentage (numeric).
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(0, 100)
        self.trans_slider.valueChanged.connect(self._on_trans_slider)
        self.trans_spin = self._numeric_spin(0, 100, "%")
        self.trans_spin.valueChanged.connect(self._on_trans_spin)
        grid.addWidget(self._row_label("Opacity"), 1, 0)
        grid.addWidget(self.trans_slider, 1, 1)
        grid.addWidget(self.trans_spin, 1, 2)

        # Row 2 — Show border (left, on the label guide) paired with the icon
        # size spin on the right. A spanning row whose trailing spin is fixed to
        # the numeric width, so its right edge lands on the same guide as the
        # font-size and opacity spins above.
        self.border_checkbox = QCheckBox("Show border")
        self.border_checkbox.toggled.connect(self._on_border_toggled)
        self.control_size = self._numeric_spin(8, 40, "")
        self.control_size.valueChanged.connect(self._on_style_changed)
        icon_label = QLabel("Icon size")
        icon_label.setObjectName("RowLabel")
        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        bottom.addWidget(self.border_checkbox)
        bottom.addStretch(1)
        bottom.addWidget(icon_label)
        bottom.addWidget(self.control_size)
        grid.addLayout(bottom, 2, 0, 1, 3)

        return group

    def _build_choices_group(self):
        """Act-reward choices, or ``None`` when no act offers a choice.

        3 columns: emblem icon (fixed) | label (fixed to the widest label) |
        dropdown (stretch). Icons sit on the left guide, labels share a column,
        and every dropdown shares both edges.
        """
        self.choice_combos = []
        rows = []
        for act in self.state.acts:
            for item in act.get("items", []):
                if item.get("choices"):
                    rows.append((act, item))
        if not rows:
            return None

        group = QGroupBox("ACT REWARD CHOICES")
        grid = QGridLayout(group)
        grid.setContentsMargins(16, 16, 16, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)
        grid.setColumnMinimumWidth(0, ACT_ICON_COL)
        grid.setColumnStretch(2, 1)

        # Size the label column to the widest label so every dropdown lines up.
        metrics = self.fontMetrics()
        label_texts = [
            item.get("choice_label") or f'{act.get("name", "Act")} choice'
            for act, item in rows
        ]
        grid.setColumnMinimumWidth(
            1, max(metrics.horizontalAdvance(t) for t in label_texts) + 8
        )

        for row, (act, item) in enumerate(rows):
            combo = QComboBox()
            combo.addItems(item["choices"])
            combo.setProperty("item_id", item["id"])
            self._make_combo_compact(combo)
            combo.currentIndexChanged.connect(self._on_choice_changed)
            self.choice_combos.append(combo)

            icon = QLabel()
            icon.setPixmap(make_act_icon(item.get("icon"), 30))
            icon.setFixedWidth(ACT_ICON_COL)
            icon.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            grid.addWidget(icon, row, 0)
            grid.addWidget(self._row_label(label_texts[row]), row, 1)
            grid.addWidget(combo, row, 2)

        return group

    def _build_buttons(self):
        """Bottom button row: three resets on the left, Close (primary) right."""
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.reset_progress_btn = QPushButton("Reset act")
        self.reset_progress_btn.setToolTip("Clear all checkmarks for the current act")
        self.reset_progress_btn.clicked.connect(self._reset_progress)
        self.reset_all_btn = QPushButton("Reset all")
        self.reset_all_btn.setToolTip("Clear all checkmarks for every act")
        self.reset_all_btn.clicked.connect(self._reset_all_progress)
        self.reset_settings_btn = QPushButton("Reset settings")
        self.reset_settings_btn.clicked.connect(self._reset_settings)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("PrimaryBtn")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.close)
        buttons.addWidget(self.reset_progress_btn)
        buttons.addWidget(self.reset_all_btn)
        buttons.addWidget(self.reset_settings_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        return buttons

    # ----- small widget helpers -----------------------------------------
    def _numeric_spin(self, lo, hi, suffix):
        """A fixed-width spin box so the numeric column aligns exactly."""
        spin = QSpinBox()
        spin.setRange(lo, hi)
        if suffix:
            spin.setSuffix(suffix)
        spin.setFixedWidth(NUMERIC_COL_WIDTH)
        spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return spin

    def _make_combo_compact(self, combo):
        """Stop a combo's longest item from dictating the window width.

        The collapsed box shrinks to its column (auto-eliding its current text
        with an ellipsis), while the drop-down popup is widened to show every
        option in full. The current selection is exposed via a tooltip.
        """
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(10)
        combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        metrics = combo.fontMetrics()
        widest = max(
            (metrics.horizontalAdvance(combo.itemText(i))
             for i in range(combo.count())),
            default=0,
        )
        combo.view().setMinimumWidth(widest + 40)
        combo.setToolTip(combo.currentText())

    # ----- loading -------------------------------------------------------
    def _load_from_config(self):
        self._loading = True
        cfg = self.state.config
        trans_pct = int(round(cfg.get("transparency", 0.85) * 100))
        self.trans_slider.setValue(trans_pct)
        self.trans_spin.setValue(trans_pct)
        self.font_size.setValue(int(cfg.get("font_size", 14)))
        self._select_font(cfg.get("font_family", "Roboto"))
        self.control_size.setValue(int(cfg.get("control_size", 20)))
        self.border_checkbox.setChecked(bool(cfg.get("border_enabled", True)))
        self._load_choices()
        self._loading = False

    def _load_choices(self):
        """Select each choice combo to match the item's saved (or default) pick."""
        items = {
            item["id"]: item
            for act in self.state.acts
            for item in act.get("items", [])
        }
        for combo in self.choice_combos:
            item = items.get(combo.property("item_id"))
            if item is None:
                continue
            index = combo.findText(self.state.get_item_choice(item))
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.setToolTip(combo.currentText())

    def _select_font(self, family):
        """Select ``family`` in the combo, adding it if it isn't listed."""
        index = self.font_combo.findText(family)
        if index < 0:
            self.font_combo.addItem(family)
            index = self.font_combo.count() - 1
        self.font_combo.setCurrentIndex(index)
        self._preview_font(family)

    def _preview_font(self, family):
        """Render the font dropdown in the selected family when available."""
        resolved = ensure_font(family)
        if resolved:
            self.font_combo.setFont(QFont(resolved))

    def sync_from_state(self):
        """Refresh the window after the overlay changed state (e.g. next act)."""
        self._load_from_config()

    # ----- handlers ------------------------------------------------------
    def _on_border_toggled(self, _checked):
        if self._loading:
            return
        self._on_style_changed()

    def _on_trans_slider(self, value):
        if self._loading:
            return
        self._loading = True
        self.trans_spin.setValue(value)
        self._loading = False
        self._on_style_changed()

    def _on_trans_spin(self, value):
        if self._loading:
            return
        self._loading = True
        self.trans_slider.setValue(value)
        self._loading = False
        self._on_style_changed()

    def _on_font_changed(self, _index):
        if self._loading:
            return
        self._preview_font(self.font_combo.currentText())
        self._on_style_changed()

    def _on_choice_changed(self, _index):
        if self._loading:
            return
        combo = self.sender()
        combo.setToolTip(combo.currentText())
        self.state.set_item_choice(combo.property("item_id"), combo.currentText())
        # The chosen option is part of the item's text, so rebuild the list.
        self.overlay.rebuild_items()

    def _on_style_changed(self, *_):
        if self._loading:
            return
        cfg = self.state.config
        cfg["transparency"] = self.trans_slider.value() / 100.0
        cfg["font_size"] = self.font_size.value()
        cfg["font_family"] = self.font_combo.currentText()
        cfg["control_size"] = self.control_size.value()
        cfg["border_enabled"] = self.border_checkbox.isChecked()
        self.state.save_config()
        self.overlay.apply_style()

    def _reset_progress(self):
        act = self.state.current_act
        if not act:
            return
        answer = QMessageBox.question(
            self, "Reset progress",
            f'Clear all checkmarks for "{act["name"]}"?',
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.state.reset_act_progress(act["id"])
            self.overlay.rebuild_items()

    def _reset_all_progress(self):
        answer = QMessageBox.question(
            self, "Reset all progress",
            "Clear all checkmarks for every act?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.state.reset_all_progress()
            self.overlay.rebuild_items()

    def _reset_settings(self):
        for key, value in DEFAULT_CONFIG.items():
            if key in ("current_act", "overlay_geometry"):
                continue
            self.state.config[key] = value
        self.state.save_config()
        self._load_from_config()
        self.overlay.apply_style()
        self.overlay.rebuild_items()
        self.overlay.sync_lock_from_config()

    # ----- resize mode tie-in -------------------------------------------
    def showEvent(self, event):
        self.overlay.set_resize_enabled(True)
        super().showEvent(event)

    def hideEvent(self, event):
        self.overlay.set_resize_enabled(False)
        super().hideEvent(event)

    def closeEvent(self, event):
        self.overlay.set_resize_enabled(False)
        self.state.save_config()
        super().closeEvent(event)
