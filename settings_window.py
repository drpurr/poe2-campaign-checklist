"""The separate settings window for customizing the overlay."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSlider,
    QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QFrame,
    QColorDialog, QMessageBox,
)

from app_state import DEFAULT_CONFIG
from google_fonts import GOOGLE_FONTS, ensure_font


class ClickableSwatch(QFrame):
    """A small color square that opens a color picker when clicked."""

    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self._on_click = on_click
        self.setObjectName("Swatch")
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to choose a color")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
            event.accept()
            return
        super().mousePressEvent(event)


class SettingsWindow(QWidget):
    def __init__(self, state, overlay):
        super().__init__()
        self.state = state
        self.overlay = overlay
        # Start "loading" so widget signals that fire during construction
        # (e.g. setRange/addItem emitting valueChanged/currentIndexChanged)
        # are ignored until _load_from_config has populated everything.
        self._loading = True
        self._color = state.config.get("font_color", "#f0e6d2")
        self._bg_color = state.config.get("bg_color", "#121218")

        self.setWindowTitle("PoE2 Campaign Overlay — Settings")
        self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        # Current act
        self.act_combo = QComboBox()
        for act in state.acts:
            self.act_combo.addItem(act["name"], act["id"])
        self.act_combo.currentIndexChanged.connect(self._on_act_changed)
        form.addRow("Current Act:", self.act_combo)

        # Transparency: slider + manual numeric entry
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(20, 100)
        self.trans_slider.valueChanged.connect(self._on_trans_slider)
        self.trans_spin = QSpinBox()
        self.trans_spin.setRange(20, 100)
        self.trans_spin.setSuffix(" %")
        self.trans_spin.valueChanged.connect(self._on_trans_spin)
        trans_row = QHBoxLayout()
        trans_row.addWidget(self.trans_slider, 1)
        trans_row.addWidget(self.trans_spin)
        form.addRow("Transparency:", self._wrap(trans_row))

        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 40)
        self.font_size.setSuffix(" pt")
        self.font_size.valueChanged.connect(self._on_style_changed)
        form.addRow("Font size:", self.font_size)

        # Font family (Google Fonts)
        self.font_combo = QComboBox()
        self.font_combo.addItems(GOOGLE_FONTS)
        self.font_combo.currentIndexChanged.connect(self._on_font_changed)
        form.addRow("Font family:", self.font_combo)

        # Font color — click the swatch to open the picker
        self.color_swatch = ClickableSwatch(self._pick_color)
        color_row = QHBoxLayout()
        color_row.addWidget(self.color_swatch)
        color_row.addStretch(1)
        form.addRow("Font color:", self._wrap(color_row))

        # Background color — click the swatch to open the picker
        self.bg_swatch = ClickableSwatch(self._pick_bg_color)
        bg_row = QHBoxLayout()
        bg_row.addWidget(self.bg_swatch)
        bg_row.addStretch(1)
        form.addRow("Background color:", self._wrap(bg_row))

        # Scale
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.5, 3.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setDecimals(1)
        self.scale_spin.setSuffix(" ×")
        self.scale_spin.valueChanged.connect(self._on_style_changed)
        form.addRow("Scale:", self.scale_spin)

        root.addLayout(form)

        tip = QLabel(
            "Tip: while this window is open the overlay is in resize mode — "
            "drag its edges or corners to resize, or drag the body to move it. "
            "Changes apply live and are saved automatically."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #888;")
        root.addWidget(tip)

        # Buttons
        buttons = QHBoxLayout()
        self.reset_progress_btn = QPushButton("Reset progress (this act)")
        self.reset_progress_btn.clicked.connect(self._reset_progress)
        self.reset_all_btn = QPushButton("Reset all progress")
        self.reset_all_btn.clicked.connect(self._reset_all_progress)
        self.reset_settings_btn = QPushButton("Reset settings")
        self.reset_settings_btn.clicked.connect(self._reset_settings)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        buttons.addWidget(self.reset_progress_btn)
        buttons.addWidget(self.reset_all_btn)
        buttons.addWidget(self.reset_settings_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._load_from_config()

    # ----- helpers -------------------------------------------------------
    def _wrap(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _load_from_config(self):
        self._loading = True
        cfg = self.state.config
        index = self.act_combo.findData(cfg.get("current_act"))
        if index >= 0:
            self.act_combo.setCurrentIndex(index)
        trans_pct = int(round(cfg.get("transparency", 0.85) * 100))
        self.trans_slider.setValue(trans_pct)
        self.trans_spin.setValue(trans_pct)
        self.font_size.setValue(int(cfg.get("font_size", 14)))
        self._select_font(cfg.get("font_family", "Roboto"))
        self.scale_spin.setValue(float(cfg.get("scale", 1.0)))
        self._color = cfg.get("font_color", "#f0e6d2")
        self._bg_color = cfg.get("bg_color", "#121218")
        self._update_swatch()
        self._update_bg_swatch()
        self._loading = False

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
        if ensure_font(family):
            self.font_combo.setFont(QFont(family))

    def sync_from_state(self):
        """Refresh the window after the overlay changed state (e.g. next act)."""
        self._load_from_config()

    def _update_swatch(self):
        self.color_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._color}; "
            f"border: 1px solid #555; border-radius: 4px; }}"
        )

    def _update_bg_swatch(self):
        self.bg_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._bg_color}; "
            f"border: 1px solid #555; border-radius: 4px; }}"
        )

    # ----- handlers ------------------------------------------------------
    def _pick_color(self):
        chosen = QColorDialog.getColor(
            QColor(self._color), self, "Choose font color"
        )
        if chosen.isValid():
            self._color = chosen.name()
            self._update_swatch()
            self._on_style_changed()

    def _pick_bg_color(self):
        chosen = QColorDialog.getColor(
            QColor(self._bg_color), self, "Choose background color"
        )
        if chosen.isValid():
            self._bg_color = chosen.name()
            self._update_bg_swatch()
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

    def _on_act_changed(self, _index):
        if self._loading:
            return
        self.state.config["current_act"] = self.act_combo.currentData()
        self.state.save_config()
        self.overlay.rebuild_items()

    def _on_style_changed(self, *_):
        if self._loading:
            return
        cfg = self.state.config
        cfg["transparency"] = self.trans_slider.value() / 100.0
        cfg["font_size"] = self.font_size.value()
        cfg["font_family"] = self.font_combo.currentText()
        cfg["scale"] = round(self.scale_spin.value(), 2)
        cfg["font_color"] = self._color
        cfg["bg_color"] = self._bg_color
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
