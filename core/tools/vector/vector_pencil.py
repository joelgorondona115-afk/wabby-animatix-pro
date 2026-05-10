# core/tools/vector/vector_pencil.py
"""Vector pencil tool for clean lineart - CORREGIDO."""

from PySide6.QtGui import QPainterPath, QColor
from PySide6.QtCore import Qt, QPoint, QPointF

from core.tools.base import DrawingTool


class VectorPencilTool(DrawingTool):
    """Draws vector strokes on VectorLayer."""

    name = "vector_pencil"
    cursor = Qt.CrossCursor

    def __init__(self, color: QColor = None, width: float = 2.0, opacity: int = 255):
        if color is None:
            color = QColor(0, 0, 0)
        self.color = color
        self.width = width
        self.opacity = opacity
        self._drawing = False
        self._current_stroke = None

    def _get_vector_layer(self, canvas):
        """Get active vector layer."""
        if not canvas.project:
            print("[DEBUG] No hay proyecto")
            return None
        frame = canvas.project.get_current_frame()
        idx = frame.current_layer_idx
        print(f"[DEBUG] Índice de capa activa: {idx}, total capas: {len(frame.layers)}")
        if idx < 0 or idx >= len(frame.layers):
            print(f"[DEBUG] Índice fuera de rango")
            return None
        layer = frame.layers[idx]
        is_vec = hasattr(layer, 'is_vector') and layer.is_vector
        print(f"[DEBUG] Capa: {layer.name}, is_vector={is_vec}")
        if is_vec:
            return layer
        print(f"[DEBUG] La capa activa NO es vectorial")
        return None

    def on_press(self, canvas, pos: QPoint) -> None:
        """Start new stroke."""
        print(f"[PENCIL] on_press en {pos.x()}, {pos.y()}")
        layer = self._get_vector_layer(canvas)
        if layer is None or getattr(layer, 'locked', False):
            print(f"[PENCIL] Capa bloqueada o None, saliendo")
            return

        print(f"[PENCIL] Creando stroke con color={self.color.name()}, width={self.width}")
        if hasattr(canvas.project.get_current_frame(), 'push_undo'):
            canvas.project.get_current_frame().push_undo()

        self._drawing = True
        pos_f = QPointF(pos.x(), pos.y())
        self._current_stroke = layer.start_new_stroke(
            pos_f, self.color, self.width, self.opacity
        )
        print(f"[PENCIL] Stroke creado. Total strokes en capa: {len(layer.strokes)}")
        canvas.update()

    def on_move(self, canvas, pos: QPoint) -> None:
        """Extend current stroke."""
        if not self._drawing or self._current_stroke is None:
            return
        layer = self._get_vector_layer(canvas)
        if layer is None:
            return
        pos_f = QPointF(pos.x(), pos.y())
        layer.extend_last_stroke_smooth(pos_f)
        canvas.update()

    def on_release(self, canvas, pos: QPoint) -> None:
        """Finish stroke."""
        print(f"[PENCIL] on_release en {pos.x()}, {pos.y()}, drawing={self._drawing}")
        if self._drawing and self._current_stroke:
            layer = self._get_vector_layer(canvas)
            if layer:
                pos_f = QPointF(pos.x(), pos.y())
                layer.extend_last_stroke_smooth(pos_f)
                print(f"[PENCIL] Stroke finalizado. Total: {len(layer.strokes)}")
        self._drawing = False
        self._current_stroke = None
        canvas.update()
