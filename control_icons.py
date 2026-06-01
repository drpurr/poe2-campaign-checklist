"""Runtime-drawn flat icons for the overlay's header/footer control buttons.

Companion to ``act_icons.py``: simple, flat, pastel glyphs (previous, next,
settings gear, exit, lock, unlock) painted with QPainter so there are no binary
assets to ship. ``make_control_icon(kind, size, color)`` returns a ``QPixmap``
stroked/filled in ``color`` — the overlay regenerates them at the user's "Icon
size" whenever it restyles, and swaps colour for hover/exit states.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QPolygonF


def _pen(color, s, width=0.10):
    pen = QPen(QColor(color), max(1.4, s * width))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _prev(p, s, color):
    """Skip-to-previous: a bar with a left-pointing triangle."""
    p.setPen(_pen(color, s, 0.10))
    p.drawLine(QPointF(s * 0.30, s * 0.30), QPointF(s * 0.30, s * 0.70))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.68, s * 0.30), QPointF(s * 0.68, s * 0.70),
        QPointF(s * 0.38, s * 0.50),
    ]))


def _next(p, s, color):
    """Skip-to-next: a right-pointing triangle with a bar (mirror of prev)."""
    p.setPen(_pen(color, s, 0.10))
    p.drawLine(QPointF(s * 0.70, s * 0.30), QPointF(s * 0.70, s * 0.70))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPolygon(QPolygonF([
        QPointF(s * 0.32, s * 0.30), QPointF(s * 0.32, s * 0.70),
        QPointF(s * 0.62, s * 0.50),
    ]))


def _gear(p, s, color):
    """A settings cog: a hub circle with eight radial teeth (outline style)."""
    import math
    p.setPen(_pen(color, s, 0.085))
    cx, cy = s * 0.5, s * 0.5
    p.drawEllipse(QRectF(cx - s * 0.15, cy - s * 0.15, s * 0.30, s * 0.30))
    for i in range(8):
        ang = math.radians(i * 45)
        dx, dy = math.cos(ang), math.sin(ang)
        p.drawLine(QPointF(cx + dx * s * 0.22, cy + dy * s * 0.22),
                   QPointF(cx + dx * s * 0.36, cy + dy * s * 0.36))


def _exit(p, s, color):
    """A close cross."""
    p.setPen(_pen(color, s, 0.11))
    p.drawLine(QPointF(s * 0.32, s * 0.32), QPointF(s * 0.68, s * 0.68))
    p.drawLine(QPointF(s * 0.68, s * 0.32), QPointF(s * 0.32, s * 0.68))


def _lock_body(p, s, color):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(QRectF(s * 0.30, s * 0.46, s * 0.40, s * 0.30),
                      s * 0.06, s * 0.06)


def _lock(p, s, color):
    """Closed padlock: body + a centred closed shackle."""
    p.setPen(_pen(color, s, 0.09))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Closed shackle: an arch whose legs drop onto the body top.
    p.drawArc(QRectF(s * 0.36, s * 0.26, s * 0.28, s * 0.34), 0, 180 * 16)
    p.drawLine(QPointF(s * 0.36, s * 0.43), QPointF(s * 0.36, s * 0.48))
    p.drawLine(QPointF(s * 0.64, s * 0.43), QPointF(s * 0.64, s * 0.48))
    _lock_body(p, s, color)


def _unlock(p, s, color):
    """Open padlock: body + a shackle lifted and swung open to the left."""
    p.setPen(_pen(color, s, 0.09))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Open shackle: arch shifted up/left; only the right leg returns to the body.
    p.drawArc(QRectF(s * 0.22, s * 0.18, s * 0.28, s * 0.34), 0, 180 * 16)
    p.drawLine(QPointF(s * 0.22, s * 0.35), QPointF(s * 0.22, s * 0.42))
    p.drawLine(QPointF(s * 0.50, s * 0.35), QPointF(s * 0.50, s * 0.46))
    _lock_body(p, s, color)


_GLYPHS = {
    "prev": _prev,
    "next": _next,
    "gear": _gear,
    "exit": _exit,
    "lock": _lock,
    "unlock": _unlock,
}


def make_control_icon(kind, size, color):
    """Return a flat ``QPixmap`` glyph for ``kind`` drawn in ``color``."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _GLYPHS.get(kind, _exit)(painter, size, color)
    painter.end()
    return pixmap
