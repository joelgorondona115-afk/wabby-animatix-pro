# core/tools/shape/line.py
"""Line tool."""

from PySide6.QtCore import QPoint

from .base import ShapeBase


class LineTool(ShapeBase):
    name = "line"

    def on_press(self, canvas, pos):
        self._start = pos

    def on_move(self, canvas, pos):
        if self._start:
            self._draw_preview(canvas, lambda p: p.drawLine(self._start, pos))

    def on_release(self, canvas, pos):
        if self._start:
            self._draw_final(canvas, lambda p: p.drawLine(self._start, pos))
        self._start = None