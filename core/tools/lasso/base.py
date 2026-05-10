# core/tools/lasso/base.py
"""Lasso base class - ancestor for all lasso tools."""

from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, QPoint, QTimer

from core.tools.base import DrawingTool


class LassoBase(DrawingTool):
    """Base class for all lasso tools with marching ants preview."""

    name = "lasso_base"
    cursor = Qt.CrossCursor

    def __init__(self, color: QColor = None, stroke_width: int = 2):
        if color is None:
            color = Qt.magenta
        self.color = color
        self.stroke_width = stroke_width
        self._start: QPoint = None
        self._path = QPainterPath()
        self._dash_offset = 0
        self._is_drawing = False
        self._current_shape_fn = None
        self._animation_timer = QTimer()

    def _start_animation(self, canvas):
        """Start marching ants animation."""
        self._is_drawing = True
        self._animation_timer.timeout.connect(lambda: self._on_animation_tick(canvas))
        self._animation_timer.start(50)

    def _stop_animation(self):
        """Stop marching ants animation."""
        self._is_drawing = False
        self._animation_timer.stop()
        self._current_shape_fn = None

    def _on_animation_tick(self, canvas):
        """Animation tick - update and redraw."""
        self._dash_offset -= 2
        if self._dash_offset < -20:
            self._dash_offset = 0
        if self._current_shape_fn:
            self._draw_marching_ants(canvas, self._current_shape_fn)

    def _draw_marching_ants(self, canvas, shape_fn):
        """Draw preview line with marching ants effect."""
        self._current_shape_fn = shape_fn
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(self.color, self.stroke_width)
        pen.setStyle(Qt.DashLine)
        pen.setDashOffset(self._dash_offset)
        p.setPen(pen)
        
        shape_fn(p)
        p.end()
        canvas.update()

    def _clear_overlay(self, canvas):
        """Clear the overlay."""
        self._stop_animation()
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()

    def _cancel(self, canvas):
        """Cancel current drawing."""
        self._clear_overlay(canvas)
        self._path = QPainterPath()
        self._start = None