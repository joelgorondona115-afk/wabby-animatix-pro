# gui/dialogs.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QComboBox,
    QPushButton, QDialogButtonBox, QScrollArea,
    QWidget, QGridLayout, QFileDialog, QMessageBox,
    QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QColor

_DIALOG_STYLE = """
    QDialog   { background: #1e1e1e; color: #ddd; }
    QLabel    { color: #ccc; font-size: 12px; }
    QLineEdit { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 3px; padding: 4px; font-size: 12px; }
    QSpinBox  { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 3px; padding: 2px; font-size: 12px; }
    QComboBox { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                border-radius: 3px; padding: 4px; font-size: 12px; }
    QComboBox QAbstractItemView { background: #2d2d2d; color: #ddd;
                selection-background-color: #0078d7; }
    QPushButton { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                  border-radius: 4px; padding: 6px 16px; font-size: 12px; }
    QPushButton:hover   { background: #3a3a3a; }
    QPushButton:checked { background: #0078d7; border-color: #005fa3; }
    QPushButton#btnOk   { background: #005fa3; }
    QPushButton#btnOk:hover { background: #0078d7; }
    QScrollArea { border: none; background: #141414; }
    QFrame#brushCard { background: #252525; border: 2px solid #333;
                       border-radius: 6px; }
    QFrame#brushCard[selected=true] { border-color: #0078d7; }
"""


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Proyecto")
        self.setFixedSize(360, 240)
        self.setStyleSheet("""
            QDialog   { background: #1e1e1e; color: #ddd; }
            QLabel    { color: #ccc; font-size: 12px; }
            QLineEdit { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                        border-radius: 3px; padding: 4px; font-size: 12px; }
            QSpinBox  { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                        border-radius: 3px; padding: 2px; font-size: 12px; }
            QComboBox { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                        border-radius: 3px; padding: 4px; font-size: 12px; }
            QComboBox QAbstractItemView { background: #2d2d2d; color: #ddd;
                        selection-background-color: #0078d7; }
            QPushButton { background: #2d2d2d; color: #ddd; border: 1px solid #444;
                          border-radius: 4px; padding: 6px 16px; font-size: 12px; }
            QPushButton:hover   { background: #3a3a3a; }
            QPushButton#btnOk   { background: #005fa3; }
            QPushButton#btnOk:hover { background: #0078d7; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit("Nuevo Proyecto")
        form.addRow("Nombre:", self.name_edit)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 7680)
        self.width_spin.setValue(1920)
        form.addRow("Ancho (px):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4320)
        self.height_spin.setValue(1080)
        form.addRow("Alto (px):", self.height_spin)

        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Transparente", "Blanco", "Negro"])
        form.addRow("Fondo:", self.bg_combo)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok     = QPushButton("Crear")
        btn_ok.setObjectName("btnOk")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def get_data(self) -> dict:
        return {
            "name":   self.name_edit.text().strip() or "Proyecto",
            "width":  self.width_spin.value(),
            "height": self.height_spin.value(),
            "bg":     self.bg_combo.currentText(),
        }


# ============================================================
# Biblioteca de pinceles personalizados
# ============================================================
class BrushLibraryDialog(QDialog):
    """
    Diálogo para importar y seleccionar pinceles de:
      - Photoshop (.abr)
      - Clip Studio Paint (punta PNG exportada)
      - Cualquier imagen PNG/JPG como punta de pincel
    """
    brush_selected = Signal(object, str)   # (QImage tip, nombre)

    _PREVIEW_SIZE = 64
    _COLS         = 4

    def __init__(self, existing: list | None = None, parent=None):
        """
        existing: lista de (nombre: str, tip: QImage) ya cargados.
        """
        super().__init__(parent)
        self.setWindowTitle("Biblioteca de pinceles")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(_DIALOG_STYLE)

        self._brushes: list[tuple[str, QImage]] = list(existing or [])
        self._selected_idx: int | None = None
        self._cards: list[QFrame] = []

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # --- botones de importación ---
        btn_row = QHBoxLayout()
        btn_abr = QPushButton("📂 Importar .abr (Photoshop)")
        btn_img = QPushButton("🖼️ Importar imagen (PNG / CSP)")
        btn_abr.clicked.connect(self._import_abr)
        btn_img.clicked.connect(self._import_image)
        btn_row.addWidget(btn_abr)
        btn_row.addWidget(btn_img)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # --- scroll area con grilla de tarjetas ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(320)
        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(8)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self.scroll.setWidget(self._grid_widget)
        root.addWidget(self.scroll)

        # --- info + botón confirmar ---
        self._lbl_sel = QLabel("Ningún pincel seleccionado")
        self._lbl_sel.setAlignment(Qt.AlignCenter)
        root.addWidget(self._lbl_sel)

        btn_row2 = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        self._btn_use = QPushButton("✅ Usar este pincel")
        self._btn_use.setObjectName("btnOk")
        self._btn_use.setEnabled(False)
        btn_cancel.clicked.connect(self.reject)
        self._btn_use.clicked.connect(self._confirm)
        btn_row2.addStretch()
        btn_row2.addWidget(btn_cancel)
        btn_row2.addWidget(self._btn_use)
        root.addLayout(btn_row2)

        self._rebuild_grid()

    # ------------------------------------------------------------------ helpers
    def _rebuild_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        if not self._brushes:
            lbl = QLabel("Sin pinceles cargados.\nImportá un .abr o una imagen.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #666; font-size: 13px;")
            self._grid.addWidget(lbl, 0, 0, 1, self._COLS)
            return

        for i, (name, tip) in enumerate(self._brushes):
            card = self._make_card(i, name, tip)
            self._cards.append(card)
            row, col = divmod(i, self._COLS)
            self._grid.addWidget(card, row, col)

        self._grid.setRowStretch(self._grid.rowCount(), 1)

    def _make_card(self, idx: int, name: str, tip: QImage) -> QFrame:
        card = QFrame()
        card.setObjectName("brushCard")
        card.setFixedSize(self._PREVIEW_SIZE + 24, self._PREVIEW_SIZE + 34)
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("selected", False)

        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)

        # preview
        pm = QPixmap.fromImage(
            tip.scaled(self._PREVIEW_SIZE, self._PREVIEW_SIZE,
                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        lbl_px = QLabel()
        lbl_px.setPixmap(pm)
        lbl_px.setAlignment(Qt.AlignCenter)
        lbl_px.setStyleSheet("background: #141414; border-radius: 3px;")
        lbl_px.setFixedSize(self._PREVIEW_SIZE + 12, self._PREVIEW_SIZE + 6)

        # nombre truncado
        short = name if len(name) <= 10 else name[:9] + "…"
        lbl_name = QLabel(short)
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setToolTip(name)
        lbl_name.setStyleSheet("color: #bbb; font-size: 9px;")

        vbox.addWidget(lbl_px)
        vbox.addWidget(lbl_name)

        # click
        card.mousePressEvent = lambda _ev, i=idx: self._select(i)
        return card

    def _select(self, idx: int):
        self._selected_idx = idx
        for i, card in enumerate(self._cards):
            card.setProperty("selected", i == idx)
            card.setStyleSheet(
                "QFrame#brushCard { background: #252525; border: 2px solid %s; border-radius: 6px; }"
                % ("#0078d7" if i == idx else "#333")
            )
        name = self._brushes[idx][0]
        self._lbl_sel.setText(f"Seleccionado: {name}")
        self._btn_use.setEnabled(True)

    def _confirm(self):
        if self._selected_idx is None:
            return
        name, tip = self._brushes[self._selected_idx]
        self.brush_selected.emit(tip, name)
        self.accept()

    # ------------------------------------------------------------------ importación
    def _import_abr(self):
        from tools import parse_abr
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir archivo de pinceles Photoshop",
            "", "Pinceles Photoshop (*.abr);;Todos (*.*)"
        )
        if not path:
            return
        found = parse_abr(path)
        if not found:
            QMessageBox.warning(
                self, "Sin pinceles",
                "No se encontraron pinceles en el archivo.\n"
                "Solo se admiten archivos .abr versión 1 y 2."
            )
            return
        self._brushes.extend(found)
        self._rebuild_grid()

    def _import_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar imagen como punta de pincel",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;Todos (*.*)"
        )
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.warning(self, "Error", "No se pudo cargar la imagen.")
            return
        img = img.convertToFormat(QImage.Format_ARGB32)
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        self._brushes.append((name, img))
        self._rebuild_grid()

    def get_brushes(self) -> list:
        """Retorna la lista actualizada de (nombre, QImage)."""
        return list(self._brushes)
