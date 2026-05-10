"""Simple test for brush system."""

import sys
import os

sys.path.insert(0, '.')

print("Starting simple test...")
print(f"Current directory: {os.getcwd()}")

try:
    print("Importing BrushAdapter...")
    from gui.brush_panel.brush_adapter import BrushAdapter
    print("BrushAdapter imported OK")
    
    print("Creating default tip...")
    tip = BrushAdapter._create_default_tip()
    print(f"Tip created: {tip.width()}x{tip.height()}")
    
    print("Importing BrushManager...")
    from gui.brush_panel.brush_manager import BrushManager
    print("BrushManager imported OK")
    
    print("Creating manager...")
    manager = BrushManager()
    print(f"Manager created. Converted folder: {manager.converted_folder}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
