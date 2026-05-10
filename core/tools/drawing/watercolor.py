# core/tools/drawing/watercolor.py
"""Watercolor brush with wet blending, fringe edges, and paper texture."""

import math
import numpy as np
from PySide6.QtGui import QColor, QImage, QPainter, QBrush, QRadialGradient
from PySide6.QtCore import Qt, QPoint, QPointF

from core.tools.drawing.base import DrawingToolBase
from core.tools.base import _push_undo, _active_layer, _draw_on_layer


class WatercolorBrush:
    """
    Watercolor brush engine with SAI-like behavior.
    
    Parameters:
    - size: Brush diameter in pixels
    - opacity: Maximum pigment density (0-255)
    - wetness: How much water is on the brush (0.0-1.0). Higher = more transparent, more blending
    - fringe: Edge darkening intensity (0.0-1.0). Creates the characteristic water ring
    - dilution: How much existing canvas color is picked up (0.0-1.0)
    - texture_strength: Paper texture visibility (0.0-1.0)
    """
    
    def __init__(
        self,
        size: int = 25,
        opacity: int = 128,
        wetness: float = 0.6,
        fringe: float = 0.0,
        dilution: float = 0.4,
        texture_strength: float = 0.05,
        color: QColor = QColor(0, 0, 0)
    ):
        self.size = size
        self.opacity = opacity
        self.wetness = wetness
        self.fringe = fringe
        self.dilution = dilution
        self.texture_strength = texture_strength
        self.color = color
        
        # Pre-compute brush mask and texture
        self._mask_cache: dict[tuple, np.ndarray] = {}
        self._texture_cache: dict[tuple, np.ndarray] = {}
    
    def _get_brush_mask(self, radius: int) -> np.ndarray:
        """
        Create watercolor brush mask with smooth falloff.
        Pigment accumulates evenly from center to edge with no visible boundary.
        """
        cache_key = (radius, self.fringe)
        if cache_key in self._mask_cache:
            return self._mask_cache[cache_key]
        
        y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
        dist = np.sqrt(x*x + y*y)
        
        nd = np.clip(dist / radius, 0, 1)
        
        # Very smooth quadratic falloff - no ring, soft edge
        mask = (1.0 - nd * nd) * (1.0 - nd * nd)
        
        # Optional fringe only if user explicitly enables it
        if self.fringe > 0.01:
            fringe_ring = np.exp(-((nd - 0.75) ** 2) / 0.04)
            mask = mask * (1.0 - self.fringe) + fringe_ring * self.fringe
        
        mask[nd > 1.0] = 0.0
        
        self._mask_cache[cache_key] = mask
        return mask
    
    def _get_paper_texture(self, radius: int) -> np.ndarray:
        """Generate subtle paper texture - very smooth to avoid visible streaks."""
        cache_key = (radius, int(self.texture_strength * 100))
        if cache_key in self._texture_cache:
            return self._texture_cache[cache_key]
        
        size = radius * 2 + 1
        
        # Single layer of smooth noise only - no streaks
        texture = self._generate_value_noise(size, 0.08)
        
        t_min, t_max = texture.min(), texture.max()
        if t_max > t_min:
            texture = (texture - t_min) / (t_max - t_min)
        else:
            texture = np.ones_like(texture) * 0.5
        
        # Very subtle modulation
        texture = 1.0 - (1.0 - texture) * self.texture_strength * 0.5
        
        self._texture_cache[cache_key] = texture
        return texture
    
    def _generate_value_noise(self, size: int, frequency: float) -> np.ndarray:
        """Generate smooth value noise using interpolated random grid."""
        grid_size = max(2, int(size * frequency))
        rng = np.random.RandomState(hash((size, frequency)) % 2**31)
        grid = rng.rand(grid_size + 1, grid_size + 1)
        
        result = np.zeros((size, size))
        for y in range(size):
            for x in range(size):
                gx, gy = (x / size) * grid_size, (y / size) * grid_size
                ix, iy = min(int(gx), grid_size), min(int(gy), grid_size)
                fx, fy = gx - ix, gy - iy
                ix1, iy1 = min(ix + 1, grid_size), min(iy + 1, grid_size)
                
                top = grid[iy, ix] * (1 - fx) + grid[iy, ix1] * fx
                bot = grid[iy1, ix] * (1 - fx) + grid[iy1, ix1] * fx
                result[y, x] = top * (1 - fy) + bot * fy
        
        return result
    
    def stamp(self, layer_image: QImage, pos: QPoint, pressure: float) -> None:
        """Apply a watercolor stamp. Reads pixels, blends, writes back."""
        radius = max(2, int(self.size * pressure))
        w, h = layer_image.width(), layer_image.height()
        cx, cy = pos.x(), pos.y()
        
        x0 = max(0, cx - radius)
        y0 = max(0, cy - radius)
        x1 = min(w, cx + radius + 1)
        y1 = min(h, cy + radius + 1)
        
        if x1 <= x0 or y1 <= y0:
            return
        
        reg_w = x1 - x0
        reg_h = y1 - y0
        
        mask = self._get_brush_mask(radius)
        texture = self._get_paper_texture(radius)
        
        mask_off_x = radius - (cx - x0)
        mask_off_y = radius - (cy - y0)
        mask_region = mask[
            max(0, mask_off_y):max(0, mask_off_y) + reg_h,
            max(0, mask_off_x):max(0, mask_off_x) + reg_w
        ]
        texture_region = texture[
            max(0, mask_off_y):max(0, mask_off_y) + reg_h,
            max(0, mask_off_x):max(0, mask_off_x) + reg_w
        ]
        
        # Get writable numpy view of image pixels
        # Layers use Format_ARGB32_Premultiplied, same byte layout as ARGB32: [B, G, R, A]
        bits = layer_image.bits()
        stride = layer_image.bytesPerLine()
        pixel_data = np.frombuffer(bits, dtype=np.uint8)
        pixel_data = pixel_data.reshape((h, stride // 4, 4))
        
        # QImage.Format_ARGB32 byte order in memory: [B, G, R, A]
        region = pixel_data[y0:y1, x0:x1].astype(np.float64)
        
        brush_b = float(self.color.blue())
        brush_g = float(self.color.green())
        brush_r = float(self.color.red())
        
        base_alpha = self.opacity * pressure / 255.0
        
        # Pigment deposition: mask affects flow rate, not color value
        # Each pass deposits pigment - edges accumulate with repeated passes
        flow = mask_region * texture_region * base_alpha
        
        # Dilution: pick up existing color from canvas
        if self.dilution > 0:
            existing_alpha = region[:, :, 3] / 255.0
            weight = existing_alpha * self.dilution
            weight_total = weight.sum()
            
            if weight_total > 0:
                pick_b = (region[:, :, 0] * weight).sum() / weight_total
                pick_g = (region[:, :, 1] * weight).sum() / weight_total
                pick_r = (region[:, :, 2] * weight).sum() / weight_total
                
                brush_b = brush_b * (1 - self.dilution) + pick_b * self.dilution
                brush_g = brush_g * (1 - self.dilution) + pick_g * self.dilution
                brush_r = brush_r * (1 - self.dilution) + pick_r * self.dilution
        
        # Wet blending: mix with existing pixels proportionally to flow
        wet_factor = 1.0 - self.wetness * 0.3
        
        # Accumulate pigment: current + flow * (target - current)
        # This ensures edges build up to full opacity with repeated passes
        region[:, :, 0] = region[:, :, 0] + flow * wet_factor * (brush_b - region[:, :, 0])
        region[:, :, 1] = region[:, :, 1] + flow * wet_factor * (brush_g - region[:, :, 1])
        region[:, :, 2] = region[:, :, 2] + flow * wet_factor * (brush_r - region[:, :, 2])
        region[:, :, 3] = np.minimum(255.0, region[:, :, 3] + flow * 255.0 * 0.5)
        
        # Write back
        pixel_data[y0:y1, x0:x1] = np.clip(region, 0, 255).astype(np.uint8)


class WatercolorTool(DrawingToolBase):
    """
    Watercolor tool with wet blending, fringe edges, and paper texture.
    """
    
    name: str = "watercolor"
    
    def __init__(
        self,
        color: QColor = QColor(0, 100, 200),
        size: int = 25,
        opacity: int = 128,
        wetness: float = 0.6,
        fringe: float = 0.0,
        dilution: float = 0.4,
        texture_strength: float = 0.05
    ):
        self._brush = WatercolorBrush(
            size=size, opacity=opacity, wetness=wetness,
            fringe=fringe, dilution=dilution,
            texture_strength=texture_strength, color=color
        )
        self._last = None
    
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
        self._brush._mask_cache.clear()
        self._brush._texture_cache.clear()
    
    @property
    def opacity(self) -> int:
        return self._brush.opacity
    
    @opacity.setter
    def opacity(self, value: int) -> None:
        self._brush.opacity = value
    
    @property
    def wetness(self) -> float:
        return self._brush.wetness
    
    @wetness.setter
    def wetness(self, value: float) -> None:
        self._brush.wetness = max(0.0, min(1.0, value))
        self._brush._mask_cache.clear()
        self._brush._texture_cache.clear()
    
    @property
    def fringe(self) -> float:
        return self._brush.fringe
    
    @fringe.setter
    def fringe(self, value: float) -> None:
        self._brush.fringe = max(0.0, min(1.0, value))
        self._brush._mask_cache.clear()
    
    @property
    def dilution(self) -> float:
        return self._brush.dilution
    
    @dilution.setter
    def dilution(self, value: float) -> None:
        self._brush.dilution = max(0.0, min(1.0, value))
    
    @property
    def texture_strength(self) -> float:
        return self._brush.texture_strength
    
    @texture_strength.setter
    def texture_strength(self, value: float) -> None:
        self._brush.texture_strength = max(0.0, min(1.0, value))
        self._brush._texture_cache.clear()
    
    def on_press(self, canvas, pos: QPoint) -> None:
        _push_undo(canvas)
        self._last = pos
        pressure = getattr(canvas, '_pressure', 1.0)
        
        layer = _active_layer(canvas)
        if layer and not getattr(layer, 'locked', False):
            self._brush.stamp(layer.image, pos, pressure)
            canvas.update()
    
    def on_move(self, canvas, pos: QPoint) -> None:
        if not self._last:
            self._last = pos
            return
        
        pressure = getattr(canvas, '_pressure', 1.0)
        
        dx = pos.x() - self._last.x()
        dy = pos.y() - self._last.y()
        dist = math.hypot(dx, dy)
        
        if dist < 1:
            layer = _active_layer(canvas)
            if layer and not getattr(layer, 'locked', False):
                self._brush.stamp(layer.image, pos, pressure)
                canvas.update()
            self._last = pos
            return
        
        spacing = max(1, self._brush.size * pressure * 0.1)
        steps = max(1, int(dist / spacing))
        
        layer = _active_layer(canvas)
        if layer and not getattr(layer, 'locked', False):
            for i in range(1, steps + 1):
                t = i / steps
                x = int(self._last.x() + dx * t)
                y = int(self._last.y() + dy * t)
                
                speed_factor = min(1.0, dist / 50.0)
                local_pressure = pressure * (0.7 + 0.3 * (1 - speed_factor))
                
                self._brush.stamp(layer.image, QPoint(x, y), local_pressure)
            
            canvas.update()
        
        self._last = pos
    
    def on_release(self, canvas, pos: QPoint) -> None:
        self._last = None
