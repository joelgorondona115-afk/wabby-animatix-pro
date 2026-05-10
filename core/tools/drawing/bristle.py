# core/tools/drawing/bristle.py
"""Bristle brush (brocha) - rectangular shape that rotates with stroke direction."""

import math
import numpy as np
from PySide6.QtGui import QColor, QImage
from PySide6.QtCore import Qt, QPoint

from core.tools.drawing.base import DrawingToolBase
from core.tools.base import _push_undo, _active_layer


# Aspect ratio of the brush: width / height
_BRUSH_ASPECT = 3.0


class BristleBrush:
    """
    Bristle brush engine. Rectangular pattern that auto-rotates to match
    stroke direction, like a real flat brush / brocha.
    """
    
    def __init__(
        self,
        size: int = 30,
        bristle_count: int = 60,
        bristle_spread: float = 0.7,
        stiffness: float = 0.6,
        opacity: int = 150,
        color: QColor = QColor(0, 0, 0),
        split_chance: float = 0.08,
        aspect: float = _BRUSH_ASPECT,
    ):
        self._size = size
        self._bristle_count = bristle_count
        self._bristle_spread = bristle_spread
        self._stiffness = stiffness
        self._opacity = opacity
        self._color = color
        self._split_chance = split_chance
        self._aspect = aspect
        
        self._pattern_cache: dict[tuple, np.ndarray] = {}
        self._rng = np.random.RandomState(42)
    
    @property
    def size(self) -> int:
        return self._size
    
    @size.setter
    def size(self, value: int) -> None:
        self._size = max(1, value)
        if hasattr(self, '_pattern_cache'):
            self._pattern_cache.clear()
    
    @property
    def bristle_count(self) -> int:
        return self._bristle_count
    
    @bristle_count.setter
    def bristle_count(self, value: int) -> None:
        self._bristle_count = max(5, value)
        if hasattr(self, '_pattern_cache'):
            self._pattern_cache.clear()
    
    @property
    def bristle_spread(self) -> float:
        return self._bristle_spread
    
    @bristle_spread.setter
    def bristle_spread(self, value: float) -> None:
        self._bristle_spread = max(0.0, min(1.0, value))
        if hasattr(self, '_pattern_cache'):
            self._pattern_cache.clear()
    
    @property
    def stiffness(self) -> float:
        return self._stiffness
    
    @stiffness.setter
    def stiffness(self, value: float) -> None:
        self._stiffness = max(0.0, min(1.0, value))
    
    @property
    def color(self) -> QColor:
        return self._color
    
    @color.setter
    def color(self, value: QColor) -> None:
        self._color = value
    
    @property
    def opacity(self) -> int:
        return self._opacity
    
    @opacity.setter
    def opacity(self, value: int) -> None:
        self._opacity = max(0, min(255, value))
    
    @property
    def aspect(self) -> float:
        return self._aspect
    
    @aspect.setter
    def aspect(self, value: float) -> None:
        self._aspect = max(0.1, value)
        if hasattr(self, '_pattern_cache'):
            self._pattern_cache.clear()
    
    def _build_pattern(self, half_w: int, half_h: int, angle: float) -> np.ndarray:
        """Build a rectangular bristle pattern rotated by angle (radians)."""
        w = half_w * 2 + 1
        h = half_h * 2 + 1
        spread_w = half_w * self._bristle_spread
        spread_h = half_h * self._bristle_spread
        
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        pattern = np.zeros((h, w), dtype=np.float64)
        cx, cy = half_w, half_h
        
        for _ in range(self._bristle_count):
            # Generate bristle in unrotated rectangle
            ux = self._rng.uniform(-spread_w, spread_w)
            uy = self._rng.uniform(-spread_h, spread_h)
            thickness = self._rng.uniform(0.5, 2.5)
            alpha = self._rng.uniform(0.5, 1.0)
            jx = self._rng.uniform(-1.0, 1.0)
            jy = self._rng.uniform(-1.0, 1.0)
            
            # Rotate to match stroke direction
            rx = ux * cos_a - uy * sin_a + jx
            ry = ux * sin_a + uy * cos_a + jy
            
            bx = int(cx + rx)
            by = int(cy + ry)
            
            if bx < 0 or bx >= w or by < 0 or by >= h:
                continue
            
            br = max(1, int(thickness * 1.2))
            y0 = max(0, by - br)
            y1 = min(h, by + br + 1)
            x0 = max(0, bx - br)
            x1 = min(w, bx + br + 1)
            
            ry_idx, rx_idx = np.ogrid[y0:y1, x0:x1]
            dist = np.sqrt((rx_idx - bx)**2 + (ry_idx - by)**2)
            dab = np.clip(1.0 - dist / (br + 1), 0, 1) * alpha
            
            pattern[y0:y1, x0:x1] += dab
            
            # Split
            if self._rng.random() < self._split_chance:
                sa = self._rng.uniform(0, 2 * np.pi)
                so = self._rng.uniform(1, 3)
                sx = int(bx + so * math.cos(sa))
                sy = int(by + so * math.sin(sa))
                if 0 <= sx < w and 0 <= sy < h:
                    y0 = max(0, sy - br)
                    y1 = min(h, sy + br + 1)
                    x0 = max(0, sx - br)
                    x1 = min(w, sx + br + 1)
                    ry_idx, rx_idx = np.ogrid[y0:y1, x0:x1]
                    dist = np.sqrt((rx_idx - sx)**2 + (ry_idx - sy)**2)
                    dab = np.clip(1.0 - dist / (br + 1), 0, 1) * alpha * 0.7
                    pattern[y0:y1, x0:x1] += dab
        
        pmax = pattern.max()
        if pmax > 0:
            pattern /= pmax
        
        return pattern
    
    def stamp(self, layer_image: QImage, pos: QPoint, pressure: float, angle: float = 0.0) -> None:
        """Apply rectangular bristle stamp. Angle is in radians, 0 = horizontal."""
        radius = max(2, int(self._size * pressure))
        half_w = int(radius * self._aspect * 0.5)
        half_h = int(radius * 0.5)
        
        w, h = layer_image.width(), layer_image.height()
        cx, cy = pos.x(), pos.y()
        
        # Pattern bounds
        x0 = max(0, cx - half_w)
        y0 = max(0, cy - half_h)
        x1 = min(w, cx + half_w + 1)
        y1 = min(h, cy + half_h + 1)
        
        if x1 <= x0 or y1 <= y0:
            return
        
        reg_w = x1 - x0
        reg_h = y1 - y0
        
        # Cache key: (half_w, half_h, angle_bin)
        angle_bin = int(math.degrees(angle) / 10) * 10
        cache_key = (half_w, half_h, angle_bin)
        
        pattern = self._pattern_cache.get(cache_key)
        if pattern is None:
            rad = math.radians(angle_bin)
            pattern = self._build_pattern(half_w, half_h, rad)
            self._pattern_cache[cache_key] = pattern
        
        # Clip pattern to region
        px_off = half_w - (cx - x0)
        py_off = half_h - (cy - y0)
        pat = pattern[
            max(0, py_off):max(0, py_off) + reg_h,
            max(0, px_off):max(0, px_off) + reg_w
        ]
        
        base_alpha = self.opacity * pressure / 255.0
        brush_b = float(self.color.blue())
        brush_g = float(self.color.green())
        brush_r = float(self.color.red())
        
        bits = layer_image.bits()
        stride = layer_image.bytesPerLine()
        pixel_data = np.frombuffer(bits, dtype=np.uint8)
        pixel_data = pixel_data.reshape((h, stride // 4, 4))
        
        region = pixel_data[y0:y1, x0:x1].astype(np.float64)
        
        deposit = pat * base_alpha
        
        region[:, :, 0] = region[:, :, 0] + deposit * (brush_b - region[:, :, 0])
        region[:, :, 1] = region[:, :, 1] + deposit * (brush_g - region[:, :, 1])
        region[:, :, 2] = region[:, :, 2] + deposit * (brush_r - region[:, :, 2])
        region[:, :, 3] = np.minimum(255.0, region[:, :, 3] + deposit * 255.0 * 0.8)
        
        pixel_data[y0:y1, x0:x1] = np.clip(region, 0, 255).astype(np.uint8)


class BristleTool(DrawingToolBase):
    """
    Bristle brush tool (brocha). Rectangular shape auto-rotates with stroke.
    """
    
    name: str = "bristle"
    
    def __init__(
        self,
        color: QColor = QColor(200, 50, 50),
        size: int = 55,
        opacity: int = 220,
        bristle_count: int = 80,
        bristle_spread: float = 0.75,
        stiffness: float = 0.6,
        split_chance: float = 0.08,
        aspect: float = _BRUSH_ASPECT,
    ):
        self._brush = BristleBrush(
            size=size,
            bristle_count=bristle_count,
            bristle_spread=bristle_spread,
            stiffness=stiffness,
            opacity=opacity,
            color=color,
            split_chance=split_chance,
            aspect=aspect,
        )
        self._last = None
        self._angle = 0.0
    
    @property
    def color(self) -> QColor:
        return self._brush.color
    
    @color.setter
    def color(self, value: QColor) -> None:
        self._brush.color = value
    
    @property
    def size(self) -> int:
        return self._brush.size
    
    @size.setter
    def size(self, value: int) -> None:
        self._brush.size = value
    
    @property
    def opacity(self) -> int:
        return self._brush.opacity
    
    @opacity.setter
    def opacity(self, value: int) -> None:
        self._brush.opacity = value
    
    @property
    def bristle_count(self) -> int:
        return self._brush.bristle_count
    
    @bristle_count.setter
    def bristle_count(self, value: int) -> None:
        self._brush.bristle_count = value
    
    @property
    def bristle_spread(self) -> float:
        return self._brush.bristle_spread
    
    @bristle_spread.setter
    def bristle_spread(self, value: float) -> None:
        self._brush.bristle_spread = value
    
    @property
    def stiffness(self) -> float:
        return self._brush.stiffness
    
    @stiffness.setter
    def stiffness(self, value: float) -> None:
        self._brush.stiffness = value
    
    @property
    def aspect(self) -> float:
        return self._brush.aspect
    
    @aspect.setter
    def aspect(self, value: float) -> None:
        self._brush.aspect = value
    
    def on_press(self, canvas, pos: QPoint) -> None:
        _push_undo(canvas)
        self._last = pos
        pressure = getattr(canvas, '_pressure', 1.0)
        
        layer = _active_layer(canvas)
        if layer and not getattr(layer, 'locked', False):
            self._brush.stamp(layer.image, pos, pressure, 0.0)
            canvas.update()
    
    def on_move(self, canvas, pos: QPoint) -> None:
        if not self._last:
            self._last = pos
            return
        
        pressure = getattr(canvas, '_pressure', 1.0)
        
        dx = pos.x() - self._last.x()
        dy = pos.y() - self._last.y()
        dist = math.hypot(dx, dy)
        
        # Angle perpendicular to stroke direction (flat brush orientation)
        self._angle = math.atan2(-dx, dy) if dist > 0 else self._angle
        
        if dist < 1:
            layer = _active_layer(canvas)
            if layer and not getattr(layer, 'locked', False):
                self._brush.stamp(layer.image, pos, pressure, self._angle)
                canvas.update()
            self._last = pos
            return
        
        spacing = max(2, self._brush.size * pressure * 0.25)
        steps = max(1, int(dist / spacing))
        
        layer = _active_layer(canvas)
        if layer and not getattr(layer, 'locked', False):
            for i in range(1, steps + 1):
                t = i / steps
                x = int(self._last.x() + dx * t)
                y = int(self._last.y() + dy * t)
                self._brush.stamp(layer.image, QPoint(x, y), pressure, self._angle)
            
            canvas.update()
        
        self._last = pos
    
    def on_release(self, canvas, pos: QPoint) -> None:
        self._last = None
