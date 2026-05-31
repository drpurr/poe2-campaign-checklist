"""The separate settings window for customizing the overlay."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QSlider,
    QSpinBox, QPushButton, QLabel, QFrame,
    QColorDialog, QMessageBox, QCheckBox,
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
        self._accent_color = state.config.get("accent_color", "#5cb85c")
        self._bg_color = state.config.get("bg_color", "#121218")
        self._border_color = state.config.get("border_color", "#7882a0")

        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        # Transparency: slider + manual numeric entry
        self.trans_slider = QSlider(Qt.Orientation.Horizontal)
        self.trans_slider.setRange(0, 100)
        self.trans_slider.valueChanged.connect(self._on_trans_slider)
        self.trans_spin = QSpinBox()
        self.trans_spin.setRange(0, 100)
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

        # Colors — grouped into one compact row of labelled swatches so they
        # don't each consume a full form row of vertical space.
        self.color_swatch = ClickableSwatch(self._pick_color)
        self.accent_swatch = ClickableSwatch(self._pick_accent_color)
        self.bg_swatch = ClickableSwatch(self._pick_bg_color)
        self.border_swatch = ClickableSwatch(self._pick_border_color)
        colors_row = QHBoxLayout()
        colors_row.setSpacing(14)
        colors_row.addLayout(self._labeled_swatch("Text", self.color_swatch))
        colors_row.addLayout(self._labeled_swatch("Accent", self.accent_swatch))
        colors_row.addLayout(self._labeled_swatch("BG", self.bg_swatch))
        colors_row.addLayout(self._labeled_swatch("Border", self.border_swatch))
        colors_row.addStretch(1)
        form.addRow("Colors:", self._wrap(colors_row))

        # Border toggle
        self.border_checkbox = QCheckBox("Show border")
        self.border_checkbox.toggled.connect(self._on_border_toggled)
        form.addRow("", self.border_checkbox)

        # Control size — sizes the overlay buttons (not the Act dropdown)
        self.control_size = QSpinBox()
        self.control_size.setRange(8, 40)
        self.control_size.setSuffix(" pt")
        self.control_size.valueChanged.connect(self._on_style_changed)
        form.addRow("Control size:", self.control_size)

        # Per-item choices (e.g. Act 3's permanent Servi's Draught). One labelled
        # dropdown per checklist item that defines a ``choices`` list; the pick is
        # substituted into that item's ``$VAR`` in the overlay.
        self.choice_combos = []
        self._build_choice_rows(form)

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

    def _labeled_swatch(self, text, swatch):
        """Return a small vertical column: a caption above its color swatch."""
        column = QVBoxLayout()
        column.setSpacing(3)
        caption = QLabel(text)
        caption.setStyleSheet("color: #888;")
        caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(caption, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(swatch, 0, Qt.AlignmentFlag.AlignHCenter)
        return column

    def _build_choice_rows(self, form):
        """Add a dropdown for every checklist item that defines ``choices``.

        Each combo carries the owning item's id so its selection can be saved
        and substituted into that item's ``$VAR`` placeholder in the overlay.
        """
        for act in self.state.acts:
            for item in act.get("items", []):
                choices = item.get("choices")
                if not choices:
                    continue
                combo = QComboBox()
                combo.addItems(choices)
                combo.setProperty("item_id", item["id"])
                combo.currentIndexChanged.connect(self._on_choice_changed)
                self.choice_combos.append(combo)
                label = item.get("choice_label") or f'{act.get("name", "Act")} choice'
                form.addRow(f"{label}:", combo)

    def _load_from_config(self):
        self._loading = True
        cfg = self.state.config
        trans_pct = int(round(cfg.get("transparency", 0.85) * 100))
        self.trans_slider.setValue(trans_pct)
        self.trans_spin.setValue(trans_pct)
        self.font_size.setValue(int(cfg.get("font_size", 14)))
        self._select_font(cfg.get("font_family", "Roboto"))
        self.control_size.setValue(int(cfg.get("control_size", 20)))
        self._color = cfg.get("font_color", "#f0e6d2")
        self._accent_color = cfg.get("accent_color", "#5cb85c")
        self._bg_color = cfg.get("bg_color", "#121218")
        self._border_color = cfg.get("border_color", "#7882a0")
        self.border_checkbox.setChecked(bool(cfg.get("border_enabled", True)))
        self._update_swatch()
        self._update_accent_swatch()
        self._update_bg_swatch()
        self._update_border_swatch()
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

    def _update_swatch(self):
        self.color_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._color}; "
            f"border: 1px solid #555; border-radius: 4px; }}"
        )

    def _update_accent_swatch(self):
        self.accent_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._accent_color}; "
            f"border: 1px solid #555; border-radius: 4px; }}"
        )

    def _update_bg_swatch(self):
        self.bg_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._bg_color}; "
            f"border: 1px solid #555; border-radius: 4px; }}"
        )

    def _update_border_swatch(self):
        self.border_swatch.setStyleSheet(
            f"#Swatch {{ background: {self._border_color}; "
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

    def _pick_accent_color(self):
        chosen = QColorDialog.getColor(
            QColor(self._accent_color), self, "Choose (accent) color"
        )
        if chosen.isValid():
            self._accent_color = chosen.name()
            self._update_accent_swatch()
            self._on_style_changed()

    def _pick_bg_color(self):
        chosen = QColorDialog.getColor(
            QColor(self._bg_color), self, "Choose background color"
        )
        if chosen.isValid():
            self._bg_color = chosen.name()
            self._update_bg_swatch()
            self._on_style_changed()

    def _pick_border_color(self):
        chosen = QColorDialog.getColor(
            QColor(self._border_color), self, "Choose border color"
        )
        if chosen.isValid():
            self._border_color = chosen.name()
            self._update_border_swatch()
            self._on_style_changed()

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
        cfg["font_color"] = self._color
        cfg["accent_color"] = self._accent_color
        cfg["bg_color"] = self._bg_color
        cfg["border_color"] = self._border_color
        cfg["border_enabled"] = self.border_checkbox.isChecked()
        self.state.save_config()
        self.overlay.apply_style()

    def _reset_progress(self):
        act = self.state.current_act
        if not act:
            return
        answer = QMessageBox.question(
            self, "Clear current act",
            f'Clear all checkmarks for "{act["name"]}"?',
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.state.reset_act_progress(act["id"])
            self.overlay.rebuild_items()

    def _reset_all_progress(self):
        answer = QMessageBox.question(
            self, "Clear all acts",
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
