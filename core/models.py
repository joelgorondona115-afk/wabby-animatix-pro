# core/models.py
"""Lightweight animation models."""

from collections import deque
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt

from core.vector_layer import VectorLayer


_layer_id = 0

class AnimationLayer:
    def __init__(self, size: tuple, name: str = "Capa 1"):
        global _layer_id
        _layer_id += 1
        self.id = _layer_id
        self.name = name
        self.visible = True
        self.locked = False
        self.opacity = 255
        self.image = QImage(size[0], size[1], QImage.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.transparent)
        # Group support
        self.is_group = False
        self.children = []  # List of AnimationLayer/VectorLayer if is_group
        self.expanded = False  # UI state: is the group expanded?


class AnimationFrame:
    def __init__(self, size: tuple):
        self.size = size
        self.layers = [AnimationLayer(size, "Capa 1")]
        self.current_layer_idx = 0
        self.duration_ms = 100
        self._undo_stack = deque(maxlen=20)
        self._redo_stack = deque(maxlen=20)

    def push_undo(self):
        snapshot = []
        for layer in self.layers:
            if hasattr(layer, 'is_vector') and layer.is_vector:
                snapshot.append(('vector', layer.undo_snapshot(), layer.image.copy()))
            else:
                snapshot.append(('raster', layer.image.copy()))
        self._undo_stack.append(snapshot)
        self._redo_stack.clear()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        current_snapshot = []
        for layer in self.layers:
            if hasattr(layer, 'is_vector') and layer.is_vector:
                current_snapshot.append(('vector', layer.undo_snapshot(), layer.image.copy()))
            else:
                current_snapshot.append(('raster', layer.image.copy()))
        self._redo_stack.append(current_snapshot)
        snapshot = self._undo_stack.pop()
        for layer, data in zip(self.layers, snapshot):
            layer_type, *rest = data
            if layer_type == 'vector':
                strokes, image = rest
                layer.restore_snapshot(strokes)
                layer.image = image
            else:
                layer.image = rest[0]
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        current_snapshot = []
        for layer in self.layers:
            if hasattr(layer, 'is_vector') and layer.is_vector:
                current_snapshot.append(('vector', layer.undo_snapshot(), layer.image.copy()))
            else:
                current_snapshot.append(('raster', layer.image.copy()))
        self._undo_stack.append(current_snapshot)
        snapshot = self._redo_stack.pop()
        for layer, data in zip(self.layers, snapshot):
            layer_type, *rest = data
            if layer_type == 'vector':
                strokes, image = rest
                layer.restore_snapshot(strokes)
                layer.image = image
            else:
                layer.image = rest[0]
        return True

    def add_layer(self, name: str = None) -> AnimationLayer:
        n = len(self.layers) + 1
        layer = AnimationLayer(self.size, name or f"Capa {n}")
        self.layers.insert(self.current_layer_idx, layer)
        return layer

    def add_vector_layer(self, name: str = None) -> VectorLayer:
        n = len(self.layers) + 1
        layer = VectorLayer(self.size, name or f"Vector {n}")
        self.layers.insert(self.current_layer_idx, layer)
        return layer

    def remove_layer(self, idx: int):
        if len(self.layers) > 1:
            self.layers.pop(idx)
            self.current_layer_idx = max(0, min(self.current_layer_idx, len(self.layers) - 1))

    @property
    def current_layer(self):
        return self.layers[self.current_layer_idx]

    def move_layer(self, from_idx: int, to_idx: int):
        layer = self.layers.pop(from_idx)
        self.layers.insert(to_idx, layer)

    def copy_from(self, other: 'AnimationFrame'):
        self.layers = []
        for old_layer in other.layers:
            if hasattr(old_layer, 'is_vector') and old_layer.is_vector:
                new_layer = VectorLayer(self.size, old_layer.name)
                new_layer.strokes = [s.copy() for s in old_layer.strokes]
                new_layer.image = old_layer.image.copy()
                new_layer.opacity = old_layer.opacity
                new_layer.visible = old_layer.visible
                self.layers.append(new_layer)
            else:
                new_layer = AnimationLayer(self.size, old_layer.name)
                new_layer.image = old_layer.image.copy()
                new_layer.opacity = old_layer.opacity
                new_layer.visible = old_layer.visible
                self.layers.append(new_layer)
        self.current_layer_idx = other.current_layer_idx

    def move_layer_up(self, idx: int):
        if idx > 0:
            self.layers[idx], self.layers[idx - 1] = self.layers[idx - 1], self.layers[idx]
            self.current_layer_idx = idx - 1

    def move_layer_down(self, idx: int):
        if idx < len(self.layers) - 1:
            self.layers[idx], self.layers[idx + 1] = self.layers[idx + 1], self.layers[idx]
            self.current_layer_idx = idx + 1

    def merge_down_layer(self, idx: int):
        """Merge layer idx onto layer idx+1. Opacities multiply like polarized glass.
        
        Formula: effective = child_opacity * bottom_opacity
        The merged pixels have the final opacity baked in, layer resets to 100%.
        """
        if idx >= len(self.layers) - 1:
            return
        top = self.layers[idx]
        bottom = self.layers[idx + 1]
        
        # Step 1: Bake bottom layer opacity into pixels using Source composition
        bottom_baked = QImage(self.size[0], self.size[1], QImage.Format_ARGB32_Premultiplied)
        bottom_baked.fill(Qt.transparent)
        bp = QPainter(bottom_baked)
        bp.setCompositionMode(QPainter.CompositionMode_Source)
        if hasattr(bottom, 'is_vector') and bottom.is_vector:
            # For vector layers, draw with opacity
            bp.setOpacity(bottom.opacity / 255.0)
            bottom.draw_all(bp)
        else:
            # For raster: multiply image alpha by layer opacity
            bp.setOpacity(bottom.opacity / 255.0)
            bp.drawImage(0, 0, bottom.image)
        bp.end()
        
        # Step 2: Bake top layer opacity and composite over bottom
        merged = QImage(self.size[0], self.size[1], QImage.Format_ARGB32_Premultiplied)
        merged.fill(Qt.transparent)
        mp = QPainter(merged)
        # Draw bottom (already baked)
        mp.drawImage(0, 0, bottom_baked)
        # Draw top with its opacity baked in
        mp.setOpacity(top.opacity / 255.0)
        if hasattr(top, 'is_vector') and top.is_vector:
            top.draw_all(mp)
        else:
            mp.drawImage(0, 0, top.image)
        mp.end()
        
        # Replace bottom with merged result at 100% (opacity is now baked into pixels)
        bottom.image = merged
        bottom.opacity = 255
        self.layers.pop(idx)
        self.current_layer_idx = min(idx, len(self.layers) - 1)

    def flatten_group(self, group_idx: int):
        """Flatten a group layer into a single raster layer, respecting group opacity multiplication.
        The folder's opacity multiplies over all children: effective = child_opacity * folder_opacity.
        """
        if group_idx < 0 or group_idx >= len(self.layers):
            return
        group = self.layers[group_idx]
        if not group.is_group:
            return
        # Composite group with proper opacity multiplication
        merged = QImage(self.size[0], self.size[1], QImage.Format_ARGB32_Premultiplied)
        merged.fill(Qt.transparent)
        painter = QPainter(merged)
        painter.setRenderHint(QPainter.Antialiasing)
        # Apply group opacity over all children with multiplication
        self._composite_group_with_opacity(painter, group, group.opacity / 255.0)
        painter.end()
        # Create new layer with baked opacity (100%)
        new_layer = AnimationLayer(self.size, group.name + " (Fusionado)")
        new_layer.image = merged
        new_layer.opacity = 255  # Opacity is now baked into pixels
        # Replace group with new layer
        self.layers.pop(group_idx)
        self.layers.insert(group_idx, new_layer)
        self.current_layer_idx = group_idx

    def composite(self) -> QImage:
        """Composite all layers. For groups, the folder's opacity multiplies over children."""
        result = QImage(self.size[0], self.size[1], QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        for layer in reversed(self.layers):
            if not layer.visible:
                continue
            if layer.is_group:
                # Group opacity multiplies over all children
                # Pass the group's own opacity as the starting point
                self._composite_group_with_opacity(painter, layer, layer.opacity / 255.0)
            else:
                painter.save()
                painter.setOpacity(layer.opacity / 255.0)
                if hasattr(layer, 'is_vector') and layer.is_vector:
                    painter.drawImage(0, 0, layer.image)
                    layer.draw_all(painter)
                else:
                    painter.drawImage(0, 0, layer.image)
                painter.restore()
        painter.end()
        return result

    def _composite_group_with_opacity(self, painter, group_layer, current_opacity: float):
        """Composite a group layer with proper opacity multiplication.
        
        The formula is: effective_opacity = layer_opacity * current_opacity
        This ensures the folder's opacity multiplies over all children.
        For nested groups, the multiplication chains correctly.
        """
        for child in reversed(group_layer.children):
            if not child.visible:
                continue
            if child.is_group:
                # Nested group: pass down the cumulative opacity
                # The child group's own opacity multiplies with the current opacity
                child_opacity = (child.opacity / 255.0) * current_opacity
                self._composite_group_with_opacity(painter, child, child_opacity)
            else:
                # Child layer: multiply its opacity with the current (parent) opacity
                child_factor = child.opacity / 255.0
                effective_opacity = child_factor * current_opacity
                painter.save()
                painter.setOpacity(effective_opacity)
                if hasattr(child, 'is_vector') and child.is_vector:
                    painter.drawImage(0, 0, child.image)
                    child.draw_all(painter)
                else:
                    painter.drawImage(0, 0, child.image)
                painter.restore()

    def thumbnail(self, w: int = 80, h: int = 55) -> QImage:
        return self.composite().scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class AnimationProject:
    PLAY_NORMAL = "normal"
    PLAY_LOOP = "loop"
    PLAY_PINGPONG = "pingpong"

    def __init__(self, width=1920, height=1080, name="Nuevo Proyecto"):
        self.size = (int(width), int(height))
        self.name = name
        self.frames = [AnimationFrame(self.size)]
        self.current_frame_idx = 0
        self.fps = 24
        self.play_mode = self.PLAY_LOOP
        self.bg_mode = "Transparente"
        self.onion_skin = False
        self._pingpong_dir = 1

    def get_current_frame(self):
        """Return current frame or None if invalid."""
        try:
            if not isinstance(self.frames, list) or len(self.frames) == 0:
                return None
            idx = self.current_frame_idx
            if idx < 0 or idx >= len(self.frames):
                return None
            return self.frames[idx]
        except (IndexError, TypeError, AttributeError):
            return None
    
    @property
    def current_layer(self):
        return self.get_current_frame().layers[self.get_current_frame().current_layer_idx]

    def add_frame(self):
        self.frames.append(AnimationFrame(self.size))

    def insert_frame(self, idx: int):
        self.frames.insert(idx, AnimationFrame(self.size))

    def remove_frame(self, idx: int):
        if len(self.frames) > 1:
            self.frames.pop(idx)
            self.current_frame_idx = max(0, min(self.current_frame_idx, len(self.frames) - 1))

    def advance_frame(self):
        n = len(self.frames)
        if n <= 1:
            return
        if self.play_mode == self.PLAY_NORMAL:
            if self.current_frame_idx < n - 1:
                self.current_frame_idx += 1
        elif self.play_mode == self.PLAY_LOOP:
            self.current_frame_idx = (self.current_frame_idx + 1) % n
        elif self.play_mode == self.PLAY_PINGPONG:
            self.current_frame_idx += self._pingpong_dir
            if self.current_frame_idx >= n - 1:
                self._pingpong_dir = -1
            elif self.current_frame_idx <= 0:
                self._pingpong_dir = 1
    
    def next_frame(self):
        self.advance_frame()
    
    def prev_frame(self):
        n = len(self.frames)
        if n <= 1:
            return
        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1
        else:
            self.current_frame_idx = n - 1

    def insert_frames_from_video(self, qimages: list):
        for img in qimages:
            new_frame = AnimationFrame(self.size)
            painter = QPainter(new_frame.layers[0].image)
            painter.drawImage(
                0, 0,
                img.scaled(self.size[0], self.size[1], Qt.KeepAspectRatioByExpanding),
            )
            painter.end()
            self.frames.append(new_frame)

    def move_frame(self, from_idx: int, to_idx: int):
        """Move a frame from one position to another."""
        if from_idx == to_idx:
            return
        n = len(self.frames)
        if from_idx < 0 or from_idx >= n or to_idx < 0 or to_idx >= n:
            return
        frame = self.frames.pop(from_idx)
        if from_idx < to_idx:
            to_idx -= 1
        self.frames.insert(to_idx, frame)
        if self.current_frame_idx == from_idx:
            self.current_frame_idx = to_idx
        elif from_idx < self.current_frame_idx <= to_idx:
            self.current_frame_idx -= 1
        elif to_idx <= self.current_frame_idx < from_idx:
            self.current_frame_idx += 1
