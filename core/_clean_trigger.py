    def _trigger_quickshape(self):
        """Dibuja forma perfecta sobre el trazo actual."""
        if not self._drawing or not self._stroke_points or not self._stroke_tool:
            return
            
        shape_info = self._quickshape_detector.detect_shape(self._stroke_points)
        
        if shape_info:
            layer = self._active_layer()
            if layer:
                painter = QPainter(layer.image)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Configurar pen
                color = QColor(255, 0, 0)  # Rojo para probar
                width = 5
                if hasattr(self._stroke_tool, 'color'):
                    color = QColor(self._stroke_tool.color)
                if hasattr(self._stroke_tool, 'width'):
                    width = self._stroke_tool.width
                if hasattr(self._stroke_tool, 'opacity'):
                    color.setAlpha(self._stroke_tool.opacity)
                
                pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                QuickShapeRenderer.draw_shape(painter, shape_info, pen)
                painter.end()
                
                self.update()
                
                mw = self.window()
                if hasattr(mw, 'statusBar'):
                    msg = "Forma: " + str(shape_info['type'])
                    mw.statusBar().showMessage(msg, 2000)
        
        self._stroke_points = []
        self._stroke_tool = None
        self._drawing = False
