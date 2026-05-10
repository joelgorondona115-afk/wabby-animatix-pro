# gui/reference/window.py
from PySide6.QtWidgets import (QMainWindow, QLabel, QFileDialog, QToolBar, QScrollArea,
                               QWidget, QVBoxLayout)
from PySide6.QtGui import QPixmap, QAction, QColor, QImage
from PySide6.QtCore import Qt, Signal


class ReferenceImageLabel(QLabel):
    """Custom QLabel that allows picking colors by right-click/dragging on the image."""
    color_picked = Signal(QColor)
    color_preview = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self._picking = False

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._picking = True
            self._pick_color(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._picking and (event.buttons() & Qt.RightButton):
            self._pick_color(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._picking = False
        super().mouseReleaseEvent(event)

    def _pick_color(self, pos):
        pixmap = self.pixmap()
        if not pixmap or pixmap.isNull():
            return

        label_size = self.size()
        pixmap_size = pixmap.size()
        if label_size.width() == 0 or label_size.height() == 0:
            return

        scale_x = pixmap_size.width() / label_size.width()
        scale_y = pixmap_size.height() / label_size.height()

        img_x = int(pos.x() * scale_x)
        img_y = int(pos.y() * scale_y)

        img_x = max(0, min(img_x, pixmap_size.width() - 1))
        img_y = max(0, min(img_y, pixmap_size.height() - 1))

        img = pixmap.toImage()
        color = img.pixelColor(img_x, img_y)

        self.color_picked.emit(color)
        self.color_preview.emit(color)


class ReferenceWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Referencia")
        self.resize(480, 400)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("QMainWindow { background: #111; }")

        self._zoom = 1.0
        self._pixmap = None

        toolbar = QToolBar("Acciones", self)
        toolbar.setStyleSheet(
            "QToolBar { background: #1e1e1e; border-bottom: 1px solid #333; spacing: 4px; }"
            "QToolButton { background: #2d2d2d; color: #ddd; border: 1px solid #444;"
            "              border-radius: 3px; padding: 4px 8px; }"
            "QToolButton:hover { background: #3a3a3a; }"
            "QToolButton:pressed { background: #00aa00; color: #fff; }"
            "QToolButton:checked { background: #00aa00; border-color: #00ff00; }"
        )
        self.addToolBar(toolbar)

        act_open = QAction("Abrir imagen", self)
        act_open.triggered.connect(self._open_image)
        toolbar.addAction(act_open)

        act_zoom_in = QAction("+", self)
        act_zoom_out = QAction("-", self)
        act_fit = QAction("Ajustar", self)
        act_zoom_in.triggered.connect(lambda: self._set_zoom(self._zoom * 1.25))
        act_zoom_out.triggered.connect(lambda: self._set_zoom(self._zoom / 1.25))
        act_fit.triggered.connect(self._fit)
        toolbar.addSeparator()
        toolbar.addAction(act_zoom_in)
        toolbar.addAction(act_zoom_out)
        toolbar.addAction(act_fit)

        # Reference image label with color picking (right click)
        self._label = ReferenceImageLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("background: #111;")
        self._label.color_picked.connect(self._on_color_picked)
        self._label.color_preview.connect(self._on_color_preview)

        scroll = QScrollArea()
        scroll.setWidget(self._label)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet("QScrollArea { border: none; background: #111; }")

        # Color preview
        self._preview = QLabel("Color: Ninguno (Clic derecho para capturar)")
        self._preview.setStyleSheet(
            "padding: 4px; background: #1e1e1e; color: #ddd; border-top: 1px solid #333;"
        )
        self._preview.setFixedHeight(32)
        self._preview.setAlignment(Qt.AlignCenter)

        # Central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll)
        layout.addWidget(self._preview)
        self.setCentralWidget(central)

    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir referencia", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp);;Todos (*.*)"
        )
        if path:
            self._pixmap = QPixmap(path)
            self._fit()

    def _set_zoom(self, factor: float):
        self._zoom = max(0.05, min(8.0, factor))
        self._refresh()

    def _fit(self):
        if self._pixmap is None:
            return
        avail = self._label.size()
        sx = avail.width() / self._pixmap.width()
        sy = avail.height() / self._pixmap.height()
        self._zoom = min(sx, sy)
        self._refresh()

    def _refresh(self):
        if self._pixmap is None:
            return
        w = max(1, int(self._pixmap.width() * self._zoom))
        h = max(1, int(self._pixmap.height() * self._zoom))
        scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    def _on_color_picked(self, color: QColor):
        """Send color to main window canvas if available."""
        main_window = self.parent()
        if main_window and hasattr(main_window, 'canvas'):
            if hasattr(main_window.canvas, 'set_reference_color'):
                main_window.canvas.set_reference_color(color)

    def _on_color_preview(self, color: QColor):
        """Show color preview in the window."""
        self._preview.setText(f"Color: {color.name()}")
        self._preview.setStyleSheet(
            f"background-color: {color.name()}; padding: 4px; color: #000; border-top: 1px solid #333;"
        )