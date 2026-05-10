# main.py
"""
Animatix Pro — interfaz estilo Paint Tool SAI + línea de tiempo Ibis Paint
"""
import sys
import json
import os
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QMessageBox, QProgressDialog,
    QSizePolicy, QSpinBox, QScrollArea, QStatusBar, QMenu, QTextBrowser,
    QGridLayout, QToolButton, QDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QKeySequenceEdit, QColorDialog,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QEvent, QKeyCombination, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QColor, QFont, QKeySequence, QShortcut, QIcon,
    QPainter, QPen, QPixmap, QPainterPath, QImage,
)

from core.models import AnimationProject, AnimationFrame
from core.video_importer import VideoImporter, GifImporter
from core.recorder import TimelapseExporter
from core.canvas import CanvasWidget
from .dialogs import NewProjectDialog
from .color_wheel import ColorWheel
from .capas import LayerPanel
from .reference_window import ReferenceWindow
from .timeline import TimelineWidget
from .panels.opacity import OpacityPanel
from .panels.blur_panel import BlurPanel
from .reference.window import ReferenceWindow


# ---------------------------------------------------------------------------
# Thread de importación de video
# ---------------------------------------------------------------------------
class VideoImportThread(QThread):
    finished = Signal(list, int, tuple)
    error = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            frames, fps, size = VideoImporter.import_video(self.file_path)
            self.finished.emit(frames, fps, size)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Atajos por defecto
# ---------------------------------------------------------------------------
DEFAULT_SHORTCUTS = {
    # Herramientas de dibujo (teclado)
    "Lápiz":              "P",
    "Pincel":             "B",
    "Goma":               "E",
    "Relleno":            "G",
    "Cuentagotas":        "I",
    "Texto":              "T",
    "Difuminar":          "U",
    "Aerógrafo":          "A",
    "Acuarela":           "W",
    "Brocha":             "K",
    "Línea":              "L",
    "Rectángulo":         "R",
    "Elipse":             "O",
    "curva":              "C",
    # Mover
    "Mover capa":         "V",
    # Vector tools
    "Lápiz Vectorial":    "Ctrl+V",
    "Pincel Vectorial":   "Shift+V",
    "Polilínea Curva":    "Shift+P",
    "Relleno Polilínea":  "Shift+K",
    # Lazos de relleno
    "Lazo relleno libre":  "Shift+L",
    "Lazo relleno rect.":  "Shift+R",
    "Lazo relleno elipse":"Shift+O",
    # Selección
    "Selec. rect.":       "M",
    "Lazo borrador":      "Shift+M",
    "Lazo selección":     "Shift+N",
    "Selec. elipse":      "Shift+E",
    # Edición
    "Deshacer":           "Ctrl+Z",
    "Rehacer":            "Ctrl+Y",
    # Animación
    "Play / Stop":        "Space",
    "Frame anterior":     "Left",
    "Frame siguiente":    "Right",
    # Vista
    "Zoom +":             "=",
    "Zoom -":             "-",
    "Zoom ajustar":       "F",
    "Zoom 100%":         "Ctrl+0",
}

SHORTCUT_FILE = os.path.join(os.path.dirname(__file__), "shortcuts.json")

# Mapa atajo → nombre de herramienta en canvas
_TOOL_MAP = {
    "Lápiz":               "pencil",
    "Pincel":              "brush",
    "Goma":                "eraser",
    "Relleno":             "fill",
    "Cuentagotas":         "eyedrop",
    "Texto":               "text",
    "Difuminar":           "blur",
    "Aerógrafo":           "airbrush",
    "Acuarela":            "watercolor",
    "Brocha":              "bristle",
    "Línea":               "line",
    "Rectángulo":          "rect",
    "Elipse":              "ellipse",
    "Mover capa":          "move",
    "Lazo relleno libre":  "lasso_fill",
    "Lazo relleno rect.":  "lasso_fill_rect",
    "Lazo relleno elipse": "lasso_fill_ellipse",
    "Selec. rect.":        "select_rect",
    "Lazo borrador":       "lasso_eraser",
    "Lazo selección":      "lasso_marquee",
    "Selec. elipse":       "select_ellipse",
    "Lápiz Vectorial":     "vector_pencil",
    "Pincel Vectorial":    "vector_brush",
    "Polilínea Curva":     "polyline",
    "Relleno Polilínea":   "poly_fill",
}


