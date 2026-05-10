# core/tools/shape/polyline.py
"""Polyline tool with smooth curves for lineart cleanup."""

from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QPolygonF
from PySide6.QtCore import Qt, QPoint, QPointF

from core.tools.base import DrawingTool, _draw_on_layer, _push_undo


class PolylineTool(DrawingTool):
    """
    Polyline tool with smooth curve interpolation.
    
    Usage:
    - Click to add anchor points
    - Lines connect with smooth curves automatically
    - Double-click or press Enter to finalize
    - Press Escape to cancel
    - Works on both raster and vector layers
    """
    name = "polyline"
    cursor = Qt.CrossCursor

    def __init__(self, color: QColor = None, width: float = 2.0, opacity: int = 255):
        if color is None:
            color = QColor(0, 0, 0)
        self.color = color
        self.width = width
        self.opacity = opacity
        self._points = []
        self._is_drawing = False
        self._current_pos = None

    def _get_vector_layer(self, canvas):
        if canvas.project:
            frame = canvas.project.get_current_frame()
            layer = frame.layers[frame.current_layer_idx]
            if hasattr(layer, 'is_vector') and layer.is_vector:
                return layer
        return None

    def _build_path(self, points: list) -> QPainterPath:
        """Build smooth path from points using Catmull-Rom spline."""
        if not points:
            return QPainterPath()

        path = QPainterPath()
        path.moveTo(points[0])

        if len(points) < 3:
            for p in points[1:]:
                path.lineTo(p)
            return path

        for i in range(1, len(points) - 1):
            p0 = QPointF(points[max(0, i - 1)])
            p1 = QPointF(points[i])
            p2 = QPointF(points[min(len(points) - 1, i + 1)])

            mid_x = (p1.x() + p2.x()) / 2.0
            mid_y = (p1.y() + p2.y()) / 2.0
            path.quadTo(p1, QPointF(mid_x, mid_y))

        path.lineTo(QPointF(points[-1]))
        return path

    def _draw_preview(self, canvas):
        """Draw polyline preview on overlay."""
        canvas.overlay_image.fill(Qt.transparent)
        if not self._points:
            return

        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)

        c = QColor(self.color)
        c.setAlpha(self.opacity)
        pen = QPen(c, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)

        points_with_cursor = list(self._points)
        if self._current_pos:
            points_with_cursor.append(self._current_pos)

        path = self._build_path(points_with_cursor)
        p.drawPath(path)

        p.end()
        canvas.update()

    def _finalize(self, canvas):
        """Finalize the polyline."""
        if len(self._points) < 2:
            self._reset()
            return

        _push_undo(canvas)
        path = self._build_path(self._points)

        vector_layer = self._get_vector_layer(canvas)
        if vector_layer:
            # Draw on vector layer
            pos_f = QPointF(self._points[0])
            vector_layer.start_new_stroke(pos_f, self.color, self.width, self.opacity)
            for pt in self._points[1:]:
                vector_layer.strokes[-1].path.lineTo(QPointF(pt))
            # Rebuild with smooth curves
            smooth = self._build_path(self._points)
            vector_layer.strokes[-1].path = smooth
        else:
            # Draw on raster layer
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                c = QColor(self.color)
                c.setAlpha(self.opacity)
                pen = QPen(c, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(path)

            _draw_on_layer(canvas, draw)

        self._reset()
        canvas.update()

    def _reset(self):
        self._points = []
        self._is_drawing = False
        self._current_pos = None

    def on_press(self, canvas, pos):
        if not self._is_drawing:
            _push_undo(canvas)
            self._is_drawing = True

        self._points.append(QPointF(pos))
        self._current_pos = None
        self._draw_preview(canvas)

    def on_move(self, canvas, pos):
        if self._is_drawing:
            self._current_pos = QPointF(pos)
            self._draw_preview(canvas)

    def on_release(self, canvas, pos):
        pass

    def _cancel(self, canvas):
        self._reset()
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
