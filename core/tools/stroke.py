# core/tools/stroke.py
"""Stroke drawing handlers."""

from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QRadialGradient
from PySide6.QtCore import QPoint, QPointF, Qt
import math

from .stabilizer import get_shared_stabilizer, Stabilizer


class StrokeHandler:
    def __init__(self, color: QColor, width: int, opacity: int = 255):
        self.color = color
        self.width = width
        self.opacity = opacity
        self._stabilizer = get_shared_stabilizer()

        self._stabilizer.signals.stability_changed.connect(self._on_stability_changed)
        self._stabilizer.signals.reset_requested.connect(self._on_reset_requested)

    def _on_stability_changed(self, value: int) -> None:
        pass

    def _on_reset_requested(self) -> None:
        self._stabilizer.reset()

    @property
    def stability(self) -> int:
        return self._stabilizer.stability

    @stability.setter
    def stability(self, value: int) -> None:
        self._stabilizer.set_stability(value)

    def reset(self) -> None:
        self._stabilizer.reset()

    def get_smooth_point(self, x: float, y: float) -> QPoint:
        return self._stabilizer.get_smooth_point(x, y)

    def draw_point(self, painter: QPainter, pos: QPoint, pressure: float = 1.0) -> None:
        raise NotImplementedError

    def draw_line(self, painter: QPainter, p1: QPoint, p2: QPoint, pressure: float = 1.0) -> None:
        raise NotImplementedError

    def set_color(self, color: QColor) -> None:
        self.color = color

    def set_width(self, width: int) -> None:
        self.width = width

    def set_opacity(self, opacity: int) -> None:
        self.opacity = opacity


class PencilStroke(StrokeHandler):
    """Lápiz con bordes duros."""

    def __init__(self, color: QColor = QColor(0, 0, 0), width: int = 3, opacity: int = 255):
        super().__init__(color, width, opacity)

    def draw_point(self, painter: QPainter, pos: QPoint, pressure: float = 1.0) -> None:
        w = max(1, int(self.width * pressure))
        c = QColor(self.color)
        c.setAlpha(self.opacity)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPoint(pos)

    def draw_line(self, painter: QPainter, p1: QPoint, p2: QPoint, pressure: float = 1.0) -> None:
        w = max(1, int(self.width * pressure))
        c = QColor(self.color)
        c.setAlpha(self.opacity)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

    def draw_smooth_line(self, painter: QPainter, p1, p2, pressure: float = 1.0) -> None:
        w = max(1, int(self.width * pressure))
        c = QColor(self.color)
        c.setAlpha(self.opacity)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)


