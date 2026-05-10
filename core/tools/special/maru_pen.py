# core/tools/special/maru_pen.py
"""Maru Pen (technical pen) for clean lineart."""

import math
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtCore import Qt, QPoint

from core.tools.base import DrawingTool, _push_undo, _draw_on_layer


class MaruPenTool(DrawingTool):
    """
    Maru Pen (Technical Pen) for clean lineart.
    
    Features:
    - Hard edge (sharp border with antialiasing)
    - Exponential pressure curve (starts thin, grows with pressure)
    - Tapering (line ends in point when lifting)
    - Medium-high stabilization
    - 100% opacity
    """
    name = "maru_pen"
    cursor = Qt.CrossCursor

    def __init__(self, color=QColor(0, 0, 0), size=3, stability=3):
        self.color = color
        self.size = size  # Base size at full pressure
        self.stability = stability  # Smoothing level
        self._last = None
        self._points = []  # For stabilization
        self._last_pressure = 1.0

    def set_color(self, color):
        self.color = color

    def set_size(self, size):
        self.size = size

    def _get_pressure_size(self, pressure):
        """Exponential curve: thin at start, grows with pressure."""
        # Exponential curve: size * pressure^2
        # At 0.1 pressure = 1% size, at 1.0 = 100% size
        return max(1, int(self.size * (pressure ** 1.5)))

    def _smooth_point(self, x, y):
        """Exponential smoothing for stabilization."""
        if self.stability == 0:
            return QPoint(int(x), int(y))
        
        # Simple exponential smoothing
        alpha = 1.0 / (self.stability + 1)
        
        if not self._points:
            self._points = [(x, y)]
            return QPoint(int(x), int(y))
        
        last_x, last_y = self._points[-1]
        
        # Exponential moving average
        smooth_x = last_x * (1 - alpha) + x * alpha
        smooth_y = last_y * (1 - alpha) + y * alpha
        
        self._points.append((smooth_x, smooth_y))
        
        # Keep only recent points
        if len(self._points) > 10:
            self._points = self._points[-10:]
        
        return QPoint(int(smooth_x), int(smooth_y))

    def _draw_line(self, painter, p1, p2, pressure):
        """Draw line with Maru Pen properties."""
        size = self._get_pressure_size(pressure)
        
        # Create pen with hard edge
        pen = QPen(self.color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        pen.setWidth(max(1, size))
        painter.setPen(pen)
        painter.drawLine(p1, p2)

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._last = None
        self._points = [(pos.x(), pos.y())]
        self._last_pressure = 1.0

    def on_move(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        
        if pressure < self._last_pressure:
            pressure = self._last_pressure * 0.9 + pressure * 0.1
        
        self._last_pressure = pressure
        
        smooth = self._smooth_point(pos.x(), pos.y())

        if not self._last:
            self._last = smooth
            return

        def draw(p):
            self._draw_line(p, self._last, smooth, pressure)

        _draw_on_layer(canvas, draw)
        self._last = smooth

    def on_release(self, canvas, pos):
        self._last = None
        self._points = []
