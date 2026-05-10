# gui/capas/row.py
"""LayerRow - Individual layer row widget with drag & drop."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QSizePolicy, QLineEdit
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QPixmap, QDrag


class LayerRow(QWidget):
    selected = Signal(int)
    visibility_changed = Signal(int, bool)
    layer_moved = Signal(int, int)
    layer_renamed = Signal(int, str)

    THUMB_W = 42
    THUMB_H = 30

    def __init__(self, layer, index: int, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self._layer = layer
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)

        if is_current:
            bg = "#2a5a8a"
            border = "2px solid #00bfff"
        else:
            bg = "#252525"
            border = "1px solid #333"
        self.setStyleSheet(
            f"QWidget {{ background-color: {bg}; border-bottom: {border}; }}"
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
        self.btn_eye.clicked.connect(self._on_eye_clicked)

        thumb_label = QLabel()
        thumb_label.setFixedSize(self.THUMB_W, self.THUMB_H)
        thumb_label.setStyleSheet("background: #111; border: 1px solid #444;")
        
        is_vector = hasattr(layer, 'is_vector') and layer.is_vector
        if is_vector:
            thumb_label.setToolTip("Capa Vectorial")
            thumb_label.setStyleSheet("background: #1a2a1a; border: 1px solid #00aa00;")
            from PySide6.QtGui import QPainter
            from PySide6.QtGui import QColor as QtColor
            pixmap = QPixmap(self.THUMB_W, self.THUMB_H)
            pixmap.fill(QtColor(26, 42, 26))
            p = QPainter(pixmap)
            layer.draw_all(p)
            p.end()
            thumb_label.setPixmap(pixmap)
        else:
            thumb = layer.image.scaled(
                self.THUMB_W, self.THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            thumb_label.setPixmap(QPixmap.fromImage(thumb))
        
        self.name_label = QLabel(layer.name)
        self.name_label.setStyleSheet(
            "color: #ddd; font-size: 11px; background: transparent;"
        )
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        if is_vector:
            self.name_label.setStyleSheet("color: #7fff7f; font-size: 11px; background: transparent; font-style: italic;")

        self._name_label_style = self.name_label.styleSheet()

        op_label = QLabel(f"{int(layer.opacity / 255 * 100)}%")
        op_label.setFixedWidth(35)
        op_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        op_label.setStyleSheet("color: #888; font-size: 10px; background: transparent;")

        layout.addWidget(self.btn_eye)
        layout.addWidget(thumb_label)
        layout.addWidget(self.name_label)
        layout.addWidget(op_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.type() == event.Type.MouseButtonDblClick:
            self._start_rename()
            return
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.index)
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_rename()
            return
        super().mouseDoubleClickEvent(event)

    def _start_rename(self):
        self.name_label.hide()
        self._edit = QLineEdit(self._layer.name, self)
        self._edit.setFixedSize(self.name_label.sizeHint().width() + 40, 22)
        self._edit.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #ddd; border: 1px solid #00bfff; "
            "border-radius: 3px; padding: 0 4px; font-size: 11px; }"
        )
        self._edit.selectAll()
        self._edit.editingFinished.connect(self._finish_rename)
        self._edit.keyPressEvent = self._on_edit_key
        self._edit.show()
        self._edit.setFocus()

    def _on_edit_key(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._finish_rename()
        elif event.key() == Qt.Key_Escape:
            self._cancel_rename()
        else:
            QLineEdit.keyPressEvent(self._edit, event)

    def _finish_rename(self):
        new_name = self._edit.text().strip()
        if new_name:
            self._layer.name = new_name
            self.name_label.setText(new_name)
            self.layer_renamed.emit(self.index, new_name)
        self._cancel_rename()

    def _cancel_rename(self):
        self._edit.deleteLater()
        self.name_label.show()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_start_pos'):
            diff = event.pos() - self._drag_start_pos
            if diff.manhattanLength() > 10:
                self._start_drag()
                del self._drag_start_pos
        super().mouseMoveEvent(event)

    def _on_eye_clicked(self):
        new_visible = not self._layer.visible
        self._layer.visible = new_visible
        self.btn_eye.setText("👁" if new_visible else "🚫")
        self.visibility_changed.emit(self.index, new_visible)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet("QWidget { background-color: #2a5a8a; border-bottom: 2px solid #00bfff; }")
        else:
            self.setStyleSheet("QWidget { background-color: #252525; border-bottom: 1px solid #333; }")

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
