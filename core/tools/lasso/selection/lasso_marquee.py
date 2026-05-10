# core/tools/lasso/selection/lasso_marquee.py
"""Lasso marquee selection tool."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainterPath

from ..base import LassoBase


class LassoMarqueeTool(LassoBase):
    """Lasso marquee selection - closes automatically."""
    name = "lasso_marquee"

    def __init__(self):
        super().__init__(Qt.blue)
        self.points = []

    def on_press(self, canvas, pos):
        if self._is_drawing:
            self._cancel(canvas)
            return
        self.points = [QPointF(pos)]
        self._path = QPainterPath()
        self._path.moveTo(QPointF(pos))
        self._start_animation(canvas)

    def on_move(self, canvas, pos):
        if not self._is_drawing:
            return
        self.points.append(QPointF(pos))
        self._path.lineTo(QPointF(pos))
        self._draw_marching_ants(canvas, lambda p: p.drawPath(self._path))

    def on_release(self, canvas, pos):
        if not self._is_drawing:
            return
        if len(self.points) > 2:
            self._path.closeSubpath()
            canvas.selection_path = self._path
            canvas.selection_active = True
        self._clear_overlay(canvas)
        self.points = []
        self._path = QPainterPath()

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)