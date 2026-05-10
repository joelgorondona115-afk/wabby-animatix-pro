# core/tools/special/custom_brush.py
"""Custom brush tool with imported tip using QBrush texture."""

import math
from PySide6.QtGui import (QPainter, QPen, QColor, QImage, QPixmap, 
                              QBrush, QPainterPath)
from PySide6.QtCore import Qt, QPoint

from core.tools.base import DrawingTool, _push_undo, _draw_on_layer


class CustomBrushTool(DrawingTool):
    """Brush with imported bitmap tip using QBrush texture."""
    name = "custom_brush"
    cursor = Qt.CrossCursor

    def __init__(self, tip: QImage, display_name: str = "Pincel",
                 color=QColor(0, 0, 0), size: int = 40,
                 opacity: int = 180, spacing: float = 0.25):
        self.tip = tip
        self.display_name = display_name
        self.color = color
        self.size = size
        self.opacity = opacity
        self.spacing = spacing
        self._last_pos = None
        self._path = QPainterPath()

    def _create_brush(self, size: int, opacity: int) -> QBrush:
        """Create a QBrush with the PNG texture for solid painting."""
        # Scale the tip to current size
        scaled = self.tip.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Create pixmap from scaled image
        pixmap = QPixmap.fromImage(scaled)
        
        # Create brush with texture (Qt.TexturePattern)
        brush = QBrush(pixmap)
        
        return brush

    def _draw_stroke(self, canvas, path: QPainterPath):
        """Draw the stroke using QPainterPath with brush texture."""
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set pen with solid line style
            pen = QPen()
            pen.setStyle(Qt.SolidLine)
            pen.setWidth(max(2, int(self.size)))
            pen.setColor(QColor(self.color.red(), self.color.green(), 
                              self.color.blue(), max(5, self.opacity)))
            pen.setBrush(self._create_brush(self.size, self.opacity))
            painter.setPen(pen)
            
            # Stroke the path
            painter.drawPath(path)
        
        _draw_on_layer(canvas, draw)

    def on_press(self, canvas, pos: QPoint):
        _push_undo(canvas)
        self._last_pos = None
        self._path = QPainterPath()
        self._path.moveTo(pos)
        
        pressure = getattr(canvas, '_pressure', 1.0)
        self.size = max(2, int(self.size * pressure))

    def on_move(self, canvas, pos: QPoint):
        if self._last_pos is None:
            self._last_pos = pos
            return
        
        self._path.lineTo(pos)
        
        pressure = getattr(canvas, '_pressure', 1.0)
        size = max(2, int(self.size * pressure))
        opacity = max(5, int(self.opacity * pressure))
        
        step = max(1.0, size * self.spacing)
        dx = pos.x() - self._last_pos.x()
        dy = pos.y() - self._last_pos.y()
        dist = math.hypot(dx, dy)
        
        if dist >= step:
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                
                pen = QPen()
                pen.setStyle(Qt.SolidLine)
                pen.setWidth(1)
                pen.setColor(QColor(self.color.red(), self.color.green(), 
                                  self.color.blue(), max(5, opacity)))
                
                brush = self._create_brush(size, opacity)
                pen.setBrush(brush)
                painter.setPen(pen)
                
                painter.drawLine(self._last_pos, pos)
            
            _draw_on_layer(canvas, draw)
            self._last_pos = pos

    def on_release(self, canvas, pos: QPoint):
        # Draw final stroke
        if not self._path.isEmpty():
            self._draw_stroke(canvas, self._path)
        self._last_pos = None
        self._path = QPainterPath()