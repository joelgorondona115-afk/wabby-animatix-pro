# core/vector_layer.py
"""Vector layer for clean animation lineart - CORREGIDO."""

from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QImage
from PySide6.QtCore import Qt


_layer_id = 0


class VectorStroke:
    """A single vector stroke with styling."""

    def __init__(self, path: QPainterPath, color: QColor, width: float, opacity: int = 255):
        self.path = path
        self.color = QColor(color)
        self.width = width
        self.opacity = opacity
        self.selected = False

    def draw(self, painter: QPainter) -> None:
        """Draw stroke with antialiasing."""
        c = QColor(self.color)
        c.setAlpha(self.opacity)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(c, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(self.path)

    def copy(self) -> 'VectorStroke':
        """Create a copy of this stroke."""
        return VectorStroke(QPainterPath(self.path), self.color, self.width, self.opacity)


class VectorLayer:
    """Layer that stores vector strokes instead of raster pixels."""

    def __init__(self, size: tuple, name: str = "Capa Vectorial"):
        global _layer_id
        _layer_id += 1
        self.id = _layer_id
        self.name = name
        self.visible = True
        self.locked = False
        self.opacity = 255
        self.strokes: list[VectorStroke] = []
        self.size = size
        self.is_vector = True
        self.image = QImage(size[0], size[1], QImage.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.transparent)

    def add_stroke(self, path: QPainterPath, color: QColor, width: float, opacity: int = 255) -> VectorStroke:
        """Add a new stroke to the layer."""
        stroke = VectorStroke(path, color, width, opacity)
        self.strokes.append(stroke)
        return stroke

    def start_new_stroke(self, pos, color: QColor, width: float, opacity: int = 255) -> VectorStroke:
        """Start a new stroke at given position."""
        path = QPainterPath()
        path.moveTo(pos)
        return self.add_stroke(path, color, width, opacity)

    def extend_last_stroke(self, pos) -> None:
        """Extend the last stroke with a straight line."""
        if self.strokes and pos:
            self.strokes[-1].path.lineTo(pos)

    def extend_last_stroke_smooth(self, pos) -> None:
        """Extend the last stroke smoothly."""
        if self.strokes and pos:
            self.strokes[-1].path.lineTo(pos)

    def clear(self) -> None:
        """Clear all strokes."""
        self.strokes.clear()

    def draw_all(self, painter: QPainter) -> None:
        """Draw all strokes with current opacity."""
        painter.save()
        painter.setOpacity(self.opacity / 255.0)
        for stroke in self.strokes:
            stroke.draw(painter)
        painter.restore()

    def render_to_image(self, image: QImage) -> None:
        """Render all strokes to a QImage."""
        p = QPainter(image)
        self.draw_all(p)
        p.end()

    def undo_snapshot(self) -> list[VectorStroke]:
        """Create snapshot for undo."""
        return [s.copy() for s in self.strokes]

    def restore_snapshot(self, snapshot: list[VectorStroke]) -> None:
        """Restore from snapshot for undo."""
        self.strokes = [s.copy() for s in snapshot]

    def copy(self) -> 'VectorLayer':
        """Create a copy of this layer."""
        new_layer = VectorLayer(self.size, self.name)
        new_layer.visible = self.visible
        new_layer.locked = self.locked
        new_layer.opacity = self.opacity
        new_layer.strokes = [s.copy() for s in self.strokes]
        new_layer.image = self.image.copy()
        return new_layer
