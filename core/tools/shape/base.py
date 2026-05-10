# core/tools/shape/base.py
"""Shape tool base class."""

from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtCore import Qt, QPoint, QRect

from core.tools.base import DrawingTool


class ShapeBase(DrawingTool):
    """Base class for shape tools."""

    def __init__(self, color: QColor = None, width: int = 3, opacity: int = 255):
        if color is None:
            color = QColor(0, 0, 0)
        self.color = color
        self.width = width
        self.opacity = opacity  # Add opacity
        self._start = None

    def _draw_preview(self, canvas, draw_fn):
        """Draw preview on overlay."""
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.color)
        color.setAlpha(self.opacity)
        p.setPen(QPen(color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        draw_fn(p)
        p.end()
        canvas.update()

    def _clear_overlay(self, canvas):
        """Clear the overlay."""
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()

    def _draw_final(self, canvas, draw_fn):
        """Draw final shape on layer."""
        from core.tools.base import _draw_on_layer, _push_undo
        _push_undo(canvas)
        
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            # Apply opacity to color
            color = QColor(self.color)
            color.setAlpha(self.opacity)
            painter.setPen(QPen(color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            draw_fn(painter)
        
        _draw_on_layer(canvas, draw)
        self._clear_overlay(canvas)