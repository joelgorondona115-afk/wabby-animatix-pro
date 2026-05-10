# core/tools/lasso/selection/move_selection.py
"""Move selection tool."""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter

from core.tools.base import DrawingTool, _active_layer, _push_undo


class MoveSelectionTool(DrawingTool):
    """Move current selection."""
    name = "move_selection"
    cursor = Qt.OpenHandCursor

    def __init__(self):
        self._start = None
        self._offset = QPoint(0, 0)

    def on_press(self, canvas, pos):
        self._start = pos

    def on_move(self, canvas, pos):
        if self._start and canvas.selection_active:
            dx = pos.x() - self._start.x()
            dy = pos.y() - self._start.y()
            self._offset = QPoint(dx, dy)
            canvas.update()

    def on_release(self, canvas, pos):
        if canvas.selection_active and canvas.selection_path:
            layer = _active_layer(canvas)
            if layer and (self._offset.x() != 0 or self._offset.y() != 0):
                _push_undo(canvas)
                temp = layer.image.copy()
                layer.image.fill(Qt.transparent)
                p = QPainter(layer.image)
                p.drawImage(self._offset, temp)
                p.end()
            canvas.selection_path.translate(self._offset)
            self._start = None
            self._offset = QPoint(0, 0)
            canvas.update()