# core/tools/lasso/selection/rect_select.py
"""Rectangle selection tool."""

from PySide6.QtCore import QRect

from ..base import LassoBase


class RectSelectTool(LassoBase):
    """Rectangle selection tool."""
    name = "select_rect"

    def __init__(self):
        super().__init__()
        self.selection = None

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
            lambda p: p.drawRect(self._start.x(), self._start.y(),
                                pos.x() - self._start.x(), pos.y() - self._start.y())
        )

    def on_release(self, canvas, pos):
        if not self._is_drawing or not self._start:
            return
        canvas.selection_rect = QRect(self._start, pos).normalized()
        self._clear_overlay(canvas)
        self._start = None

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)