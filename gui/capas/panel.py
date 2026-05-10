# gui/capas/panel.py
"""LayerPanel - Container widget for layers."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from .row import LayerRow


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
        self.btn_vector_layer = QPushButton("V")
        self.btn_vector_layer.setFixedWidth(28)
        self.btn_vector_layer.setToolTip("Agregar capa vectorial (Cleanup)")
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
        hl.addWidget(self.btn_vector_layer)
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
        self.btn_vector_layer.clicked.connect(self.add_vector_layer)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        self.btn_merge.clicked.connect(self.merge_layer)
        self.op_slider.valueChanged.connect(self._on_opacity_changed)

    def add_layer(self):
        if self.canvas.project:
            self.canvas.project.get_current_frame().add_layer()
            self.update_ui()

    def add_vector_layer(self):
        if self.canvas.project:
            self.canvas.project.get_current_frame().add_vector_layer()
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
            current = frame.layers[frame.current_layer_idx]
            if hasattr(current, 'is_vector') and current.is_vector:
                new_layer = current.copy()
                new_layer.name = current.name + " (copy)"
                frame.layers.insert(frame.current_layer_idx, new_layer)
            else:
                frame.add_layer(current.name + " (copy)")
                new_layer = frame.layers[frame.current_layer_idx]
                new_layer.image = current.image.copy()
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
                frame.merge_down_layer(idx)
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
            if 0 <= index < len(frame.layers):
                frame.current_layer_idx = index
                self._sync_opacity()
                self.update_ui()

    def _on_visibility_changed(self, index: int, visible: bool):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            if 0 <= index < len(frame.layers):
                frame.layers[index].visible = visible
                self.canvas.update()

    def _on_layer_moved(self, from_idx: int, to_idx: int):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            frame.move_layer(from_idx, to_idx)
            frame.current_layer_idx = to_idx
            self.update_ui()
            self.canvas.update()

    def _on_layer_renamed(self, idx: int, new_name: str):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            if 0 <= idx < len(frame.layers):
                frame.layers[idx].name = new_name
                self.canvas.update()

    def _sync_opacity(self):
        if self.canvas.project:
            frame = self.canvas.project.get_current_frame()
            if not frame.layers:
                return
            idx = frame.current_layer_idx
            if idx < 0 or idx >= len(frame.layers):
                frame.current_layer_idx = 0
                idx = 0
            layer = frame.layers[idx]
            self.op_slider.blockSignals(True)
            self.op_slider.setValue(layer.opacity)
            self.op_slider.blockSignals(False)
            self.op_label.setText(f"{int(layer.opacity / 255 * 100)}%")

    def update_ui(self):
        if not self.canvas.project:
            return
        frame = self.canvas.project.get_current_frame()
        if not frame.layers:
            return
        current_idx = frame.current_layer_idx
        if current_idx < 0 or current_idx >= len(frame.layers):
            current_idx = 0
            frame.current_layer_idx = 0

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, layer in enumerate(frame.layers):
            row = LayerRow(layer, i, is_current=(i == current_idx))
            row.selected.connect(self._on_layer_selected)
            row.visibility_changed.connect(self._on_visibility_changed)
            row.layer_moved.connect(self._on_layer_moved)
            row.layer_renamed.connect(self._on_layer_renamed)
            self.list_layout.insertWidget(i, row)