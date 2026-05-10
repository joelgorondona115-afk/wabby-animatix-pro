# core/tools/lasso/fill/lasso_fill_rect.py
"""Lasso fill rectangle tool."""

from PySide6.QtGui import QPainter

from core.tools.base import _push_undo, _draw_on_layer
from ..base import LassoBase


class LassoFillRectTool(LassoBase):
    """Rectangle lasso that fills the enclosed area."""
    name = "lasso_fill_rect"

    def on_press(self, canvas, pos):
        if self._is_drawing:
            self._cancel(canvas)
            return
        _push_undo(canvas)
        self._start = pos
        self._start_animation(canvas)

    def on_move(self, canvas, pos):
        if not self._is_drawing or not self._start:
            return
        self._draw_marching_ants(
            canvas,
            lambda p: p.drawRect(
                self._start.x(), self._start.y(),
                pos.x() - self._start.x(), pos.y() - self._start.y()
            )
        )

    def on_release(self, canvas, pos):
        if not self._is_drawing or not self._start:
            return
        x1, y1 = self._start.x(), self._start.y()
        x2, y2 = pos.x(), pos.y()
        
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        
        def fill(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(x1, y1, x2 - x1, y2 - y1, self.color)
        
        _draw_on_layer(canvas, fill)
        
        # Save selection for persistent display
        from PySide6.QtCore import QRect
        canvas.selection_rect = QRect(x1, y1, x2 - x1, y2 - y1)
        canvas.selection_active = True
        
        self._clear_overlay(canvas)
        self._start = None

    def on_right_press(self, canvas, pos):
        """Right click to cancel."""
        self._cancel(canvas)