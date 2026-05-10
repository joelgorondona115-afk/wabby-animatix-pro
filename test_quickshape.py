# test_quickshape.py - Prueba simple de QuickShape
import sys
import os
sys.path.insert(0, '.')

from PySide6.QtGui import QImage, QColor, QPainter, QPen
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
import math

# Importar QuickShape
from core.tools.quickshape import QuickShapeDetector, QuickShapeRenderer

# Crear detector
detector = QuickShapeDetector()

# Simular un círculo
print("Probando detección de círculo...")
points = []
for i in range(100):
    angle = (i / 99) * 2 * math.pi
    x = int(100 + 50 * math.cos(angle))
    y = int(100 + 50 * math.sin(angle))
    points.append(QPoint(x, y))

result = detector.detect_shape(points)
if result:
    print(f"Detectado: {result['type']} con confianza {result['confidence']:.2f}")
    
    # Dibujar en una imagen
    img = QImage(200, 200, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(255, 255, 255))
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(255, 0, 0), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    QuickShapeRenderer.draw_shape(painter, result, pen)
    painter.end()
    
    img.save('test_quickshape_circle.png')
    print("Imagen guardada: test_quickshape_circle.png")
else:
    print("No se detectó forma")

# Probar curva
print("\nProbando detección de curva...")
points2 = [QPoint(50, 100)]
for i in range(1, 100):
    t = i / 99
    x = int(50 + t * 100)
    y = int(100 - 80 * math.sin(t * math.pi))
    points2.append(QPoint(x, y))

result2 = detector.detect_shape(points2)
if result2:
    print(f"Detectado: {result2['type']} con confianza {result2['confidence']:.2f}")
    
    img2 = QImage(200, 200, QImage.Format_ARGB32_Premultiplied)
    img2.fill(QColor(255, 255, 255))
    
    painter2 = QPainter(img2)
    painter2.setRenderHint(QPainter.Antialiasing)
    pen2 = QPen(QColor(0, 0, 255), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    QuickShapeRenderer.draw_shape(painter2, result2, pen2)
    painter2.end()
    
    img2.save('test_quickshape_curve.png')
    print("Imagen guardada: test_quickshape_curve.png")
else:
    print("No se detectó forma")

print("\nPrueba completada.")
