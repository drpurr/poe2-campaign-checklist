"""Runtime-generated emblem icons for the Act reward choices.

Each icon is a small medallion drawn with QPainter, so there are no binary asset
files to ship or resolve at runtime (important for the PyInstaller build). The
medallion is a dark Catppuccin base disc; each emblem is stroked/filled in its
own Catppuccin Mocha accent colour so the list reads as a colourful set rather
than one flat tone. ``make_act_icon(name)`` returns a ``QPixmap``; unknown names
fall back to a neutral gem in mauve.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QPolygonF

# Catppuccin Mocha tones for the medallion body (kept in sync with
# settings_window.CAT; duplicated here so this module stays import-light).
_DISC = QColor("#181825")        # mantle — medallion fill
_CUTOUT = QColor("#11111b")      # crust — cut-outs (eye sockets etc.)

# Per-emblem accent colour (Catppuccin Mocha).
_ACCENTS = {
    "skull": "#f38ba8",      # red
    "axes": "#fab387",       # peach
    "lightning": "#f9e2af",  # yellow
    "gate": "#89b4fa",       # blue
    "map": "#a6e3a1",        # green
    "gem": "#cba6f7",        # mauve (fallback)
}


def _medallion(painter, s, accent):
    """Draw the dark base disc with a ring in the emblem's accent colour."""
    painter.setBrush(QBrush(_DISC))
    painter.setPen(QPen(accent, max(1.5, s * 0.06)))
    inset = s * 0.08
    painter.drawEllipse(QRectF(inset, inset, s - 2 * inset, s - 2 * inset))


def _pen(accent, s, width=0.09):
    pen = QPen(accent, max(1.5, s * width))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _skull(p, s, accent):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(accent))
    # Cranium + jaw as one rounded blob.
    p.drawEllipse(QRectF(s * 0.28, s * 0.24, s * 0.44, s * 0.40))
    p.drawRoundedRect(QRectF(s * 0.36, s * 0.52, s * 0.28, s * 0.20),
                      s * 0.06, s * 0.06)
    # Eye sockets + nose.
    p.setBrush(QBrush(_CUTOUT))
    p.drawEllipse(QRectF(s * 0.34, s * 0.36, s * 0.12, s * 0.12))
    p.drawEllipse(QRectF(s * 0.54, s * 0.36, s * 0.12, s * 0.12))
    p.drawEllipse(QRectF(s * 0.46, s * 0.50, s * 0.08, s * 0.08))


def _axes(p, s, accent):
    """Two crossed axes."""
    for sign in (-1, 1):
        p.save()
        p.translate(s * 0.5, s * 0.5)
        p.rotate(sign * 32)
        # Handle.
        p.setPen(_pen(accent, s, 0.07))
        p.drawLine(QPointF(0, s * 0.30), QPointF(0, -s * 0.26))
        # Axe head (a crescent-ish blade) at the top of the handle.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(accent))
        blade = QPolygonF([
            QPointF(0, -s * 0.30), QPointF(s * 0.20, -s * 0.20),
            QPointF(s * 0.14, -s * 0.06), QPointF(0, -s * 0.14),
        ])
        p.drawPolygon(blade)
        p.restore()


def _lightning(p, s, accent):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(accent))
    bolt = QPolygonF([
        QPointF(s * 0.56, s * 0.20), QPointF(s * 0.34, s * 0.54),
        QPointF(s * 0.48, s * 0.54), QPointF(s * 0.42, s * 0.80),
        QPointF(s * 0.66, s * 0.44), QPointF(s * 0.52, s * 0.44),
    ])
    p.drawPolygon(bolt)


def _gate(p, s, accent):
    """A portcullis: arched frame with vertical + horizontal bars."""
    p.setPen(_pen(accent, s, 0.06))
    p.setBrush(Qt.BrushStyle.NoBrush)
    left, right, top, bot = s * 0.32, s * 0.68, s * 0.30, s * 0.70
    # Arched top.
    p.drawArc(QRectF(left, top - (right - left) / 2, right - left, right - left),
              0, 180 * 16)
    # Vertical bars.
    for frac in (0.0, 0.5, 1.0):
        x = left + (right - left) * frac
        p.drawLine(QPointF(x, top), QPointF(x, bot))
    # Horizontal bars.
    for y in (top + (bot - top) * 0.45, bot):
        p.drawLine(QPointF(left, y), QPointF(right, y))


def _map(p, s, accent):
    """An island blob with an X marking the spot."""
    p.setPen(_pen(accent, s, 0.055))
    p.setBrush(Qt.BrushStyle.NoBrush)
    island = QPolygonF([
        QPointF(s * 0.32, s * 0.52), QPointF(s * 0.40, s * 0.36),
        QPointF(s * 0.56, s * 0.34), QPointF(s * 0.68, s * 0.46),
        QPointF(s * 0.62, s * 0.62), QPointF(s * 0.44, s * 0.68),
    ])
    p.drawPolygon(island)
    # X marks the spot.
    p.setPen(_pen(accent, s, 0.06))
    cx, cy, r = s * 0.54, s * 0.50, s * 0.05
    p.drawLine(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
    p.drawLine(QPointF(cx - r, cy + r), QPointF(cx + r, cy - r))


def _gem(p, s, accent):
    """Neutral fallback emblem: a faceted gem."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(accent))
    gem = QPolygonF([
        QPointF(s * 0.5, s * 0.28), QPointF(s * 0.70, s * 0.46),
        QPointF(s * 0.5, s * 0.72), QPointF(s * 0.30, s * 0.46),
    ])
    p.drawPolygon(gem)
    p.setPen(_pen(_CUTOUT, s, 0.04))
    p.drawLine(QPointF(s * 0.30, s * 0.46), QPointF(s * 0.70, s * 0.46))


_EMBLEMS = {
    "skull": _skull,
    "axes": _axes,
    "lightning": _lightning,
    "gate": _gate,
    "map": _map,
    "gem": _gem,
}


def make_act_icon(name, size=30):
    """Return a ``QPixmap`` medallion for ``name`` (falls back to a mauve gem)."""
    accent = QColor(_ACCENTS.get(name, _ACCENTS["gem"]))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _medallion(painter, size, accent)
    _EMBLEMS.get(name, _gem)(painter, size, accent)
    painter.end()
    return pixmap
