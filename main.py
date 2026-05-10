#!/usr/bin/env python3
"""Entry point for Animation Studio."""

import sys
from gui.main import AnimatixPro, NewProjectDialog
from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    dialog = NewProjectDialog()
    if dialog.exec():
        data = dialog.get_data()
    else:
        data = {'name': 'Nuevo Proyecto', 'width': 1920, 'height': 1080, 'bg': 'Transparente'}
    window = AnimatixPro(data)
    window.show()
    # Activar papel cebolla en modo futuro para prueba
    if hasattr(window, 'canvas'):
        window.canvas.onion_skin = True
        window.canvas.onion_mode = "Futuro"
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
