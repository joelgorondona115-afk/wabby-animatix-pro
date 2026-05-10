"""Test for brush_panel system."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QImage, QColor
from gui.brush_panel import BrushAdapter, BrushManager

def test_brush_system():
    """Test the brush conversion and loading system."""
    
    print("=== Testing Brush Panel System ===\n")
    
    # Test 1: Create default tip
    print("1. Testing default tip creation...")
    default_tip = BrushAdapter._create_default_tip()
    if default_tip and not default_tip.isNull():
        print(f"   [OK] Default tip created: {default_tip.width()}x{default_tip.height()}")
    else:
        print("   [FAIL] Failed to create default tip")
        return False
    
    # Test 2: Test BrushManager
    print("\n2. Testing BrushManager...")
    manager = BrushManager()
    print(f"   Brushes folder: {manager.brushes_folder}")
    print(f"   Converted folder: {manager.converted_folder}")
    
    # Test 3: Create a dummy PNG to simulate a converted brush
    print("\n3. Creating test brush structure...")
    test_folder = os.path.join(manager.converted_folder, 'test_brush')
    os.makedirs(test_folder, exist_ok=True)
    
    # Save a test tip
    test_tip_path = os.path.join(test_folder, 'tip.png')
    default_tip.save(test_tip_path, 'PNG')
    
    # Create test config
    test_config = {
        "nombre": "Test Brush",
        "espaciado": 0.25,
        "tamano_base": 40,
        "opacidad_flujo": 0.8,
        "rotacion_dinamica": False,
        "origen": "test"
    }
    
    import json
    config_path = os.path.join(test_folder, 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, indent=2)
    
    print(f"   [OK] Test brush created at: {test_folder}")
    
    # Test 4: Load brushes
    print("\n4. Loading brushes...")
    brushes = manager.load_all_brushes()
    print(f"   Loaded {len(brushes)} brush(es)")
    
    for i, brush in enumerate(brushes):
        print(f"   - {brush['name']}: {brush['image'].width()}x{brush['image'].height()}")
    
    # Test 5: Create CustomBrushTool
    if brushes:
        print("\n5. Testing CustomBrushTool creation...")
        tool = manager.create_custom_brush_tool(0, color=QColor(255, 0, 0))
        if tool:
            print(f"   [OK] Created tool: {tool.display_name}")
            print(f"   - Size: {tool.size}")
            print(f"   - Opacity: {tool.opacity}")
            print(f"   - Spacing: {tool.spacing}")
        else:
            print("   [FAIL] Failed to create tool")
    
    print("\n=== Test Completed ===")
    return True

if __name__ == '__main__':
    test_brush_system()
