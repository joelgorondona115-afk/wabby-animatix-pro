# gui/panels/opacity.py
"""Opacity control panel for brush/drawing tools."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt, Signal


class OpacityPanel(QWidget):
    """Panel to control drawing tool opacity (10-100%)."""
    
    opacity_changed = Signal(int)  # 0-255
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OpacityPanel")
        
        self._current_value = 255  # Default 100%
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Label
        self.op_label = QLabel("Opacidad:")
        self.op_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.op_label)
        
        # Slider (10-100)
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(10, 100)
        self.op_slider.setValue(100)
        self.op_slider.setTickPosition(QSlider.NoTicks)
        self.op_slider.setTickInterval(0)
        self.op_slider.valueChanged.connect(self._on_changed)
        layout.addWidget(self.op_slider)
        
        # Value label
        self.val_label = QLabel("100%")
        self.val_label.setStyleSheet("color: #aaa; font-size: 11px; min-width: 35px;")
        layout.addWidget(self.val_label)
        
        # Set stylesheet
        self.setStyleSheet("""
            QWidget#OpacityPanel {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 3px;
            }
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #333;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                margin: -4px 0;
                background: #0078d7;
                border-radius: 2px;
            }
            QSlider::handle:horizontal:hover {
                background: #1084d8;
            }
        """)
    
    def _on_changed(self, val: int):
        """Convert percentage to 0-255 and emit."""
        opacity = int(val * 2.55)
        opacity = max(25, min(255, opacity))
        
        self._current_value = opacity
        self.val_label.setText(f"{val}%")
        self.opacity_changed.emit(opacity)
    
    def set_opacity(self, val: int):
        """Set opacity from 0-255 value."""
        val = max(0, min(255, val))
        pct = int(val / 2.55)
        pct = max(10, min(100, pct))
        self.op_slider.blockSignals(True)
        self.op_slider.setValue(pct)
        self.val_label.setText(f"{pct}%")
        self.op_slider.blockSignals(False)
        self._current_value = val
    
    def get_opacity(self) -> int:
        """Get current opacity as 0-255."""
        return self._current_value
    
    def set_enabled(self, enabled: bool):
        """Enable/disable the panel."""
        self.op_slider.setEnabled(enabled)
        self.op_label.setEnabled(enabled)
        self.val_label.setEnabled(enabled)