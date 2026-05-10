# core/tools/drawing/eraser.py
"""Eraser tool."""

from PySide6.QtCore import QPoint, Qt

from core.tools.stroke import EraserStroke
from core.tools.drawing.base import DrawingToolBase


class EraserTool(DrawingToolBase):
    """Eraser tool using EraserStroke."""
    
    name: str = "eraser"
    cursor: int = Qt.CrossCursor
    
    def __init__(self, width: int = 20):
        super().__init__(EraserStroke(width))
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