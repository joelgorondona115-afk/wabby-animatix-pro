# core/tools/drawing/base.py
"""Drawing tool base class."""

from PySide6.QtGui import QColor
from PySide6.QtCore import QPoint
from typing import Optional

from core.tools.base import DrawingTool
from core.tools.stroke import StrokeHandler, PencilStroke, BrushStroke, EraserStroke


class DrawingToolBase(DrawingTool):
    """Base class for drawing tools using StrokeHandler."""

    def __init__(self, stroke: StrokeHandler):
        self._stroke = stroke
        self._last: Optional[QPoint] = None

    @property
    def color(self) -> QColor:
        return self._stroke.color

    @color.setter
    def color(self, value: QColor) -> None:
        self._stroke.set_color(value)

    @property
    def width(self) -> int:
        return self._stroke.width

    @width.setter
    def width(self, value: int) -> None:
        self._stroke.set_width(value)

    @property
    def opacity(self) -> int:
        return self._stroke.opacity

    @opacity.setter
    def opacity(self, value: int) -> None:
        self._stroke.set_opacity(value)

    @property
    def stability(self) -> int:
        return self._stroke.stability

    @stability.setter
    def stability(self, value: int) -> None:
        self._stroke.stability = value