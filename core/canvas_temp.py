    def _trigger_quickshape(self):
        """Detecta forma y dibuja la forma perfecta."""
        if not self._drawing or not self._stroke_points or not self._stroke_tool:
            return
            
        # Detectar forma
        shape_info = self._quickshape_detector.detect_shape(self._stroke_points)
        
        if shape_info:
            # Dibujar forma perfecta sobre el trazo actual
            layer = self._active_layer()
            if layer:
                painter = QPainter(layer.image)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Configurar pen con los atributos del pincel actual
                color = QColor(0, 0, 0)
                width = 3
                opacity = 255
                
                if hasattr(self._stroke_tool, 'color'):
                    color = QColor(self._stroke_tool.color)
                if hasattr(self._stroke_tool, 'width'):
                    width = self._stroke_tool.width
                if hasattr(self._stroke_tool, 'opacity'):
                    opacity = self._stroke_tool.opacity
                    
                color.setAlpha(opacity)
                pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                
                QuickShapeRenderer.draw_shape(painter, shape_info, pen)
                painter.end()
                
                self.update()
                
                # Mostrar mensaje
                mw = self.window()
                if hasattr(mw, 'statusBar'):
                    msg = "Forma detectada: " + str(shape_info['type'])
                    mw.statusBar().showMessage(msg, 2000)
        
        # Limpiar
        self._stroke_points = []
        self._stroke_tool = None
        self._drawing = False