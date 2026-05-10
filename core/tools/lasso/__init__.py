# core/tools/lasso/__init__.py
"""Lasso tools - selection and fill tools with common ancestor."""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter

from .base import LassoBase
from core.tools.base import DrawingTool, _active_layer, _push_undo

# Fill tools
from .fill.lasso_fill import LassoFillTool
from .fill.lasso_fill_rect import LassoFillRectTool
from .fill.lasso_fill_ellipse import LassoFillEllipseTool
from .fill.eraser.lasso_eraser import LassoEraserTool

# Selection tools
from .selection.rect_select import RectSelectTool
from .selection.lasso_select import LassoSelectTool
from .selection.ellipse_select import EllipseSelectTool
from .selection.lasso_marquee import LassoMarqueeTool
from .selection.move_selection import MoveSelectionTool


class MoveTool(DrawingTool):
    """Move the active layer."""
    name = "move"
    cursor = Qt.OpenHandCursor

    def __init__(self):
        self._start = None
        self._start_pos = None

    def on_press(self, canvas, pos):
        self._start = pos
        layer = _active_layer(canvas)
        if layer:
            self._start_pos = (layer.image.copy(), pos)

    def on_move(self, canvas, pos):
        if self._start_pos:
            canvas.update()

    def on_release(self, canvas, pos):
        layer = _active_layer(canvas)
        if layer and self._start:
            dx = pos.x() - self._start.x()
            dy = pos.y() - self._start.y()
            if dx != 0 or dy != 0:
                _push_undo(canvas)
                temp = layer.image.copy()
                layer.image.fill(0x00000000)
                p = QPainter(layer.image)
                p.drawImage(dx, dy, temp)
                p.end()
        self._start = None
        self._start_pos = None
        canvas.update()


__all__ = [
    'LassoBase',
    # Fill
    'LassoFillTool',
    'LassoFillRectTool',
    'LassoFillEllipseTool',
    'LassoEraserTool',
    # Selection
    'RectSelectTool',
    'LassoSelectTool',
    'EllipseSelectTool',
    'LassoMarqueeTool',
    'MoveSelectionTool',
    # Move
    'MoveTool',
]