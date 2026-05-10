# core/tools.py
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QImage, QRegion, QPixmap
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QPointF
import math
import struct


# ---------------------------------------------------------------------------
# Parser de pinceles .abr (Photoshop v1 y v2)
# ---------------------------------------------------------------------------
def parse_abr(path: str) -> list:
    """
    Parsea un archivo .abr de Photoshop (versiones 1 y 2).
    Retorna lista de (nombre: str, tip: QImage).
    """
    results = []
    try:
        with open(path, 'rb') as f:
            data = f.read()
        version = struct.unpack_from('>H', data, 0)[0]
        if version not in (1, 2):
            return results
        count  = struct.unpack_from('>H', data, 2)[0]
        offset = 4
        for i in range(count):
            if offset + 6 > len(data):
                break
            btype  = struct.unpack_from('>H', data, offset)[0]
            blen   = struct.unpack_from('>I', data, offset + 2)[0]
            offset += 6
            end = offset + blen
            if btype == 2:
                o = offset
                o += 4  # misc flags
                o += 2  # spacing
                brush_name = f"Pincel {i + 1}"
                if version == 2:
                    if o + 2 > len(data):
                        offset = end
                        continue
                    nlen = struct.unpack_from('>H', data, o)[0]
                    o += 2
                    try:
                        brush_name = data[o:o + nlen * 2].decode('utf-16-be').rstrip('\x00') or brush_name
                    except Exception:
                        pass
                    o += nlen * 2
                o += 1  # antialiasing
                if o + 8 > len(data):
                    offset = end
                    continue
                top    = struct.unpack_from('>h', data, o)[0]; o += 2
                left   = struct.unpack_from('>h', data, o)[0]; o += 2
                bottom = struct.unpack_from('>h', data, o)[0]; o += 2
                right  = struct.unpack_from('>h', data, o)[0]; o += 2
                w = right - left
                h = bottom - top
                if w > 0 and h > 0 and o + w * h <= len(data):
                    bitmap = data[o:o + w * h]
                    img = QImage(w, h, QImage.Format_ARGB32)
                    img.fill(Qt.transparent)
                    for row in range(h):
                        for col in range(w):
                            alpha = 255 - bitmap[row * w + col]
                            img.setPixel(col, row, QColor(0, 0, 0, alpha).rgba())
                    results.append((brush_name, img))
            offset = end
    except Exception:
        pass
    return results


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class DrawingTool:
    name   = "tool"
    cursor = Qt.CrossCursor

    def on_press(self, canvas, pos: QPoint): pass
    def on_move(self, canvas, pos: QPoint):  pass
    def on_release(self, canvas, pos: QPoint): pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _active_layer(canvas):
    if canvas.project:
        frame = canvas.project.get_current_frame()
        idx = frame.current_layer_idx
        if 0 <= idx < len(frame.layers):
            return frame.layers[idx]
    return None


def _push_undo(canvas):
    if canvas.project:
        canvas.project.get_current_frame().push_undo()


def _draw_on_layer(canvas, fn):
    layer = _active_layer(canvas)
    if layer and not layer.locked:
        p = QPainter(layer.image)
        fn(p)
        p.end()
        canvas.update()
    else:
        print(f"DEBUG: No se pudo dibujar - layer={layer}, locked={layer.locked if layer else 'N/A'}")


