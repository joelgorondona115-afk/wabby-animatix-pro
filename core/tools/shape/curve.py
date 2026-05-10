# core/tools/shape/curve.py
"""Curve tool - Bezier curve."""

from PySide6.QtGui import QPainter, QPen, QPainterPath, QColor
from PySide6.QtCore import Qt, QPoint, QPointF

from core.tools.base import DrawingTool, _draw_on_layer


class CurveTool(DrawingTool):
    """Bezier curve tool with 2-click logic."""
    name = "curve"

    def __init__(self, color=None, width=3, opacity=255):
        if color is None:
            from PySide6.QtGui import QColor
            color = QColor(0, 0, 0)
        self.color = color
        self.width = width
        self.opacity = opacity
        self.state = 0
        self.p1 = QPointF()
        self.p2 = QPointF()
        self.cp1 = QPointF()
        self.cp2 = QPointF()

    def on_press(self, canvas, pos):
        if self.state == 0:
            from core.tools.base import _push_undo
            _push_undo(canvas)
            self.p1 = self.p2 = QPointF(pos)
            self.state = 1
            canvas.overlay_image.fill(Qt.transparent)
        elif self.state == 1:
            self.cp1 = self.cp2 = QPointF(pos)
            self.state = 2

    def on_move(self, canvas, pos):
        p = QPointF(pos)
        
        if self.state == 1:
            self.p2 = p
        elif self.state == 2:
            self.cp1 = self.cp2 = p
        
        self._preview(canvas)

    def on_release(self, canvas, pos):
        if self.state == 1:
            mid_x = (self.p1.x() + self.p2.x()) / 2
            mid_y = (self.p1.y() + self.p2.y()) / 2
            self.cp1 = self.cp2 = QPointF(mid_x, mid_y)
            self.state = 2
        elif self.state == 2:
            self._final_draw(canvas)
            self.state = 0
        
        canvas.overlay_image.fill(Qt.transparent)

    def _preview(self, canvas):
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.color)
        color.setAlpha(self.opacity)
        p.setPen(QPen(color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        path = QPainterPath()
        path.moveTo(self.p1)
        
        if self.state == 1:
            path.lineTo(self.p2)
        else:
            path.cubicTo(self.cp1, self.cp2, self.p2)
        
        p.drawPath(path)
        p.end()
        canvas.update()

    def _final_draw(self, canvas):
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            color = QColor(self.color)
            color.setAlpha(self.opacity)
            painter.setPen(QPen(color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath()
            path.moveTo(self.p1)
            path.cubicTo(self.cp1, self.cp2, self.p2)
            painter.drawPath(path)
        
        _draw_on_layer(canvas, draw)