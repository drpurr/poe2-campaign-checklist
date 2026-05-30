"""The always-on-top checklist overlay window."""

from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QCheckBox, QVBoxLayout, QHBoxLayout,
    QScrollArea, QToolButton, QSizePolicy, QApplication,
)

from google_fonts import ensure_font


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

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.on_open_settings = None  # set by main.py
        self.on_act_changed = None  # set by main.py to sync the settings window

        self.resize_enabled = False
        self._drag_pos = None
        self._resizing = False
        self._resize_edges = (False, False, False, False)
        self._start_geom = None
        self._start_mouse = None
        self.item_widgets = []
        self.category_labels = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        # Allow the overlay to be dragged down to a small size regardless of
        # how large the (scaled) content's natural size hint is.
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

        # Header: title + progress + next act + close + settings gear
        header = QHBoxLayout()
        self.title_label = QLabel("PoE2 Overlay")
        self.title_label.setObjectName("Title")
        # Wrap + zero min width so a long act name never forces the window wide.
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(0)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("Progress")
        self.next_btn = QToolButton()
        self.next_btn.setObjectName("NextBtn")
        self.next_btn.setText("⏭")  # next act
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setToolTip("Go to next act")
        self.next_btn.clicked.connect(self._next_act)
        self.gear_btn = QToolButton()
        self.gear_btn.setObjectName("GearBtn")
        self.gear_btn.setText("⚙")  # gear
        self.gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear_btn.setToolTip("Open settings")
        self.gear_btn.clicked.connect(self._open_settings)
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setText("✕")  # close
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Hide overlay")
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.title_label, 1)
        header.addStretch(0)
        header.addWidget(self.progress_label)
        header.addWidget(self.next_btn)
        header.addWidget(self.gear_btn)
        header.addWidget(self.close_btn)
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
            self.title_label.setText("No acts found")
            self.progress_label.setText("")
            return

        self.title_label.setText(act.get("name", "Act"))
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
                item["text"], self.state.is_done(act["id"], item["id"])
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

    def _update_progress_label(self):
        act = self.state.current_act
        if not act:
            self.progress_label.setText("")
            return
        done, total = self.state.act_completion(act["id"])
        self.progress_label.setText(f"{done}/{total}")

    def _update_nav(self):
        """Disable the 'next act' button when already on the last act."""
        acts = self.state.acts
        current = self.state.config.get("current_act")
        ids = [a["id"] for a in acts]
        has_next = bool(acts) and current in ids and ids.index(current) + 1 < len(ids)
        self.next_btn.setEnabled(has_next)

    # ----- styling -------------------------------------------------------
    def apply_style(self):
        cfg = self.state.config
        scale = float(cfg.get("scale", 1.0))
        font_size = max(6, int(round(cfg.get("font_size", 14) * scale)))
        family = cfg.get("font_family", "Roboto")
        ensure_font(family)
        color = cfg.get("font_color", "#f0e6d2")
        alpha = float(cfg.get("transparency", 0.85))
        bg_color = cfg.get("bg_color", "#121218")

        r, g, b = _hex_to_rgb(bg_color)
        bg = f"rgba({r}, {g}, {b}, {alpha:.3f})"
        accent = "#5cb85c"
        indicator = max(12, int(round(16 * scale)))
        radius = max(2, int(round(3 * scale)))
        if self.resize_enabled:
            border = "2px dashed #6ca0ff"
        else:
            border = f"1px solid rgba(120, 130, 160, {min(1.0, alpha + 0.15):.3f})"

        self.card.setStyleSheet(f"""
            #Card {{
                background-color: {bg};
                border: {border};
                border-radius: 10px;
            }}
            QLabel {{ color: {color}; background: transparent; }}
            #Title {{ color: {color}; font-weight: 700; }}
            #Progress {{ color: rgba(255,255,255,0.65); }}
            #Category {{ color: {accent}; font-weight: 700; }}
            #Hint {{ color: #6ca0ff; }}
            QToolButton#GearBtn {{
                color: {color}; background: transparent; border: none;
                font-size: {font_size + 4}px; padding: 0 2px;
            }}
            QToolButton#GearBtn:hover {{ color: #ffffff; }}
            QToolButton#NextBtn, QToolButton#CloseBtn {{
                color: {color}; background: transparent; border: none;
                font-size: {font_size + 4}px; padding: 0 2px;
            }}
            QToolButton#NextBtn:hover, QToolButton#CloseBtn:hover {{
                color: #ffffff;
            }}
            QToolButton#NextBtn:disabled {{ color: rgba(255,255,255,0.25); }}
            QCheckBox {{ background: transparent; }}
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
                background: rgba(255,255,255,0.25);
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
        title_font = QFont(family, font_size + 3)
        title_font.setBold(True)
        small_font = QFont(family, max(6, font_size - 2))

        self.title_label.setFont(title_font)
        self.progress_label.setFont(small_font)
        self.hint_label.setFont(small_font)
        for label in self.category_labels:
            cat_font = QFont(family, font_size)
            cat_font.setBold(True)
            label.setFont(cat_font)
        for row in self.item_widgets:
            row.set_base_font(base_font)

        self.hint_label.setVisible(self.resize_enabled)

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

    def _next_act(self):
        """Advance to the next act and refresh the overlay."""
        if self.state.go_to_next_act():
            self.rebuild_items()
            if self.on_act_changed:
                self.on_act_changed()
