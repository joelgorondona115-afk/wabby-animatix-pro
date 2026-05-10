# core/tools/fill/fill.py
"""Fill tools - Bucket fill and Eyedropper."""

from PySide6.QtGui import QColor, QRegion, QPainterPath, QPainter
from PySide6.QtCore import Qt, QPoint, QTimer

from core.tools.base import DrawingTool, _active_layer, _push_undo


# ---------------------------------------------------------------------------
# Flood Fill Algorithm
# ---------------------------------------------------------------------------
class FloodFillAlgorithm:
    """Flood fill algorithm with clipping support."""

    def __init__(self, max_pixels: int = 100000):
        self.max_pixels = max_pixels
        self.pixels_filled = 0

    def fill(self, image, start_pos: QPoint, fill_color: QColor, 
             tolerance: int, limit_region: QRegion = None) -> tuple[bool, str]:
        """Execute flood fill."""
        x_start, y_start = int(start_pos.x()), int(start_pos.y())
        width, height = image.width(), image.height()

        if not (0 <= x_start < width and 0 <= y_start < height):
            return False, "Posición fuera de la imagen"

        target_color = image.pixelColor(x_start, y_start)

        if target_color.alpha() == 0:
            return False, "Área transparente"

        if target_color.red() == fill_color.red() and \
           target_color.green() == fill_color.green() and \
           target_color.blue() == fill_color.blue() and \
           target_color.alpha() == fill_color.alpha():
            return False, "El color ya es el mismo"

        self.pixels_filled = 0
        from collections import deque
        queue = deque([(x_start, y_start)])
        visited = set()

        r_target = target_color.red()
        g_target = target_color.green()
        b_target = target_color.blue()

        while queue and self.pixels_filled < self.max_pixels:
            x, y = queue.popleft()

            if (x, y) in visited:
                continue
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            if limit_region and not limit_region.contains(x, y):
                visited.add((x, y))
                continue

            current = image.pixelColor(x, y)
            if current.alpha() == 0:
                visited.add((x, y))
                continue

            diff = (abs(current.red() - r_target) +
                    abs(current.green() - g_target) +
                    abs(current.blue() - b_target)) / 3

            if diff <= tolerance:
                image.setPixelColor(x, y, fill_color)
                visited.add((x, y))
                self.pixels_filled += 1
                queue.append((x + 1, y))
                queue.append((x - 1, y))
                queue.append((x, y + 1))
                queue.append((x, y - 1))

        if self.pixels_filled >= self.max_pixels:
            return False, f"Límite ({self.pixels_filled}/{self.max_pixels})"

        return True, f"OK ({self.pixels_filled} pixels)"


# ---------------------------------------------------------------------------
# Fill Tool Base
# ---------------------------------------------------------------------------
class FillToolBase(DrawingTool):
    """Base class for fill tools."""

    def __init__(self, color: QColor = None, tolerance: int = 30):
        if color is None:
            color = QColor(0, 0, 0)
        self.color = color
        self.tolerance = tolerance
        self._algorithm = FloodFillAlgorithm()
        self._dash_offset = 0
        self._is_drawing = False
        self._current_shape_fn = None
        self._animation_timer = QTimer()
        self._path = QPainterPath()
        self._start = None

    def _start_animation(self, canvas):
        self._is_drawing = True
        self._animation_timer.timeout.connect(lambda: self._on_animation_tick(canvas))
        self._animation_timer.start(50)

    def _stop_animation(self):
        self._is_drawing = False
        self._animation_timer.stop()
        self._current_shape_fn = None

    def _on_animation_tick(self, canvas):
        self._dash_offset -= 2
        if self._dash_offset < -20:
            self._dash_offset = 0
        if self._current_shape_fn:
            self._draw_marching_ants(canvas, self._current_shape_fn)

    def _draw_marching_ants(self, canvas, shape_fn):
        self._current_shape_fn = shape_fn
        canvas.overlay_image.fill(Qt.transparent)
        p = QPainter(canvas.overlay_image)
        p.setRenderHint(QPainter.Antialiasing)
        from PySide6.QtGui import QPen
        pen = QPen(self.color, 2)
        pen.setStyle(Qt.DashLine)
        pen.setDashOffset(self._dash_offset)
        p.setPen(pen)
        shape_fn(p)
        p.end()
        canvas.update()

    def _clear_overlay(self, canvas):
        self._stop_animation()
        canvas.overlay_image.fill(Qt.transparent)
        canvas.update()

    def _cancel(self, canvas):
        self._clear_overlay(canvas)
        self._path = QPainterPath()
        self._start = None