# ---------------------------------------------------------------------------
# Ventana de atajos customizables
# ---------------------------------------------------------------------------
class ShortcutEditor(QDialog):
    shortcuts_changed = Signal(dict)

    def __init__(self, shortcuts: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atajos de teclado")
        self.resize(480, 520)
        self._shortcuts = dict(shortcuts)

        self.setStyleSheet("""
            QDialog { background: #1e1e1e; color: #ddd; }
            QTableWidget {
                background: #252525; color: #ddd; gridline-color: #333;
                border: 1px solid #333; font-size: 12px;
            }
            QTableWidget::item:selected { background: #0078d7; }
            QHeaderView::section {
                background: #2d2d2d; color: #aaa; padding: 4px;
                border: 1px solid #333; font-size: 11px; font-weight: bold;
            }
            QPushButton {
                background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 4px; padding: 6px 14px; font-size: 12px;
            }
            QPushButton:hover  { background: #3a3a3a; }
            QPushButton#btnOk  { background: #005fa3; }
            QPushButton#btnOk:hover { background: #0078d7; }
            QLabel { color: #888; font-size: 11px; }
        """)

        layout = QVBoxLayout(self)

        lbl = QLabel("Doble clic en una fila para editar el atajo. Presioná la nueva combinación de teclas.")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.table = QTableWidget(len(self._shortcuts), 2)
        self.table.setHorizontalHeaderLabels(["Acción", "Atajo"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            self.table.styleSheet() +
            "QTableWidget { alternate-background-color: #2a2a2a; }"
        )

        for row, (action, key) in enumerate(self._shortcuts.items()):
            self.table.setItem(row, 0, QTableWidgetItem(action))
            self.table.setItem(row, 1, QTableWidgetItem(key))

        self.table.cellDoubleClicked.connect(self._edit_shortcut)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_reset = QPushButton("↩ Restaurar por defecto")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_ok    = QPushButton("✓ Aceptar")
        btn_ok.setObjectName("btnOk")
        btn_ok.clicked.connect(self._accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _edit_shortcut(self, row, col):
        action = self.table.item(row, 0).text()
        dlg    = _KeyCaptureDialog(action, self)
        if dlg.exec():
            new_key = dlg.captured_key
            # Detectar conflicto
            for r in range(self.table.rowCount()):
                if r != row and self.table.item(r, 1).text() == new_key:
                    other = self.table.item(r, 0).text()
                    QMessageBox.warning(
                        self, "Conflicto",
                        f"El atajo '{new_key}' ya está asignado a '{other}'.\n"
                        "Cambiá uno de los dos primero."
                    )
                    return
            self._shortcuts[action] = new_key
            self.table.item(row, 1).setText(new_key)

    def _reset_defaults(self):
        self._shortcuts = dict(DEFAULT_SHORTCUTS)
        for row, (action, key) in enumerate(self._shortcuts.items()):
            self.table.item(row, 0).setText(action)
            self.table.item(row, 1).setText(key)

    def _accept(self):
        self.shortcuts_changed.emit(self._shortcuts)
        self.accept()

    def get_shortcuts(self) -> dict:
        return self._shortcuts


class _KeyCaptureDialog(QDialog):
    """Diálogo que captura combinaciones de teclas y mouse."""
    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar atajo — {action}")
        self.setFixedSize(360, 160)
        self.captured_key = ""
        
        self.setStyleSheet("""
            QDialog { background: #1e1e1e; color: #ddd; }
            QLabel { color: #ddd; font-size: 13px; }
            QPushButton {
                background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 4px; padding: 8px 16px;
            }
            QPushButton:hover { background: #3a3a3a; }
        """)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Presioná la combinación para:\n{action}"))
        
        self.key_label = QLabel("Esperando (tecla o clic)...")
        self.key_label.setStyleSheet("color: #0078d7; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.key_label)
        
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Aceptar")
        btn_ok.setObjectName("btnOk")
        btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Install event filter for mouse events
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Capturar eventos de mouse."""
        if event.type() == event.MouseButtonPress:
            self._capture_mouse(event.button())
            return True
        return super().eventFilter(obj, event)
    
    def _capture_mouse(self, button):
        """Procesar clic del mouse."""
        if button == Qt.LeftButton:
            self.captured_key = "LeftButton"
        elif button == Qt.RightButton:
            self.captured_key = "RightButton"
        elif button == Qt.MiddleButton:
            self.captured_key = "MiddleButton"
        else:
            return
        
        modifiers = Qt.NoButton
        # Check current modifiers
        mods = self.queryKeyboardModifiers()
        if mods & Qt.ControlModifier:
            self.captured_key = "Ctrl+" + self.captured_key
        if mods & Qt.AltModifier:
            self.captured_key = "Alt+" + self.captured_key
        if mods & Qt.ShiftModifier:
            self.captured_key = "Shift+" + self.captured_key
        
        self.key_label.setText(self.captured_key)
    
    def keyPressEvent(self, event):
        """Capturar teclas."""
        key = event.key()
        
        if key in (Qt.Key_Escape,):
            self.reject()
            return
        
        modifiers = event.modifiers()
        parts = []
        
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        
        if key == Qt.Key_Space:
            parts.append("Space")
        elif key == Qt.Key_Return:
            parts.append("Enter")
        elif key == Qt.Key_Tab:
            parts.append("Tab")
        elif key == Qt.Key_Backspace:
            parts.append("Backspace")
        elif key == Qt.Key_Delete:
            parts.append("Delete")
        elif key == Qt.Key_Left:
            parts.append("Left")
        elif key == Qt.Key_Right:
            parts.append("Right")
        elif key == Qt.Key_Up:
            parts.append("Up")
        elif key == Qt.Key_Down:
            parts.append("Down")
        elif key == Qt.Key_Home:
            parts.append("Home")
        elif key == Qt.Key_End:
            parts.append("End")
        elif key == Qt.Key_PageUp:
            parts.append("PageUp")
        elif key == Qt.Key_PageDown:
            parts.append("PageDown")
        elif Qt.Key_A <= key <= Qt.Key_Z:
            parts.append(chr(key).upper())
        elif Qt.Key_0 <= key <= Qt.Key_9:
            parts.append(chr(key))
        elif Qt.Key_F1 <= key <= Qt.Key_F12:
            parts.append(f"F{key - Qt.Key_F1 + 1}")
        else:
            key_text = event.text().upper()
            if key_text:
                parts.append(key_text)
            else:
                return
        
        self.captured_key = "+".join(parts)
        self.key_label.setText(self.captured_key)
    
    def _accept(self):
        if self.captured_key:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Presioná una combinación de teclas primero.")


# Ventana de configuración de papel cebolla
# ---------------------------------------------------------------------------
class OnionSkinConfigDialog(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Papel cebolla")
        self.resize(320, 280)
        self._canvas = canvas

        self.setStyleSheet("""
            QDialog { background: #1e1e1e; color: #ddd; }
            QLabel { color: #ccc; font-size: 12px; }
            QPushButton {
                background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 4px; padding: 6px 14px;
            }
            QPushButton:hover { background: #3a3a3a; }
            QComboBox {
                background: #252525; color: #ddd; border: 1px solid #444;
                padding: 4px; border-radius: 3px;
            }
            QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
            QSlider::handle:horizontal { width: 14px; margin: -4px 0; background: #0078d7; border-radius: 7px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Tipo
        layout.addWidget(QLabel("Tipo:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Pasado", "Futuro", "Ambos"])
        self.combo_tipo.setCurrentText(canvas.onion_mode)
        self.combo_tipo.currentTextChanged.connect(self._update_preview)
        layout.addWidget(self.combo_tipo)

        # Frames a mostrar
        layout.addWidget(QLabel("Frames a mostrar:"))
        self.slider_frames = QSlider(Qt.Horizontal)
        self.slider_frames.setRange(1, 5)
        self.slider_frames.setValue(3)
        self.slider_frames.setTickPosition(QSlider.TicksBelow)
        self.slider_frames.setTickInterval(1)
        layout.addWidget(self.slider_frames)

        # Opacidad
        layout.addWidget(QLabel("Opacidad:"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(10, 100)
        self.slider_opacity.setValue(canvas.onion_opacity)
        self.slider_opacity.valueChanged.connect(self._update_preview)
        layout.addWidget(self.slider_opacity)

        # Color pasado
        layout.addWidget(QLabel("Color pasado:"))
        self.btn_color_prev = QPushButton()
        self.btn_color_prev.setFixedSize(60, 25)
        c = canvas.onion_color_prev
        self.btn_color_prev.setStyleSheet(f"background-color: rgb({c.red()},{c.green()},{c.blue()});")
        self.btn_color_prev.clicked.connect(lambda: self._pick_color("prev"))
        layout.addWidget(self.btn_color_prev)

        # Color futuro
        layout.addWidget(QLabel("Color futuro:"))
        self.btn_color_next = QPushButton()
        self.btn_color_next.setFixedSize(60, 25)
        c = canvas.onion_color_next
        self.btn_color_next.setStyleSheet(f"background-color: rgb({c.red()},{c.green()},{c.blue()});")
        self.btn_color_next.clicked.connect(lambda: self._pick_color("next"))
        layout.addWidget(self.btn_color_next)

        layout.addStretch()

        # Botón cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("btnOk")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _update_preview(self):
        self._canvas.onion_mode = self.combo_tipo.currentText()
        self._canvas.onion_opacity = self.slider_opacity.value()
        self._canvas.update()

    def _pick_color(self, which):
        dlg = QColorDialog(self)
        if which == "prev":
            dlg.setCurrentColor(self._canvas.onion_color_prev)
        else:
            dlg.setCurrentColor(self._canvas.onion_color_next)
        if dlg.exec():
            color = dlg.currentColor()
            if which == "prev":
                self._canvas.onion_color_prev = color
                self.btn_color_prev.setStyleSheet(f"background-color: rgb({color.red()},{color.green()},{color.blue()});")
            else:
                self._canvas.onion_color_next = color
                self.btn_color_next.setStyleSheet(f"background-color: rgb({color.red()},{color.green()},{color.blue()});")
            self._canvas.update()
        self.lbl = QLabel("...")
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #0078d7; "
            "border: 1px solid #444; padding: 8px; background: #2d2d2d;"
        )
        layout.addWidget(self.lbl)

        btn_row = QHBoxLayout()
        btn_ok  = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def keyPressEvent(self, event):
        mods  = event.modifiers()
        key   = event.key()
        parts = []
        if mods & Qt.ControlModifier: parts.append("Ctrl")
        if mods & Qt.ShiftModifier:   parts.append("Shift")
        if mods & Qt.AltModifier:     parts.append("Alt")
        key_str = QKeySequence(key).toString()
        if key_str and key_str not in ("Ctrl", "Shift", "Alt", "Meta"):
            parts.append(key_str)
        if parts:
            self.captured_key = "+".join(parts)
            self.lbl.setText(self.captured_key)


# ============================================================
# Ventana Principal
# ============================================================
class AnimatixPro(QMainWindow):

    def __init__(self, project_data: dict):
        super().__init__()

        self.w            = project_data['width']
        self.h            = project_data['height']
        self.project_name = project_data['name']
        self.bg_mode      = project_data['bg']

        self.project = AnimationProject(
            width=self.w, height=self.h,
            name=self.project_name,
        )
        self.project._bg_mode = self.bg_mode

        # Referencia de video para rotoscopia
        self.ref_frames = []  # Frames del video de referencia
        self.ref_idx = 0     # Frame actual de referencia
        self.ref_opacity = 80  # Opacidad de la referencia (0-255)

        self.setWindowTitle(f"Animatix Pro — {self.project_name}")
        self.showMaximized()

        # Cargar atajos (JSON o defecto)
        self._shortcuts = self._load_shortcuts()
        self._mouse_shortcuts = {}  # Para atajos de mouse

        self._apply_global_stylesheet()

        # Canvas
        self.canvas = CanvasWidget(self.w, self.h)
        self.canvas.project = self.project
        self.canvas.set_bg_mode(self.bg_mode)

        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidget(self.canvas)
        self.canvas_scroll.setAlignment(Qt.AlignCenter)
        self.canvas_scroll.setStyleSheet("QScrollArea { background: #0a0a0a; border: none; }")
        self.setCentralWidget(self.canvas_scroll)
        self.canvas_scroll.viewport().installEventFilter(self)

        self.reference_window = ReferenceWindow(self)

        self._docks: list[QDockWidget] = []
        self._init_status_bar()
        self._init_inspector_dock()  # Crea size_slider antes
        self._init_tools_dock()
        self._init_layers_dock()
        self._init_timeline_dock()
        self._init_menu_bar()
        self._register_shortcuts()

        self.import_thread:   VideoImportThread | None = None
        self.progress_dialog: QProgressDialog   | None = None

        self.timeline.update_ui()
        self.layer_panel.update_ui()

    # ------------------------------------------------------------------
    # Estilo global
    # ------------------------------------------------------------------
    def _apply_global_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QDockWidget {
                color: #aaa; background-color: #1e1e1e; border: 1px solid #333;
            }
            QDockWidget::title {
                background-color: #252525; padding: 5px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton {
                background-color: #2d2d2d; color: #ddd; border-radius: 4px;
                padding: 6px 10px; font-weight: bold;
                border: 1px solid #444; font-size: 12px;
            }
            QPushButton:hover   { background-color: #3a3a3a; border: 1px solid #666; }
            QPushButton:pressed { background-color: #00aa00; color: #fff; }
            QPushButton:checked { background-color: #00aa00; border-color: #00ff00; }
            QToolButton {
                background-color: #2d2d2d; color: #ddd;
                border: 1px solid #444; border-radius: 3px;
                font-size: 18px; padding: 2px;
            }
            QToolButton:hover   { background-color: #3a3a3a; border: 1px solid #666; }
            QToolButton:pressed { background-color: #00aa00; color: #fff; }
            QToolButton:checked { background-color: #00aa00; border-color: #00ff00; }
            QLabel      { color: #888; font-size: 11px; }
            QScrollArea { border: none; }
            QStatusBar  { background: #1a1a1a; color: #888; font-size: 11px; }
            QSpinBox    { background: #2d2d2d; color: #ddd; border: 1px solid #444; padding: 2px; }
            QSlider::groove:horizontal { height: 4px; background: #444; }
            QSlider::handle:horizontal {
                background: #0078d7; width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px;
            }
            QMenuBar { background-color: #252525; color: #ddd; }
            QMenuBar::item:selected { background: #333; }
            QMenu { background: #252525; color: #ddd; border: 1px solid #444; }
            QMenu::item:selected { background: #0078d7; }
        """)

    # ------------------------------------------------------------------
    # Íconos dibujados con QPainter para cada herramienta
    # ------------------------------------------------------------------
    @staticmethod
    def _tool_icon(name: str, size: int = 20) -> QIcon:
        px = QPixmap(size, size)
        px.fill(Qt.transparent)
        p  = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)

        fg  = QColor(210, 210, 210)
        pn  = QPen(fg, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        pd  = QPen(fg, 1.2, Qt.DashLine,  Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pn)
        p.setBrush(Qt.NoBrush)

        c  = size / 2
        m  = 3
        s  = size - 2 * m

        if name == "pencil":
            # Cuerpo diagonal
            p.drawLine(QPointF(m+1, size-m-1), QPointF(size-m-3, m+3))
            # Punta (triángulo pequeño)
            tip = QPainterPath()
            tip.moveTo(m+1, size-m-1)
            tip.lineTo(m+4, size-m-1)
            tip.lineTo(m+1, size-m-4)
            tip.closeSubpath()
            p.setBrush(fg); p.setPen(Qt.NoPen)
            p.drawPath(tip)
            # Goma (línea gruesa al otro extremo)
            p.setPen(QPen(fg, 2.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(size-m-3, m+3), QPointF(size-m-1, m+1))

        elif name == "brush":
            path = QPainterPath()
            path.moveTo(m+2, size-m-2)
            path.cubicTo(c-2, c+2,  c+2, c-2,  size-m-2, m+2)
            p.drawPath(path)
            p.setBrush(fg); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(m+2, size-m-2), 2.0, 2.0)

        elif name == "airbrush":
            # Mango diagonal
            p.drawLine(QPointF(m+1, size-m-1), QPointF(c+1, c-1))
            # Boquilla
            p.drawLine(QPointF(c+1, c-1), QPointF(c+4, c-4))
            # Puntos de spray
            p.setBrush(fg); p.setPen(Qt.NoPen)
            for dx, dy in [(5,-3),(6,-1),(5,1),(7,-2),(7,0)]:
                p.drawEllipse(QPointF(c+dx, c+dy), 0.9, 0.9)

        elif name == "eraser":
            path = QPainterPath()
            path.moveTo(m+2,  size-m-4)
            path.lineTo(m+5,  size-m-1)
            path.lineTo(size-m-1, m+3)
            path.lineTo(size-m-4, m)
            path.closeSubpath()
            p.setBrush(QColor(210, 210, 210, 55))
            p.setPen(pn)
            p.drawPath(path)
            # Borde inferior (parte que borra)
            p.setPen(QPen(QColor(120, 180, 255), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(m+2, size-m-4), QPointF(m+5, size-m-1))

        elif name == "eyedrop":
            # Tubo diagonal
            p.drawLine(QPointF(m+2, size-m-2), QPointF(size-m-2, m+2))
            # Bulbo superior
            p.setBrush(fg)
            p.drawEllipse(QPointF(size-m-2, m+2), 2.2, 2.2)
            # Punta inferior
            p.drawEllipse(QPointF(m+2, size-m-2), 1.3, 1.3)

        elif name == "blur":
            p.setBrush(QColor(210, 210, 210, 45))
            for cx, cy, r in [(c-2.5, c-1, 4.5), (c+2.5, c-1, 4.5), (c, c+2, 4.5)]:
                p.drawEllipse(QPointF(cx, cy), r, r)

        elif name == "fill":
            # Balde
            path = QPainterPath()
            path.moveTo(c-3, m+5)
            path.lineTo(c-4.5, size-m-4)
            path.lineTo(c+4.5, size-m-4)
            path.lineTo(c+3,   m+5)
            path.closeSubpath()
            p.drawPath(path)
            # Asa
            p.drawLine(QPointF(c+3, m+5), QPointF(c+6, m+2))
            # Gota
            drop = QPainterPath()
            drop.moveTo(c+7, c+1)
            drop.cubicTo(c+10, c+4, c+10, c+8, c+7, c+8)
            drop.cubicTo(c+4,  c+8, c+4,  c+4, c+7, c+1)
            p.setBrush(fg); p.setPen(Qt.NoPen)
            p.drawPath(drop)

        elif name == "text":
            p.setPen(QPen(fg, 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(m+1, m+3), QPointF(size-m-1, m+3))
            p.drawLine(QPointF(c,   m+3), QPointF(c, size-m-1))

        elif name == "line":
            p.drawLine(QPointF(m+1, size-m-1), QPointF(size-m-1, m+1))

        elif name == "rect":
            p.drawRect(QRectF(m+1, m+1, s-2, s-2))

        elif name == "ellipse":
            p.drawEllipse(QRectF(m+1, m+1, s-2, s-2))

        elif name == "select_rect":
            p.setPen(pd)
            p.drawRect(QRectF(m+1, m+1, s-2, s-2))

        elif name == "select_ellipse":
            p.setPen(pd)
            p.drawEllipse(QRectF(m+1, m+1, s-2, s-2))

        elif name == "lasso_fill_rect":
            p.setBrush(QColor(210, 210, 210, 50))
            p.setPen(pd)
            p.drawRect(QRectF(m+1, m+1, s-2, s-2))

        elif name == "lasso_fill_ellipse":
            p.setBrush(QColor(210, 210, 210, 50))
            p.setPen(pd)
            p.drawEllipse(QRectF(m+1, m+1, s-2, s-2))

        elif name in ("lasso_fill", "lasso_marquee", "select_lasso", "lasso_eraser"):
            path = QPainterPath()
            path.moveTo(c,       m+2)
            path.cubicTo(size-m, m,      size-m, size-m, c+1,  size-m-1)
            path.cubicTo(m,      size-m, m+1,    m+2,    c,    m+2)
            if name == "lasso_fill":
                p.setBrush(QColor(210, 210, 210, 50))
                p.setPen(pn)
            else:
                p.setPen(pd)
            p.drawPath(path)

        elif name == "move":
            aw = 2.5
            for ax, ay, bx, by, cx1, cy1, cx2, cy2 in [
                # up
                (c, m,      c, c-2, c-aw, m+aw*1.5, c+aw, m+aw*1.5),
                # down
                (c, size-m, c, c+2, c-aw, size-m-aw*1.5, c+aw, size-m-aw*1.5),
                # left
                (m, c,      c-2, c, m+aw*1.5, c-aw, m+aw*1.5, c+aw),
                # right
                (size-m, c, c+2, c, size-m-aw*1.5, c-aw, size-m-aw*1.5, c+aw),
            ]:
                p.drawLine(QPointF(ax, ay), QPointF(bx, by))
                p.drawLine(QPointF(ax, ay), QPointF(cx1, cy1))
                p.drawLine(QPointF(ax, ay), QPointF(cx2, cy2))

        else:
            p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "?")

        p.end()
        return QIcon(px)

    # ------------------------------------------------------------------
    # Panel de herramientas estilo SAI — grilla de iconos, sin texto
# ------------------------------------------------------------------
    def _init_tools_dock(self):
        dock      = QDockWidget("Herramientas", self)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        container = QWidget()
        layout    = QVBoxLayout(container)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tool_buttons: dict[str, QToolButton] = {}

        def make_btn(icon: str, tooltip: str, tool_name: str) -> QToolButton:
            btn = QToolButton()
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(30, 30)
            ti = AnimatixPro._tool_icon(tool_name, 20)
            if ti.isNull():
                btn.setText(icon)
            else:
                btn.setIcon(ti)
                btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda checked, n=tool_name: self._set_tool(n))
            self.tool_buttons[tool_name] = btn
            return btn

        def add_combo_box(label_text, items, callback):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
            layout.addWidget(lbl)
            
            combo = QComboBox()
            combo.setFixedHeight(24)
            combo.setStyleSheet("""
                QComboBox {
                    background: #252525; color: #ddd; border: 1px solid #444;
                    padding-left: 8px; border-radius: 4px;
                }
                QComboBox::drop-down { width: 20px; border: none; }
                QComboBox::down-arrow { image: none; }
            """)
            for icon, tooltip, name in items:
                combo.addItem(icon, name)
                combo.setItemData(combo.count() - 1, tooltip, Qt.ToolTipRole)
            combo.currentIndexChanged.connect(lambda idx: callback(combo.itemData(idx)))
            layout.addWidget(combo)
            layout.addSpacing(2)
            return combo

        # --- Dibujo ---
        self._tool_combos: list[QComboBox] = []
        
        combo = add_combo_box("DIBUJO", [
            ("✏️", "Lápiz  [P]",       "pencil"),
            ("🖌️", "Pincel  [B]",      "brush"),
            ("🧽", "Goma  [E]",        "eraser"),
            ("💧", "Cuentagotas  [I]", "eyedrop"),
            ("💨", "Difuminar  [U]",   "blur"),
            ("🎨", "Aerógrafo  [A]",   "airbrush"),
            ("💧", "Acuarela  [W]",    "watercolor"),
            ("🖌️", "Brocha  [K]",      "bristle"),
            ("🔤", "Texto  [T]",       "text"),
            ("➰", "Curva  [C]", "curve"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        combo = add_combo_box("FORMAS", [
            ("📏", "Línea  [L]",         "line"),
            ("⬜", "Rectángulo  [R]",    "rect"),
            ("⭕", "Elipse  [O]",        "ellipse"),
            ("🪣", "Relleno  [G]",       "fill"),
            ("〰️", "Polilínea Curva",    "polyline"),
            ("🔷", "Relleno Polilínea",  "poly_fill"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        combo = add_combo_box("MOVER", [
            ("✋", "Mover capa  [V]",    "move"),
            ("✋", "Mover selección", "move_selection"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        combo = add_combo_box("LAZO RELLENO", [
            ("🌀", "Lazo libre relleno",    "lasso_fill"),
            ("◻️", "Lazo rect. relleno",    "lasso_fill_rect"),
            ("⭕", "Lazo elipse relleno",   "lasso_fill_ellipse"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        combo = add_combo_box("SELECCIÓN", [
            ("⬜", "Rectángulo",   "select_rect"),
            ("🌀", "Lazo libre",  "select_lasso"),
            ("⭕", "Elipse",     "select_ellipse"),
            ("〰️", "Bordado",    "lasso_marquee"),
            ("🧽", "Lazo borrador", "lasso_eraser"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        combo = add_combo_box(" capz / PEG BAR", [
            ("↔️", "Mover selección", "move_selection"),
            ("🔁", "Repetir frame", "dup_frame"),
        ], lambda x: None)
        self._tool_combos.append(combo)

        combo = add_combo_box("VECTORES (CLEANUP)", [
            ("✏️", "Lápiz Vectorial  [V]",     "vector_pencil"),
            ("🖊️", "Pincel Vectorial  [Shift+V]", "vector_brush"),
        ], self._set_tool)
        self._tool_combos.append(combo)

        # --- Accesos directos ---
        layout.addSpacing(12)
        lbl = QLabel("ACCESOS RÁPIDOS")
        lbl.setStyleSheet("color: #555; font-size: 9px; font-weight: bold;")
        layout.addWidget(lbl)
        
        quick = QGridLayout()
        quick.setSpacing(2)
        quick.addWidget(make_btn("✏️", "Lápiz  [P]", "pencil"), 0, 0)
        quick.addWidget(make_btn("🖌️", "Pincel  [B]", "brush"), 0, 1)
        quick.addWidget(make_btn("🧽", "Goma  [E]", "eraser"), 0, 2)
        quick.addWidget(make_btn("📏", "Línea  [L]", "line"), 1, 0)
        quick.addWidget(make_btn("⬜", "Rectángulo  [R]", "rect"), 1, 1)
        quick.addWidget(make_btn("🪣", "Relleno  [G]", "fill"), 1, 2)
        quick.addWidget(make_btn("✋", "Mover  [V]", "move"), 2, 0)
        quick.addWidget(make_btn("⭕", "Elipse  [O]", "ellipse"), 2, 1)
        quick.addWidget(make_btn("💧", "Cuentagotas  [I]", "eyedrop"), 2, 2)
        quick.addWidget(make_btn("🖊️", "Lápiz Vectorial", "vector_pencil"), 3, 0)
        quick.addWidget(make_btn("✒️", "Pincel Vectorial", "vector_brush"), 3, 1)
        layout.addLayout(quick)

        layout.addStretch()
        dock.setWidget(container)
        self.tools_dock = dock
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._docks.append(dock)

        self._set_tool("pencil")

    # ------------------------------------------------------------------
    # Inspector (color + estabilizador + opacidad pincel)
    # ------------------------------------------------------------------
    def _init_inspector_dock(self):
        dock      = QDockWidget("Color", self)
        dock.setFeatures(QDockWidget.DockWidgetClosable)  # Solo cierra
        container = QWidget()
        layout    = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.color_picker = ColorWheel()
        self.color_picker.color_changed.connect(self._on_color_changed)
        self.color_picker.setFixedSize(120, 140)
        layout.addWidget(self.color_picker)
        
        layout.addSpacing(8)
        
        # Opacidad del pincel
        layout.addWidget(QLabel("OPACIDAD DEL PINCEL"))
        op_row = QHBoxLayout()
        self.opacity_panel = OpacityPanel()
        self.opacity_panel.opacity_changed.connect(self._on_brush_opacity_changed)
        op_row.addWidget(self.opacity_panel)
        layout.addLayout(op_row)

        layout.addSpacing(8)

        # Panel de Difuminado
        layout.addWidget(QLabel("DIFUMINADO"))
        self.blur_panel = BlurPanel()
        self.blur_panel.radius_changed.connect(self._on_blur_radius_changed)
        self.blur_panel.strength_changed.connect(self._on_blur_strength_changed)
        layout.addWidget(self.blur_panel)
        self.blur_panel.hide()  # Oculto por defecto

        layout.addSpacing(8)

        # Panel de Acuarela
        layout.addWidget(QLabel("ACUARELA"))
        self.watercolor_panel = QWidget()
        wc_layout = QVBoxLayout(self.watercolor_panel)
        wc_layout.setContentsMargins(0, 0, 0, 0)
        wc_layout.setSpacing(6)

        def make_wc_slider(label_text, min_val, max_val, step, default, callback):
            row = QVBoxLayout()
            row.setSpacing(2)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #aaa; font-size: 10px;")
            row.addWidget(lbl)
            hrow = QHBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default)
            slider.valueChanged.connect(callback)
            val_label = QLabel(str(default))
            val_label.setFixedWidth(30)
            val_label.setStyleSheet("color: #888; font-size: 10px;")
            slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
            hrow.addWidget(slider)
            hrow.addWidget(val_label)
            row.addLayout(hrow)
            wc_layout.addLayout(row)
            return slider, val_label

        self.wc_wetness, self.wc_wetness_val = make_wc_slider("Humedad (Wetness)", 0, 100, 5, 60, self._on_wc_wetness_changed)
        self.wc_fringe, self.wc_fringe_val = make_wc_slider("Borde de Agua (Fringe)", 0, 100, 5, 35, self._on_wc_fringe_changed)
        self.wc_dilution, self.wc_dilution_val = make_wc_slider("Dilución", 0, 100, 5, 40, self._on_wc_dilution_changed)
        self.wc_texture, self.wc_texture_val = make_wc_slider("Textura de Papel", 0, 100, 5, 15, self._on_wc_texture_changed)

        self.watercolor_panel.hide()  # Oculto por defecto

        layout.addSpacing(8)

        # Panel de Brocha
        layout.addWidget(QLabel("BROCHA"))
        self.bristle_panel = QWidget()
        br_layout = QVBoxLayout(self.bristle_panel)
        br_layout.setContentsMargins(0, 0, 0, 0)
        br_layout.setSpacing(6)

        def make_br_slider(label_text, min_val, max_val, step, default, callback):
            row = QVBoxLayout()
            row.setSpacing(2)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #aaa; font-size: 10px;")
            row.addWidget(lbl)
            hrow = QHBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default)
            slider.valueChanged.connect(callback)
            val_label = QLabel(str(default))
            val_label.setFixedWidth(30)
            val_label.setStyleSheet("color: #888; font-size: 10px;")
            slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
            hrow.addWidget(slider)
            hrow.addWidget(val_label)
            row.addLayout(hrow)
            br_layout.addLayout(row)
            return slider, val_label

        self.br_count, self.br_count_val = make_br_slider("Cerdas", 10, 200, 5, 80, self._on_br_count_changed)
        self.br_spread, self.br_spread_val = make_br_slider("Dispersión", 0, 100, 5, 75, self._on_br_spread_changed)
        self.br_stiff, self.br_stiff_val = make_br_slider("Rigidez", 0, 100, 5, 60, self._on_br_stiff_changed)
        self.br_aspect, self.br_aspect_val = make_br_slider("Ancho (Aspecto)", 10, 60, 2, 30, self._on_br_aspect_changed)
        self.br_aspect_val.setText("3.0x")

        self.bristle_panel.hide()

        layout.addSpacing(8)

        # Estabilizador
        layout.addWidget(QLabel("ESTABILIZADOR DE TRAZO"))
        stab_row = QHBoxLayout()
        self.stab_slider = QSlider(Qt.Horizontal)
        self.stab_slider.setRange(0, 10)
        self.stab_slider.setValue(0)
        self.stab_label = QLabel("Off")
        self.stab_label.setFixedWidth(30)
        self.stab_slider.valueChanged.connect(self._on_stab_changed)
        stab_row.addWidget(self.stab_slider)
        stab_row.addWidget(self.stab_label)
        layout.addLayout(stab_row)

        # --- Tamaño del pincel ---
        layout.addSpacing(8)
        lbl = QLabel("TAMAÑO DEL PINCEL")
        lbl.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        layout.addWidget(lbl)
        sz_row = QHBoxLayout()
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(3)
        self.size_label = QLabel("3 px")
        self.size_label.setFixedWidth(38)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        sz_row.addWidget(self.size_slider)
        sz_row.addWidget(self.size_label)
        layout.addLayout(sz_row)

        dock.setWidget(container)
        self.inspector_dock = dock
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self._docks.append(dock)

    def _init_layers_dock(self):
        dock = QDockWidget("Capas", self)
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.layer_panel = LayerPanel(self.canvas, self.project)
        dock.setWidget(self.layer_panel)
        self.layers_dock = dock
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self._docks.append(dock)

    def _init_timeline_dock(self):
        dock = QDockWidget("Línea de Tiempo", self)
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        self.timeline = TimelineWidget(self.canvas)
        dock.setWidget(self.timeline)
        self.timeline_dock = dock
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self._docks.append(dock)
        self.timeline.frame_changed.connect(lambda _: self.layer_panel.update_ui())

    # ------------------------------------------------------------------
    # Barra de estado
    # ------------------------------------------------------------------
    def _init_status_bar(self):
        sb = QStatusBar()
        sb.setFixedHeight(28)
        self.setStatusBar(sb)

        sb.addWidget(QLabel("Zoom:"))

        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(5, 800)
        self.zoom_spin.setValue(100)
        self.zoom_spin.setSuffix(" %")
        self.zoom_spin.setFixedWidth(80)
        self.zoom_spin.valueChanged.connect(self._on_zoom_spin_changed)
        sb.addWidget(self.zoom_spin)

        btn_fit = QPushButton("Ajustar")
        btn_fit.setFixedHeight(22)
        btn_fit.clicked.connect(self._zoom_fit)
        sb.addWidget(btn_fit)

        btn_100 = QPushButton("100%")
        btn_100.setFixedHeight(22)
        btn_100.clicked.connect(lambda: self._set_zoom_pct(100))
        sb.addWidget(btn_100)

        self.lbl_coords = QLabel("x: 0  y: 0")
        self.lbl_coords.setFixedWidth(120)
        sb.addPermanentWidget(self.lbl_coords)

        # Control de referencia de video
        self.lbl_ref_frame = QLabel("Sin ref")
        self.lbl_ref_frame.setFixedWidth(80)
        self.lbl_ref_frame.setStyleSheet("color: #888; font-size: 11px;")
        sb.addPermanentWidget(self.lbl_ref_frame)

        self.ref_opacity_slider = QSlider(Qt.Horizontal)
        self.ref_opacity_slider.setRange(0, 255)
        self.ref_opacity_slider.setValue(80)
        self.ref_opacity_slider.setFixedWidth(80)
        self.ref_opacity_slider.valueChanged.connect(self._on_ref_opacity_changed)
        sb.addPermanentWidget(self.ref_opacity_slider)

        self.lbl_tool = QLabel("Herramienta: Lápiz")
        self.lbl_tool.setFixedWidth(160)
        sb.addPermanentWidget(self.lbl_tool)

        # Toggle QuickShape
        self.btn_quickshape = QPushButton("⚡ QuickShape")
        self.btn_quickshape.setCheckable(True)
        self.btn_quickshape.setChecked(True)
        self.btn_quickshape.setFixedHeight(22)
        self.btn_quickshape.setToolTip("Detectar formas automáticamente (mantén presionado 650ms)")
        self.btn_quickshape.clicked.connect(self._on_quickshape_toggled)
        self._update_quickshape_btn()
        sb.addPermanentWidget(self.btn_quickshape)

    # ------------------------------------------------------------------
    # Menú
    # ------------------------------------------------------------------
    def _init_menu_bar(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("&Archivo")
        file_menu.addAction("📄 Nuevo Proyecto").triggered.connect(self._new_project)
        file_menu.addSeparator()
        file_menu.addAction("🎬 Importar Video...").triggered.connect(self._import_video)
        file_menu.addAction("🖼️ Importar Secuencia de Imágenes...").triggered.connect(self._import_image_sequence)
        file_menu.addAction("🖼️ Importar GIF...").triggered.connect(self._import_gif)
        file_menu.addAction("🖼️ Importar Imagen...").triggered.connect(self._import_image)
        file_menu.addSeparator()
        file_menu.addAction("💾 Exportar como Video...").triggered.connect(self._export_video)
        file_menu.addAction("💾 Exportar como GIF...").triggered.connect(self._export_gif)
        file_menu.addAction("📁 Exportar secuencia de imágenes...").triggered.connect(self._export_sequence)
        file_menu.addAction("🎨 Exportar como PSD...").triggered.connect(self._export_psd)
        file_menu.addAction("📷 Exportar fotograma actual (PNG)...").triggered.connect(self._export_current_frame_png)
        file_menu.addSeparator()
        file_menu.addAction("🎬 Exportar Time-lapse...").triggered.connect(self._export_timelapse)

        edit_menu = bar.addMenu("&Edición")
        edit_menu.addAction("↩ Deshacer  Ctrl+Z").triggered.connect(self.canvas.undo)
        edit_menu.addAction("↪ Rehacer  Ctrl+Y").triggered.connect(self.canvas.redo)

        view_menu = bar.addMenu("&Vista")
        view_menu.addAction("🖼️ Referencias").triggered.connect(self._show_reference)
        view_menu.addSeparator()
        view_menu.addAction("🔄 Restablecer paneles").triggered.connect(self._restore_docks)
        view_menu.addSeparator()
        view_menu.addAction("Zoom: Ajustar").triggered.connect(self._zoom_fit)
        view_menu.addAction("Zoom: 100%").triggered.connect(lambda: self._set_zoom_pct(100))
        view_menu.addAction("Zoom: 200%").triggered.connect(lambda: self._set_zoom_pct(200))
        view_menu.addAction("Zoom: 50%").triggered.connect(lambda: self._set_zoom_pct(50))

        windows_menu = bar.addMenu("&Ventanas")
        for dock in self._docks:
            windows_menu.addAction(dock.toggleViewAction())
        windows_menu.addSeparator()
        windows_menu.addAction("Restablecer paneles").triggered.connect(self._restore_docks)

        shortcuts_menu = bar.addMenu("⌨️ &Atajos")
        shortcuts_menu.addAction("Editar atajos de teclado...").triggered.connect(self._open_shortcut_editor)
        shortcuts_menu.addSeparator()
        shortcuts_menu.addAction("Papel cebolla...").triggered.connect(self._open_onion_config)

    # ------------------------------------------------------------------
    # Registro de atajos de teclado
    # ------------------------------------------------------------------
    def _load_shortcuts(self) -> dict:
        if os.path.exists(SHORTCUT_FILE):
            try:
                with open(SHORTCUT_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Completar con defaults si faltan claves
                merged = dict(DEFAULT_SHORTCUTS)
                merged.update(loaded)
                return merged
            except Exception:
                pass
        return dict(DEFAULT_SHORTCUTS)

    def _save_shortcuts(self):
        try:
            with open(SHORTCUT_FILE, "w", encoding="utf-8") as f:
                json.dump(self._shortcuts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _register_shortcuts(self):
        """Registra QShortcut para cada acción."""
        self._shortcut_objects: list[QShortcut] = []

        actions = {
            # Herramientas
            "Lápiz":               lambda: self._set_tool("pencil"),
            "Pincel":              lambda: self._set_tool("brush"),
            "Goma":                lambda: self._set_tool("eraser"),
            "Relleno":             lambda: self._set_tool("fill"),
            "Cuentagotas":         lambda: self._set_tool("eyedrop"),
            "Texto":              lambda: self._set_tool("text"),
            "Difuminar":          lambda: self._set_tool("blur"),
            "Aerógrafo":          lambda: self._set_tool("airbrush"),
            "Acuarela":           lambda: self._set_tool("watercolor"),
            "Línea":              lambda: self._set_tool("line"),
            "Rectángulo":         lambda: self._set_tool("rect"),
            "Elipse":             lambda: self._set_tool("ellipse"),
            "Mover capa":          lambda: self._set_tool("move"),
            "Lazo relleno libre":  lambda: self._set_tool("lasso_fill"),
            "Lazo relleno rect.":  lambda: self._set_tool("lasso_fill_rect"),
            "Lazo relleno elipse": lambda: self._set_tool("lasso_fill_ellipse"),
            "Selec. rect.":        lambda: self._set_tool("select_rect"),
            "Lazo borrador":      lambda: self._set_tool("lasso_eraser"),
            "Lazo selección":     lambda: self._set_tool("lasso_marquee"),
            "Selec. elipse":      lambda: self._set_tool("select_ellipse"),
            # Vector tools
            "Lápiz Vectorial":     lambda: self._set_tool("vector_pencil"),
            "Pincel Vectorial":    lambda: self._set_tool("vector_brush"),
            "Polilínea Curva":     lambda: self._set_tool("polyline"),
            "Relleno Polilínea":   lambda: self._set_tool("poly_fill"),
            # Editing
            "Deshacer":            self.canvas.undo,
            "Rehacer":             self.canvas.redo,
            # Animation
            "Play / Stop":        lambda: self.timeline.btn_play.toggle(),
            "Frame anterior":      self.timeline.prev_frame,
            "Frame siguiente":     self.timeline.next_frame,
            # Vista
            "Zoom +":              lambda: self._set_zoom_pct(int(self.canvas.zoom * 115)),
            "Zoom -":              lambda: self._set_zoom_pct(int(self.canvas.zoom * 87)),
            "Zoom ajustar":        self._zoom_fit,
            "Zoom 100%":           lambda: self._set_zoom_pct(100),
        }

        for name, fn in actions.items():
            key = self._shortcuts.get(name, "")
            
            # Manejar mouse buttons
            if key in ("LeftButton", "RightButton", "MiddleButton",
                    "Ctrl+LeftButton", "Ctrl+RightButton", "Ctrl+MiddleButton",
                    "Alt+LeftButton", "Alt+RightButton", "Alt+MiddleButton",
                    "Shift+LeftButton", "Shift+RightButton", "Shift+MiddleButton"):
                self._mouse_shortcuts[key] = fn
                continue
            
            if key:
                try:
                    sc = QShortcut(QKeySequence(key), self)
                    sc.activated.connect(fn)
                    self._shortcut_objects.append(sc)
                except Exception:
                    pass

        # Shortcut global: Enter finaliza polyline/poly_fill sin importar foco
        sc_enter = QShortcut(QKeySequence("Return"), self)
        sc_enter.activated.connect(self._finalize_drawing_tool)
        self._shortcut_objects.append(sc_enter)

        sc_enter2 = QShortcut(QKeySequence("Enter"), self)
        sc_enter2.activated.connect(self._finalize_drawing_tool)
        self._shortcut_objects.append(sc_enter2)

        # Shortcut global: Escape cancela polyline/poly_fill
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self._cancel_drawing_tool)
        self._shortcut_objects.append(sc_esc)

        # Shortcut: Tab alterna aspecto de la brocha (horizontal/vertical)
        sc_tab = QShortcut(QKeySequence("Tab"), self)
        sc_tab.activated.connect(self._toggle_bristle_orientation)
        self._shortcut_objects.append(sc_tab)
        self._bristle_vertical = False

    def _open_shortcut_editor(self):
        dlg = ShortcutEditor(self._shortcuts, self)
        dlg.shortcuts_changed.connect(self._apply_new_shortcuts)
        dlg.exec()

    def _open_onion_config(self):
        dlg = OnionSkinConfigDialog(self.canvas, self)
        dlg.exec()

    def _apply_new_shortcuts(self, new_shortcuts: dict):
        self._shortcuts = new_shortcuts
        self._save_shortcuts()
        # Eliminar atajos viejos
        for sc in self._shortcut_objects:
            sc.setParent(None)
        self._shortcut_objects = []
        # Re-registrar
        self._register_shortcuts()

    # ------------------------------------------------------------------
    # Herramientas
    # ------------------------------------------------------------------
    _TOOL_LABELS = {
        "pencil":              "Lápiz",
        "brush":               "Pincel",
        "eraser":              "Goma",
        "fill":                "Relleno",
        "eyedrop":             "Cuentagotas",
        "text":                "Texto",
        "blur":                "Difuminar",
        "airbrush":            "Aerógrafo",
        "watercolor":          "Acuarela",
        "bristle":             "Brocha",
        "line":                "Línea",
        "rect":                "Rectángulo",
        "ellipse":             "Elipse",
        "move":                "Mover capa",
        "move_selection":     "Mover selección",
        "lasso_fill":          "Lazo relleno libre",
        "lasso_fill_rect":     "Lazo relleno rect.",
        "lasso_fill_ellipse":  "Lazo relleno elipse",
        "select_rect":         "Selec. rect.",
        "lasso_eraser":        "Lazo borrador",
        "lasso_marquee":       "Lazo selección",
        "select_ellipse":      "Selec. elipse",
        "polyline":            "Polilínea Curva",
        "poly_fill":           "Relleno Polilínea",
    }

    def _set_tool(self, name: str):
        for btn in set(self.tool_buttons.values()):
            btn.setChecked(False)
        if name in self.tool_buttons:
            self.tool_buttons[name].setChecked(True)
        self.canvas.set_tool(name)

        tool = self.canvas.tools.get(name)
        if tool:
            sz = None
            if hasattr(tool, "width"): sz = int(tool.width)
            elif hasattr(tool, "size"): sz = int(tool.size)
            elif hasattr(tool, "radius"): sz = int(tool.radius)
            if sz is not None:
                self.size_slider.blockSignals(True)
                self.size_slider.setValue(sz)
                self.size_slider.blockSignals(False)
                self.size_label.setText(f"{sz} px")

        # Mostrar/ocultar panel de blur
        if name == "blur":
            self.blur_panel.show()
            if tool:
                self.blur_panel.set_radius(int(tool.radius))
                self.blur_panel.set_strength(tool.strength)
            self.watercolor_panel.hide()
        elif name == "watercolor":
            self.blur_panel.hide()
            self.bristle_panel.hide()
            self.watercolor_panel.show()
            if tool:
                self.wc_wetness.blockSignals(True)
                self.wc_wetness.setValue(int(tool.wetness * 100))
                self.wc_wetness_val.setText(str(int(tool.wetness * 100)))
                self.wc_wetness.blockSignals(False)

                self.wc_fringe.blockSignals(True)
                self.wc_fringe.setValue(int(tool.fringe * 100))
                self.wc_fringe_val.setText(str(int(tool.fringe * 100)))
                self.wc_fringe.blockSignals(False)

                self.wc_dilution.blockSignals(True)
                self.wc_dilution.setValue(int(tool.dilution * 100))
                self.wc_dilution_val.setText(str(int(tool.dilution * 100)))
                self.wc_dilution.blockSignals(False)

                self.wc_texture.blockSignals(True)
                self.wc_texture.setValue(int(tool.texture_strength * 100))
                self.wc_texture_val.setText(str(int(tool.texture_strength * 100)))
                self.wc_texture.blockSignals(False)
        elif name == "bristle":
            self.blur_panel.hide()
            self.watercolor_panel.hide()
            self.bristle_panel.show()
            self._bristle_vertical = False
            if tool:
                self.br_count.blockSignals(True)
                self.br_count.setValue(tool.bristle_count)
                self.br_count_val.setText(str(tool.bristle_count))
                self.br_count.blockSignals(False)

                self.br_spread.blockSignals(True)
                self.br_spread.setValue(int(tool.bristle_spread * 100))
                self.br_spread_val.setText(str(int(tool.bristle_spread * 100)))
                self.br_spread.blockSignals(False)

                self.br_stiff.blockSignals(True)
                self.br_stiff.setValue(int(tool.stiffness * 100))
                self.br_stiff_val.setText(str(int(tool.stiffness * 100)))
                self.br_stiff.blockSignals(False)

                self.br_aspect.blockSignals(True)
                self.br_aspect.setValue(int(tool.aspect * 10))
                self.br_aspect_val.setText("V" if self._bristle_vertical else f"{tool.aspect:.1f}x")
                self.br_aspect.blockSignals(False)
        else:
            self.blur_panel.hide()
            self.watercolor_panel.hide()
            self.bristle_panel.hide()

        label = self._TOOL_LABELS.get(name, name)
        if hasattr(self, "lbl_tool"):
            self.lbl_tool.setText(f"Herramienta: {label}")

    def _finalize_drawing_tool(self):
        """Finaliza polyline/poly_fill desde cualquier contexto (shortcut global)."""
        tool = self.canvas.tools.get(self.canvas.current_tool)
        if tool and hasattr(tool, '_finalize') and getattr(tool, '_is_drawing', False):
            tool._finalize(self.canvas)

    def _cancel_drawing_tool(self):
        """Cancela polyline/poly_fill desde cualquier contexto (shortcut global)."""
        tool = self.canvas.tools.get(self.canvas.current_tool)
        if tool and hasattr(tool, '_cancel') and getattr(tool, '_is_drawing', False):
            tool._cancel(self.canvas)

    def _on_size_changed(self, val: int):
        self.size_label.setText(f"{val} px")
        name = self.canvas.current_tool
        tool = self.canvas.tools.get(name)
        if tool:
            if hasattr(tool, "width"):  tool.width  = val
            if hasattr(tool, "radius"): tool.radius = val
            if hasattr(tool, "size") and not hasattr(tool, "width"): tool.size = val
        self.canvas.update()

    def _on_color_changed(self, color):
        """Propaga el color del selector a todas las herramientas de dibujo."""
        for tool_name in ("pencil", "brush", "airbrush", "watercolor", "bristle", "lasso_fill",
                          "lasso_fill_rect", "lasso_fill_ellipse",
                          "line", "rect", "ellipse", "fill", "text", "curve", "poly_fill"):
            tool = self.canvas.tools.get(tool_name)
            if tool and hasattr(tool, "color"):
                tool.color = color

    def _on_brush_opacity_changed(self, val: int):
        """Aplicar opacidad a todas las herramientas de dibujo."""
        brush = self.canvas.tools.get("brush")
        if brush:
            brush.opacity = val
        pencil = self.canvas.tools.get("pencil")
        if pencil:
            pencil.opacity = val
        
        # Aerógrafo
        airbrush = self.canvas.tools.get("airbrush")
        if airbrush:
            airbrush.opacity = val
        
        # Brocha
        bristle = self.canvas.tools.get("bristle")
        if bristle:
            bristle.opacity = val
        
        # Goma
        eraser = self.canvas.tools.get("eraser")
        if eraser:
            eraser.opacity = val
        
        # Herramientas de forma
        for shape_tool in ("line", "rect", "ellipse", "curve"):
            tool = self.canvas.tools.get(shape_tool)
            if tool and hasattr(tool, "opacity"):
                tool.opacity = val
        
        # Actualizar el canvas para reflejar cambios
        self.canvas.update()

    def _on_stab_changed(self, val: int):
        from core.tools import get_shared_stabilizer
        stabilizer = get_shared_stabilizer()
        # Map 0-100 to 0-10
        stabilizer.set_stability(val // 10)
        self.stab_label.setText("Off" if val == 0 else str(val))

    def _on_blur_radius_changed(self, val: int):
        tool = self.canvas.tools.get("blur")
        if tool:
            tool.radius = val
            # Actualizar también el size slider si está sincronizado
            self.size_slider.blockSignals(True)
            self.size_slider.setValue(val)
            self.size_slider.blockSignals(False)
            self.size_label.setText(f"{val} px")

    def _on_blur_strength_changed(self, val: float):
        tool = self.canvas.tools.get("blur")
        if tool:
            tool.strength = max(0.05, min(1.0, val))

    def _on_wc_wetness_changed(self, val: int):
        tool = self.canvas.tools.get("watercolor")
        if tool:
            tool.wetness = val / 100.0

    def _on_wc_fringe_changed(self, val: int):
        tool = self.canvas.tools.get("watercolor")
        if tool:
            tool.fringe = val / 100.0

    def _on_wc_dilution_changed(self, val: int):
        tool = self.canvas.tools.get("watercolor")
        if tool:
            tool.dilution = val / 100.0

    def _on_wc_texture_changed(self, val: int):
        tool = self.canvas.tools.get("watercolor")
        if tool:
            tool.texture_strength = val / 100.0

    def _on_br_count_changed(self, val: int):
        tool = self.canvas.tools.get("bristle")
        if tool:
            tool.bristle_count = val

    def _on_br_spread_changed(self, val: int):
        tool = self.canvas.tools.get("bristle")
        if tool:
            tool.bristle_spread = val / 100.0

    def _on_br_stiff_changed(self, val: int):
        tool = self.canvas.tools.get("bristle")
        if tool:
            tool.stiffness = val / 100.0

    def _on_br_aspect_changed(self, val: int):
        tool = self.canvas.tools.get("bristle")
        if tool:
            tool.aspect = val / 10.0
            if hasattr(self, 'br_aspect_val'):
                self.br_aspect_val.setText(f"{tool.aspect:.1f}x")

    def _toggle_bristle_orientation(self):
        """Toggle bristle brush between horizontal and vertical."""
        tool = self.canvas.tools.get("bristle")
        if not tool:
            return
        if self._bristle_vertical:
            tool.aspect = 3.0
            self._bristle_vertical = False
        else:
            tool.aspect = 0.5
            self._bristle_vertical = True
        if hasattr(self, 'br_aspect_val'):
            self.br_aspect.blockSignals(True)
            self.br_aspect.setValue(int(tool.aspect * 10))
            self.br_aspect_val.setText(f"V" if self._bristle_vertical else "H")
            self.br_aspect.blockSignals(False)
        self.canvas.update()

    # ------------------------------------------------------------------
    # Zoom helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Event filter — ruedita del scroll
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self.canvas_scroll.viewport() and event.type() == QEvent.Wheel:
            delta = event.angleDelta().y()
            if delta:
                factor = 1.15 if delta > 0 else 1.0 / 1.15
                pos    = event.position().toPoint() if hasattr(event, "position") else event.pos()
                self._zoom_at_viewport_pos(pos, factor)
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def _on_zoom_spin_changed(self, pct: int):
        self.canvas.set_zoom(pct / 100.0)
    
    def _on_ref_opacity_changed(self, val: int):
        self.ref_opacity = val
        self.canvas.ref_opacity = val
        self.canvas.update()
    
    def _on_ref_frame_changed(self):
        """Actualiza frame de referencia en canvas."""
        if self.ref_frames:
            self.canvas.ref_image = self.ref_frames[self.ref_idx]
            self.canvas.update()
            self.lbl_ref_frame.setText(f"Ref: {self.ref_idx + 1}/{len(self.ref_frames)}")

    def _on_quickshape_toggled(self, checked: bool):
        """Toggle QuickShape on/off."""
        self.canvas._quickshape_enabled = checked
        if not checked:
            self.canvas._quickshape_timer.stop()
            if self.canvas._quickshape_active:
                self.canvas._cancel_quickshape()
        self._update_quickshape_btn()
    
    def _update_quickshape_btn(self):
        """Actualizar estilo del botón QuickShape."""
        if self.canvas._quickshape_enabled:
            self.btn_quickshape.setStyleSheet(
                "QPushButton { background: #005fa3; color: #fff; border: 1px solid #0078d7; "
                "border-radius: 3px; padding: 2px 8px; font-size: 11px; }"
                "QPushButton:hover { background: #0078d7; }"
            )
        else:
            self.btn_quickshape.setStyleSheet("")

    def _zoom_at_viewport_pos(self, viewport_pos, factor: float):
        old_zoom   = self.canvas.zoom
        canvas_pos = self.canvas.mapFrom(self.canvas_scroll.viewport(), viewport_pos)
        native_x   = canvas_pos.x() / old_zoom
        native_y   = canvas_pos.y() / old_zoom
        self.canvas.set_zoom(old_zoom * factor)
        new_x = native_x * self.canvas.zoom
        new_y = native_y * self.canvas.zoom
        self.canvas_scroll.horizontalScrollBar().setValue(int(new_x - viewport_pos.x()))
        self.canvas_scroll.verticalScrollBar().setValue(int(new_y - viewport_pos.y()))

    def _set_zoom_pct(self, pct: int):
        self.zoom_spin.setValue(pct)

    def _zoom_fit(self):
        avail_w = self.canvas_scroll.viewport().width()  - 20
        avail_h = self.canvas_scroll.viewport().height() - 20
        fit_x   = avail_w / self.canvas.res[0]
        fit_y   = avail_h / self.canvas.res[1]
        pct     = int(min(fit_x, fit_y) * 100)
        self._set_zoom_pct(max(5, pct))

    def _show_reference(self):
        self.reference_window.show()
        self.reference_window.raise_()
        self.reference_window.activateWindow()

    def _restore_docks(self):
        for dock in self._docks:
            dock.show()

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------
    def _import_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Video", "", "Videos (*.mp4 *.avi *.mov *.mkv);;Todos (*.*)"
        )
        if not path:
            return
        
        self.progress_dialog = QProgressDialog("Importando video...", "Cancelar", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        self.progress_dialog.setLabelText("Cargando video...")
        
        self.import_thread = VideoImportThread(path)
        self.import_thread.finished.connect(self._on_video_imported)
        self.import_thread.error.connect(self._on_import_error)
        self.import_thread.start()

    def _import_image_sequence(self):
        """Import all PNG/JPG images from a selected folder (one image per frame)."""
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con imágenes", ""
        )
        if not folder:
            return
        
        import os, re
        from PySide6.QtGui import QImage
        
        supported = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(supported)]
        
        if not files:
            QMessageBox.warning(self, "Error", "No se encontraron imágenes en la carpeta.")
            return
        
        files_sorted = sorted(files, key=lambda x: [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', x) if c])
        
        # Load first image to check size
        first_img = QImage(files_sorted[0])
        if first_img.isNull():
            QMessageBox.warning(self, "Error", "No se pudo cargar la primera imagen.")
            return
        
        img_w, img_h = first_img.width(), first_img.height()
        current_w, current_h = self.project.size
        
        # Preguntar si adaptar lienzo
        if (img_w, img_h) != (current_w, current_h):
            reply = QMessageBox.question(
                self, "Adaptar lienzo",
                f"Las imágenes son {img_w}x{img_h} y tu lienzo es {current_w}x{current_h}.\n¿Quieres adaptar el lienzo al tamaño de las imágenes?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.project.size = (img_w, img_h)
                self.canvas.res = (img_w, img_h)
                self.w, self.h = img_w, img_h
                self.canvas.setFixedSize(img_w, img_h)
                self.canvas._bg_cache = None
        
        # Clear frames and import
        self.project.frames = []
        self.project.current_frame_idx = 0
        frames_loaded = 0
        self.setUpdatesEnabled(False)
        
        try:
            for file_path in files_sorted:
                img = QImage(file_path)
                if img.isNull():
                    continue
                
                new_frame = AnimationFrame(self.project.size)
                
                if new_frame.layers:
                    painter = QPainter(new_frame.layers[0].image)
                    scaled_img = img.scaled(
                        self.project.size[0], self.project.size[1],
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    # Center image on canvas
                    x = (self.project.size[0] - scaled_img.width()) // 2
                    y = (self.project.size[1] - scaled_img.height()) // 2
                    painter.drawImage(x, y, scaled_img)
                    painter.end()
                
                self.project.frames.append(new_frame)
                frames_loaded += 1
            
            if self.project.frames:
                self.project.current_frame_idx = 0
            else:
                QMessageBox.warning(self, "Error", "No se pudo cargar ninguna imagen válida.")
                return
            
        finally:
            self.setUpdatesEnabled(True)
            self.canvas.update()
            if hasattr(self, 'timeline'):
                self.timeline.update_ui()
            if hasattr(self, 'layer_panel'):
                self.layer_panel.update_ui()
            
            QMessageBox.information(
                self, "Importación completada",
                f"Se importaron {frames_loaded} fotogramas desde:\n{folder}"
            )

    def _on_video_imported(self, frames: list, fps: int, size: tuple):
        if self.progress_dialog:
            self.progress_dialog.close()
        
        w, h = size
        if size != self.project.size:
            reply = QMessageBox.question(
                self, "Redimensionar lienzo",
                f"El video es {size[0]}×{size[1]} pero el lienzo es "
                f"{self.project.size[0]}×{self.project.size[1]}.\n"
                "¿Querés adaptar el lienzo al tamaño del video?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.project.size = (w, h)
                self.canvas.resize(w, h)
                self.project.fps = fps
        
        self.project.insert_frames_from_video(frames)
        self.project.fps = fps
        self.timeline.update_ui()
        self.canvas.update()
        
        QMessageBox.information(
            self, "Éxito",
            f"Video importado: {len(frames)} frames a {fps} FPS\n"
            f"Tamaño: {size[0]}×{size[1]}"
        )
        self.timeline.update_ui()
        self.canvas.update()
        
        if self.progress_dialog:
            self.progress_dialog.close()
        
        QMessageBox.information(
            self, "Video importado",
            f"✅ Lienzo ajustado a: {w} x {h}\n"
            f"✅ {num_frames} frames en la línea de tiempo\n"
            f"✅ FPS configurado a: {fps}"
        )
    
    def _import_gif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir GIF", "", "GIF Files (*.gif)")
        if not path:
            return
        try:
            frames, size = GifImporter.import_gif(path)
            self.project.insert_frames_from_video(frames)
            self.timeline.update_ui()
            self.canvas.update()
            QMessageBox.information(self, "Éxito", f"GIF importado: {len(frames)} frames.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar el GIF:\n{e}")

    def _import_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar Imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return

        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtCore import Qt

        img = QImage(path)
        if img.isNull():
            return

        img = img.scaled(self.w, self.h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        frame = self.project.get_current_frame()
        new_layer = frame.add_layer(f"Imagen {len([l for l in frame.layers if 'Imagen' in l.name]) + 1}")

        x = (self.w - img.width()) // 2
        y = (self.h - img.height()) // 2
        painter = QPainter(new_layer.image)
        painter.drawImage(x, y, img)
        painter.end()

        self.canvas.update()
        self.layer_panel.update_ui()

    def _resize_project(self, size: tuple):
        """Redimensiona el lienzo y el proyecto al nuevo tamaño."""
        from PySide6.QtGui import QImage
        self.w, self.h = size
        self.project.size = size
        self.canvas.res = size
        self.canvas.overlay_image = QImage(
            self.w, self.h, QImage.Format_ARGB32_Premultiplied
        )
        self.canvas.overlay_image.fill(Qt.transparent)
        self.canvas._bg_cache = None
        self.canvas._apply_zoom()

    def _on_import_error(self, msg: str):
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self, "Error", f"No se pudo importar el video:\n{msg}")

    def _export_video(self):
        print("[DEBUG] _export_video called")
        carpeta_base = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para exportar video", ""
        )
        print(f"[DEBUG] carpeta_base: {carpeta_base}")
        if not carpeta_base:
            return
        
        carpeta_proyecto = os.path.join(carpeta_base, self.project_name)
        os.makedirs(carpeta_proyecto, exist_ok=True)
        
        ext = "mp4" if self.project_name else "mp4"
        nombre_video = f"{self.project_name}.{ext}"
        path = os.path.join(carpeta_proyecto, nombre_video)
        print(f"[DEBUG] export path: {path}")
        
        try:
            import cv2
            import numpy as np
            from PySide6.QtGui import QImage

            w, h   = self.project.size
            fps    = self.project.fps
            fourcc = cv2.VideoWriter_fourcc(*("mp4v" if path.endswith(".mp4") else "XVID"))
            out    = cv2.VideoWriter(path, fourcc, fps, (w, h))

            progress = QProgressDialog(
                "Exportando video...", "Cancelar", 0, len(self.project.frames), self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, frame in enumerate(self.project.frames):
                if progress.wasCanceled():
                    break
                composite = frame.composite().convertToFormat(QImage.Format_RGB888)
                ptr = composite.bits()
                ptr.setsize(composite.sizeInBytes())
                arr = np.array(ptr).reshape((h, w, 3))
                out.write(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
                progress.setValue(i + 1)

            out.release()
            progress.close()
            QMessageBox.information(self, "Éxito", f"Video exportado:\n{path}")
        except ImportError:
            QMessageBox.critical(
                self, "Error",
                "Se necesita opencv-python y numpy.\n"
                "Instalá con:  pip install opencv-python numpy"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def _export_gif(self):
        carpeta_base = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para exportar GIF", ""
        )
        if not carpeta_base:
            return
        
        carpeta_proyecto = os.path.join(carpeta_base, self.project_name)
        os.makedirs(carpeta_proyecto, exist_ok=True)
        
        path = os.path.join(carpeta_proyecto, f"{self.project_name}.gif")
        
        try:
            from PIL import Image as PILImage
            import numpy as np
            from PySide6.QtGui import QImage

            w, h   = self.project.size
            fps    = max(1, self.project.fps)
            delay  = int(1000 / fps)

            progress = QProgressDialog(
                "Exportando GIF...", "Cancelar", 0, len(self.project.frames), self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            pil_frames = []
            for i, frame in enumerate(self.project.frames):
                if progress.wasCanceled():
                    break
                composite = frame.composite().convertToFormat(QImage.Format_RGBA8888)
                ptr = composite.bits()
                ptr.setsize(composite.sizeInBytes())
                data = np.array(ptr).tobytes()
                pil_img = PILImage.frombytes("RGBA", (w, h), data)
                pil_frames.append(pil_img.convert("RGBA"))
                progress.setValue(i + 1)

            progress.close()
            if pil_frames:
                pil_frames[0].save(
                    path, save_all=True, append_images=pil_frames[1:],
                    loop=0, duration=delay, disposal=2
                )
                QMessageBox.information(self, "Éxito", f"GIF exportado:\n{path}")
        except ImportError:
            QMessageBox.critical(
                self, "Error", "Se necesita Pillow.\nInstalá con:  pip install Pillow"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def _export_sequence(self):
        carpeta_base = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta BASE para exportar", ""
        )
        if not carpeta_base:
            return
        
        carpeta_proyecto = os.path.join(carpeta_base, self.project_name)
        os.makedirs(carpeta_proyecto, exist_ok=True)
        
        try:
            from PySide6.QtGui import QImage
            
            w, h = self.project.size
            num_frames = len(self.project.frames)
            
            progress = QProgressDialog(
                "Exportando secuencia...", "Cancelar", 0, num_frames, self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            for i, frame in enumerate(self.project.frames):
                if progress.wasCanceled():
                    break
                
                composite = frame.composite()
                
                nombre = f"frame_{i+1:04d}.png"
                ruta = os.path.join(carpeta_proyecto, nombre)
                composite.save(ruta)
                
                progress.setValue(i + 1)
            
            progress.close()
            
            QMessageBox.information(
                self, "Éxito", 
                f"✅ Proyecto: {self.project_name}\n"
                f"📁 Guardado en:\n{carpeta_proyecto}\n\n"
                f"🖼️ {num_frames} imágenes exportadas"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def _export_psd(self):
        """Export current project as PSD with layers."""
        try:
            from psd_tools import PSDImage
            from PIL import Image
            from PySide6.QtGui import QImage
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta psd-tools.\nEjecutá: pip install psd-tools")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar como PSD", "", "Archivo PSD (*.psd)"
        )
        if not path:
            return

        try:
            frame = self.project.get_current_frame()
            w, h = self.project.size

            # Composite all layers into base image
            composite = frame.composite()
            base_img = Image.fromarray(
                np.frombuffer(composite.bits(), dtype=np.uint8)
                .reshape((h, w, 4))[:, :, :3]
            )

            psd = PSDImage.frompil(base_img)

            # Add each layer as a PSD layer
            num_layers = len(frame.layers)
            for i, layer in enumerate(reversed(frame.layers)):
                if hasattr(layer, 'is_vector') and layer.is_vector:
                    # Render vector layer to image
                    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
                    img.fill(0)
                    p = QPainter(img)
                    layer.draw_all(p)
                    p.end()
                    rgb = img.convertToFormat(QImage.Format_RGB888)
                    arr = np.frombuffer(rgb.bits(), dtype=np.uint8).reshape((h, w, 3))
                else:
                    arr = np.frombuffer(layer.image.bits(), dtype=np.uint8).reshape((h, w, 4))[:, :, :3]

                pil_img = Image.fromarray(arr)
                psd_layer = psd.create_pixel_layer(pil_img)
                psd_layer.name = layer.name
                psd_layer.opacity = layer.opacity / 255.0

            psd.save(path)
            QMessageBox.information(self, "PSD exportado", f"✅ Guardado:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar PSD", str(e))

    def _export_current_frame_png(self):
        """Exporta el fotograma actual como PNG."""
        if not self.project:
            QMessageBox.warning(self, "Exportar", "No hay proyecto abierto.")
            return
        
        frame = self.project.get_current_frame()
        if not frame:
            QMessageBox.warning(self, "Exportar", "No hay fotogramas en el proyecto.")
            return
        
        # Componer el fotograma (todas las capas visibles)
        img = frame.composite()
        
        # Pedir ruta de guardado
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar fotograma actual como PNG",
            f"fotograma_{self.project.current_frame_idx + 1}.png",
            "Imágenes PNG (*.png)"
        )
        
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            success = img.save(path, "PNG")
            if success:
                QMessageBox.information(self, "Exportar", f"Fotograma exportado:\n{path}")
            else:
                QMessageBox.critical(self, "Error", "No se pudo guardar la imagen.")

    def _export_timelapse(self):
        """Export all project frames as a time-lapse compressed into fixed duration."""
        if not self.project or not self.project.frames:
            QMessageBox.warning(self, "Time-lapse", "No hay frames en la línea de tiempo.")
            return

        # Show duration dialog
        durations = [10, 30, 60]
        dur_labels = ["10 segundos", "30 segundos", "1 minuto"]
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Exportar Time-lapse")
        dlg.setModal(True)
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Resumir toda la animación en:"))
        combo = QComboBox()
        combo.addItems(dur_labels)
        layout.addWidget(combo)
        
        btn_export = QPushButton("🎬 Exportar")
        btn_export.clicked.connect(dlg.accept)
        layout.addWidget(btn_export)
        
        if dlg.exec() != QDialog.Accepted:
            return

        duration = durations[combo.currentIndex()]

        # Create exporter
        from core.recorder import TimelapseExporter
        exporter = TimelapseExporter(self.project, self)
        exporter.duration = duration
        exporter.export_started.connect(lambda n: print(f"Exportando {n} frames..."))
        exporter.export_complete.connect(
            lambda p: QMessageBox.information(self, "Time-lapse completo", f"Exportado:\n{p}")
        )
        exporter.export_error.connect(
            lambda e: QMessageBox.critical(self, "Error", e)
        )
        exporter.export()

    def _new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.w            = data['width']
            self.h            = data['height']
            self.project_name = data['name']
            self.bg_mode      = data['bg']
            self.project      = AnimationProject(
                width=self.w, height=self.h,
                name=self.project_name,
            )
            self.project._bg_mode = self.bg_mode
            self.canvas.res     = (self.w, self.h)
            self.canvas.project = self.project
            self.canvas.overlay_image = __import__('PySide6.QtGui', fromlist=['QImage']).QImage(
                self.w, self.h,
                __import__('PySide6.QtGui', fromlist=['QImage']).QImage.Format_ARGB32_Premultiplied
            )
            self.canvas.overlay_image.fill(Qt.transparent)
            self.canvas.set_bg_mode(self.bg_mode)
            self.canvas._bg_cache = None
            self.canvas._apply_zoom()
            self.timeline.canvas  = self.canvas
            self.layer_panel.canvas = self.canvas
            self.setWindowTitle(f"Animatix Pro — {self.project_name}")
            self.timeline.update_ui()
            self.layer_panel.update_ui()


# ============================================================
# Punto de entrada
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = NewProjectDialog()
    if dialog.exec():
        data   = dialog.get_data()
        window = AnimatixPro(data)
        window.show()
        sys.exit(app.exec())
