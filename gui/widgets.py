# gui/widgets.py
"""UI widgets for Animatix Pro."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QScrollArea,
    QToolButton, QSizePolicy, QAbstractItemView, QListWidget, QListWidgetItem,
    QSpinBox, QComboBox, QPushButton
)
from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QTimer
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QDrag, QLinearGradient, QBrush, QFont
)
from core.models import AnimationProject, AnimationFrame, AnimationLayer


# ============================================================
# ColorWheel - Simple color picker widget with brightness slider
# ============================================================
class ColorWheel(QWidget):
    color_changed = Signal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(0, 0, 0)
        self._value = 255
        self.setFixedSize(80, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self._wheel = QWidget()
        self._wheel.setFixedSize(80, 80)
        self._wheel.setStyleSheet("""
            QWidget { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff0000, stop:0.17#ffff00, stop:0.33#00ff00,
                    stop:0.5#00ffff, stop:0.67#0000ff, stop:0.83#ff00ff,
                    stop:1 #ff0000);
                border: 2px solid #444; border-radius: 40px;
            }
        """)
        
        self.val_slider = QSlider(Qt.Horizontal)
        self.val_slider.setRange(0, 255)
        self.val_slider.setValue(255)
        self.val_slider.setFixedHeight(16)
        self.val_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #333;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 8px;
                margin: -2px 0;
                background: #fff;
                border-radius: 2px;
            }
        """)
        self.val_slider.valueChanged.connect(self._on_val_changed)
        
        layout.addWidget(self._wheel)
        layout.addWidget(self.val_slider)
    
    def _on_val_changed(self, val):
        self._value = val
        h, s, _ = self._color.hsv()
        self._color = QColor.fromHsv(h, s, val)
        self.color_changed.emit(self._color)
    
    def mousePressEvent(self, event):
        self._pick_color(event.position().toPoint())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick_color(event.position().toPoint())
        super().mouseMoveEvent(event)
    
    def _pick_color(self, pos):
        import math
        cx, cy = self._wheel.width() / 2, self._wheel.height() / 2
        x, y = pos.x() - cx, pos.y() - cy
        
        angle = math.atan2(y, x)
        hue = int((angle + math.pi) / (2 * math.pi) * 360)
        hue = max(0, min(360, hue))
        
        dist = math.hypot(x, y)
        max_dist = min(cx, cy)
        sat = int(dist / max_dist * 255)
        sat = max(0, min(255, sat))
        
        self._color = QColor.fromHsv(hue, sat, self._value)
        self.color_changed.emit(self._color)
    
    def mousePressEvent(self, event):
        self._pick_color(event.position().toPoint())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick_color(event.position().toPoint())
        super().mouseMoveEvent(event)
    
    def _pick_color(self, pos):
        import math
        cx, cy = self.width() / 2, self.height() / 2
        x, y = pos.x() - cx, pos.y() - cy
        
        angle = math.atan2(y, x)
        hue = int((angle + math.pi) / (2 * math.pi) * 360)
        hue = max(0, min(360, hue))
        
        dist = math.hypot(x, y)
        max_dist = min(cx, cy)
        sat = int(dist / max_dist * 255)
        sat = max(0, min(255, sat))
        
        self._color = QColor.fromHsv(hue, sat, self._value)
        self.color_changed.emit(self._color)
    
    def set_value(self, val: int):
        self._value = val
    
    def current_color(self) -> QColor:
        return self._color
    
    def set_color(self, color: QColor):
        self._color = color
        self.color_changed.emit(color)


