# core/tools/shape/rectangle.py
"""Rectangle tool."""

from PySide6.QtCore import QRect

from .base import ShapeBase


class RectangleTool(ShapeBase):
    name = "rect"

    def on_press(self, canvas, pos):
        self._start = pos

    def on_move(self, canvas, pos):
        if self._start:
            rect = QRect(self._start, pos)
            self._draw_preview(canvas, lambda p: p.drawRect(rect))

    def on_release(self, canvas, pos):
        if self._start:
            rect = QRect(self._start, pos)
            self._draw_final(canvas, lambda p: p.drawRect(rect))
        self._start = None