# ---------------------------------------------------------------------------
# Lápiz
# ---------------------------------------------------------------------------
class PencilTool(DrawingTool):
    name = "pencil"

    def __init__(self, color=QColor(0, 0, 0), width=3, opacity=255):
        self.color   = color
        self.width   = width
        self.opacity = opacity
        self._last   = None
        self._temp_points = []  # Buffer para suavizado Pencil2D

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._temp_points = [pos]
        self._last = pos
        # Dibujar punto inicial
        self._dot(canvas, pos)

    def on_move(self, canvas, pos):
        if not self._last:
            self._last = pos
            return
        
        # Umbral mínimo de distancia (evita micro-saltos por temblor de mano)
        if self._temp_points:
            last_pt = self._temp_points[-1]
            dx = pos.x() - last_pt.x()
            dy = pos.y() - last_pt.y()
            dist = math.hypot(dx, dy)
            if dist < 0.5:  # Ignora movimientos menores a 0.5px en coordenadas de imagen
                return
        
        self._temp_points.append(pos)
        
        # Suavizado Pencil2D CORREGIDO: usa los últimos 3 puntos para la curva
        if len(self._temp_points) >= 3:
            A = self._temp_points[-3]  # Punto anterior anterior
            B = self._temp_points[-2]  # Punto anterior (control point)
            C = self._temp_points[-1]  # Punto nuevo
            mid = (B + C) / 2.0  # Punto medio entre B y C
            
            pressure = getattr(canvas, '_pressure', 1.0)
            w = max(1.0, self.width * pressure)
            opacity = max(5, int(self.opacity * pressure))
            c = QColor(self.color)
            c.setAlpha(opacity)
            
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                pen = QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                # Curva cuadrática: de A a mid, con punto de control B
                path = QPainterPath()
                path.moveTo(A)
                path.quadTo(B, mid)
                painter.drawPath(path)
            
            _draw_on_layer(canvas, draw)
        
        self._last = pos

    def on_release(self, canvas, pos):
        self._temp_points = []
        self._last = None

    def _dot(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        width = max(1, int(self.width * pressure))
        opacity = max(5, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(c, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(pos)
        _draw_on_layer(canvas, draw)

    def _seg(self, canvas, p1, p2):
        pressure = getattr(canvas, '_pressure', 1.0)
        width = max(1, int(self.width * pressure))
        opacity = max(5, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < width:
            self._dot(canvas, p2)
            return
        step = max(1, width // 2)
        steps = max(1, int(dist / step))
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            for i in range(steps + 1):
                t = i / steps
                # ✅ Interpolar opacidad
                alpha = int(opacity * (1.0 - t * 0.1))
                c_fade = QColor(self.color)
                c_fade.setAlpha(alpha)
                painter.setPen(QPen(c_fade, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                x = int(p1.x() + dx * t)
                y = int(p1.y() + dy * t)
                painter.drawPoint(QPoint(x, y))
        _draw_on_layer(canvas, draw)


# ---------------------------------------------------------------------------
# Pincel
# ---------------------------------------------------------------------------
class BrushTool(DrawingTool):
    name = "brush"

    def __init__(self, color=QColor(0, 0, 0), width=10, opacity=180):
        self.color   = color
        self.width   = width
        self.opacity = opacity
        self._last   = None
        self._temp_points = []  # Buffer para suavizado Pencil2D

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._temp_points = [pos]
        self._last = pos
        self._dot(canvas, pos)

    def on_move(self, canvas, pos):
        if not self._last:
            self._last = pos
            return
        
        self._temp_points.append(pos)
        
        # Suavizado Pencil2D: curva quadTo con punto medio
        if len(self._temp_points) > 2:
            p0 = self._temp_points[-2]
            p1 = self._temp_points[-1]
            mid = (p0 + p1) / 2
            
            pressure = getattr(canvas, '_pressure', 1.0)
            w = max(1, int(self.width * pressure))
            opacity = max(5, int(self.opacity * pressure))
            c = QColor(self.color)
            c.setAlpha(opacity)
            
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                pen = QPen(c, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                path = QPainterPath()
                path.moveTo(p0)
                path.quadTo(p0, mid)
                painter.drawPath(path)
            
            _draw_on_layer(canvas, draw)
        
        self._last = pos

    def on_release(self, canvas, pos):
        self._temp_points = []
        self._last = None

    def _dot(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        width = max(1, int(self.width * pressure))
        opacity = max(5, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(c, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(pos)
        _draw_on_layer(canvas, draw)

    def _seg(self, canvas, p1, p2):
        pressure = getattr(canvas, '_pressure', 1.0)
        width   = max(1, int(self.width * pressure))
        opacity = max(10, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < width:
            self._dot(canvas, p2)
            return
        step = max(1, width // 2)
        steps = max(1, int(dist / step))
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(c, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for i in range(steps + 1):
                t = i / steps
                # ✅ Interpolar opacidad también (fade progresivo)
                alpha = int(opacity * (1.0 - t * 0.1))  # Ligeramente más débil al final
                c_fade = QColor(self.color)
                c_fade.setAlpha(alpha)
                painter.setPen(QPen(c_fade, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                x = int(p1.x() + dx * t)
                y = int(p1.y() + dy * t)
                painter.drawPoint(QPoint(x, y))
        _draw_on_layer(canvas, draw)


# ---------------------------------------------------------------------------
# Goma
# ---------------------------------------------------------------------------
class EraserTool(DrawingTool):
    name   = "eraser"
    cursor = Qt.CrossCursor

    def __init__(self, width=20):
        self.width = width
        self._last = None

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._last = pos
        self._dot(canvas, pos)

    def on_move(self, canvas, pos):
        if self._last:
            self._seg(canvas, self._last, pos)
            self._last = pos
        else:
            self._last = pos

    def on_release(self, canvas, pos):
        self._last = None

    def _dot(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        width = max(1, int(self.width * pressure))
        def draw(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QPen(Qt.transparent, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(pos)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        _draw_on_layer(canvas, draw)

    def _seg(self, canvas, p1, p2):
        pressure = getattr(canvas, '_pressure', 1.0)
        width = max(1, int(self.width * pressure))
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        if dist < width:
            self._dot(canvas, p2)
            return
        step = max(1, width // 2)
        steps = max(1, int(dist / step))
        def draw(painter):
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            # ✅ Borrado suave con opacidad interpolada
            for i in range(steps + 1):
                t = i / steps
                # Opacidad baja al inicio, sube hacia el final (fade in)
                opacity = max(50, int(255 * t))
                painter.setOpacity(opacity / 255.0)
                painter.setPen(QPen(Qt.transparent, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                x = int(p1.x() + dx * t)
                y = int(p1.y() + dy * t)
                painter.drawPoint(QPoint(x, y))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setOpacity(1.0)
        _draw_on_layer(canvas, draw)


# ---------------------------------------------------------------------------
# Balde de relleno
# ---------------------------------------------------------------------------
class FillTool(DrawingTool):
    name   = "fill"
    cursor = Qt.PointingHandCursor

    def __init__(self, color=QColor(0, 0, 0), tolerance=30):
        self.color     = color
        self.tolerance = tolerance

    def on_press(self, canvas, pos):
        layer = _active_layer(canvas)
        if not layer or layer.locked:
            return
        _push_undo(canvas)
        self._flood_fill(layer.image, int(pos.x()), int(pos.y()), self.color, self.tolerance)
        canvas.update()

    def on_move(self, canvas, pos): pass
    def on_release(self, canvas, pos): pass

    @staticmethod
    def _flood_fill(image: QImage, sx: int, sy: int, fill_color: QColor, tolerance: int):
        if not (0 <= sx < image.width() and 0 <= sy < image.height()):
            return

        w, h = image.width(), image.height()

        fill_rgba = fill_color.rgba()
        fill_r = (fill_rgba >> 16) & 0xFF
        fill_g = (fill_rgba >> 8) & 0xFF
        fill_b = fill_rgba & 0xFF
        fill_a = (fill_rgba >> 24) & 0xFF

        ptr = image.bits()
        ptr.setsize(w * h * 4)
        buf = list(struct.unpack(f"{w * h * 4}B", ptr.tobytes()))

        idx_start = (sy * w + sx) * 4
        target_r = buf[idx_start]
        target_g = buf[idx_start + 1]
        target_b = buf[idx_start + 2]
        target_a = buf[idx_start + 3]

        if fill_r == target_r and fill_g == target_g and fill_b == target_b and fill_a == target_a:
            return

        tol = tolerance * 4

        def similar(px_idx):
            return (
                abs(buf[px_idx] - target_r) +
                abs(buf[px_idx + 1] - target_g) +
                abs(buf[px_idx + 2] - target_b) +
                abs(buf[px_idx + 3] - target_a)
            ) <= tol

        stack = [(sx, sy)]
        visited = bytearray(w * h)

        while stack:
            x, y = stack.pop()
            if not (0 <= x < w and 0 <= y < h):
                continue
            key = y * w + x
            if visited[key]:
                continue
            px_idx = (y * w + x) * 4
            if not similar(px_idx):
                continue
            visited[key] = 1
            buf[px_idx] = fill_r
            buf[px_idx + 1] = fill_g
            buf[px_idx + 2] = fill_b
            buf[px_idx + 3] = fill_a
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

        for y in range(h):
            for x in range(w):
                px_idx = (y * w + x) * 4
                idx = y * w + x
                if visited[idx]:
                    image.setPixel(x, y, (
                        (buf[px_idx] << 24) |
                        (buf[px_idx + 1] << 16) |
                        (buf[px_idx + 2] << 8) |
                        buf[px_idx + 3]
                    ))


# ---------------------------------------------------------------------------
# Mover capa
# ---------------------------------------------------------------------------
class MoveTool(DrawingTool):
    name   = "move"
    cursor = Qt.SizeAllCursor

    def __init__(self):
        self._start    = None
        self._snapshot = None
        self._layer_ref = None

    def on_press(self, canvas, pos):
        layer = _active_layer(canvas)
        if layer:
            _push_undo(canvas)
            self._start    = pos
            self._layer_ref = layer
            temp = QImage(layer.image.size(), layer.image.format())
            temp.fill(Qt.transparent)
            p = QPainter(temp)
            p.drawImage(0, 0, layer.image)
            p.end()
            self._snapshot = temp

    def on_move(self, canvas, pos):
        if self._start is None or self._snapshot is None:
            return
        layer = self._layer_ref
        if not layer:
            return
        dx = pos.x() - self._start.x()
        dy = pos.y() - self._start.y()
        new_img = QImage(self._snapshot.size(), self._snapshot.format())
        new_img.fill(Qt.transparent)
        painter = QPainter(new_img)
        painter.drawImage(int(dx), int(dy), self._snapshot)
        painter.end()
        layer.image = new_img
        canvas.update()

    def on_release(self, canvas, pos):
        self._start    = None
        self._snapshot = None
        self._layer_ref = None


# ---------------------------------------------------------------------------
# Cuentagotas
# ---------------------------------------------------------------------------
class EyedropperTool(DrawingTool):
    name   = "eyedrop"
    cursor = Qt.CrossCursor

    def on_press(self, canvas, pos):
        # Leer del frame compuesto (todas las capas visibles)
        if not canvas.project:
            return
        frame = canvas.project.get_current_frame()
        if not frame:
            return
        
        # Generar la imagen compuesta (todas las capas visibles)
        composite_img = frame.composite()
        
        x, y = int(pos.x()), int(pos.y())
        if 0 <= x < composite_img.width() and 0 <= y < composite_img.height():
            color = QColor(composite_img.pixel(x, y))
            main_win = canvas.window()
            if hasattr(main_win, "color_picker"):
                main_win.color_picker.set_color(color)
            for tool_name, tool in canvas.tools.items():
                if hasattr(tool, "color"):
                    tool.color = QColor(color)

    def on_move(self, canvas, pos): pass
    def on_release(self, canvas, pos): pass


# ---------------------------------------------------------------------------
# Línea
# ---------------------------------------------------------------------------
class LineTool(DrawingTool):
    name = "line"

    def __init__(self, color=QColor(0, 0, 0), width=3):
        self.color  = color
        self.width  = width
        self._start = None

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._start = pos
        canvas.overlay_image.fill(Qt.transparent)

    def on_move(self, canvas, pos):
        if self._start is None:
            return
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(self._start, pos)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        if self._start is None:
            return
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self._start, pos)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._start = None


# ---------------------------------------------------------------------------
# Rectángulo
# ---------------------------------------------------------------------------
class RectangleTool(DrawingTool):
    name = "rect"

    def __init__(self, color=QColor(0, 0, 0), width=3, filled=False):
        self.color  = color
        self.width  = width
        self.filled = filled
        self._start = None

    def _make_rect(self, p1, p2) -> QRect:
        return QRect(
            min(p1.x(), p2.x()), min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()), abs(p2.y() - p1.y())
        )

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._start = pos
        canvas.overlay_image.fill(Qt.transparent)

    def on_move(self, canvas, pos):
        if self._start is None:
            return
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self._make_rect(self._start, pos)
        if self.filled:
            p.fillRect(rect, self.color)
        else:
            p.setPen(QPen(self.color, self.width))
            p.setBrush(Qt.NoBrush)
            p.drawRect(rect)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        if self._start is None:
            return
        rect = self._make_rect(self._start, pos)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            if self.filled:
                painter.fillRect(rect, self.color)
            else:
                painter.setPen(QPen(self.color, self.width))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._start = None


# ---------------------------------------------------------------------------
# Elipse
# ---------------------------------------------------------------------------
class EllipseTool(DrawingTool):
    name = "ellipse"

    def __init__(self, color=QColor(0, 0, 0), width=3, filled=False):
        self.color  = color
        self.width  = width
        self.filled = filled
        self._start = None

    def _make_rect(self, p1, p2) -> QRect:
        return QRect(
            min(p1.x(), p2.x()), min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()), abs(p2.y() - p1.y())
        )

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._start = pos
        canvas.overlay_image.fill(Qt.transparent)

    def on_move(self, canvas, pos):
        if self._start is None:
            return
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self._make_rect(self._start, pos)
        if self.filled:
            p.setPen(Qt.NoPen)
            p.setBrush(self.color)
        else:
            p.setPen(QPen(self.color, self.width))
            p.setBrush(Qt.NoBrush)
        p.drawEllipse(rect)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        if self._start is None:
            return
        rect = self._make_rect(self._start, pos)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            if self.filled:
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.color)
            else:
                painter.setPen(QPen(self.color, self.width))
                painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(rect)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._start = None


# ===========================================================================
# LAZOS DE RELLENO (pintan — no seleccionan)
# ===========================================================================

class LassoFillTool(DrawingTool):
    """Lazo libre que RELLENA la zona trazada."""
    name = "lasso_fill"

    def __init__(self, color=QColor(0, 120, 215)):
        self.color = color
        self._path = QPainterPath()

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._path = QPainterPath()
        self._path.moveTo(QPointF(pos))

    def on_move(self, canvas, pos):
        self._path.lineTo(QPointF(pos))
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setPen(QPen(self.color, 1, Qt.DashLine))
        p.drawPath(self._path)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        self._path.closeSubpath()
        solid = QColor(self.color.red(), self.color.green(), self.color.blue(), 255)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillPath(self._path, solid)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._path = QPainterPath()


class LassoFillRectTool(DrawingTool):
    """Lazo rectangular que RELLENA."""
    name = "lasso_fill_rect"

    def __init__(self, color=QColor(0, 120, 215)):
        self.color  = color
        self._start = None

    def _make_rect(self, p1, p2):
        return QRect(min(p1.x(), p2.x()), min(p1.y(), p2.y()),
                     abs(p2.x()-p1.x()), abs(p2.y()-p1.y()))

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._start = pos

    def on_move(self, canvas, pos):
        if not self._start:
            return
        rect = self._make_rect(self._start, pos)
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setPen(QPen(self.color, 1, Qt.DashLine))
        p.setBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 45))
        p.drawRect(rect)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        if not self._start:
            return
        rect  = self._make_rect(self._start, pos)
        solid = QColor(self.color.red(), self.color.green(), self.color.blue(), 255)
        def draw(painter):
            painter.fillRect(rect, solid)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._start = None


class LassoFillEllipseTool(DrawingTool):
    """Lazo elíptico que RELLENA."""
    name = "lasso_fill_ellipse"

    def __init__(self, color=QColor(0, 120, 215)):
        self.color  = color
        self._start = None

    def _make_rect(self, p1, p2):
        return QRect(min(p1.x(), p2.x()), min(p1.y(), p2.y()),
                     abs(p2.x()-p1.x()), abs(p2.y()-p1.y()))

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._start = pos

    def on_move(self, canvas, pos):
        if not self._start:
            return
        rect = self._make_rect(self._start, pos)
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self.color, 1, Qt.DashLine))
        p.setBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 45))
        p.drawEllipse(rect)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        if not self._start:
            return
        rect  = self._make_rect(self._start, pos)
        solid = QColor(self.color.red(), self.color.green(), self.color.blue(), 255)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(solid)
            painter.drawEllipse(rect)
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()
        self._start = None


# ===========================================================================
# HERRAMIENTAS DE SELECCIÓN REAL (seleccionan y permiten mover/deformar)
# ===========================================================================

class _SelectionToolBase(DrawingTool):
    """
    Base para herramientas de selección real.
    Gestiona: seleccionar → mover contenido → confirmar.
    """
    cursor = Qt.CrossCursor

    def __init__(self):
        self._start     = None
        self._selecting = False   # Fase 1: dibujando la selección
        self._moving    = False   # Fase 2: moviendo el contenido
        self._move_start   = None
        self._selection_snapshot: QImage | None = None  # recorte del contenido
        self._bg_snapshot:        QImage | None = None  # capa sin el recorte

    # -- Subclases implementan esto --
    def _compute_selection_region(self, canvas) -> QRect | None:
        """Devuelve el QRect/región activa de selección del canvas."""
        return canvas.selection_rect

    def _draw_overlay_preview(self, canvas, current_pos): pass

    # -- Fase 1: selección --
    def on_press(self, canvas, pos):
        sel = canvas.selection_rect
        # Si ya hay selección y el clic cae dentro → iniciar movimiento
        if sel and sel.contains(pos) and self._selection_snapshot:
            self._moving    = True
            self._move_start = pos
            self.cursor = Qt.SizeAllCursor
            canvas.setCursor(Qt.SizeAllCursor)
            return

        # Nueva selección
        self._selecting = True
        self._moving    = False
        self._selection_snapshot = None
        self._bg_snapshot        = None
        canvas.selection_rect    = None
        canvas.overlay_image.fill(Qt.transparent)
        self._start = pos

    def on_move(self, canvas, pos):
        if self._selecting:
            self._draw_overlay_preview(canvas, pos)
        elif self._moving and self._move_start and self._selection_snapshot:
            self._do_move_preview(canvas, pos)

    def on_release(self, canvas, pos):
        if self._selecting:
            self._selecting = False
            self._finalize_selection(canvas, pos)
        elif self._moving:
            self._moving = False
            self._commit_move(canvas)
            canvas.setCursor(Qt.CrossCursor)

    # -- Confirmar selección: recortar contenido --
    def _finalize_selection(self, canvas, pos):
        sel = canvas.selection_rect
        if not sel or sel.width() < 2 or sel.height() < 2:
            return
        layer = _active_layer(canvas)
        if not layer:
            return
        _push_undo(canvas)
        # Guardar recorte
        self._selection_snapshot = layer.image.copy(sel)
        # Borrar zona de la capa
        self._bg_snapshot = layer.image.copy()
        painter = QPainter(layer.image)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillRect(sel, Qt.transparent)
        painter.end()
        canvas.update()

    # -- Mover preview --
    def _do_move_preview(self, canvas, pos):
        if not self._bg_snapshot or not self._selection_snapshot:
            return
        dx = pos.x() - self._move_start.x()
        dy = pos.y() - self._move_start.y()
        layer = _active_layer(canvas)
        if not layer:
            return
        layer.image = self._bg_snapshot.copy()
        painter = QPainter(layer.image)
        old_sel = canvas.selection_rect
        painter.drawImage(old_sel.x() + dx, old_sel.y() + dy, self._selection_snapshot)
        painter.end()
        # Mover el rect de selección visualmente
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        moved_rect = old_sel.translated(dx, dy)
        p.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(moved_rect)
        p.end()
        canvas.update()

    # -- Confirmar movimiento --
    def _commit_move(self, canvas):
        # La imagen ya quedó modificada en _do_move_preview
        # Solo limpiar overlay y selección
        canvas.overlay_image.fill(Qt.transparent)
        canvas.selection_rect = None
        self._selection_snapshot = None
        self._bg_snapshot        = None
        canvas.update()


class RectSelectTool(_SelectionToolBase):
    name   = "select_rect"
    cursor = Qt.CrossCursor

    def _draw_overlay_preview(self, canvas, pos):
        if not self._start:
            return
        rect = QRect(
            min(self._start.x(), pos.x()), min(self._start.y(), pos.y()),
            abs(pos.x() - self._start.x()), abs(pos.y() - self._start.y())
        )
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
        p.setBrush(QColor(0, 120, 215, 25))
        p.drawRect(rect)
        p.end()
        canvas.selection_rect = rect
        canvas.update()


class LassoSelectTool(_SelectionToolBase):
    """Selección por lazo libre."""
    name   = "select_lasso"
    cursor = Qt.CrossCursor

    def __init__(self):
        super().__init__()
        self._path = QPainterPath()

    def on_press(self, canvas, pos):
        sel = canvas.selection_rect
        if sel and sel.contains(pos) and self._selection_snapshot:
            self._moving     = True
            self._move_start = pos
            canvas.setCursor(Qt.SizeAllCursor)
            return
        self._selecting = True
        self._moving    = False
        self._selection_snapshot = None
        self._bg_snapshot        = None
        canvas.selection_rect    = None
        canvas.overlay_image.fill(Qt.transparent)
        self._start = pos
        self._path  = QPainterPath()
        self._path.moveTo(QPointF(pos))

    def on_move(self, canvas, pos):
        if self._selecting:
            self._path.lineTo(QPointF(pos))
            canvas.overlay_image.fill(Qt.transparent)
            p = QPainter(canvas.overlay_image)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(0, 200, 255), 1, Qt.DashLine))
            p.setBrush(QColor(0, 120, 215, 20))
            p.drawPath(self._path)
            p.end()
            canvas.update()
        elif self._moving and self._move_start and self._selection_snapshot:
            self._do_move_preview(canvas, pos)

    def on_release(self, canvas, pos):
        if self._selecting:
            self._selecting = False
            self._finalize_selection(canvas, pos)
        elif self._moving:
            self._moving = False
            self._commit_move(canvas)
            canvas.setCursor(Qt.CrossCursor)

    def _finalize_selection(self, canvas, pos):
        self._path.closeSubpath()
        bounding = self._path.boundingRect().toRect()
        canvas.selection_rect = bounding
        layer = _active_layer(canvas)
        if not layer or bounding.width() < 2 or bounding.height() < 2:
            self._path = QPainterPath()
            return
        _push_undo(canvas)
        self._selection_snapshot = layer.image.copy(bounding)
        self._bg_snapshot        = layer.image.copy()
        painter = QPainter(layer.image)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillPath(self._path, Qt.transparent)
        painter.end()
        canvas.overlay_image.fill(Qt.transparent)
        self._path = QPainterPath()
        canvas.update()


class LassoMarqueeTool(DrawingTool):
    """
    Lazo de selección libre — muestra el contorno pero NO borra el contenido
    al finalizar. El recorte solo ocurre cuando el usuario arrastra la zona.
    """
    name   = "lasso_marquee"
    cursor = Qt.CrossCursor

    def __init__(self):
        self._selecting  = False
        self._moving     = False
        self._has_cut    = False
        self._move_start = None
        self._path       = QPainterPath()
        self._selection_snapshot: QImage | None = None
        self._bg_snapshot:        QImage | None = None

    # ------------------------------------------------------------------ dibujo
    def on_press(self, canvas, pos):
        sel = canvas.selection_rect
        if sel and sel.contains(pos):
            # Iniciar movimiento (el corte se hace al primer drag)
            self._moving     = True
            self._has_cut    = False
            self._move_start = pos
            canvas.setCursor(Qt.SizeAllCursor)
            return
        # Nueva selección
        self._selecting  = True
        self._moving     = False
        self._has_cut    = False
        self._selection_snapshot = None
        self._bg_snapshot        = None
        canvas.selection_rect    = None
        canvas.overlay_image.fill(Qt.transparent)
        self._path = QPainterPath()
        self._path.moveTo(QPointF(pos))

    def on_move(self, canvas, pos):
        if self._selecting:
            self._path.lineTo(QPointF(pos))
            canvas.overlay_image.fill(Qt.transparent)
            p = QPainter(canvas.overlay_image)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(50, 220, 100), 1, Qt.DashLine))
            p.setBrush(QColor(50, 220, 100, 18))
            p.drawPath(self._path)
            p.end()
            canvas.selection_rect = self._path.boundingRect().toRect()
            canvas.update()
        elif self._moving and self._move_start:
            self._do_move_preview(canvas, pos)

    def on_release(self, canvas, pos):
        if self._selecting:
            self._selecting = False
            self._path.closeSubpath()
            bounding = self._path.boundingRect().toRect()
            if bounding.width() < 2 or bounding.height() < 2:
                canvas.overlay_image.fill(Qt.transparent)
                canvas.selection_rect = None
                canvas.update()
                return
            canvas.selection_rect = bounding
            # Mostrar borde punteado sin borrar nada
            canvas.overlay_image.fill(Qt.transparent)
            p = QPainter(canvas.overlay_image)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(50, 220, 100), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawPath(self._path)
            p.end()
            canvas.update()
        elif self._moving:
            self._moving = False
            self._commit_move(canvas)
            canvas.setCursor(Qt.CrossCursor)

    # ------------------------------------------------------------------ mover
    def _do_move_preview(self, canvas, pos):
        if not self._has_cut:
            # Primera vez que se arrastra → recortar ahora
            layer = _active_layer(canvas)
            if not layer:
                return
            _push_undo(canvas)
            sel = canvas.selection_rect
            self._selection_snapshot = layer.image.copy(sel)
            # Borrar la zona seleccionada de la capa
            painter = QPainter(layer.image)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(self._path, Qt.transparent)
            painter.end()
            # El snapshot de fondo se toma DESPUÉS del corte, sin el contenido original
            self._bg_snapshot = layer.image.copy()
            self._has_cut = True

        if not self._bg_snapshot or not self._selection_snapshot:
            return
        dx  = pos.x() - self._move_start.x()
        dy  = pos.y() - self._move_start.y()
        layer = _active_layer(canvas)
        if not layer:
            return
        layer.image = self._bg_snapshot.copy()
        painter = QPainter(layer.image)
        old_sel = canvas.selection_rect
        painter.drawImage(old_sel.x() + dx, old_sel.y() + dy, self._selection_snapshot)
        painter.end()
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        moved = old_sel.translated(dx, dy)
        p.setPen(QPen(QColor(50, 220, 100), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(moved)
        p.end()
        canvas.update()

    def _commit_move(self, canvas):
        canvas.overlay_image.fill(Qt.transparent)
        canvas.selection_rect    = None
        self._selection_snapshot = None
        self._bg_snapshot        = None
        self._has_cut            = False
        canvas.update()


class EllipseSelectTool(_SelectionToolBase):
    """Selección elíptica."""
    name   = "select_ellipse"
    cursor = Qt.CrossCursor

    def _make_rect(self, p1, p2):
        return QRect(min(p1.x(), p2.x()), min(p1.y(), p2.y()),
                     abs(p2.x()-p1.x()), abs(p2.y()-p1.y()))

    def _draw_overlay_preview(self, canvas, pos):
        if not self._start:
            return
        rect = self._make_rect(self._start, pos)
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
        p.setBrush(QColor(0, 120, 215, 25))
        p.drawEllipse(rect)
        p.end()
        canvas.selection_rect = rect
        canvas.update()

    def _finalize_selection(self, canvas, pos):
        if not self._start:
            return
        rect  = self._make_rect(self._start, pos)
        canvas.selection_rect = rect
        layer = _active_layer(canvas)
        if not layer or rect.width() < 2 or rect.height() < 2:
            return
        _push_undo(canvas)
        path = QPainterPath()
        path.addEllipse(QRectF(rect))
        self._selection_snapshot = layer.image.copy(rect)
        self._bg_snapshot        = layer.image.copy()
        painter = QPainter(layer.image)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillPath(path, Qt.transparent)
        painter.end()
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()


# ---------------------------------------------------------------------------
# Pincel personalizado (punta importada de ABR / imagen)
# ---------------------------------------------------------------------------
class CustomBrushTool(DrawingTool):
    """Pincel con punta bitmap importada desde .abr (Photoshop) o imagen."""
    name   = "custom_brush"
    cursor = Qt.CrossCursor

    def __init__(self, tip: QImage, display_name: str = "Pincel",
                 color=QColor(0, 0, 0), size: int = 40,
                 opacity: int = 180, spacing: float = 0.25):
        self.tip          = tip
        self.display_name = display_name
        self.color        = color
        self.size         = size
        self.opacity      = opacity
        self.spacing      = spacing
        self._last_pos    = None

    # --- helpers ------------------------------------------------------------
    def _make_stamp(self, size: int, opacity: int) -> QPixmap:
        """Escala la punta y la tiñe con el color actual + opacidad."""
        scaled = self.tip.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        tw, th = scaled.width(), scaled.height()
        colored = QPixmap(tw, th)
        colored.fill(Qt.transparent)
        tp = QPainter(colored)
        tp.setCompositionMode(QPainter.CompositionMode_Source)
        tp.drawImage(0, 0, scaled)
        tp.setCompositionMode(QPainter.CompositionMode_SourceIn)
        c = QColor(self.color)
        # ✅ Aplicar opacidad DIRECTAMENTE en el stamp
        c.setAlpha(max(5, opacity))
        tp.fillRect(0, 0, tw, th, c)
        tp.end()
        return colored

    def _stamp_at(self, canvas, pos: QPoint, stamp: QPixmap, opacity: int):
        tw, th = stamp.width(), stamp.height()
        x = int(pos.x() - tw / 2)
        y = int(pos.y() - th / 2)
        _stamp = stamp

        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            # ✅ Ya la opacidad está en el stamp, pero aplicar por capas
            painter.drawPixmap(x, y, _stamp)
        _draw_on_layer(canvas, draw)

    # --- interface ----------------------------------------------------------
    def on_press(self, canvas, pos: QPoint):
        _push_undo(canvas)
        self._last_pos = pos
        pressure = getattr(canvas, '_pressure', 1.0)
        size     = max(2, int(self.size * pressure))
        opacity  = max(5, int(self.opacity * pressure))
        stamp    = self._make_stamp(size, opacity)
        self._stamp_at(canvas, pos, stamp, opacity)

    def on_move(self, canvas, pos: QPoint):
        if self._last_pos is None:
            self._last_pos = pos
            return
        pressure = getattr(canvas, '_pressure', 1.0)
        size     = max(2, int(self.size * pressure))
        opacity  = max(5, int(self.opacity * pressure))
        stamp    = self._make_stamp(size, opacity)
        step = max(1.0, size * self.spacing)
        dx   = pos.x() - self._last_pos.x()
        dy   = pos.y() - self._last_pos.y()
        dist = math.hypot(dx, dy)
        if dist >= step:
            steps = max(1, int(dist / step))
            for i in range(1, steps + 1):
                t  = i / steps
                ip = QPoint(int(self._last_pos.x() + dx * t),
                            int(self._last_pos.y() + dy * t))
                self._stamp_at(canvas, ip, stamp, opacity)
            self._last_pos = pos

    def on_release(self, canvas, pos: QPoint):
        self._last_pos = None


# ---------------------------------------------------------------------------
# Aerógrafo
# ---------------------------------------------------------------------------
class AirbrushTool(DrawingTool):
    name   = "airbrush"
    cursor = Qt.CrossCursor

    def __init__(self, color=QColor(0, 0, 0), size=60, opacity=60):
        self.color   = color
        self.size    = size
        self.opacity = opacity
        self._last   = None

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self._last = pos
        self._spray(canvas, pos)

    def on_move(self, canvas, pos):
        if self._last:
            self._line(canvas, self._last, pos)
            self._last = pos
        else:
            self._last = pos

    def on_release(self, canvas, pos):
        self._last = None

    def _spray(self, canvas, pos):
        pressure = getattr(canvas, '_pressure', 1.0)
        radius = max(2, int(self.size * pressure))
        opacity = max(5, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(c, radius, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(pos)
        _draw_on_layer(canvas, draw)

    def _line(self, canvas, p1, p2):
        pressure = getattr(canvas, '_pressure', 1.0)
        radius = max(2, int(self.size * pressure))
        opacity = max(5, int(self.opacity * pressure))
        c = QColor(self.color)
        c.setAlpha(opacity)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = math.hypot(dx, dy)
        step = max(1, radius // 2)
        steps = max(1, int(dist / step))
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            for i in range(steps + 1):
                t = i / steps
                # ✅ Opacidad interpolada para spray suave
                alpha = int(opacity * (0.5 + 0.5 * t))  # Empieza más suave
                c_fade = QColor(self.color)
                c_fade.setAlpha(alpha)
                painter.setPen(QPen(c_fade, radius, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                x = int(p1.x() + dx * t)
                y = int(p1.y() + dy * t)
                painter.drawPoint(QPoint(x, y))
        _draw_on_layer(canvas, draw)


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------
class TextTool(DrawingTool):
    name   = "text"
    cursor = Qt.IBeamCursor

    def __init__(self, color=QColor(0, 0, 0), font_size=24):
        self.color     = color
        self.font_size = font_size

    def on_press(self, canvas, pos):
        from PySide6.QtWidgets import QInputDialog
        txt, ok = QInputDialog.getText(canvas, "Texto", "Escribí el texto:")
        if ok and txt:
            _push_undo(canvas)
            def draw(painter):
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(self.color)
                painter.setFont(QFont("Arial", self.font_size))
                painter.drawText(pos, txt)
            _draw_on_layer(canvas, draw)

    def on_move(self, canvas, pos): pass
    def on_release(self, canvas, pos): pass


# ---------------------------------------------------------------------------
# Difuminar (blur brush) - MOVIDO A core/tools/special/blur.py
# ---------------------------------------------------------------------------
# class BlurTool(DrawingTool):
#     name   = "blur"
#     cursor = Qt.CrossCursor
# 
#     def __init__(self, radius=15):
#         self.radius = radius
#         self._pushed = False
# 
#     def on_press(self, canvas, pos):
#         _push_undo(canvas)
#         self._pushed = True
#         self._apply(canvas, pos)
# 
#     def on_move(self, canvas, pos):
#         self._apply(canvas, pos)
# 
#     def on_release(self, canvas, pos):
#         self._pushed = False
# 
#     def _apply(self, canvas, pos):
#         layer = _active_layer(canvas)
#         if not layer or layer.locked:
#             return
#         x, y  = int(pos.x()), int(pos.y())
#         r     = self.radius
#         img   = layer.image
#         w, h  = img.width(), img.height()
#         x1, y1 = max(0, x - r), max(0, y - r)
#         x2, y2 = min(w, x + r), min(h, y + r)
#         if x2 <= x1 or y2 <= y1:
#             return
#         region  = img.copy(x1, y1, x2 - x1, y2 - y1)
#         small   = region.scaled(max(1, (x2-x1)//4), max(1, (y2-y1)//4),
#                                 Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
#         blurred = small.scaled(x2-x1, y2-y1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
#         painter = QPainter(img)
#         painter.drawImage(x1, y1, blurred)
#         painter.end()
#         canvas.update()
# ---------------------------------------------------------------------------
# Pincel de Curva Suave (Tipo Paint) - MEJORADO
# ---------------------------------------------------------------------------
class CurveTool(DrawingTool):
    """Dibuja curvas fluidas en tiempo real usando Catmull-Rom, suavizando el trazo."""
    name = "curve"

    def __init__(self, color=QColor(0, 0, 0), width=3):
        self.color = color
        self.width = width
        self.points = []

    def on_press(self, canvas, pos):
        _push_undo(canvas)
        self.points = [QPointF(pos)]
        canvas.overlay_image.fill(Qt.transparent)

    def on_move(self, canvas, pos):
        self.points.append(QPointF(pos))
        
        # Dibujamos en el overlay para que veas la curva mientras movés el mouse
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        path = self._build_smooth_path()
        p.drawPath(path)
        p.end()
        canvas.update()

    def on_release(self, canvas, pos):
        # Al soltar el mouse, pasamos la curva del overlay a la capa real
        def draw(painter):
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(self._build_smooth_path())
            
        _draw_on_layer(canvas, draw)
        canvas.overlay_image.fill(Qt.transparent)
        self.points = []
        canvas.update()

    def _build_smooth_path(self):
        """Calcula curva suave usando Catmull-Rom spline (interpolación de verdad)."""
        path = QPainterPath()
        if len(self.points) < 2:
            return path
        
        # Necesitamos al menos 2 puntos para empezar
        if len(self.points) < 3:
            path.moveTo(self.points[0])
            path.lineTo(self.points[-1])
            return path
        
        path.moveTo(self.points[0])
        
        # Usar cubicTo para Bezier cúbica verdadera
        # Cada segmento conecta 2 puntos de control
        for i in range(len(self.points) - 1):
            p0 = self.points[i]
            p1 = self.points[i + 1]
            
            # Calcular puntos de control para Bezier cúbica
            # Usando Catmull-Rom: los puntos de control están a 1/3 del camino
            if i > 0:
                p_prev = self.points[i - 1]
            else:
                p_prev = p0
            
            if i < len(self.points) - 2:
                p_next = self.points[i + 2]
            else:
                p_next = p1
            
            # Puntos de control de Catmull-Rom
            ctrl1_x = p0.x() + (p_next.x() - p_prev.x()) / 6.0
            ctrl1_y = p0.y() + (p_next.y() - p_prev.y()) / 6.0
            
            ctrl2_x = p1.x() - (p_next.x() - p_prev.x()) / 6.0
            ctrl2_y = p1.y() - (p_next.y() - p_prev.y()) / 6.0
            
            path.cubicTo(QPointF(ctrl1_x, ctrl1_y),
                        QPointF(ctrl2_x, ctrl2_y),
                        p1)
        
        return path