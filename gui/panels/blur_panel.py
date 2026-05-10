# gui/panels/blur_panel.py
"""Control panel for Blur tool with preset saving to brush system."""

import json
import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QSlider,
                                QPushButton, QLineEdit, QComboBox,
                                QVBoxLayout, QMessageBox)
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt, Signal


class BlurPanel(QWidget):
    radius_changed = Signal(int)
    strength_changed = Signal(float)
    preset_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BlurPanel")
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.brushes_folder = os.path.join(base_dir, 'brushes', 'converted')
        os.makedirs(self.brushes_folder, exist_ok=True)
        self._setup_ui()
        self._populate_presets()

    def _get_blur_presets(self):
        presets = []
        if not os.path.exists(self.brushes_folder):
            return presets
        for folder_name in os.listdir(self.brushes_folder):
            folder_path = os.path.join(self.brushes_folder, folder_name)
            config_path = os.path.join(folder_path, 'config.json')
            if os.path.isdir(folder_path) and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    if config.get('type') == 'blur':
                        presets.append((folder_name, config.get('nombre', folder_name)))
                except Exception:
                    pass
        return sorted(presets, key=lambda x: x[1])

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(4)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(6)

        self.rad_label = QLabel("Radio:")
        self.rad_label.setStyleSheet("color: #888; font-size: 11px;")
        controls.addWidget(self.rad_label)

        self.rad_slider = QSlider(Qt.Horizontal)
        self.rad_slider.setRange(5, 50)
        self.rad_slider.setValue(15)
        self.rad_slider.setTickPosition(QSlider.NoTicks)
        self.rad_slider.valueChanged.connect(self._on_radius_changed)
        controls.addWidget(self.rad_slider)

        self.rad_val = QLabel("15")
        self.rad_val.setStyleSheet("color: #aaa; font-size: 11px; min-width: 25px;")
        controls.addWidget(self.rad_val)

        self.str_label = QLabel("Fuerza:")
        self.str_label.setStyleSheet("color: #888; font-size: 11px;")
        controls.addWidget(self.str_label)

        self.str_slider = QSlider(Qt.Horizontal)
        self.str_slider.setRange(5, 100)
        self.str_slider.setValue(25)
        self.str_slider.setTickPosition(QSlider.NoTicks)
        self.str_slider.valueChanged.connect(self._on_strength_changed)
        controls.addWidget(self.str_slider)

        self.str_val = QLabel("25%")
        self.str_val.setStyleSheet("color: #aaa; font-size: 11px; min-width: 35px;")
        controls.addWidget(self.str_val)

        main_layout.addLayout(controls)

        # Presets row
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(120)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre del preset")
        self.name_edit.setMaximumWidth(150)
        preset_layout.addWidget(self.name_edit)

        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self._save_current_preset)
        preset_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.clicked.connect(self._delete_current_preset)
        preset_layout.addWidget(self.delete_btn)

        main_layout.addLayout(preset_layout)

        self.setStyleSheet("""
            QWidget#BlurPanel {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 3px;
            }
            QSlider { background: transparent; }
            QSlider::groove:horizontal {
                height: 4px; background: #333; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px; margin: -4px 0;
                background: #0078d7; border-radius: 2px;
            }
            QSlider::handle:horizontal:hover { background: #1084d8; }
            QComboBox {
                background: #2a2a2a; color: #aaa;
                border: 1px solid #444; border-radius: 2px;
                padding: 2px 4px; font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QLineEdit {
                background: #2a2a2a; color: #aaa;
                border: 1px solid #444; border-radius: 2px;
                padding: 2px 4px; font-size: 11px;
            }
            QPushButton {
                background: #2a2a2a; color: #aaa;
                border: 1px solid #444; border-radius: 2px;
                padding: 3px 8px; font-size: 11px;
            }
            QPushButton:hover { background: #333; }
        """)

    def _populate_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("-- Seleccionar preset --")
        presets = self._get_blur_presets()
        for folder_name, display_name in presets:
            self.preset_combo.addItem(display_name, folder_name)
        self.preset_combo.blockSignals(False)

    def _on_radius_changed(self, val):
        self.rad_val.setText(str(val))
        self.radius_changed.emit(val)

    def _on_strength_changed(self, val):
        self.str_val.setText(f"{val}%")
        self.strength_changed.emit(val / 100.0)

    def _on_preset_selected(self, display_name):
        if display_name == "-- Seleccionar preset --":
            return
        folder_name = self.preset_combo.currentData()
        if not folder_name:
            return
        folder_path = os.path.join(self.brushes_folder, folder_name)
        config_path = os.path.join(folder_path, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.rad_slider.setValue(config.get('radius', 15))
            self.str_slider.setValue(int(config.get('strength', 0.25) * 100))
            self.name_edit.setText(config.get('nombre', display_name))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar: {e}")

    def _save_current_preset(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Ingresa un nombre para el preset.")
            return
        if name == "-- Seleccionar preset --":
            QMessageBox.warning(self, "Error", "Nombre no valido.")
            return

        allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_')
        folder_name = ''.join(c for c in name if c in allowed)
        folder_name = folder_name.replace(' ', '_').lower()
        if not folder_name:
            folder_name = "blur_preset"
        folder_path = os.path.join(self.brushes_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Create tip image
        size = 64
        tip = QImage(size, size, QImage.Format_ARGB32)
        tip.fill(QColor(0, 0, 0, 0))
        painter = QPainter(tip)
        painter.setBrush(QColor(100, 100, 100, 180))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)
        painter.end()
        tip.save(os.path.join(folder_path, 'tip.png'), 'PNG')

        config = {
            'nombre': name,
            'type': 'blur',
            'radius': self.rad_slider.value(),
            'strength': self.str_slider.value() / 100.0,
            'espaciado': 0.25,
            'tamano_base': 40,
            'opacidad_flujo': 0.8
        }
        with open(os.path.join(folder_path, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self._populate_presets()
        idx = self.preset_combo.findData(folder_name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_saved.emit()
        QMessageBox.information(self, "Guardado", f"Preset '{name}' guardado.")

    def _delete_current_preset(self):
        display_name = self.preset_combo.currentText()
        folder_name = self.preset_combo.currentData()
        if not folder_name or display_name == "-- Seleccionar preset --":
            QMessageBox.warning(self, "Error", "Selecciona un preset para eliminar.")
            return
        folder_path = os.path.join(self.brushes_folder, folder_name)
        import shutil
        try:
            shutil.rmtree(folder_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo eliminar: {e}")
            return
        self._populate_presets()
        self.name_edit.clear()
        self.preset_saved.emit()
        QMessageBox.information(self, "Eliminado", "Preset eliminado.")

    def set_radius(self, val):
        self.rad_slider.setValue(max(5, min(50, val)))

    def set_strength(self, val):
        pct = int(val * 100)
        self.str_slider.setValue(max(5, min(100, pct)))
