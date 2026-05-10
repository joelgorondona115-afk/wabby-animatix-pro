# core/tools/lasso/fill/eraser/lasso_eraser.py
"""Lasso eraser tool - erases inside the drawn area."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPainterPath

from core.tools.base import _push_undo, _active_layer, _draw_on_layer
from ...base import LassoBase


class LassoEraserTool(LassoBase):
    """Lasso that erases inside the drawn area."""
    name = "lasso_eraser"

    def __init__(self):
        super().__init__(Qt.red)
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
        if len(self.points) > 2:
            self._path.closeSubpath()
            layer = _active_layer(canvas)
            if layer:
                def cut(painter):
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.fillPath(self._path, Qt.transparent)
                _draw_on_layer(canvas, cut)
        self._clear_overlay(canvas)
        self._path = QPainterPath()
        self.points = []

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)