# core/tools/lasso/fill/lasso_fill.py
"""Lasso fill free-form tool."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPainterPath

from core.tools.base import _push_undo, _draw_on_layer
from ..base import LassoBase


class LassoFillTool(LassoBase):
    """Free-form lasso that fills the enclosed area."""
    name = "lasso_fill"

    def __init__(self, color=None):
        super().__init__(color)
        self.points = []

    def on_press(self, canvas, pos):
        if self._is_drawing:
            self._cancel(canvas)
            return
        _push_undo(canvas)
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
        if len(self.points) < 3:
            self._cancel(canvas)
            return

        self._path.closeSubpath()

        def fill(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillPath(self._path, self.color)

        _draw_on_layer(canvas, fill)

        self._clear_overlay(canvas)
        self._path = QPainterPath()
        self.points = []

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)