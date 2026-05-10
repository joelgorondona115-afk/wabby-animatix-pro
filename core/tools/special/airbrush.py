# core/tools/special/airbrush.py
"""Professional Airbrush tool with radial gradient."""

from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPainterPath
from PySide6.QtCore import Qt, QPoint

from core.tools.base import DrawingTool, _push_undo, _draw_on_layer


class AirbrushTool(DrawingTool):
    """
    Professional Airbrush with flow control.
    
    Flow: How much paint is deposited per dab (accumulates)
    Opacity: Maximum density of the spray
    """
    name = "airbrush"
    cursor = Qt.CrossCursor

    def __init__(self, color=QColor(0, 0, 0), size=60, flow=15, opacity=255):
        self.color = color
        self.size = size
        self.flow = flow
        self.opacity = opacity
        self._last = None
        self._dabs = []
    
    @property
    def width(self) -> int:
        return self.size
    
    @width.setter
    def width(self, value: int) -> None:
        self.size = value

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._last = None
        self._dabs = []

    def on_move(self, canvas, pos):
        if not self._last:
            self._last = pos
            return
        self._spray_line(canvas, self._last, pos)
        self._last = pos

    def on_release(self, canvas, pos):
        self._last = None
        self._dabs = []

    def _create_gradient_dab(self, x, y, radius, intensity):
        """Soft gaussian gradient - edges blend into nothing."""
        gradient = QRadialGradient(x, y, radius)
        
        c = QColor(self.color)
        base_alpha = min(255, int(self.flow * intensity * 2.55))
        center_alpha = int(base_alpha * (self.opacity / 255.0))
        c.setAlpha(center_alpha)
        
        gradient.setColorAt(0.0, c)
        gradient.setColorAt(0.4, QColor(c.red(), c.green(), c.blue(), int(center_alpha * 0.5)))
        gradient.setColorAt(0.8, QColor(c.red(), c.green(), c.blue(), int(center_alpha * 0.05)))
        gradient.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
        
        return gradient

    def _spray(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        radius = max(5, int(self.size * pressure))
        
        # Create soft gradient dab
        gradient = self._create_gradient_dab(pos.x(), pos.y(), radius, pressure)
        
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            # Draw ellipse with gradient
            painter.setPen(Qt.NoPen)
            brush = painter.brush()
            painter.setBrush(gradient)
            painter.drawEllipse(pos, radius, radius)
        
        _draw_on_layer(canvas, draw)

    def _spray_line(self, canvas, p1, p2):
        """Interpolate between two points for smooth spray."""
        import math
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        
        if dist < 2:
            self._spray(canvas, p2)
            return
        
        pressure = getattr(canvas, '_pressure', 1.0)
        radius = max(5, int(self.size * pressure))
        
        # Interpolate dabs close enough for smooth overlap
        step = max(1, radius // 3)
        steps = max(1, int(dist / step))
        
        for i in range(steps + 1):
            t = i / steps
            x = int(p1.x() + dx * t)
            y = int(p1.y() + dy * t)
            pos = QPoint(x, y)
            
            self._spray(canvas, pos)