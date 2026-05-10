# core/tools/special/blur.py
"""Blur tool - desenfoca píxeles como filtro Gaussiano."""

import numpy as np
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt

from core.tools.base import DrawingTool, _active_layer, _push_undo


def _qimage_to_numpy(img: QImage) -> np.ndarray:
    """Convert QImage (ARGB32) to numpy array (RGBA/BGRA)."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    # Leer píxeles correctamente en PySide6
    buffer = img.constBits().asstring(h * w * 4)
    arr = np.frombuffer(buffer, dtype=np.uint8).reshape(h, w, 4)
    return arr.copy()


def _numpy_to_qimage(arr: np.ndarray) -> QImage:
    """Convert numpy array (RGBA) back to QImage."""
    h, w = arr.shape[:2]
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    img = QImage(arr.data, w, h, w * 4, QImage.Format_ARGB32)
    return img.copy()


class BlurTool(DrawingTool):
    name = "blur"
    cursor = Qt.CrossCursor

    def __init__(self, radius=30, strength=0.7):
        self.radius = max(5, radius)
        self.strength = max(0.1, min(1.0, strength))
        self._pushed = False
        self._last_pos = None

    def on_press(self, canvas, pos):
        if not self._pushed:
            _push_undo(canvas)
        self._pushed = True
        self._last_pos = pos
        self._apply(canvas, pos)

    def on_move(self, canvas, pos):
        self._apply(canvas, pos)
        self._last_pos = pos

    def on_release(self, canvas, pos):
        self._pushed = False
        self._last_pos = None

    def _apply(self, canvas, pos):
        layer = _active_layer(canvas)
        if not layer or layer.locked:
            return

        # Presión de tableta
        pressure = getattr(canvas, '_pressure', 1.0)
        x, y = int(pos.x()), int(pos.y())
        img = layer.image
        w, h = img.width(), img.height()

        # Radio y fuerza afectados por presión
        r = max(5, int(self.radius * pressure))
        current_strength = max(0.1, self.strength * pressure)

        # Interpolar si el movimiento es rápido
        if self._last_pos:
            lx, ly = int(self._last_pos.x()), int(self._last_pos.y())
            dist = max(1, int(((x - lx) ** 2 + (y - ly) ** 2) ** 0.5))
            steps = min(dist, max(2, dist // max(1, r // 4)))
            for i in range(1, steps + 1):
                fx = lx + (x - lx) * i / steps
                fy = ly + (y - ly) * i / steps
                self._blur_point(img, fx, fy, w, h, r, current_strength)
        else:
            self._blur_point(img, x, y, w, h, r, current_strength)

        canvas.update()

    def _blur_point(self, img, x, y, w, h, r, strength):
        """Aplica desenfoque Gaussiano en un punto."""
        cx, cy = int(x), int(y)

        # Región a desenfocar
        x1, y1 = max(0, cx - r), max(0, cy - r)
        x2, y2 = min(w, cx + r), min(h, cy + r)
        if x2 <= x1 or y2 <= y1:
            return

        region = img.copy(x1, y1, x2 - x1, y2 - y1)
        if region.isNull():
            return

        if HAS_CV2:
            arr = _qimage_to_numpy(region)
            rh, rw = arr.shape[:2]

            # Sigma basado en fuerza y presión
            sigma = max(3.0, r * 0.4 * strength)
            k = max(3, int(6.0 * sigma) | 1)
            blurred_arr = cv2.GaussianBlur(arr, (k, k), sigmaX=sigma, sigmaY=sigma)

            # Máscara radial: centro se difumina más
            center_x, center_y = cx - x1, cy - y1
            Y, X = np.ogrid[:rh, :rw]
            dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
            mask = np.clip(1.0 - (dist / r), 0, 1)
            mask = mask[:, :, np.newaxis]

            # Mezclar: desenfocado adentro, original afuera
            result = (blurred_arr.astype(np.float32) * mask +
                      arr.astype(np.float32) * (1.0 - mask)).astype(np.uint8)

            blurred = _numpy_to_qimage(result)
        else:
            # Fallback sin OpenCV: escalar hacia abajo y arriba
            rw, rh = region.width(), region.height()
            factor = max(2, int(4 + (1.0 - strength) * 8))
            small = region.scaled(max(1, rw // factor), max(1, rh // factor),
                                  Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            blurred = small.scaled(rw, rh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(x1, y1, blurred)
        painter.end()