# ============================================================
# LayerRow - Individual layer row with drag & drop
# ============================================================
class LayerRow(QWidget):
    selected = Signal(int)
    visibility_changed = Signal(int, bool)
    layer_moved = Signal(int, int)  # from_idx, to_idx

    THUMB_W = 42
    THUMB_H = 30

    def __init__(self, layer, index: int, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self._layer = layer
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)

        bg = "#2a4a6a" if is_current else "#252525"
        self.setStyleSheet(
            f"QWidget {{ background-color: {bg}; border-bottom: 1px solid #333; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.btn_eye = QToolButton()
        self.btn_eye.setText("👁" if layer.visible else "🚫")
        self.btn_eye.setFixedSize(24, 24)
        self.btn_eye.setStyleSheet(
            "QToolButton { background: transparent; border: none; font-size: 14px; }"
        )
        self.btn_eye.clicked.connect(
            lambda: self.visibility_changed.emit(self.index, not layer.visible)
        )

        thumb_label = QLabel()
        thumb_label.setFixedSize(self.THUMB_W, self.THUMB_H)
        thumb_label.setStyleSheet("background: #111; border: 1px solid #444;")
        thumb = layer.image.scaled(
            self.THUMB_W, self.THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        thumb_label.setPixmap(QPixmap.fromImage(thumb))

        name_label = QLabel(layer.name)
        name_label.setStyleSheet(
            "color: #ddd; font-size: 11px; background: transparent;"
        )
        name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        op_label = QLabel(f"{int(layer.opacity / 255 * 100)}%")
        op_label.setFixedWidth(35)
        op_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        op_label.setStyleSheet("color: #888; font-size: 10px; background: transparent;")

        layout.addWidget(self.btn_eye)
        layout.addWidget(thumb_label)
        layout.addWidget(name_label)
        layout.addWidget(op_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_start_pos'):
            diff = event.pos() - self._drag_start_pos
            if diff.manhattanLength() > 10:
                self._start_drag()
                del self._drag_start_pos
        super().mouseMoveEvent(event)

    def _start_drag(self):
        mime = QMimeData()
        mime.setText(str(self.index))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        event.accept()
        self.setStyleSheet("QWidget { background-color: #3a5a7a; border-bottom: 2px solid #0078d7; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("QWidget { background-color: #252525; border-bottom: 1px solid #333; }")

    def dropEvent(self, event):
        try:
            from_idx = int(event.mimeData().text())
            to_idx = self.index
            if from_idx != to_idx:
                self.layer_moved.emit(from_idx, to_idx)
        except:
            pass
        self.setStyleSheet("QWidget { background-color: #252525; border-bottom: 1px solid #333; }")


# ============================================================
# LayerPanel
# ============================================================
class LayerPanel(QWidget):
    def __init__(self, canvas_reference, project=None):
        super().__init__()
        self.canvas = canvas_reference
        self.setMinimumWidth(200)

        self.setStyleSheet("""
            QWidget { background-color: #1a1a1a; }
            QPushButton {
                background-color: #2d2d2d; color: #ddd;
                border: 1px solid #444; border-radius: 3px;
                padding: 3px 8px; font-size: 12px;
            }
            QPushButton:hover  { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #00aa00; color: #fff; }
            QLabel { color: #aaa; font-size: 11px; }
            QSlider::groove:horizontal { height: 4px; background: #444; }
            QSlider::handle:horizontal {
                background: #0078d7; width: 10px; margin: -3px 0; border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background-color: #252525; border-bottom: 1px solid #333;")
        header.setFixedHeight(34)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(6, 2, 6, 2)
        hl.setSpacing(4)

        lbl = QLabel("CAPAS")
        lbl.setStyleSheet("color: #bbb; font-weight: bold; font-size: 11px; background: transparent;")

        self.btn_add_layer = QPushButton("＋")
        self.btn_add_layer.setFixedWidth(28)
        self.btn_del_layer = QPushButton("－")
        self.btn_del_layer.setFixedWidth(28)
        self.btn_dup_layer = QPushButton("⧉")
        self.btn_dup_layer.setFixedWidth(28)
        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedWidth(28)
        self.btn_down = QPushButton("↓")
        self.btn_down.setFixedWidth(28)
        self.btn_merge = QPushButton("⊞")
        self.btn_merge.setFixedWidth(28)
        self.btn_merge.setToolTip("Fusionar con capa inferior")

        hl.addWidget(lbl)
        hl.addStretch()
        hl.addWidget(self.btn_up)
        hl.addWidget(self.btn_down)
        hl.addWidget(self.btn_merge)
        hl.addWidget(self.btn_dup_layer)
        hl.addWidget(self.btn_del_layer)
        hl.addWidget(self.btn_add_layer)
        layout.addWidget(header)

        op_widget = QWidget()
        op_widget.setStyleSheet("background: #1e1e1e; border-bottom: 1px solid #2a2a2a;")
        op_widget.setFixedHeight(30)
        ol = QHBoxLayout(op_widget)
        ol.setContentsMargins(8, 2, 8, 2)
        lbl_op = QLabel("Opacidad:")
        lbl_op.setStyleSheet("background: transparent;")
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(0, 255)
        self.op_slider.setValue(255)
        self.op_label = QLabel("100%")
        self.op_label.setFixedWidth(35)
        self.op_label.setStyleSheet("background: transparent;")
        ol.addWidget(lbl_op)
        ol.addWidget(self.op_slider)
        ol.addWidget(self.op_label)
        layout.addWidget(op_widget)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll)

        self.btn_add_layer.clicked.connect(self.add_layer)
        self.btn_del_layer.clicked.connect(self.del_layer)
        self.btn_dup_layer.clicked.connect(self.dup_layer)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        self.btn_merge.clicked.connect(self.merge_layer)
        self.op_slider.valueChanged.connect(self._on_opacity_changed)

    def add_layer(self):
        if self.canvas.project:
            self.canvas.project.get_current_frame().add_layer()
            self.update_ui()

    def del_layer(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            if len(frame.layers) > 1:
                frame.remove_layer(frame.current_layer_idx)
                self.update_ui()

    def dup_layer(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.add_layer(frame.current_layer.name + " (copy)")
            self.update_ui()

    def move_up(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            idx = frame.current_layer_idx
            if idx > 0:
                frame.move_layer(idx, idx - 1)
                self.update_ui()

    def move_down(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            idx = frame.current_layer_idx
            if idx < len(frame.layers) - 1:
                frame.move_layer(idx, idx + 1)
                self.update_ui()

    def merge_layer(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            idx = frame.current_layer_idx
            if idx < len(frame.layers) - 1:
                # Merge current layer into below one
                lower = frame.layers[idx + 1]
                current = frame.layers[idx]
                p = QPainter(lower.image)
                p.drawImage(0, 0, current.image)
                p.end()
                frame.remove_layer(idx)
                self.update_ui()
                self.canvas.update()

    def _on_opacity_changed(self, val: int):
        self.op_label.setText(f"{int(val / 255 * 100)}%")
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.current_layer.opacity = val
            self.canvas.update()

    def _on_layer_selected(self, index: int):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.current_layer_idx = index
            self._sync_opacity()

    def _on_visibility_changed(self, index: int, visible: bool):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.layers[index].visible = visible
            self.canvas.update()

    def _on_layer_moved(self, from_idx: int, to_idx: int):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.move_layer(from_idx, to_idx)
            # Update selection
            frame.current_layer_idx = to_idx
            self.update_ui()
            self.canvas.update()

    def _sync_opacity(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            layer = frame.current_layer
            self.op_slider.blockSignals(True)
            self.op_slider.setValue(layer.opacity)
            self.op_slider.blockSignals(False)
            self.op_label.setText(f"{int(layer.opacity / 255 * 100)}%")

    def update_ui(self):
        if not self.canvas.project:
            return
        frame = self.canvas.project.get_current_frame()
        current_idx = frame.current_layer_idx

        # Clear existing rows
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

# Add new rows
        for i, layer in enumerate(frame.layers):
            row = LayerRow(layer, i, is_current=(i == current_idx))
            row.selected.connect(self._on_layer_selected)
            row.visibility_changed.connect(self._on_visibility_changed)
            row.layer_moved.connect(self._on_layer_moved)
            self.list_layout.insertWidget(i, row)


# ============================================================
# TimelineListWidget - List with playhead indicator
# ============================================================
class TimelineListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_frame = 0

    def set_current_frame(self, idx):
        self.current_frame = idx
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.current_frame < self.count():
            item = self.item(self.current_frame)
            if item:
                painter = QPainter(self.viewport())
                pen = painter.pen()
                pen.setColor(QColor("#00ff00"))
                pen.setWidth(2)
                painter.setPen(pen)
                rect = self.visualRect(self.model().index(self.current_frame, 0))
                painter.drawLine(rect.left(), 0, rect.left(), self.height())
                painter.drawLine(rect.right(), 0, rect.right(), self.height())


# ============================================================
# Timeline Widget
# ============================================================
class TimelineWidget(QWidget):
    frame_changed = Signal(int)
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setFixedHeight(120)

        self.setStyleSheet("""
            QWidget { background-color: #1a1a1a; }
            QPushButton {
                background-color: #2d2d2d; color: #ddd;
                border: 1px solid #444; border-radius: 3px;
                padding: 4px 12px; font-size: 12px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #00aa00; color: #fff; }
            QPushButton:checked { background-color: #00aa00; border-color: #00ff00; }
            QLabel { color: #aaa; font-size: 11px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #252525;")
        toolbar.setFixedHeight(36)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 2, 8, 2)

        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedWidth(36)
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedWidth(30)
        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedWidth(30)
        
        self.lbl_frame = QLabel("1")
        self.lbl_frame.setStyleSheet("color: #ddd; font-size: 14px; font-weight: bold;")
        
        self.btn_add = QPushButton("＋")
        self.btn_add.setFixedWidth(30)
        self.btn_add.setEnabled(True)
        self.btn_del = QPushButton("－")
        self.btn_del.setFixedWidth(30)
        
        self.fps_spin = QSlider(Qt.Horizontal)
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(24)
        self.fps_spin.setFixedWidth(80)
        
        self.lbl_fps = QLabel("24 FPS")
        
        tl.addWidget(self.btn_play)
        tl.addWidget(self.btn_prev)
        tl.addWidget(self.lbl_frame)
        tl.addWidget(self.btn_next)
        tl.addStretch()
        tl.addWidget(self.lbl_fps)
        tl.addWidget(self.fps_spin)
        tl.addWidget(self.btn_add)
        tl.addWidget(self.btn_del)
        
        layout.addWidget(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: #111; border: none; }")

        self.list = TimelineListWidget()
        self.list.setFlow(QListWidget.LeftToRight)
        self.list.setSpacing(4)
        self.list.setMinimumHeight(70)
        self.list.setStyleSheet("""
            QListWidget { background-color: #111; border: none; }
            QListWidget::item { 
                background-color: #252525; 
                border: 1px solid #333;
                border-radius: 3px;
            }
            QListWidget::item:selected { 
                background-color: #005fa3; 
                border: 1px solid #0078d7;
            }
        """)
        
        self.scroll.setWidget(self.list)
        layout.addWidget(self.scroll)

    def set_project(self, proj):
        self.proj = proj
        self.btn_play.toggled.connect(self._on_play_toggled)
        self.btn_prev.clicked.connect(self.prev_frame)
        self.btn_next.clicked.connect(self.next_frame)
        self.btn_add.clicked.connect(self.add_frame)
        self.btn_del.clicked.connect(self.del_frame)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        self.list.currentRowChanged.connect(self._on_frame_selected)

    def update_ui(self):
        if not self.canvas.project:
            return
        proj = self.canvas.project
        mode = proj.play_mode
        
        self.fps_spin.blockSignals(True)
        self.fps_spin.setValue(proj.fps)
        self.fps_spin.blockSignals(False)
        self.lbl_fps.setText(f"{proj.fps} FPS")
        
        self.lbl_frame.setText(f"{proj.current_frame_idx + 1}")
        
        self.list.set_current_frame(proj.current_frame_idx)
        
        self.list.clear()
        for i, frame in enumerate(proj.frames):
            item = QListWidgetItem(f"F{i+1}")
            if i == proj.current_frame_idx:
                item.setSelected(True)
            self.list.addItem(item)
        
        self.list.setCurrentRow(proj.current_frame_idx)
        
        # Enable/disable buttons
        self.btn_del.setEnabled(len(proj.frames) > 1)
        self.btn_prev.setEnabled(proj.current_frame_idx > 0)
        self.btn_next.setEnabled(proj.current_frame_idx < len(proj.frames) - 1)

    def prev_frame(self):
        if self.canvas.project:
            self.canvas.project.prev_frame()
            self.update_ui()
            self.canvas.update()
            self.frame_changed.emit(self.canvas.project.current_frame_idx)

    def next_frame(self):
        if self.canvas.project:
            self.canvas.project.next_frame()
            self.update_ui()
            self.canvas.update()
            self.frame_changed.emit(self.canvas.project.current_frame_idx)

    def add_frame(self):
        print(f"[DEBUG] add_frame called, canvas: {self.canvas}, project: {getattr(self.canvas, 'project', 'NO_PROJECT_ATTR')}")
        if self.canvas and self.canvas.project:
            self.canvas.project.add_frame()
            self.update_ui()
            print(f"[DEBUG] added frame, total frames: {len(self.canvas.project.frames)}")

    def del_frame(self):
        if self.canvas.project and len(self.canvas.project.frames) > 1:
            idx = self.canvas.project.current_frame_idx
            self.canvas.project.remove_frame(idx)
            self.update_ui()

    def _on_play_toggled(self, checked):
        if checked:
            self._start_playback()
        else:
            self._stop_playback()

    def _on_fps_changed(self, val):
        if self.canvas.project:
            self.canvas.project.fps = val
            self.lbl_fps.setText(f"{val} FPS")

    def _on_frame_selected(self, idx):
        if self.canvas.project:
            self.canvas.project.current_frame_idx = idx
            self.canvas.update()

    def _start_playback(self):
        pass

    def _stop_playback(self):
        pass