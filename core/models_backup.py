# core/models.py
"""Animation models with OOP."""

from collections import deque
from PySide6.QtCore import QObject, Signal, Property, Qt
from PySide6.QtGui import QImage, QPainter, QColor


class AnimationLayer(QObject):
    """OOP Layer with encapsulation and signals."""
    
    visible_changed = Signal(bool)
    opacity_changed = Signal(int)
    name_changed = Signal(str)
    locked_changed = Signal(bool)
    
    def __init__(self, size: tuple, name: str = "Layer", parent=None):
        super().__init__(parent)
        self._name = name
        self._size = size
        self._image = QImage(size[0], size[1], QImage.Format_ARGB32_Premultiplied)
        self._image.fill(QColor(0, 0, 0, 0))
        self._opacity = 255
        self._visible = True
        self._locked = False
    
    # Properties
    @Property(str)
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str):
        if self._name != value:
            self._name = value
            self.name_changed.emit(value)
    
    @Property(bool)
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        if self._visible != value:
            self._visible = value
            self.visible_changed.emit(value)
    
    @Property(int)
    def opacity(self) -> int:
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: int):
        value = max(0, min(255, value))
        if self._opacity != value:
            self._opacity = value
            self.opacity_changed.emit(value)
    
    @Property(bool)
    def locked(self) -> bool:
        return self._locked
    
    @locked.setter
    def locked(self, value: bool):
        if self._locked != value:
            self._locked = value
            self.locked_changed.emit(value)
    
    @Property(QImage)
    def image(self) -> QImage:
        return self._image
    
    @image.setter
    def image(self, value: QImage):
        self._image = value
    
    @Property(tuple)
    def size(self) -> tuple:
        return self._size
    
    def copy(self) -> 'AnimationLayer':
        """Create a copy of this layer."""
        new_layer = AnimationLayer(self._size, self._name + " (copy)")
        new_layer._image = self._image.copy()
        new_layer._opacity = self._opacity
        new_layer._visible = self._visible
        new_layer._locked = self._locked
        return new_layer
    
    def clear(self):
        """Clear the layer."""
        self._image.fill(QColor(0, 0, 0, 0))


class AnimationFrame(QObject):
    """OOP Frame containing layers."""
    
    current_layer_changed = Signal(int)
    
    def __init__(self, size: tuple, parent=None):
        super().__init__(parent)
        self._size = size
        self._layers = [AnimationLayer(size, "Capa 1")]
        self._current_layer_idx = 0
        self._duration_ms = 100
        self._undo_stack = deque(maxlen=40)
        self._redo_stack = deque(maxlen=40)
    
    @Property(list)
    def layers(self) -> list:
        return self._layers
    
    @Property(int)
    def current_layer_idx(self) -> int:
        return self._current_layer_idx
    
    @current_layer_idx.setter
    def current_layer_idx(self, value: int):
        if 0 <= value < len(self._layers):
            self._current_layer_idx = value
            self.current_layer_changed.emit(value)
    
    @Property(AnimationLayer)
    def current_layer(self) -> AnimationLayer:
        return self._layers[self._current_layer_idx]
    
@Property(int)
    def duration_ms(self) -> int:
        return self._duration_ms

    @duration_ms.setter
    def duration_ms(self, value: int):
        self._duration_ms = value

    def copy_from(self, other):
        """Copy layers from another frame."""
        self._layers = [layer.copy() for layer in other._layers]
        self._current_layer_idx = other._current_layer_idx
    
    @Property(object)
    def composite(self) -> object:
        """Get composited image of all visible layers."""
        from PySide6.QtGui import QImage, QPainter
        w, h = self._size
        result = QImage(w, h, QImage.Format_ARGB32)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        for layer in self._layers:
            if layer.visible:
                painter.drawImage(0, 0, layer.image)
        painter.end()
        return result
    
    # Methods
    def add_layer(self, name: str = None) -> AnimationLayer:
        """Add a new layer."""
        if name is None:
            name = f"Capa {len(self._layers) + 1}"
        layer = AnimationLayer(self._size, name)
        self._layers.append(layer)
        return layer
    
    def remove_layer(self, idx: int) -> bool:
        """Remove layer by index."""
        if len(self._layers) <= 1:
            return False
        if 0 <= idx < len(self._layers):
            self._layers.pop(idx)
            if self._current_layer_idx >= len(self._layers):
                self._current_layer_idx = len(self._layers) - 1
            return True
        return False
    
    def move_layer(self, from_idx: int, to_idx: int) -> bool:
        """Move layer from one index to another."""
        if not (0 <= from_idx < len(self._layers) and 0 <= to_idx < len(self._layers)):
            return False
        layer = self._layers.pop(from_idx)
        self._layers.insert(to_idx, layer)
        return True
    
    def push_undo(self):
        """Save current state for undo."""
        snapshot = [layer._image.copy() for layer in self._layers]
        self._undo_stack.append(snapshot)
        self._redo_stack.clear()
    
    def undo(self) -> bool:
        """Undo last action."""
        if not self._undo_stack:
            return False
        self._redo_stack.append([layer._image.copy() for layer in self._layers])
        snapshot = self._undo_stack.pop()
        for layer, img in zip(self._layers, snapshot):
            layer._image = img
        return True
    
    def redo(self) -> bool:
        """Redo last undone action."""
        if not self._redo_stack:
            return False
        self._undo_stack.append([layer._image.copy() for layer in self._layers])
        snapshot = self._redo_stack.pop()
        for layer, img in zip(self._layers, snapshot):
            layer._image = img
        return True
    
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0
    
    def thumbnail(self, w: int, h: int) -> 'QImage':
        """Generate thumbnail of first visible layer."""
        from PySide6.QtGui import QImage
        thumb = QImage(w, h, QImage.Format_ARGB32)
        thumb.fill(0)
        
        # Find first visible layer
        for layer in self._layers:
            if layer._visible:
                # Scale layer to thumbnail
                scaled = layer._image.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p = QPainter(thumb)
                p.drawImage(0, 0, scaled)
                p.end()
                break
        
        return thumb


