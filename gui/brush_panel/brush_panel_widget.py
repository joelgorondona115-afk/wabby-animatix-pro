"""Brush panel widget with visual stroke preview - Ibis Paint style."""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QListWidgetItem, QLabel, QAbstractItemView, 
                               QPushButton, QFileDialog)
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QBrush, QIcon
from PySide6.QtCore import Qt, Signal, QSize, QRect, QFileInfo
import shutil
from .brush_manager import BrushManager


class BrushPanelWidget(QWidget):
    """Widget for displaying brushes with stroke preview."""
    
    brush_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = BrushManager()
        self.brushes = []
        self.selected_index = -1
        self._setup_ui()
        self.load_brushes()
    
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Compact title
        title = QLabel("Pinceles")
        title.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 10px;
                font-weight: bold;
                padding: 4px 6px;
            }
        """)
        layout.addWidget(title)
        
        # Brush list with custom display
        self.brush_list = QListWidget()
        self.brush_list.setViewMode(QListWidget.IconMode)
        self.brush_list.setIconSize(QSize(150, 50))
        self.brush_list.setSpacing(3)
        self.brush_list.setMovement(QListWidget.Static)
        self.brush_list.setResizeMode(QListWidget.Adjust)
        self.brush_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.brush_list.itemClicked.connect(self._on_brush_clicked)
        
        self.brush_list.setStyleSheet("""
            QListWidget {
                background: #1a1a1a;
                border: none;
                padding: 2px;
            }
            QListWidget::item {
                background: #252525;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 2px;
            }
            QListWidget::item:selected {
                background: #0078d7;
                border: 1px solid #00aaff;
            }
            QListWidget::item:hover {
                border: 1px solid #555;
            }
        """)
        
        layout.addWidget(self.brush_list)
        
        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)
        
        # Import button
        import_btn = QPushButton("+")
        import_btn.setFixedSize(24, 24)
        import_btn.setToolTip("Importar pinceles")
        import_btn.clicked.connect(self.import_brushes)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d2d;
                border: 1px solid #444;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0078d7; }
        """)
        btn_row.addWidget(import_btn)
        
        # Reload button (compact)
        reload_btn = QPushButton("↺")
        reload_btn.setFixedSize(24, 24)
        reload_btn.setToolTip("Recargar pinceles")
        reload_btn.clicked.connect(self.load_brushes)
        reload_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d2d;
                border: 1px solid #444;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover { background: #3a3a3a; }
        """)
        btn_row.addWidget(reload_btn)
        btn_row.addStretch()
        
        layout.addLayout(btn_row)
        
        self.setMinimumWidth(170)
        self.setMaximumWidth(200)
    
    def load_brushes(self):
        """Load brushes from converted folder."""
        self.brushes = self.manager.load_all_brushes()
        self._update_display()
    
    def import_brushes(self):
        """Open file dialog to import brushes from anywhere."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Pinceles",
            "",
            "Brush Files (*.abr *.kpp);;Photoshop Brushes (*.abr);;Krita Brushes (*.kpp);;All Files (*.*)"
        )
        
        if not files:
            return
        
        imported = 0
        for file_path in files:
            try:
                # Determine destination folder
                ext = QFileInfo(file_path).suffix().lower()
                if ext == 'abr':
                    dest_folder = os.path.join(self.manager.brushes_folder, 'photoshop')
                elif ext == 'kpp':
                    dest_folder = os.path.join(self.manager.brushes_folder, 'krita')
                else:
                    continue
                
                # Create folder if needed
                os.makedirs(dest_folder, exist_ok=True)
                
                # Copy file
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(dest_folder, file_name)
                shutil.copy2(file_path, dest_path)
                imported += 1
                print(f"Imported: {file_name}")
                
            except Exception as e:
                print(f"Error importing {file_path}: {e}")
        
        if imported > 0:
            print(f"Imported {imported} brush(es)")
            # Auto-convert and reload
            self.manager.convert_all_brushes()
            self.load_brushes()
    
    def _update_display(self):
        """Update the brush list display."""
        self.brush_list.clear()
        
        for i, brush in enumerate(self.brushes):
            # Create stroke preview image
            preview = self._create_stroke_preview(brush)
            
            # Create list item
            item = QListWidgetItem()
            item.setIcon(QIcon(preview))
            item.setText(brush['config'].get('nombre', f'Pincel {i}'))
            item.setData(Qt.UserRole, i)
            
            # Set size hint for custom display
            item.setSizeHint(QSize(150, 50))
            
            self.brush_list.addItem(item)
    
    def _create_stroke_preview(self, brush: dict, width=150, height=50) -> QPixmap:
        """Create a preview image showing the brush stroke."""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get brush tip
        tip = brush['image']
        config = brush['config']
        spacing = config.get('espaciado', 0.25)
        
        # Draw a sample stroke (S-curve)
        pen = QPen()
        pen.setColor(QColor(200, 200, 200, 180))
        pen.setWidth(max(2, int(config.get('tamano_base', 40) / 3)))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        
        # Draw stroke path
        from PySide6.QtCore import QPointF
        path_points = [
            QPointF(10, height * 0.7),
            QPointF(width * 0.3, height * 0.3),
            QPointF(width * 0.7, height * 0.7),
            QPointF(width - 10, height * 0.3)
        ]
        
        # Simple line for preview
        painter.drawPolyline(path_points)
        
        # If brush has a tip, stamp it along the path
        if tip and not tip.isNull():
            for i, point in enumerate(path_points):
                # Scale tip based on brush size
                brush_size = max(8, int(config.get('tamano_base', 40) / 2))
                scaled_tip = QPixmap.fromImage(
                    tip.scaled(brush_size, brush_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                
                # Tint with gray
                painter.save()
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.drawPixmap(
                    int(point.x() - brush_size/2),
                    int(point.y() - brush_size/2),
                    scaled_tip
                )
                painter.restore()
        
        painter.end()
        return pixmap
    
    def _on_brush_clicked(self, item: QListWidgetItem):
        """Handle brush selection."""
        index = item.data(Qt.UserRole)
        self.selected_index = index
        self.brush_selected.emit(index)
    
    def get_selected_brush(self) -> dict:
        """Get the currently selected brush."""
        if 0 <= self.selected_index < len(self.brushes):
            return self.brushes[self.selected_index]
        return None
    
    def create_tool_from_selected(self, color=None):
        """Create a CustomBrushTool from selected brush."""
        if self.selected_index >= 0:
            return self.manager.create_custom_brush_tool(self.selected_index, color)
        return None
    
    def create_tool_from_selected(self, color=None):
        """Create a CustomBrushTool from selected brush."""
        if self.selected_index >= 0:
            return self.manager.create_custom_brush_tool(self.selected_index, color)
        return None
