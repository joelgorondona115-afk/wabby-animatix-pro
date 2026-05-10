# core/tools/vector/vector_brush.py
"""Vector brush tool with stabilization - CORREGIDO."""

from PySide6.QtGui import QPainterPath, QColor
from PySide6.QtCore import Qt, QPoint, QPointF

from core.tools.base import DrawingTool


class VectorBrushTool(DrawingTool):
    """Draws smooth vector strokes on VectorLayer with stabilization."""

    name = "vector_brush"
    cursor = Qt.CrossCursor

    def __init__(self, color: QColor = None, width: float = 4.0, opacity: int = 255):
        if color is None:
            color = QColor(0, 0, 0)
        self.color = color
        self.width = width
        self.opacity = opacity
        self._drawing = False
        self._current_stroke = None
        self._points = []

    def _get_vector_layer(self, canvas):
        """Get active vector layer."""
        if canvas.project:
            frame = canvas.project.get_current_frame()
            layer = frame.layers[frame.current_layer_idx]
            if hasattr(layer, 'is_vector') and layer.is_vector:
                return layer
        return None

    def _smooth_path(self, points: list) -> QPainterPath:
        """Create smooth path from points using quadratic curves."""
        if not points:
            return QPainterPath()

        path = QPainterPath()
        path.moveTo(points[0])

        if len(points) < 3:
            for p in points[1:]:
                path.lineTo(p)
            return path

        for i in range(1, len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[min(len(points) - 1, i + 1)]

            mid_x = (p1.x() + p2.x()) / 2.0
            mid_y = (p1.y() + p2.y()) / 2.0
            path.quadTo(p1, QPointF(mid_x, mid_y))

        path.lineTo(points[-1])
        return path

    def on_press(self, canvas, pos: QPoint) -> None:
        """Start new smooth stroke."""
        layer = self._get_vector_layer(canvas)
        if layer is None or getattr(layer, 'locked', False):
            return

        if hasattr(canvas.project.get_current_frame(), 'push_undo'):
            canvas.project.get_current_frame().push_undo()

        self._drawing = True
        pos_f = QPointF(pos.x(), pos.y())
        self._points = [pos_f]
        self._current_stroke = layer.start_new_stroke(
            pos_f, self.color, self.width, self.opacity
        )
        canvas.update()

    def on_move(self, canvas, pos: QPoint) -> None:
        """Extend stroke with smooth interpolation."""
        if not self._drawing:
            return
        layer = self._get_vector_layer(canvas)
        if layer is None:
            return

        pos_f = QPointF(pos.x(), pos.y())
        self._points.append(pos_f)

        smooth = self._smooth_path(self._points)
        layer.strokes[-1].path = smooth
        canvas.update()

    def on_release(self, canvas, pos: QPoint) -> None:
        """Finish smooth stroke."""
        if self._drawing:
            layer = self._get_vector_layer(canvas)
            if layer:
                pos_f = QPointF(pos.x(), pos.y())
                self._points.append(pos_f)
                smooth = self._smooth_path(self._points)
                layer.strokes[-1].path = smooth

        self._drawing = False
        self._points = []
        self._current_stroke = None
        canvas.update()
