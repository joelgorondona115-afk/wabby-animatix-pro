"""Converter for Photoshop (.abr) and Krita (.kpp) brushes to PNG+JSON format."""

import os
import json
import zipfile
import struct
from PySide6.QtGui import QImage, QPixmap, QRadialGradient, QPainter, QColor
from PySide6.QtCore import Qt
from PIL import Image
import io


class BrushAdapter:
    """Converts external brush formats to internal PNG+JSON format."""
    
    @staticmethod
    def convert_to_standard_format(source_path: str, output_folder: str) -> dict:
        """Convert a brush file to PNG+JSON standard format."""
        ext = os.path.splitext(source_path)[1].lower()
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        
        brush_folder = os.path.join(output_folder, base_name)
        os.makedirs(brush_folder, exist_ok=True)
        
        tip_image = None
        config = None
        
        if ext == '.abr':
            tip_image = BrushAdapter._extract_from_abr(source_path)
            config = {
                "nombre": base_name,
                "espaciado": 0.25,
                "tamano_base": 40,
                "opacidad_flujo": 0.8,
                "rotacion_dinamica": False,
                "origen": "abr",
                "archivo_original": os.path.basename(source_path)
            }
        elif ext == '.kpp':
            tip_image, kpp_config = BrushAdapter._extract_from_kpp(source_path)
            config = kpp_config if kpp_config else {
                "nombre": base_name,
                "espaciado": 0.25,
                "tamano_base": 40,
                "opacidad_flujo": 0.8,
                "origen": "kpp",
                "archivo_original": os.path.basename(source_path)
            }
        else:
            return None
        
        if tip_image is None or tip_image.isNull():
            print(f"Warning: Could not extract tip from {base_name}, using default")
            tip_image = BrushAdapter._create_default_tip()
        
        # Save PNG tip
        png_path = os.path.join(brush_folder, 'tip.png')
        tip_image.save(png_path, 'PNG')
        
        # Save JSON config
        json_path = os.path.join(brush_folder, 'config.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {
            'name': config['nombre'],
            'folder': brush_folder,
            'tip_path': png_path,
            'config_path': json_path,
            'config': config
        }
    
    @staticmethod
    def _extract_from_abr(file_path: str) -> QImage:
        """Extract brush tip from Photoshop .abr file."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            if len(data) < 4 or data[:4] != b'8BPS':
                return BrushAdapter._create_default_tip()
            
            # Try to extract embedded images (PNG/JPEG) from ABR
            image_data = BrushAdapter._find_embedded_image(data)
            if image_data:
                image = QImage.fromData(image_data)
                if not image.isNull():
                    return image
            
            # If no embedded image found, try to parse ABR structure
            return BrushAdapter._create_tip_from_brush_data(data)
            
        except Exception as e:
            print(f"Error reading ABR: {e}")
            return BrushAdapter._create_default_tip()
    
    @staticmethod
    def _find_embedded_image(data: bytes):
        """Try to find embedded PNG or JPEG in binary data."""
        # Search for PNG
        png_start = data.find(b'\x89PNG')
        if png_start != -1:
            # Find IEND marker
            iend_pos = data.find(b'IEND', png_start)
            if iend_pos != -1:
                # Include CRC (4 bytes after IEND)
                end_pos = iend_pos + 8
                if end_pos <= len(data):
                    return data[png_start:end_pos]
        
        # Search for JPEG
        jpeg_start = data.find(b'\xff\xd8\xff')
        if jpeg_start != -1:
            # Find end of JPEG
            jpeg_end = data.find(b'\xff\xd9', jpeg_start)
            if jpeg_end != -1:
                return data[jpeg_start:jpeg_end + 2]
        
        return None
    
    @staticmethod
    def _create_tip_from_brush_data(data: bytes) -> QImage:
        """Create a brush tip based on brush file data."""
        return BrushAdapter._create_default_tip()
    
    @staticmethod
    def _extract_from_kpp(file_path: str) -> tuple:
        """Extract brush tip and parameters from Krita .kpp file."""
        tip_image = None
        config = None
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Find preview image
                for name in zip_ref.namelist():
                    if name.endswith('.png'):
                        png_data = zip_ref.read(name)
                        tip_image = QImage.fromData(png_data, 'PNG')
                        if not tip_image.isNull():
                            break
                
                # Try to read brush parameters from XML
                for xml_name in ['embedded.xml', 'brush.xml', 'preset.xml']:
                    if xml_name in zip_ref.namelist():
                        try:
                            xml_data = zip_ref.read(xml_name).decode('utf-8', errors='ignore')
                            config = BrushAdapter._parse_kpp_xml(xml_data)
                            break
                        except:
                            pass
                            
        except Exception as e:
            print(f"Error reading KPP: {e}")
        
        if config is None:
            config = {
                "nombre": os.path.splitext(os.path.basename(file_path))[0],
                "espaciado": 0.25,
                "tamano_base": 40,
                "opacidad_flujo": 0.8
            }
        
        return tip_image, config
    
    @staticmethod
    def _parse_kpp_xml(xml_data: str) -> dict:
        """Parse Krita XML to extract brush parameters."""
        config = {
            "nombre": "Pincel Krita",
            "espaciado": 0.25,
            "tamano_base": 40,
            "opacidad_flujo": 0.8,
            "rotacion_dinamica": False
        }
        
        try:
            # Extract brush size
            if '<brushSize>' in xml_data:
                start = xml_data.find('<brushSize>') + len('<brushSize>')
                end = xml_data.find('</brushSize>', start)
                if start > 0 and end > start:
                    try:
                        config['tamano_base'] = int(float(xml_data[start:end]))
                    except:
                        pass
            
            # Extract spacing
            if '<spacing>' in xml_data:
                start = xml_data.find('<spacing>') + len('<spacing>')
                end = xml_data.find('</spacing>', start)
                if start > 0 and end > start:
                    try:
                        config['espaciado'] = float(xml_data[start:end])
                    except:
                        pass
            
            # Extract opacity
            if '<opacity>' in xml_data:
                start = xml_data.find('<opacity>') + len('<opacity>')
                end = xml_data.find('</opacity>', start)
                if start > 0 and end > start:
                    try:
                        config['opacidad_flujo'] = float(xml_data[start:end])
                    except:
                        pass
                        
        except Exception as e:
            pass
        
        return config
    
    @staticmethod
    def _create_default_tip() -> QImage:
        """Create a default smooth cylinder-like brush tip (uniform density, anti-aliased edges)."""
        size = 256
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        # Uniform dense cylinder-like tip: full opacity inside, smooth edge
        painter.setBrush(QColor(0, 0, 0, 255))  # Solid interior
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, size - 4, size - 4)  # Even circle, anti-aliased edge
        painter.end()
        
        return image
