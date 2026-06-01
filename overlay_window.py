"""The always-on-top checklist overlay window."""

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QCheckBox, QVBoxLayout, QHBoxLayout,
    QScrollArea, QToolButton, QSizePolicy, QComboBox, QApplication,
)

from google_fonts import ensure_font
from theme import CAT
from control_icons import make_control_icon


def _hex_to_rgb(value):
    """Convert a ``#rrggbb`` color string to an (r, g, b) tuple."""
    color = QColor(value)
    if not color.isValid():
        color = QColor("#121218")
    return color.red(), color.green(), color.blue()


class ChecklistItemWidget(QWidget):
    """A single checklist row: a checkbox plus a word-wrapping label.

    Clicking anywhere on the row toggles the checkbox. Completed items are
    shown with a strike-through and dimmed text.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, text, checked=False, parent=None):
        super().__init__(parent)
        self._base_font = QFont()
        self._done_color = "rgba(255,255,255,0.40)"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.label, 1)

        self.checkbox.toggled.connect(self._on_toggle)
        self._refresh()

    def isChecked(self):
        return self.checkbox.isChecked()

    def mousePressEvent(self, event):
        # Clicking the label / empty part of the row toggles the box.
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_toggle(self, checked):
        self._refresh()
        self.toggled.emit(checked)

    def set_base_font(self, font):
        self._base_font = QFont(font)
        self._refresh()

    def set_done_color(self, color):
        self._done_color = color
        self._refresh()

    def _refresh(self):
        checked = self.checkbox.isChecked()
        font = QFont(self._base_font)
        font.setStrikeOut(checked)
        self.label.setFont(font)
        # Dim completed rows; let the global stylesheet color the rest.
        self.label.setStyleSheet(
            f"color: {self._done_color};" if checked else ""
        )


class OverlayWindow(QWidget):
    """Frameless translucent overlay that lists the current act's checklist."""

    RESIZE_MARGIN = 8
    MIN_W, MIN_H = 220, 160
    # The overlay uses a translucent top-level window, so fully transparent
    # pixels (alpha 0) are click-through on Windows: mouse events pass straight
    # to whatever is behind them. At a transparency setting of 0% the panel
    # background would be completely transparent, making the overlay impossible
    # to drag and its checkboxes nearly impossible to click. Painting the panel
    # with a tiny minimum alpha keeps it hit-testable while staying visually
    # see-through.
    MIN_PANEL_ALPHA = 0.04

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.on_open_settings = None  # set by main.py
        self.on_quit = None  # set by main.py
        self.on_act_changed = None  # set by main.py to sync the settings window

        self.resize_enabled = False
        self._drag_pos = None
        self._resizing = False
        self._resize_edges = (False, False, False, False)
        self._start_geom = None
        self._start_mouse = None
        self.item_widgets = []
        self.category_labels = []
        self._loading_combo = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        # Allow the overlay to be dragged down to a small size regardless of
        # how large the content's natural size hint is.
        self.setMinimumSize(self.MIN_W, self.MIN_H)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            self.RESIZE_MARGIN, self.RESIZE_MARGIN,
            self.RESIZE_MARGIN, self.RESIZE_MARGIN,
        )

        self.card = QFrame()
        self.card.setObjectName("Card")
        self.card.setMouseTracking(True)
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 14)
        card_layout.setSpacing(8)

        # Header: act selector on the left, controls grouped on the right
        header = QHBoxLayout()
        header.setSpacing(0)
        self.act_combo = QComboBox()
        self.act_combo.setObjectName("ActCombo")
        self.act_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.act_combo.setToolTip("Switch act")
        self.act_combo.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.act_combo.setMinimumWidth(0)
        for act in self.state.acts:
            self.act_combo.addItem(act.get("name", "Act"), act["id"])
        self.act_combo.currentIndexChanged.connect(self._on_combo_changed)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("Progress")
        # Header/footer controls use flat drawn icons (see control_icons); their
        # pixmaps are (re)generated in apply_style so they track the user's
        # "Icon size" and the theme colour. ``_icon_kind`` tags each button.
        self.prev_btn = QToolButton()
        self.prev_btn.setObjectName("PrevBtn")
        self.prev_btn._icon_kind = "prev"
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setToolTip("Go to previous act")
        self.prev_btn.clicked.connect(self._prev_act)
        self.next_btn = QToolButton()
        self.next_btn.setObjectName("NextBtn")
        self.next_btn._icon_kind = "next"
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setToolTip("Go to next act")
        self.next_btn.clicked.connect(self._next_act)
        self.gear_btn = QToolButton()
        self.gear_btn.setObjectName("GearBtn")
        self.gear_btn._icon_kind = "gear"
        self.gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear_btn.setToolTip("Open settings")
        self.gear_btn.clicked.connect(self._open_settings)
        self.lock_btn = QToolButton()
        self.lock_btn.setObjectName("LockBtn")
        self.lock_btn._icon_kind = "unlock"
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.clicked.connect(self._toggle_lock)
        self.exit_btn = QToolButton()
        self.exit_btn.setObjectName("ExitBtn")
        self.exit_btn._icon_kind = "exit"
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setToolTip("Exit")
        self.exit_btn.clicked.connect(self._quit)
        header.addWidget(self.act_combo, 0)
        header.addStretch(1)
        header.addWidget(self.progress_label)
        header.addSpacing(8)
        header.addWidget(self.prev_btn)
        header.addWidget(self.next_btn)
        header.addWidget(self.exit_btn)
        card_layout.addLayout(header)

        # Scrollable checklist
        self.scroll = QScrollArea()
        self.scroll.setObjectName("Scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumWidth(0)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.items_container = QWidget()
        self.items_container.setObjectName("Items")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 6, 0)
        self.items_layout.setSpacing(6)
        self.items_layout.addStretch(1)
        self.scroll.setWidget(self.items_container)
        card_layout.addWidget(self.scroll, 1)

        # Hint shown only in resize mode
        self.hint_label = QLabel("Resize mode — drag edges or corners")
        self.hint_label.setObjectName("Hint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.hide()
        card_layout.addWidget(self.hint_label)

        # Footer: lock + settings gear pinned to the bottom-right corner
        footer = QHBoxLayout()
        footer.setSpacing(2)
        footer.addStretch(1)
        footer.addWidget(self.lock_btn)
        footer.addWidget(self.gear_btn)
        card_layout.addLayout(footer)

        self.locked = bool(self.state.config.get("locked", False))
        self._update_lock_button()

        self._restore_geometry()
        self.rebuild_items()

    # ----- content -------------------------------------------------------
    def rebuild_items(self):
        """Rebuild the checklist for the currently selected act."""
        while self.items_layout.count() > 1:  # keep the trailing stretch
            entry = self.items_layout.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.deleteLater()
        self.item_widgets = []
        self.category_labels = []

        act = self.state.current_act
        if not act:
            self._sync_combo_selection()
            self.progress_label.setText("")
            return

        self._sync_combo_selection()
        insert_at = self.items_layout.count() - 1
        last_category = None
        for item in act["items"]:
            category = item.get("category")
            if category and category != last_category:
                header = QLabel(category)
                header.setObjectName("Category")
                header.setWordWrap(True)
                self.items_layout.insertWidget(insert_at, header)
                insert_at += 1
                self.category_labels.append(header)
                last_category = category

            row = ChecklistItemWidget(
                self.state.item_text(item), self.state.is_done(act["id"], item["id"])
            )
            row.toggled.connect(
                lambda checked, iid=item["id"]: self._on_item_toggled(iid, checked)
            )
            self.items_layout.insertWidget(insert_at, row)
            insert_at += 1
            self.item_widgets.append(row)

        self._update_progress_label()
        self._update_nav()
        self.apply_style()

    def _on_item_toggled(self, item_id, checked):
        act = self.state.current_act
        if act:
            self.state.set_done(act["id"], item_id, checked)
            self._update_progress_label()
            # When every item in the act is checked off, automatically
            # advance to the next act.
            if checked:
                done, total = self.state.act_completion(act["id"])
                if total > 0 and done == total:
                    self._next_act()

    def _update_progress_label(self):
        act = self.state.current_act
        if not act:
            self.progress_label.setText("")
            return
        done, total = self.state.act_completion(act["id"])
        self.progress_label.setText(f"{done}/{total}")

    def _sync_combo_selection(self):
        """Select the current act in the combo without re-triggering changes."""
        current = self.state.config.get("current_act")
        index = self.act_combo.findData(current)
        if index < 0 or index == self.act_combo.currentIndex():
            return
        self._loading_combo = True
        self.act_combo.setCurrentIndex(index)
        self._loading_combo = False

    def _on_combo_changed(self, _index):
        """Switch to the act picked from the overlay dropdown."""
        if self._loading_combo:
            return
        act_id = self.act_combo.currentData()
        if self.state.set_current_act(act_id):
            self.rebuild_items()
            if self.on_act_changed:
                self.on_act_changed()

    def _update_nav(self):
        """Disable the prev/next buttons at the ends of the act list."""
        acts = self.state.acts
        current = self.state.config.get("current_act")
        ids = [a["id"] for a in acts]
        idx = ids.index(current) if current in ids else -1
        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(0 <= idx < len(ids) - 1)

    # ----- styling -------------------------------------------------------
    def apply_style(self):
        cfg = self.state.config
        font_size = max(6, int(round(cfg.get("font_size", 14))))
        control_size = max(6, int(round(cfg.get("control_size", 20))))
        family = cfg.get("font_family", "Roboto")
        family = ensure_font(family) or family
        # Colours are fixed by the Catppuccin app theme; only opacity and the
        # border toggle stay user-controllable.
        color = CAT["text"]
        accent = CAT["accent"]
        alpha = float(cfg.get("transparency", 0.85))
        border_enabled = bool(cfg.get("border_enabled", True))

        r, g, b = _hex_to_rgb(CAT["base"])
        # Keep the panel itself slightly opaque even at 0% so it still captures
        # mouse clicks (see MIN_PANEL_ALPHA); a fully transparent panel is
        # click-through and can't be dragged or have its checkboxes clicked.
        panel_alpha = max(alpha, self.MIN_PANEL_ALPHA)
        bg = f"rgba({r}, {g}, {b}, {panel_alpha:.3f})"
        indicator = 16
        radius = 4
        if self.resize_enabled:
            border = f"2px dashed {CAT['blue']}"
        elif border_enabled:
            br, bgc, bb = _hex_to_rgb(CAT["surface2"])
            border = f"1px solid rgba({br}, {bgc}, {bb}, {min(1.0, alpha + 0.15):.3f})"
        else:
            border = "none"

        self.card.setStyleSheet(f"""
            #Card {{
                background-color: {bg};
                border: {border};
                border-radius: 10px;
            }}
            QLabel {{ color: {color}; background: transparent; }}
            #Progress {{ color: {CAT['subtext0']}; }}
            #Category {{ color: {accent}; font-weight: 700; }}
            #Hint {{ color: {CAT['blue']}; }}
            QComboBox#ActCombo {{
                color: {color}; background: transparent;
                border: none; font-weight: 700;
                padding: 0 2px;
            }}
            QComboBox#ActCombo::drop-down {{
                border: none; width: {font_size + 6}px;
            }}
            QComboBox#ActCombo::down-arrow {{
                width: 0; height: 0;
                border-left: {max(3, font_size // 3)}px solid transparent;
                border-right: {max(3, font_size // 3)}px solid transparent;
                border-top: {max(3, font_size // 3)}px solid {color};
                margin-right: 4px;
            }}
            QComboBox#ActCombo QAbstractItemView {{
                background: {CAT['base']}; color: {color};
                selection-background-color: {accent};
                selection-color: {CAT['crust']};
                border: 1px solid {CAT['surface1']};
                outline: none;
            }}
            QToolButton#GearBtn {{
                color: {color}; background: transparent; border: none;
                font-size: {control_size}px; padding: 0;
            }}
            QToolButton#GearBtn:hover {{ color: {accent}; }}
            QToolButton#LockBtn {{
                color: {color}; background: transparent; border: none;
                font-size: {control_size}px; padding: 0 2px;
            }}
            QToolButton#LockBtn:hover {{ color: {accent}; }}
            QToolButton#PrevBtn, QToolButton#NextBtn, QToolButton#ExitBtn {{
                color: {color}; background: transparent; border: none;
                font-size: {control_size}px; padding: 0;
            }}
            QToolButton#PrevBtn:hover, QToolButton#NextBtn:hover {{
                color: {accent};
            }}
            QToolButton#ExitBtn:hover {{ color: {CAT['red']}; }}
            QToolButton#PrevBtn:disabled, QToolButton#NextBtn:disabled {{
                color: {CAT['overlay0']};
            }}
            QCheckBox {{ background: transparent; spacing: 0px; }}
            QCheckBox::indicator {{
                width: {indicator}px; height: {indicator}px;
                border: 2px solid {color};
                border-radius: {radius}px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border: 2px solid {accent};
            }}
            QScrollArea, #Items {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent; width: 8px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {CAT['surface2']};
                border-radius: 4px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        base_font = QFont(family, font_size)
        title_font = QFont(family, font_size)
        title_font.setBold(True)
        small_font = QFont(family, font_size)

        self.act_combo.setFont(title_font)
        self.progress_label.setFont(small_font)
        self.hint_label.setFont(small_font)
        for label in self.category_labels:
            cat_font = QFont(family, font_size)
            cat_font.setBold(True)
            label.setFont(cat_font)
        for row in self.item_widgets:
            row.set_base_font(base_font)

        self._refresh_control_icons(color, control_size)
        self.hint_label.setVisible(self.resize_enabled)

    def _refresh_control_icons(self, color, control_size):
        """(Re)draw the flat header/footer icons at the current size + colour.

        Scaled up a touch from the old glyph font size so the drawn shapes read
        clearly; QToolButton centres the pixmap with no text.
        """
        px = max(14, int(round(control_size * 1.1)))
        # The lock button shows its current state; everything else is fixed.
        self.lock_btn._icon_kind = "lock" if self.locked else "unlock"
        for btn in (self.prev_btn, self.next_btn, self.gear_btn,
                    self.lock_btn, self.exit_btn):
            btn.setIcon(QIcon(make_control_icon(btn._icon_kind, px, color)))
            btn.setIconSize(QSize(px, px))

    def set_resize_enabled(self, enabled):
        self.resize_enabled = enabled
        if not enabled:
            self.unsetCursor()
        self.apply_style()

    # ----- geometry ------------------------------------------------------
    def _restore_geometry(self):
        geom = self.state.config.get("overlay_geometry")
        if geom and len(geom) == 4:
            rect = QRect(int(geom[0]), int(geom[1]), int(geom[2]), int(geom[3]))
            if self._on_screen(rect):
                self.setGeometry(rect)
                return
        self.resize(320, 460)
        self._move_default()

    def _on_screen(self, rect):
        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(rect):
                return True
        return False

    def _move_default(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 30, area.top() + 60)

    def reset_position(self):
        self.resize(320, 460)
        self._move_default()
        self.show()
        self.raise_()
        self._save_geometry()

    def _save_geometry(self):
        g = self.geometry()
        self.state.config["overlay_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.state.save_config()

    # ----- move / resize -------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.resize_enabled:
            edges = self._edges_at(event.position().toPoint())
            if any(edges):
                self._resizing = True
                self._resize_edges = edges
                self._start_geom = QRect(self.geometry())
                self._start_mouse = event.globalPosition().toPoint()
                return
        if self.locked:
            return
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._do_resize(event.globalPosition().toPoint())
            return
        if self._drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return
        if self.resize_enabled:
            self._update_cursor(self._edges_at(event.position().toPoint()))

    def mouseReleaseEvent(self, event):
        if self._resizing or self._drag_pos is not None:
            self._save_geometry()
        self._resizing = False
        self._drag_pos = None
        self._resize_edges = (False, False, False, False)
        if not self.resize_enabled:
            self.unsetCursor()

    def _edges_at(self, pos):
        margin = self.RESIZE_MARGIN + 4
        rect = self.rect()
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin
        return (left, top, right, bottom)

    def _update_cursor(self, edges):
        left, top, right, bottom = edges
        if (left and top) or (right and bottom):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (right and top) or (left and bottom):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif top or bottom:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def _do_resize(self, global_pos):
        left, top, right, bottom = self._resize_edges
        delta = global_pos - self._start_mouse
        g = self._start_geom
        x, y, w, h = g.x(), g.y(), g.width(), g.height()

        if left:
            new_w = w - delta.x()
            if new_w < self.MIN_W:
                x = x + (w - self.MIN_W)
                new_w = self.MIN_W
            else:
                x = x + delta.x()
            w = new_w
        if right:
            w = max(self.MIN_W, w + delta.x())
        if top:
            new_h = h - delta.y()
            if new_h < self.MIN_H:
                y = y + (h - self.MIN_H)
                new_h = self.MIN_H
            else:
                y = y + delta.y()
            h = new_h
        if bottom:
            h = max(self.MIN_H, h + delta.y())

        self.setGeometry(x, y, w, h)

    # ----- misc ----------------------------------------------------------
    def _open_settings(self):
        if self.on_open_settings:
            self.on_open_settings()

    def _toggle_lock(self):
        """Toggle whether the overlay position is locked."""
        self.locked = not self.locked
        self.state.config["locked"] = self.locked
        self.state.save_config()
        self._update_lock_button()

    def _update_lock_button(self):
        """Refresh the lock button's icon and tooltip to match state."""
        self.lock_btn.setToolTip(
            "Unlock overlay position" if self.locked else "Lock overlay position"
        )
        # Redraw the closed/open padlock at the current size + theme colour.
        control_size = max(6, int(round(self.state.config.get("control_size", 20))))
        px = max(14, int(round(control_size * 1.1)))
        self.lock_btn._icon_kind = "lock" if self.locked else "unlock"
        self.lock_btn.setIcon(QIcon(make_control_icon(
            self.lock_btn._icon_kind, px, CAT["text"])))
        self.lock_btn.setIconSize(QSize(px, px))

    def sync_lock_from_config(self):
        """Re-read the locked state from config and refresh the button."""
        self.locked = bool(self.state.config.get("locked", False))
        self._update_lock_button()

    def _quit(self):
        if self.on_quit:
            self.on_quit()
        else:
            self.close()

    def _next_act(self):
        """Advance to the next act and refresh the overlay."""
        if self.state.go_to_next_act():
            self.rebuild_items()
            if self.on_act_changed:
                self.on_act_changed()

    def _prev_act(self):
        """Step back to the previous act and refresh the overlay."""
        if self.state.go_to_prev_act():
            self.rebuild_items()
            if self.on_act_changed:
                self.on_act_changed()