class AnimationProject(QObject):
    """OOP Project containing frames."""
    
    current_frame_changed = Signal(int)
    frame_count_changed = Signal(int)
    
    def __init__(self, width: int, height: int, name: str = "Project", parent=None):
        super().__init__(parent)
        self._name = name
        self._size = (width, height)
        self._frames = [AnimationFrame((width, height))]
        self._current_frame_idx = 0
        self._bg_mode = "Transparente"
        self._fps = 24
        self._play_mode = "Loop"
        self._onion_skin = False
        self._onion_opacity = 128
    
    @Property(str)
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value
    
    @Property(int)
    def fps(self) -> int:
        return self._fps
    
    @fps.setter
    def fps(self, value: int):
        self._fps = max(1, min(60, value))
    
    @Property(str)
    def bg_mode(self) -> str:
        return self._bg_mode
    
    @bg_mode.setter
    def bg_mode(self, value: str):
        self._bg_mode = value
    
    @Property(str)
    def play_mode(self) -> str:
        return self._play_mode
    
    @play_mode.setter
    def play_mode(self, value: str):
        self._play_mode = value
    
    @Property(bool)
    def onion_skin(self) -> bool:
        return self._onion_skin
    
    @onion_skin.setter
    def onion_skin(self, value: bool):
        self._onion_skin = value
    
    @Property(int)
    def onion_opacity(self) -> int:
        return self._onion_opacity
    
    @onion_opacity.setter
    def onion_opacity(self, value: int):
        self._onion_opacity = value
    
    @Property(list)
    def frames(self) -> list:
        return self._frames
    
    @Property(int)
    def current_frame_idx(self) -> int:
        return self._current_frame_idx
    
    @current_frame_idx.setter
    def current_frame_idx(self, value: int):
        if 0 <= value < len(self._frames):
            self._current_frame_idx = value
            self.current_frame_changed.emit(value)
    
    @Property(AnimationFrame)
    def current_frame(self) -> AnimationFrame:
        return self._frames[self._current_frame_idx]
    
    # Methods
    def add_frame(self) -> AnimationFrame:
        """Add a new frame."""
        frame = AnimationFrame(self._size)
        self._frames.append(frame)
        self.frame_count_changed.emit(len(self._frames))
        return frame
    
def insert_frame(self, idx: int) -> AnimationFrame:
        """Insert frame at index."""
        frame = AnimationFrame(self._size)
        frame.copy_from(self._frames[idx - 1] if idx > 0 else self._frames[0])
        self._frames.insert(idx, frame)
        self.frame_count_changed.emit(len(self._frames))
        return frame

    def remove_frame(self, idx: int) -> bool:
        """Remove frame at index."""
        if len(self._frames) <= 1:
            return False
        self._frames.pop(idx)
        if self._current_frame_idx >= len(self._frames):
            self._current_frame_idx = len(self._frames) - 1
        self.frame_count_changed.emit(len(self._frames))
        return True
    
    def next_frame(self):
        """Go to next frame."""
        if self._current_frame_idx < len(self._frames) - 1:
            self._current_frame_idx += 1
            self.current_frame_changed.emit(self._current_frame_idx)
    
    def prev_frame(self):
        """Go to previous frame."""
        if self._current_frame_idx > 0:
            self._current_frame_idx -= 1
            self.current_frame_changed.emit(self._current_frame_idx)
    
    def get_current_frame(self) -> AnimationFrame:
        return self._frames[self._current_frame_idx]
    
    def move_frame(self, from_idx: int, to_idx: int) -> bool:
        """Reorder frame from one index to another."""
        if 0 <= from_idx < len(self._frames) and 0 <= to_idx < len(self._frames):
            frame = self._frames.pop(from_idx)
            self._frames.insert(to_idx, frame)
            if self._current_frame_idx == from_idx:
                self._current_frame_idx = to_idx
            return True
        return False