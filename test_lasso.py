import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from gui.main import AnimatixPro
w = AnimatixPro()
print('lasso_fill color:', w.canvas.tools.get('lasso_fill').color)
app.quit()