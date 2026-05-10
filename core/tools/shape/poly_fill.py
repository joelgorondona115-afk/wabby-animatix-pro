# core/tools/shape/poly_fill.py
"""Poly fill tool: click to place points, smooth curve preview, fills on finalize."""

from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush
from PySide6.QtCore import Qt, QPointF

from core.tools.base import DrawingTool, _draw_on_layer, _push_undo


class PolyFillTool(DrawingTool):
    name = "poly_fill"
    cursor = Qt.CrossCursor

    def __init__(self, color: QColor = None, width: float = 2.0, opacity: int = 255):
        if color is None:
            color = QColor(0, 120, 215)
        self.color = color
        self.width = width
        self.opacity = opacity
        self._points = []
        self._is_drawing = False
        self._current_pos = None

    def _build_path(self, points: list, closed: bool = True) -> QPainterPath:
        if not points:
            return QPainterPath()

        path = QPainterPath()
        path.moveTo(points[0])

        if len(points) < 3:
            for p in points[1:]:
                path.lineTo(p)
        else:
            for i in range(1, len(points) - 1):
                p1 = QPointF(points[i])
                p2 = QPointF(points[min(len(points) - 1, i + 1)])
                mid_x = (p1.x() + p2.x()) / 2.0
                mid_y = (p1.y() + p2.y()) / 2.0
                path.quadTo(p1, QPointF(mid_x, mid_y))

        if closed and len(points) >= 3:
            last = QPointF(points[-1])
            first = QPointF(points[0])
            mid_x = (last.x() + first.x()) / 2.0
            mid_y = (last.y() + first.y()) / 2.0
            path.quadTo(last, QPointF(mid_x, mid_y))
            path.lineTo(first)
            path.closeSubpath()
        else:
            path.lineTo(QPointF(points[-1]))

        return path

    def _draw_preview(self, canvas):
        canvas.overlay_image.fill(Qt.transparent)
        if not self._points:
            return

        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)

        points_with_cursor = list(self._points)
        if self._current_pos:
            points_with_cursor.append(self._current_pos)

        c = QColor(self.color)
        c.setAlpha(int(self.opacity * 0.3))
        if len(points_with_cursor) >= 3:
            path = self._build_path(points_with_cursor, closed=True)
            p.fillPath(path, QBrush(c))

        c_stroke = QColor(self.color)
        c_stroke.setAlpha(self.opacity)
        pen = QPen(c_stroke, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)

        if len(points_with_cursor) >= 3:
            p.drawPath(self._build_path(points_with_cursor, closed=True))
        else:
            for i in range(1, len(points_with_cursor)):
                p.drawLine(QPointF(points_with_cursor[i - 1]), QPointF(points_with_cursor[i]))

        p.end()
        canvas.update()

    def _finalize(self, canvas):
        if len(self._points) < 3:
            self._reset()
            return

        _push_undo(canvas)
        path = self._build_path(self._points, closed=True)

        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)

            c_fill = QColor(self.color)
            c_fill.setAlpha(self.opacity)
            painter.fillPath(path, QBrush(c_fill))

            c_stroke = QColor(self.color)
            c_stroke.setAlpha(self.opacity)
            pen = QPen(c_stroke, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
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
