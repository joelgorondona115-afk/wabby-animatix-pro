# core/tools/special/text.py
"""Text tool."""

from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QInputDialog
from PySide6.QtCore import Qt

from core.tools.base import DrawingTool, _push_undo, _draw_on_layer


class TextTool(DrawingTool):
    name = "text"
    cursor = Qt.IBeamCursor

    def __init__(self, color=QColor(0, 0, 0), font_size=24):
        self.color = color
        self.font_size = font_size

    def on_press(self, canvas, pos):
        txt, ok = QInputDialog.getText(canvas, "Texto", "Escribí el texto:")
        if ok and txt:
            _push_undo(canvas)
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(self.color)
                painter.setFont(QFont("Arial", self.font_size))
                painter.drawText(pos, txt)
            _draw_on_layer(canvas, draw)

    def on_move(self, canvas, pos):
        pass

    def on_release(self, canvas, pos):
        pass