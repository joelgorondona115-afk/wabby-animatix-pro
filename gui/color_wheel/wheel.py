# gui/color_wheel/wheel.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QColor, QConicalGradient, QBrush, QPen, QImage,
    QPixmap,
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
import math


class ColorWheel(QWidget):
    color_changed = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.hue = 0
        self.saturation = 1.0
        self.value = 1.0
        self.current_color = QColor(0, 0, 0)
        self._drag_ring = False
        self._drag_square = False

    def set_color(self, color: QColor):
        h, s, v, _ = color.getHsvF()
        self.hue = max(0, int(h * 360)) if h >= 0 else 0
        self.saturation = max(0.0, min(s, 1.0))
        self.value = max(0.0, min(v, 1.0))
        self._commit()

    def _center(self): return QPointF(self.width() / 2, self.height() / 2)
    def _outer_r(self): return min(self.width(), self.height()) / 2 - 4
    def _inner_r(self): return self._outer_r() - 18

    def _square_rect(self):
        r = self._inner_r() * 0.70
        cx, cy = self._center().x(), self._center().y()
        return QRectF(cx - r, cy - r, r * 2, r * 2)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        self._draw_hue_ring(p)
        self._draw_sv_square(p)
        self._draw_hue_indicator(p)
        self._draw_sv_indicator(p)

    def _draw_hue_ring(self, p):
        outer_r, inner_r = self._outer_r(), self._inner_r()
        cx, cy = self._center().x(), self._center().y()
        g = QConicalGradient(cx, cy, 0)
        for i in range(361):
            g.setColorAt(1.0 - i / 360.0, QColor.fromHsvF((i % 360) / 360.0, 1.0, 1.0))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), outer_r, outer_r)
        p.setBrush(QBrush(QColor("#1e1e1e")))
        p.drawEllipse(QPointF(cx, cy), inner_r, inner_r)

    def _draw_sv_square(self, p):
        rect = self._square_rect()
        w, h = int(rect.width()), int(rect.height())
        if w < 2 or h < 2:
            return
        img = QImage(w, h, QImage.Format_RGB32)
        for px in range(w):
            for py in range(h):
                img.setPixelColor(px, py, QColor.fromHsvF(
                    self.hue / 360.0, px / (w - 1), 1.0 - py / (h - 1)
                ))
        p.drawImage(rect.toRect(), img)
        p.setPen(QPen(QColor(80, 80, 80), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(rect)

    def _draw_hue_indicator(self, p):
        cx, cy = self._center().x(), self._center().y()
        mid_r = (self._outer_r() + self._inner_r()) / 2
        a = math.radians(self.hue)
        ix = cx + mid_r * math.cos(a)
        iy = cy - mid_r * math.sin(a)
        p.setPen(QPen(Qt.white, 2))
        p.setBrush(QBrush(QColor.fromHsvF(self.hue / 360.0, 1.0, 1.0)))
        p.drawEllipse(QPointF(ix, iy), 7, 7)

    def _draw_sv_indicator(self, p):
        rect = self._square_rect()
        x = rect.left() + self.saturation * rect.width()
        y = rect.top() + (1.0 - self.value) * rect.height()
        p.setPen(QPen(Qt.white, 2))
        p.setBrush(QBrush(self.current_color))
        p.drawEllipse(QPointF(x, y), 7, 7)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position() if hasattr(event, 'position') else QPointF(event.pos())
            if self._in_ring(pos):
                self._drag_ring = True
                self._set_hue_from_pos(pos)
            elif self._in_square(pos):
                self._drag_square = True
                self._set_sv_from_pos(pos)

    def mouseMoveEvent(self, event):
        pos = event.position() if hasattr(event, 'position') else QPointF(event.pos())
        if self._drag_ring:
            self._set_hue_from_pos(pos)
        elif self._drag_square:
            self._set_sv_from_pos(pos)

    def mouseReleaseEvent(self, event):
        self._drag_ring = self._drag_square = False

    def _in_ring(self, pos):
        d = math.hypot(pos.x() - self._center().x(), pos.y() - self._center().y())
        return self._inner_r() <= d <= self._outer_r()

    def _in_square(self, pos):
        return self._square_rect().contains(pos)

    def _set_hue_from_pos(self, pos):
        cx, cy = self._center().x(), self._center().y()
        self.hue = int(math.degrees(math.atan2(-(pos.y() - cy), pos.x() - cx))) % 360
        self._commit()

    def _set_sv_from_pos(self, pos):
        rect = self._square_rect()
        x = max(rect.left(), min(pos.x(), rect.right()))
        y = max(rect.top(), min(pos.y(), rect.bottom()))
        self.saturation = (x - rect.left()) / rect.width()
        self.value = 1.0 - (y - rect.top()) / rect.height()
        self._commit()

    def _commit(self):
        c = QColor.fromHsvF(
            self.hue / 360.0,
            max(0.0, min(self.saturation, 1.0)),
            max(0.0, min(self.value, 1.0)),
        )
        self.current_color = QColor(c.red(), c.green(), c.blue())
        main_win = self.window()
        if hasattr(main_win, 'canvas'):
            canvas = main_win.canvas
            new_color = QColor(c.red(), c.green(), c.blue())
            for tool_name in ("pencil", "brush", "lasso_fill", "lasso_fill_rect",
                            "lasso_fill_ellipse", "line", "rect", "ellipse", "fill", "text", "poly_fill"):
                tool = canvas.tools.get(tool_name)
                if tool and hasattr(tool, "color"):
                    tool.color = new_color
        self.color_changed.emit(self.current_color)
        self.update()

    def set_value(self, val: int):
        self.value = val / 255.0
        self._commit()
        self.update()