"""Brush manager for loading and managing brushes in PNG+JSON format."""

import os
import json
from PySide6.QtGui import QImage, QPixmap
from .brush_adapter import BrushAdapter


class BrushManager:
    """Manages brushes in standard PNG+JSON format."""
    
    def __init__(self, brushes_folder: str = None):
        self.brushes_folder = brushes_folder or self._get_default_brushes_folder()
        self.converted_folder = os.path.join(self.brushes_folder, 'converted')
        self.loaded_brushes = []  # List of brush dicts
        
    def _get_default_brushes_folder(self) -> str:
        """Get default brushes folder path."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, 'brushes')
    
    def convert_all_brushes(self) -> list:
        """Convert all .abr and .kpp files to PNG+JSON format."""
        os.makedirs(self.converted_folder, exist_ok=True)
        converted = []
        
        for subfolder in ['photoshop', 'krita']:
            source_folder = os.path.join(self.brushes_folder, subfolder)
            if not os.path.exists(source_folder):
                continue
            
            for file in os.listdir(source_folder):
                if file.lower().endswith(('.abr', '.kpp')):
                    source_path = os.path.join(source_folder, file)
                    try:
                        result = BrushAdapter.convert_to_standard_format(
                            source_path, self.converted_folder
                        )
                        if result:
                            converted.append(result)
                            print(f"Converted: {file}")
                    except Exception as e:
                        print(f"Error converting {file}: {e}")
        
        return converted
    
    def load_all_brushes(self) -> list:
        """Load all brushes from the converted PNG+JSON folder."""
        self.loaded_brushes = []
        
        if not os.path.exists(self.converted_folder):
            return self.loaded_brushes
        
        # Scan each brush subfolder
        for folder_name in os.listdir(self.converted_folder):
            brush_folder = os.path.join(self.converted_folder, folder_name)
            if not os.path.isdir(brush_folder):
                continue
            
            config_path = os.path.join(brush_folder, 'config.json')
            tip_path = os.path.join(brush_folder, 'tip.png')
            
            if not os.path.exists(config_path) or not os.path.exists(tip_path):
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                image = QImage(tip_path)
                if image.isNull():
                    continue
                
                pixmap = QPixmap.fromImage(image)
                
                self.loaded_brushes.append({
                    'name': config.get('nombre', folder_name),
                    'folder': brush_folder,
                    'config': config,
                    'image': image,
                    'pixmap': pixmap,
                    'tip_path': tip_path
                })
            except Exception as e:
                print(f"Error loading brush {folder_name}: {e}")
        
        return self.loaded_brushes
    
    def get_brush_by_index(self, index: int) -> dict:
        """Get brush data by index."""
        if 0 <= index < len(self.loaded_brushes):
            return self.loaded_brushes[index]
        return None
    
    def get_brush_tip(self, index: int) -> QImage:
        """Get the QImage tip for a brush."""
        brush = self.get_brush_by_index(index)
        if brush:
            return brush['image']
        return None
    
    def create_custom_brush_tool(self, index: int, color=None, size=None, opacity=None):
        """Create a CustomBrushTool from a loaded brush using its config."""
        from PySide6.QtGui import QColor
        from core.tools.special.custom_brush import CustomBrushTool
        
        brush = self.get_brush_by_index(index)
        if not brush:
            return None
        
        config = brush['config']
        image = brush['image']
        
        if color is None:
            color = QColor(0, 0, 0)
        
        # Use config values or defaults
        brush_size = size if size else config.get('tamano_base', 40)
        brush_opacity = int((opacity if opacity else config.get('opacidad_flujo', 0.8)) * 255)
        brush_spacing = config.get('espaciado', 0.25)
        
        return CustomBrushTool(
            tip=image,
            display_name=config.get('nombre', 'Pincel'),
            color=color,
            size=brush_size,
            opacity=brush_opacity,
            spacing=brush_spacing
        )
