    def _trigger_quickshape(self):
        """Dibuja forma perfecta sobre el trazo actual."""
        print("DEBUG: Timer fired!")
        
        if not self._drawing or not self._stroke_points or not self._stroke_tool:
            print("DEBUG: Early return")
            return
            
        shape_info = self._quickshape_detector.detect_shape(self._stroke_points)
        print(f"DEBUG: Shape: {shape_info}")
        
        if shape_info:
            layer = self._active_layer()
            if layer:
                painter = QPainter(layer.image)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Pen simple
                color = QColor(255, 0, 0)  # Rojo
                width = 5
                if hasattr(self._stroke_tool, 'color'):
                    color = QColor(self._stroke_tool.color)
                if hasattr(self._stroke_tool, 'width'):
                    width = self._stroke_tool.width
                
                pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                QuickShapeRenderer.draw_shape(painter, shape_info, pen)
                painter.end()
                
                self.update()
                print(f"DEBUG: Drew {shape_info['type']}")
                
                mw = self.window()
                if hasattr(mw, 'statusBar'):
                    mw.statusBar().showMessage("Forma: " + str(shape_info['type']), 2000)
        
        self._stroke_points = []
        self._stroke_tool = None
        self._drawing = False