# ---------------------------------------------------------------------------
# Fill Tool (Bucket)
# ---------------------------------------------------------------------------
class FillTool(FillToolBase):
    """
    Fill tool (bucket) with lasso clipping.
    
    Rules:
    - Click outside lasso → nothing
    - Click inside lasso → fill limited by lasso
    - No lasso → normal fill
    """
    name = "fill"
    cursor = Qt.CrossCursor

    def set_color(self, color: QColor):
        self.color = color

    def set_tolerance(self, tolerance: int):
        self.tolerance = max(0, min(255, tolerance))

    def _is_point_in_selection(self, canvas, pos: QPoint) -> bool:
        if not getattr(canvas, 'selection_active', False):
            return True
        selection_path = getattr(canvas, 'selection_path', None)
        selection_rect = getattr(canvas, 'selection_rect', None)
        if selection_path:
            return selection_path.contains(pos)
        elif selection_rect:
            return selection_rect.contains(pos)
        return True

    def _get_limit_region(self, canvas) -> QRegion:
        if not getattr(canvas, 'selection_active', False):
            return None
        selection_path = getattr(canvas, 'selection_path', None)
        selection_rect = getattr(canvas, 'selection_rect', None)
        if selection_path:
            return QRegion(selection_path.toSubpathPolygon())
        elif selection_rect:
            return QRegion(selection_rect)
        return None

    def on_press(self, canvas, pos):
        layer = _active_layer(canvas)
        if not layer:
            self._show_warning(canvas, "No hay capa activa")
            return

        # Check if there's an active selection (lasso)
        has_selection = getattr(canvas, 'selection_active', False)
        
        # With lasso active: Bypass ALL transparency checks
        # The lasso IS the boundary - no validation needed
        if not has_selection:
            # Without lazo: verify there's content below
            test_pixel = layer.image.pixelColor(pos)
            if test_pixel.alpha() == 0:
                self._show_warning(canvas, "Área transparente")
                return
        
        # If selection exists, clear it (Paint and Clean mode)
        if has_selection:
            canvas.clear_selection()
        
        _push_undo(canvas)

        # Fill the area - no limits, works anywhere
        success, message = self._algorithm.fill(
            layer.image, pos, self.color, self.tolerance, None
        )

        if not success:
            _push_undo(canvas)
            self._show_warning(canvas, message)

        canvas.update()

    def _show_warning(self, canvas, message: str):
        mw = canvas.window()
        if hasattr(mw, 'statusBar'):
            mw.statusBar().showMessage(message, 3000)


# ---------------------------------------------------------------------------
# Eyedropper Tool
# ---------------------------------------------------------------------------
class EyedropperTool(DrawingTool):
    """Color picker tool that reads from the visible canvas composite."""
    name = "eyedrop"
    cursor = Qt.CrossCursor

    def __init__(self):
        self._preview_widget = None
        self._current_pos = None

    def _get_composite_at(self, canvas, pos: QPoint) -> QColor:
        """Read color from the fully composited canvas at given position."""
        if not canvas.project:
            return QColor(0, 0, 0)

        composite = canvas.project.get_current_frame().composite()
        w, h = composite.width(), composite.height()

        if 0 <= pos.x() < w and 0 <= pos.y() < h:
            return composite.pixelColor(pos)
        return QColor(0, 0, 0)

    def _create_preview(self, canvas):
        """Create floating color preview widget."""
        if self._preview_widget:
            return
        from PySide6.QtWidgets import QLabel
        self._preview_widget = QLabel()
        self._preview_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self._preview_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._preview_widget.setFixedSize(50, 50)
        self._preview_widget.setStyleSheet(
            "background: transparent; border: 2px solid #555; border-radius: 6px;"
        )
        self._preview_widget.show()

    def _update_preview(self, canvas, pos, color: QColor):
        """Update preview widget position and color."""
        if not self._preview_widget:
            self._create_preview(canvas)
            if not self._preview_widget:
                return

        hex_color = color.name()
        r, g, b = color.red(), color.green(), color.blue()
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "#000" if brightness > 128 else "#fff"

        self._preview_widget.setStyleSheet(
            f"background: {hex_color}; border: 2px solid #555; "
            f"border-radius: 6px; color: {text_color}; font-size: 8px; "
            f"font-weight: bold; text-align: center; padding: 2px;"
        )
        self._preview_widget.setText(f"#{hex_color[1:].upper()}")

        # Position near cursor but not under it
        cursor_pos = canvas.mapToGlobal(canvas.mapFromGlobal(canvas.cursor().pos()))
        offset_x = 20
        offset_y = 20
        screen = canvas.screen().geometry() if canvas.screen() else None
        if screen and cursor_pos.x() + offset_x + 50 > screen.right():
            offset_x = -70
        if cursor_pos.y() + offset_y + 50 > screen.bottom():
            offset_y = -70
        self._preview_widget.move(cursor_pos.x() + offset_x, cursor_pos.y() + offset_y)

    def _destroy_preview(self):
        if self._preview_widget:
            self._preview_widget.deleteLater()
            self._preview_widget = None

    def on_press(self, canvas, pos):
        color = self._get_composite_at(canvas, pos)

        mw = canvas.window()
        if hasattr(mw, 'color_picker'):
            mw.color_picker.set_color(color)

        tool = canvas.tools.get(canvas.current_tool)
        if tool and hasattr(tool, 'color'):
            tool.color = color

        self._destroy_preview()

    def on_move(self, canvas, pos):
        if not canvas.project:
            return
        color = self._get_composite_at(canvas, pos)
        self._update_preview(canvas, pos, color)

    def on_release(self, canvas, pos):
        self._destroy_preview()
