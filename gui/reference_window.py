# gui/reference_window.py
"""Reference window with eyedropper tool for picking colors from reference images."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QColor


class ReferenceImageLabel(QLabel):
    """Custom QLabel that allows picking colors by clicking/dragging on the image."""
    color_picked = Signal(QColor)
    color_preview = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)  # Escala la imagen al tamaño del label
        self._picking = False  # Bandera para mantener presionado

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._picking = True
            self._pick_color(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Si está presionado el botón izquierdo, sigue capturando color
        if self._picking and (event.buttons() & Qt.LeftButton):
            self._pick_color(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._picking = False
        super().mouseReleaseEvent(event)

    def _pick_color(self, pos):
        pixmap = self.pixmap()
        if not pixmap or pixmap.isNull():
            return

        # Calcular coordenadas de imagen real considerando la escala
        label_size = self.size()
        pixmap_size = pixmap.size()
        if label_size.width() == 0 or label_size.height() == 0:
            return

        scale_x = pixmap_size.width() / label_size.width()
        scale_y = pixmap_size.height() / label_size.height()

        img_x = int(pos.x() * scale_x)
        img_y = int(pos.y() * scale_y)

        # Limitar a los límites de la imagen
        img_x = max(0, min(img_x, pixmap_size.width() - 1))
        img_y = max(0, min(img_y, pixmap_size.height() - 1))

        # Obtener el color del píxel
        img = pixmap.toImage()
        color = img.pixelColor(img_x, img_y)

        self.color_picked.emit(color)
        self.color_preview.emit(color)


class ReferenceWindow(QDialog):
    """Window to display reference images with color picking capability."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Referencias")
        self.setModal(False)  # No modal para dibujar mientras se usa

        # UI
        layout = QVBoxLayout(self)
        self.image_label = ReferenceImageLabel()
        layout.addWidget(self.image_label)

        # Previsualización del color
        self.preview_label = QLabel("Color: ")
        layout.addWidget(self.preview_label)

        # Cargar imagen inicial si existe
        if hasattr(main_window, 'ref_image') and main_window.ref_image:
            self.set_image(main_window.ref_image)

        # Conectar señales
        self.image_label.color_picked.connect(self.on_color_picked)
        self.image_label.color_preview.connect(self.on_color_preview)

    def set_image(self, image: QImage):
        """Actualizar la imagen de referencia mostrada."""
        self.image_label.setPixmap(QPixmap.fromImage(image))

    def on_color_picked(self, color: QColor):
        """Enviar el color al sistema de color principal."""
        if hasattr(self.main_window, 'canvas'):
            # Usa el método existente en CanvasWidget que ya conecta con el color_picker
            self.main_window.canvas.set_reference_color(color)

    def on_color_preview(self, color: QColor):
        """Mostrar previsualización del color seleccionado."""
        self.preview_label.setText(f"Color: {color.name()}")
        self.preview_label.setStyleSheet(f"background-color: {color.name()}; padding: 4px;")