class BrushStroke(StrokeHandler):
    """Pincel con mucho difuminado."""

    def __init__(self, color: QColor = QColor(0, 0, 0), width: int = 10, opacity: int = 180):
        super().__init__(color, width, opacity)

    def _draw_blurred_dot(self, painter: QPainter, x: float, y: float, size: int) -> None:
        """Dibuja punto con difuminado extremo."""
        size = max(1, int(size))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        gradient = QRadialGradient(x, y, size)
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        
        # Comportamiento dinámico según tamaño
        if size <= 1:
            # Radio 1: completamente difuminado tipo aerografo
            gradient.setColorAt(0.0, QColor(r, g, b, 180))
            gradient.setColorAt(0.5, QColor(r, g, b, 80))
            gradient.setColorAt(0.85, QColor(r, g, b, 10))
            gradient.setColorAt(1.0, QColor(r, g, b, 0))
        elif size <= 3:
            # Radio pequeño: muy difuminado
            gradient.setColorAt(0.0, QColor(r, g, b, 255))
            gradient.setColorAt(0.4, QColor(r, g, b, 200))
            gradient.setColorAt(0.7, QColor(r, g, b, 50))
            gradient.setColorAt(1.0, QColor(r, g, b, 0))
        else:
            # Radio grande: sharp (núcleo fuerte, bordes rápidos)
            gradient.setColorAt(0.0, QColor(r, g, b, 255))
            gradient.setColorAt(0.15, QColor(r, g, b, 255))
            gradient.setColorAt(0.35, QColor(r, g, b, 100))
            gradient.setColorAt(0.65, QColor(r, g, b, 10))
            gradient.setColorAt(1.0, QColor(r, g, b, 0))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.setOpacity(self.opacity / 255.0)
        painter.drawEllipse(int(x - size), int(y - size), size * 2, size * 2)
        painter.restore()

    def draw_point(self, painter: QPainter, pos: QPoint, pressure: float = 1.0) -> None:
        w = max(2, int(self.width * pressure))
        self._draw_blurred_dot(painter, pos.x(), pos.y(), w)

    def draw_line(self, painter: QPainter, p1: QPoint, p2: QPoint, pressure: float = 1.0) -> None:
        w = max(2, int(self.width * pressure))
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            self._draw_blurred_dot(painter, p1.x(), p1.y(), w)
            return
        min_step = w * 0.3
        num_steps = max(2, int(dist / min_step))
        for i in range(num_steps + 1):
            t = i / num_steps
            x = p1.x() + dx * t
            y = p1.y() + dy * t
            self._draw_blurred_dot(painter, x, y, w)

    def draw_smooth_line(self, painter: QPainter, p1: QPointF, p2: QPointF, pressure: float = 1.0) -> None:
        w = max(2.0, self.width * pressure)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            self._draw_blurred_dot(painter, p1.x(), p1.y(), int(w))
            return
        min_step = w * 0.3
        num_steps = max(2, int(dist / min_step))
        for i in range(num_steps + 1):
            t = i / num_steps
            x = p1.x() + dx * t
            y = p1.y() + dy * t
            self._draw_blurred_dot(painter, x, y, int(w))


class EraserStroke(StrokeHandler):
    """Borrador con bordes suaves."""

    def __init__(self, color: QColor = QColor(0, 0, 0), width: int = 10, opacity: int = 255):
        super().__init__(color, width, opacity)

    def _draw_soft_dot(self, painter: QPainter, x: float, y: float, size: int) -> None:
        size = max(2, int(size))
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        gradient = QRadialGradient(x, y, size)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 255))
        gradient.setColorAt(0.5, QColor(0, 0, 0, 200))
        gradient.setColorAt(0.8, QColor(0, 0, 0, 60))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.setOpacity(self.opacity / 255.0)
        painter.drawEllipse(int(x - size), int(y - size), size * 2, size * 2)
        painter.restore()

    def draw_point(self, painter: QPainter, pos: QPoint, pressure: float = 1.0) -> None:
        w = max(2, int(self.width * pressure))
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        self._draw_soft_dot(painter, pos.x(), pos.y(), w)

    def draw_line(self, painter: QPainter, p1: QPoint, p2: QPoint, pressure: float = 1.0) -> None:
        w = max(2, int(self.width * pressure))
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            self._draw_soft_dot(painter, p1.x(), p1.y(), w)
            return
        min_step = w * 0.3
        num_steps = max(2, int(dist / min_step))
        for i in range(num_steps + 1):
            t = i / num_steps
            x = p1.x() + dx * t
            y = p1.y() + dy * t
            self._draw_soft_dot(painter, x, y, w)

    def draw_smooth_line(self, painter: QPainter, p1: QPointF, p2: QPointF, pressure: float = 1.0) -> None:
        w = max(2.0, self.width * pressure)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            self._draw_soft_dot(painter, p1.x(), p1.y(), int(w))
            return
        min_step = w * 0.3
        num_steps = max(2, int(dist / min_step))
        for i in range(num_steps + 1):
            t = i / num_steps
            x = p1.x() + dx * t
            y = p1.y() + dy * t
            self._draw_soft_dot(painter, x, y, int(w))
