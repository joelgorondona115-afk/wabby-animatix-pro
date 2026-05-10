"""Complete test for brush system."""

import sys
import os

sys.path.insert(0, '.')

print("=== BRUSH PANEL SYSTEM TEST ===\n")

# Test 1: Imports
print("1. Testing imports...")
try:
    from gui.brush_panel import BrushAdapter, BrushManager
    print("   [OK] Imports successful\n")
except Exception as e:
    print(f"   [FAIL] {e}\n")
    sys.exit(1)

# Test 2: Create default tip
print("2. Testing default tip creation...")
try:
    tip = BrushAdapter._create_default_tip()
    print(f"   [OK] Tip created: {tip.width()}x{tip.height()}\n")
except Exception as e:
    print(f"   [FAIL] {e}\n")
    sys.exit(1)

# Test 3: Save tip to file
print("3. Testing tip save...")
try:
    os.makedirs('test_output', exist_ok=True)
    tip.save('test_output/test_tip.png', 'PNG')
    print("   [OK] Tip saved to test_output/test_tip.png\n")
except Exception as e:
    print(f"   [FAIL] {e}\n")
    sys.exit(1)

# Test 4: Create BrushManager
print("4. Testing BrushManager...")
try:
    manager = BrushManager()
    print(f"   [OK] Manager created")
    print(f"   - Brushes folder: {manager.brushes_folder}")
    print(f"   - Converted folder: {manager.converted_folder}\n")
except Exception as e:
    print(f"   [FAIL] {e}\n")
    sys.exit(1)

# Test 5: Create test brush structure
print("5. Creating test brush (PNG+JSON)...")
try:
    test_folder = os.path.join(manager.converted_folder, 'test_brush')
    os.makedirs(test_folder, exist_ok=True)
    
    # Save tip
    tip_path = os.path.join(test_folder, 'tip.png')
    tip.save(tip_path, 'PNG')
    
    # Save config
    import json
    config = {
        'nombre': 'Test Brush',
        'espaciado': 0.25,
        'tamano_base': 40,
        'opacidad_flujo': 0.8
    }
    config_path = os.path.join(test_folder, 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    print(f"   [OK] Test brush created at: {test_folder}\n")
except Exception as e:
    print(f"   [FAIL] {e}\n")
    sys.exit(1)

# Test 6: Load brushes
print("6. Loading brushes...")
try:
    brushes = manager.load_all_brushes()
    print(f"   [OK] Loaded {len(brushes)} brush(es)")
    for brush in brushes:
        print(f"   - {brush['name']}: {brush['image'].width()}x{brush['image'].height()}")
    print()
except Exception as e:
    print(f"   [FAIL] {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Create CustomBrushTool
if brushes:
    print("7. Creating CustomBrushTool...")
    try:
        from PySide6.QtGui import QColor
        tool = manager.create_custom_brush_tool(0, color=QColor(255, 0, 0))
        if tool:
            print(f"   [OK] Tool created: {tool.display_name}")
            print(f"   - Size: {tool.size}")
            print(f"   - Opacity: {tool.opacity}")
            print(f"   - Spacing: {tool.spacing}\n")
        else:
            print("   [FAIL] Tool creation returned None\n")
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        import traceback
        traceback.print_exc()

print("=== TEST COMPLETED ===")
