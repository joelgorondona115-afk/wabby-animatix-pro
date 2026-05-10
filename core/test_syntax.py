# QuickShape test - verify syntax
import sys
sys.path.insert(0, '.')

# Test the actual syntax
test_code = '''
def _trigger_quickshape(self):
    """Simple test"""
    shape_info = {"type": "circle", "confidence": 0.99}
    if shape_info:
        mw = self.window()
        if hasattr(mw, 'statusBar'):
            mw.statusBar().showMessage("Forma: " + str(shape_info['type']), 2000)
'''

import ast
try:
    ast.parse(test_code)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error: {e}")
