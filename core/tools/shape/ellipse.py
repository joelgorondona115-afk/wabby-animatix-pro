# core/tools/shape/ellipse.py
"""Ellipse tool."""

from PySide6.QtCore import QRect

from .base import ShapeBase


class EllipseTool(ShapeBase):
    name = "ellipse"

    def on_press(self, canvas, pos):
        self._start = pos

    def on_move(self, canvas, pos):
        if self._start:
            rect = QRect(self._start, pos)
            self._draw_preview(canvas, lambda p: p.drawEllipse(rect))

    def on_release(self, canvas, pos):
        if self._start:
            rect = QRect(self._start, pos)
            self._draw_final(canvas, lambda p: p.drawEllipse(rect))
        self._start = None