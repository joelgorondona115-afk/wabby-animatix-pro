"""Color picker con clic derecho en ventanas de referencia."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap


class ColorPicker:
    """Captura colores con clic derecho."""

    @staticmethod
    def pick_color(widget, event, pixmap_or_image):
        """Extrae color de un pixmap/imagen en la posición del click."""
        if pixmap_or_image is None:
            return None

        if isinstance(pixmap_or_image, QPixmap):
            if pixmap_or_image.isNull():
                return None
            img = pixmap_or_image.toImage()
        elif isinstance(pixmap_or_image, QImage):
            if pixmap_or_image.isNull():
                return None
            img = pixmap_or_image
        else:
            return None

        if img.isNull():
            return None

        lx = event.position().x() if hasattr(event, 'position') else event.pos().x()
        ly = event.position().y() if hasattr(event, 'position') else event.pos().y()

        img_w = img.width()
        img_h = img.height()
        label_w = widget.image_label.width() if hasattr(widget, 'image_label') else widget.width()
        label_h = widget.image_label.height() if hasattr(widget, 'image_label') else widget.height()

        if label_w <= 0 or label_h <= 0:
            return None

        px = int(lx * img_w / label_w)
        py = int(ly * img_h / label_h)
        px = max(0, min(px, img_w - 1))
        py = max(0, min(py, img_h - 1))

        if 0 <= px < img_w and 0 <= py < img_h:
            color = img.pixelColor(px, py)
            if color.alpha() > 0:
                return color

        return None

    @staticmethod
    def send_to_canvas(widget, color):
        """Manda el color al canvas."""
        ref_win = widget.window()
        mw = ref_win.parent() if ref_win else None
        if mw and hasattr(mw, "canvas"):
            if hasattr(mw.canvas, "set_reference_color"):
                mw.canvas.set_reference_color(color)
            elif hasattr(mw.canvas, "color_picker"):
                mw.canvas.color_picker.set_color(color)

    @staticmethod
    def pick_and_send(widget, event, pixmap_or_image):
        """Pick color y manda al canvas."""
        color = ColorPicker.pick_color(widget, event, pixmap_or_image)
        if color:
            ColorPicker.send_to_canvas(widget, color)