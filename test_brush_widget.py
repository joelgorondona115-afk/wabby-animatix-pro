"""Test script for BrushPanelWidget visual test."""

import sys
import os

sys.path.insert(0, '.')

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                                QLabel)
from PySide6.QtGui import QColor

from gui.brush_panel import BrushManager, BrushPanelWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Brush Panel Test")
        self.setGeometry(100, 100, 400, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create brush panel
        self.brush_panel = BrushPanelWidget()
        self.brush_panel.brush_selected.connect(self.on_brush_selected)
        layout.addWidget(self.brush_panel)
        
        # Info label
        self.info_label = self.brush_panel.brush_container.parent().parent().findChild(QLabel)
        
    def on_brush_selected(self, index):
        brush = self.brush_panel.get_selected_brush()
        if brush:
            config = brush['config']
            print(f"Selected: {config.get('nombre', 'Unknown')}")
            print(f"Size: {config.get('tamano_base', 40)}")
            
            # Create tool example
            tool = self.brush_panel.create_tool_from_selected(color=QColor(255, 0, 0))
            if tool:
                print(f"Tool created: {tool.display_name}")

def main():
    app = QApplication(sys.argv)
    
    # Create test brushes if needed
    manager = BrushManager()
    if not os.path.exists(os.path.join(manager.converted_folder, 'test_brush')):
        print("Creating test brush...")
        manager.convert_all_brushes()  # This will create test brush if none exist
    
    window = TestWindow()
    window.show()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
