# core/tools/lasso/selection/ellipse_select.py
"""Ellipse selection tool."""

from PySide6.QtGui import QPainterPath

from ..base import LassoBase


class EllipseSelectTool(LassoBase):
    """Ellipse selection tool."""
    name = "select_ellipse"

    def on_press(self, canvas, pos):
        if self._is_drawing:
            self._cancel(canvas)
            return
        self._start = pos
        self._start_animation(canvas)

    def on_move(self, canvas, pos):
        if not self._is_drawing or not self._start:
            return
        self._draw_marching_ants(
            canvas,
            lambda p: p.drawEllipse(self._start.x(), self._start.y(),
                                   pos.x() - self._start.x(), pos.y() - self._start.y())
        )

    def on_release(self, canvas, pos):
        if not self._is_drawing or not self._start:
            return
        x1, y1 = self._start.x(), self._start.y()
        x2, y2 = pos.x(), pos.y()
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        path = QPainterPath()
        path.addEllipse(x1, y1, x2 - x1, y2 - y1)
        canvas.selection_path = path
        canvas.selection_active = True
        self._clear_overlay(canvas)
        self._start = None

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)