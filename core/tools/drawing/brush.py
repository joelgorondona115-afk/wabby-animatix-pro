# core/tools/drawing/brush.py
"""Brush tool."""

from PySide6.QtGui import QColor
from PySide6.QtCore import QPoint

from core.tools.stroke import BrushStroke
from core.tools.drawing.base import DrawingToolBase


class BrushTool(DrawingToolBase):
    """Brush tool using BrushStroke."""
    
    name: str = "brush"
    
    def __init__(
        self,
        color: QColor = QColor(0, 0, 0),
        width: int = 10,
        opacity: int = 180
    ):
        super().__init__(BrushStroke(color, width, opacity))
        self._last = None
    
    def on_press(self, canvas, pos: QPoint) -> None:
        from core.tools.base import _push_undo
        _push_undo(canvas)
        self._stroke.reset()
        self._last = None
    
    def on_move(self, canvas, pos: QPoint) -> None:
        press = getattr(canvas, '_pressure', 1.0)
        smooth = self._stroke.get_smooth_point(pos.x(), pos.y())
        
        if not self._last:
            self._last = smooth
            return

        def draw(p):
            self._stroke.draw_smooth_line(p, self._last, smooth, press)
        
        from core.tools.base import _draw_on_layer
        _draw_on_layer(canvas, draw)
        self._last = smooth
    
    def on_release(self, canvas, pos: QPoint) -> None:
        self._last = None