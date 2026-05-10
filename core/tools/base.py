# core/tools/base.py
"""Base classes and helpers for drawing tools with Catmull-Rom stabilization."""

from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint, QPointF
from collections import deque
from typing import Optional
import math


class DrawingTool:
    """Base class for all drawing tools."""

    name: str = "tool"
    cursor: int = Qt.CrossCursor

    def on_press(self, canvas, pos: QPoint) -> None:
        """Called when mouse/stylus is pressed."""
        pass

    def on_move(self, canvas, pos: QPoint) -> None:
        """Called when mouse/stylus moves."""
        pass

    def on_release(self, canvas, pos: QPoint) -> None:
        """Called when mouse/stylus is released."""
        pass


class StabilizedDrawingTool(DrawingTool):
    """
    Drawing tool with Catmull-Rom spline smoothing and prediction.

    Features:
    - Catmull-Rom interpolation for smooth curves
    - Adjustable stability (0-10)
    - Pressure sensitivity
    - Point buffering for curve prediction
    """

    def __init__(
        self,
        color: Optional[QColor] = None,
        width: int = 10,
        opacity: int = 255,
        stability: int = 0
    ):
        self.color: QColor = color or QColor(0, 0, 0)
        self.width: int = width
        self.opacity: int = opacity
        self.stability: int = stability

        self._points: deque = deque(maxlen=4)
        self._pressure_values: deque = deque(maxlen=4)
        self._last: Optional[QPoint] = None
        self._first_point: Optional[QPoint] = None

    def add_point(self, x: float, y: float, pressure: float = 1.0) -> list[tuple[float, float, float]]:
        """
        Add point with Catmull-Rom interpolation.

        Returns list of interpolated points for smooth curves.
        """
        current_point = (float(x), float(y))
        self._points.append(current_point)
        self._pressure_values.append(float(pressure))

        interpolated: list[tuple[float, float, float]] = []

        if len(self._points) >= 2:
            # Calculate distance between last two points
            p1 = self._points[-2]
            p2 = self._points[-1]
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

            # Number of segments based on distance and width
            step = max(1, self.width // 2)
            segments = max(2, int(dist / step))

            if len(self._points) == 4:
                # Full Catmull-Rom spline
                p0 = self._points[0]
                p1 = self._points[1]
                p2 = self._points[2]
                p3 = self._points[3]

                for i in range(1, segments + 1):
                    t = i / segments
                    tt = t * t
                    ttt = tt * t

                    # Catmull-Rom matrix
                    q0 = -0.5 * ttt + tt - 0.5 * t
                    q1 = 1.5 * ttt - 2.5 * tt + 1.0
                    q2 = -1.5 * ttt + 2.0 * tt + 0.5 * t
                    q3 = 0.5 * ttt - 0.5 * tt

                    px = q0 * p0[0] + q1 * p1[0] + q2 * p2[0] + q3 * p3[0]
                    py = q0 * p0[1] + q1 * p1[1] + q2 * p2[1] + q3 * p3[1]

                    # Interpolate pressure
                    p_weight = self._pressure_values[1] * (1 - t) + self._pressure_values[2] * t
                    interpolated.append((px, py, p_weight))

            elif len(self._points) == 3:
                # Linear interpolation for 3 points
                p1 = self._points[-2]
                p2 = self._points[-1]

                for i in range(1, segments + 1):
                    t = i / segments
                    px = p1[0] + (p2[0] - p1[0]) * t
                    py = p1[1] + (p2[1] - p1[1]) * t
                    p_weight = self._pressure_values[1] * (1 - t) + self._pressure_values[2] * t
                    interpolated.append((px, py, p_weight))

        return interpolated

    def get_smooth_point(self, x: float, y: float) -> QPoint:
        """Get smoothed point using last position and stability."""
        if self._last and self.stability > 0:
            factor = self.stability / 10.0
            return QPoint(
                int(self._last.x() * factor + x * (1 - factor)),
                int(self._last.y() * factor + y * (1 - factor))
            )
        return QPoint(int(x), int(y))

    def get_interpolated_points(
        self,
        p1: QPoint,
        p2: QPoint,
        pressure: float = 1.0
    ) -> list[QPoint]:
        """Get interpolated points between two points."""
        points: list[QPoint] = []
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)

        if dist < self.width:
            return [p2]

        step = max(1, self.width // 2)
        steps = max(1, int(dist / step))

        for i in range(steps + 1):
            t = i / steps
            x = p1.x() + dx * t
            y = p1.y() + dy * t
            points.append(QPoint(int(x), int(y)))

        return points

    def reset(self) -> None:
        """Reset tool state."""
        self._points.clear()
        self._pressure_values.clear()
        self._last = None
        self._first_point = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _active_layer(canvas) -> Optional[any]:
    """Get the currently active layer."""
    if canvas.project:
        frame = canvas.project.get_current_frame()
        idx = frame.current_layer_idx
        if 0 <= idx < len(frame.layers):
            return frame.layers[idx]
    return None


def _push_undo(canvas) -> None:
    """Push current state to undo stack."""
    if canvas.project:
        canvas.project.get_current_frame().push_undo()


def _draw_on_layer(canvas, fn) -> None:
    """Execute drawing function on active layer with optional clipping.
    
    If canvas has _drawing_target set, draws to that QImage instead.
    """
    layer = _active_layer(canvas)
    if layer is None or getattr(layer, 'locked', False):
        return
    
    # Support drawing to a custom target (e.g., ghost canvas overlay)
    target = getattr(canvas, '_drawing_target', None)
    if target is None:
        target = layer.image
    
    p = QPainter(target)
    p.setRenderHint(QPainter.Antialiasing)
    
    # Enable proper alpha blending for opacity to work
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    
    # Apply clipping if there's an active selection
    if getattr(canvas, 'selection_active', False):
        selection_path = getattr(canvas, 'selection_path', None)
        selection_rect = getattr(canvas, 'selection_rect', None)
        
        if selection_path:
            p.setClipPath(selection_path)
        elif selection_rect:
            p.setClipRect(selection_rect)
    
    fn(p)
    p.end()
    canvas.update()


def create_pen(color: QColor, width: int, opacity: int = 255) -> QPen:
    """Create a configured QPen."""
    c = QColor(color)
    if opacity < 255:
        c.setAlpha(opacity)
    pen = QPen(c, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    pen.setWidth(width)
    return pen