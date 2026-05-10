# gui/canvas.py
from PySide6.QtWidgets import QWidget, QScrollArea, QAbstractScrollArea, QApplication
from PySide6.QtGui import QPainter, QImage, QColor, QPixmap, QPen, QPainterPath
from PySide6.QtCore import Qt, QPoint, QRect, QEvent, QTimer, QPointF, QRectF

import math

from core.tools import (
    PencilTool, BrushTool, EraserTool, WatercolorTool, BristleTool, FillTool, MoveTool,
    EyedropperTool, LineTool, RectangleTool, EllipseTool, CurveTool, PolylineTool, PolyFillTool,
    LassoFillTool, LassoFillRectTool, LassoFillEllipseTool,
    RectSelectTool, LassoSelectTool, LassoMarqueeTool, LassoEraserTool, EllipseSelectTool, MoveSelectionTool,
    TextTool, BlurTool, AirbrushTool, CustomBrushTool,
    get_shared_stabilizer,
)
from core.tools.vector import VectorPencilTool, VectorBrushTool
from core.tools.quickshape import QuickShapeDetector, QuickShapeRenderer


class CanvasWidget(QWidget):
    def __init__(self, width: int, height: int, parent=None):
        super().__init__(parent)
        self.res          = (width, height)
        self.project      = None
        self.current_tool = "pencil"
        self.bg_mode      = "Transparente"
        self.background_image: QImage | None = None
        self.ref_image: QImage | None = None  # Frame de referencia
        self.ref_opacity = 80  # 0-255
        self.onion_skin   = False
        self.onion_mode   = "Pasado"  # "Pasado", "Futuro", "Ambos"
        self.onion_color_prev = QColor(0, 100, 255)  # Azul para pasado
        self.onion_color_next = QColor(255, 100, 100)  # Rojo para futuro
        self.onion_opacity   = 40  # Porcentaje (0-100)
        self.selection_rect: QRect | None = None
        self.selection_path = None
        self.selection_active = False

        self.zoom = 1.0
        self._bg_cache: QPixmap | None     = None
        self._bg_cache_key: tuple | None   = None

        # Usar estabilizador compartido
        self._stabilizer = get_shared_stabilizer()

        # Tableta gráfica
        self._pressure: float      = 1.0   # 0.0 – 1.0
        self._tablet_in_use: bool  = False
        self._drawing: bool        = False  # Solo dibujar cuando se presiona activamente
        self.setAttribute(Qt.WA_TabletTracking)

        # QuickShape (detección automática de formas)
        self._quickshape_enabled = True
        self._quickshape_detector = QuickShapeDetector()
        self._quickshape_timer = QTimer()
        self._quickshape_timer.setSingleShot(True)
        self._quickshape_timer.timeout.connect(self._trigger_quickshape)
        self._quickshape_hold_ms = 650  # 650ms como Procreate
        
        # Estado del QuickShape
        self._stroke_points: list[QPoint] = []
        self._stroke_tool = None
        self._stroke_start_pos: QPoint = None
        self._quickshape_active = False
        self._quickshape_preview = None
        self._quickshape_last_mouse = None
        
        # Ghost canvas (lienzo fantasma para trazo actual)
        self._stroke_overlay = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        self._stroke_overlay.fill(Qt.transparent)
        self._drawing_target = None  # None = dibujar a la capa, = overlay para ghost canvas
        self._stroke_overlay_visible = False  # Controla si se muestra el overlay en paintEvent

        # Brush cursor (circular, estilo Photoshop)
        self._mouse_pos: QPoint = None
        self._show_brush_cursor = False

        self.overlay_image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        self.overlay_image.fill(Qt.transparent)

        self.tools: dict = {
            "pencil":              PencilTool(color=QColor(0, 0, 0), width=3),
            "brush":               BrushTool(color=QColor(0, 0, 0), width=10),
            "watercolor":          WatercolorTool(color=QColor(0, 100, 200), size=25, wetness=0.3, fringe=0.4, opacity=180),
            "bristle":             BristleTool(color=QColor(200, 50, 50), size=55, opacity=220, bristle_count=80, bristle_spread=0.75, stiffness=0.6),
            "eraser":              EraserTool(width=20),
            "fill":                FillTool(color=QColor(0, 0, 0)),
            "move":                MoveTool(),
            "move_selection":     MoveSelectionTool(),
            "eyedrop":             EyedropperTool(),
            "line":                LineTool(color=QColor(0, 0, 0), width=3),
            "rect":                RectangleTool(color=QColor(0, 0, 0), width=3),
            "ellipse":             EllipseTool(color=QColor(0, 0, 0), width=3),
            "curve":               CurveTool(color=QColor(0, 0, 0), width=3),
            "polyline":            PolylineTool(color=QColor(0, 0, 0), width=2.0),
            "poly_fill":           PolyFillTool(color=QColor(0, 120, 215), width=2.0),
            # Lazos de RELLENO
            "lasso_fill":          LassoFillTool(color=QColor(0, 120, 215)),
            "lasso_fill_rect":     LassoFillRectTool(color=QColor(0, 120, 215)),
            "lasso_fill_ellipse":  LassoFillEllipseTool(color=QColor(0, 120, 215)),
            # Herramientas de SELECCIÓN real
            "select_rect":         RectSelectTool(),
            "select_lasso":        LassoSelectTool(),
            "lasso_eraser":       LassoEraserTool(),
            "lasso_marquee":       LassoMarqueeTool(),
            "select_ellipse":      EllipseSelectTool(),
            # Resto
            "text":                TextTool(color=QColor(0, 0, 0)),
            "blur":                BlurTool(radius=15),
            "airbrush":            AirbrushTool(color=QColor(0, 0, 0), size=60, flow=15),
            # Vector tools para cleanup
            "vector_pencil":       VectorPencilTool(color=QColor(0, 0, 0), width=2.0),
            "vector_brush":        VectorBrushTool(color=QColor(0, 0, 0), width=4.0),
        }

        self._apply_zoom()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def set_zoom(self, factor: float):
        self.zoom      = max(0.05, min(8.0, factor))
        self._bg_cache = None
        self._apply_zoom()
        self.update()
        mw = self.window()
        if hasattr(mw, "zoom_spin"):
            mw.zoom_spin.blockSignals(True)
            mw.zoom_spin.setValue(int(round(self.zoom * 100)))
            mw.zoom_spin.blockSignals(False)

    def _apply_zoom(self):
        self.setFixedSize(
            max(1, int(self.res[0] * self.zoom)),
            max(1, int(self.res[1] * self.zoom)),
        )

    def _canvas_pos(self, screen_pos: QPoint) -> QPoint:
        return QPoint(
            max(0, min(self.res[0] - 1, int(screen_pos.x() / self.zoom))),
            max(0, min(self.res[1] - 1, int(screen_pos.y() / self.zoom))),
        )

    # ------------------------------------------------------------------
    # Estabilizador (usa el compartido del stroke)
    # ------------------------------------------------------------------
    def _stabilize(self, pos: QPoint) -> QPoint:
        """Usa el estabilizador compartido del stroke."""
        return self._stabilizer.get_smooth_point(pos.x(), pos.y())

    def _reset_stabilizer(self):
        """Resetea el estabilizador compartido."""
        self._stabilizer.reset()

    # ------------------------------------------------------------------
    # Buscar QScrollArea en la jerarquía de padres
    # ------------------------------------------------------------------
    def _find_scroll_area(self):
        """
        Sube por la jerarquía de widgets buscando el primer QScrollArea
        o QAbstractScrollArea. Maneja el caso en que el canvas está
        dentro del viewport() del scroll area.
        """
        p = self.parent()
        while p is not None:
            # El parent directo puede ser el viewport() del QScrollArea
            # En ese caso, el abuelo es el QScrollArea real
            if isinstance(p, (QScrollArea, QAbstractScrollArea)):
                return p
            # Algunos layouts envuelven el QScrollArea en un QWidget intermedio;
            # seguimos subiendo
            p = p.parent() if hasattr(p, 'parent') else None
        return None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_tool(self, name: str):
        old_tool = self.tools.get(self.current_tool)
        if old_tool and old_tool.name in ("polyline", "poly_fill") and getattr(old_tool, "_is_drawing", False):
            old_tool._finalize(self)
        if old_tool and hasattr(old_tool, 'reset'):
            old_tool.reset()
        self.current_tool = name
        tool = self.tools.get(name)
        
        # Brush cursor for tools with size (bristle, brush, eraser, etc.)
        self._show_brush_cursor = tool is not None and hasattr(tool, 'size') and name in ('bristle', 'brush', 'eraser', 'watercolor', 'airbrush')
        
        if self._show_brush_cursor:
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(tool.cursor if tool and hasattr(tool, "cursor") else Qt.CrossCursor)
        self.update()

    def set_bg_mode(self, mode: str):
        self.bg_mode   = mode
        self._bg_cache = None
        self.update()

    def load_background(self, path_or_image):
        if isinstance(path_or_image, str):
            self.background_image = QImage(path_or_image)
        else:
            self.background_image = path_or_image
        if self.background_image and not self.background_image.isNull():
            self.background_image = self.background_image.scaled(
                self.res[0], self.res[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        self.update()

    def get_active_layer(self):
        if self.project:
            frame = self.project.get_current_frame()
            idx   = frame.current_layer_idx
            if 0 <= idx < len(frame.layers):
                return frame.layers[idx]
        return None

    def undo(self):
        if self.project:
            self.project.get_current_frame().undo()
            self.update()

    def redo(self):
        if self.project:
            self.project.get_current_frame().redo()
            self.update()

    # ------------------------------------------------------------------
    # Caché de fondo
    # ------------------------------------------------------------------
    def _rebuild_bg_cache(self):
        key = (self.bg_mode, self.zoom)
        if self._bg_cache_key == key and self._bg_cache:
            return
        w  = max(1, int(self.res[0] * self.zoom))
        h  = max(1, int(self.res[1] * self.zoom))
        px = QPixmap(w, h)

        if self.bg_mode == "Blanco":
            px.fill(Qt.white)
        elif self.bg_mode == "Negro":
            px.fill(Qt.black)
        else:
            p    = QPainter(px)
            tile = max(4, int(16 * self.zoom))
            ca, cb = QColor(30, 30, 30), QColor(45, 45, 45)  # Dark gray checkerboard
            for row in range(0, h, tile):
                for col in range(0, w, tile):
                    p.fillRect(col, row, tile, tile,
                               ca if (col // tile + row // tile) % 2 == 0 else cb)
            p.end()

        self._bg_cache     = px
        self._bg_cache_key = key

    # ------------------------------------------------------------------
    # Selection Management
    # ------------------------------------------------------------------
    def clear_selection(self):
        """Clear selection - releases all clipping and visual feedback."""
        self.selection_rect = None
        self.selection_path = None
        self.selection_active = False
        self.overlay_image.fill(Qt.transparent)
        self.update()

    def reset_clip_region(self):
        """Reset clipping region - allows drawing on entire canvas."""
        # This is handled in _draw_on_layer by checking selection_active
        self.update()

    def is_selection_empty(self) -> bool:
        """Check if selection is empty."""
        return not self.selection_active

    def has_selection(self) -> bool:
        """Check if there is an active selection."""
        return self.selection_active and (self.selection_rect is not None or self.selection_path is not None)

    def _is_point_in_selection(self, pos: QPoint) -> bool:
        """Check if a point is inside the current selection."""
        if not self.selection_active:
            return True
        
        if self.selection_path and self.selection_path.contains(pos):
            return True
        if self.selection_rect and self.selection_rect.contains(pos):
            return True
        
        return False

    # ------------------------------------------------------------------
    # Pintura
    # ------------------------------------------------------------------
    def _draw_selection(self, painter):
        """Draw selection with marching ants effect."""
        if not self.selection_active:
            return
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw selection rectangle
        if self.selection_rect:
            pen = QPen(Qt.blue, 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)
        
        # Draw selection path
        if self.selection_path:
            pen = QPen(Qt.blue, 2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawPath(self.selection_path)
        
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        try:
            # 1. Fondo de tablero (checkerboard)
            self._rebuild_bg_cache()
            painter.drawPixmap(0, 0, self._bg_cache)

            # 2. Verificación básica
            if not self.project or not isinstance(self.project.frames, list) or len(self.project.frames) == 0:
                return

            # 3. Configurar transformación (zoom)
            painter.save()
            painter.scale(self.zoom, self.zoom)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom != 1.0)

            # 4. Obtener frame actual
            frame = self.project.get_current_frame()
            if not frame:
                painter.restore()
                return

            # 5. Fondo de referencia
            if self.background_image and not self.background_image.isNull():
                x = (self.res[0] - self.background_image.width()) // 2
                y = (self.res[1] - self.background_image.height()) // 2
                painter.drawImage(x, y, self.background_image)

            # 6. Referencia de video (rotoscopia)
            if self.ref_image and not self.ref_image.isNull():
                painter.setOpacity(self.ref_opacity / 255.0)
                painter.drawImage(0, 0, self.ref_image)
                painter.setOpacity(1.0)

            # 7. Papel cebolla (Onion Skin) - 1 pasado, 1 futuro
            if self.onion_skin and self.project:
                modo = self.onion_mode
                idx = self.project.current_frame_idx
                total = len(self.project.frames)

                if modo in ("Pasado", "Ambos") and idx > 0:
                    prev = self.project.frames[idx - 1]
                    opacity = self.onion_opacity / 100.0
                    painter.setOpacity(opacity)
                    for layer in reversed(prev.layers):
                        if layer.visible:
                            if hasattr(layer, 'is_vector') and layer.is_vector:
                                layer.draw_all(painter)
                            else:
                                painter.drawImage(0, 0, layer.image)
                    painter.setOpacity(1.0)

                if modo in ("Futuro", "Ambos") and idx < total - 1:
                    nxt = self.project.frames[idx + 1]
                    opacity = self.onion_opacity / 100.0
                    painter.setOpacity(opacity)
                    for layer in reversed(nxt.layers):
                        if layer.visible:
                            if hasattr(layer, 'is_vector') and layer.is_vector:
                                layer.draw_all(painter)
                            else:
                                painter.drawImage(0, 0, layer.image)
                    painter.setOpacity(1.0)

            # 8. Capas del frame actual
            for layer in reversed(frame.layers):
                if layer.visible:
                    painter.setOpacity(layer.opacity / 255.0)
                    if hasattr(layer, 'is_vector') and layer.is_vector:
                        layer.draw_all(painter)
                    else:
                        painter.drawImage(0, 0, layer.image)
            painter.setOpacity(1.0)

            # 9. Overlay (dibujo temporal)
            if not self.overlay_image.isNull():
                painter.drawImage(0, 0, self.overlay_image)

            # 10. Selección (marching ants)
            self._draw_selection(painter)
            
            # 11. Ghost canvas overlay (trazo actual antes de confirmar)
            if self._stroke_overlay_visible and not self._stroke_overlay.isNull():
                painter.drawImage(0, 0, self._stroke_overlay)
            
            # 12. QuickShape preview overlay
            if self._quickshape_preview:
                self._draw_quickshape_preview(painter)

            # 13. Brush cursor (circular, estilo Photoshop)
            if self._show_brush_cursor and self._mouse_pos:
                self._draw_brush_cursor(painter)

            painter.restore()

        except Exception as e:
            print(f"Error en paintEvent: {e}")
            import traceback
            traceback.print_exc()
        finally:
            painter.end()

    # ------------------------------------------------------------------
    # Rueda → zoom enfocado en el cursor
    # ------------------------------------------------------------------
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if not delta:
            super().wheelEvent(event)
            return

        # 1. Posición del cursor en coordenadas de pantalla (relativas al canvas)
        screen_pos = event.position().toPoint()

        # 2. Convertir a coordenadas de dibujo usando el zoom ACTUAL (antes de cambiar)
        old_zoom   = self.zoom
        canvas_x   = screen_pos.x() / old_zoom
        canvas_y   = screen_pos.y() / old_zoom

        # 3. Calcular nuevo zoom
        factor   = 1.15 if delta > 0 else 1.0 / 1.15
        new_zoom = max(0.05, min(8.0, old_zoom * factor))
        self.zoom = new_zoom
        self._bg_cache = None

        # 4. Buscar el QScrollArea ANTES de aplicar el tamaño
        scroll_area = self._find_scroll_area()

        # 5. Guardar posición actual del scroll
        if scroll_area:
            old_h = scroll_area.horizontalScrollBar().value()
            old_v = scroll_area.verticalScrollBar().value()

        # 6. Aplicar el nuevo tamaño del canvas
        self._apply_zoom()

        # 7. Ajustar el scroll para que el punto bajo el cursor no se mueva
        #    Fórmula: new_scroll = old_scroll + canvas_point * (new_zoom - old_zoom)
        if scroll_area:
            offset_x = int(canvas_x * (new_zoom - old_zoom))
            offset_y = int(canvas_y * (new_zoom - old_zoom))
            scroll_area.horizontalScrollBar().setValue(old_h + offset_x)
            scroll_area.verticalScrollBar().setValue(old_v + offset_y)

        # 8. Actualizar el spin de zoom en la ventana principal
        mw = self.window()
        if hasattr(mw, "zoom_spin"):
            mw.zoom_spin.blockSignals(True)
            mw.zoom_spin.setValue(int(round(self.zoom * 100)))
            mw.zoom_spin.blockSignals(False)

        self.update()
        event.accept()

    # ------------------------------------------------------------------
    # Tableta gráfica (presión, inclinación)
    # ------------------------------------------------------------------
    def tabletEvent(self, event):
        pos = self._canvas_pos(event.position().toPoint())
        self._mouse_pos = event.position().toPoint()
        self._pressure = max(0.01, float(event.pressure()))
        
        if self._show_brush_cursor:
            self.update()
        
        tool = self.tools.get(self.current_tool)

        if event.type() == QEvent.TabletPress:
            self._tablet_in_use = True
            self._drawing = True
            self._reset_stabilizer()
            
            # Iniciar captura para QuickShape (tableta)
            if self._quickshape_enabled and tool and self.current_tool in ['pencil', 'brush']:
                self._stroke_points = [pos]
                self._stroke_tool = tool
                self._stroke_start_pos = pos
                
                # Ghost canvas
                self._stroke_overlay.fill(Qt.transparent)
                self._drawing_target = self._stroke_overlay
                self._stroke_overlay_visible = True
            else:
                self._stroke_points = []
                self._stroke_tool = None
                self._stroke_start_pos = None
                self._drawing_target = None
                
            if tool and self._pressure > 0.05:
                tool.on_press(self, pos)

        elif event.type() == QEvent.TabletMove:
            mw = self.window()
            if hasattr(mw, "lbl_coords"):
                mw.lbl_coords.setText(f"x: {pos.x()}  y: {pos.y()}")
            
            if self._quickshape_active:
                # User is editing detected shape live (tablet)
                self._quickshape_last_mouse = pos
                self._update_live_shape(pos)
            elif tool and self._drawing and self._pressure > 0.10:
                # Capturar puntos para QuickShape
                if self._quickshape_enabled and self._stroke_tool and self.current_tool in ['pencil', 'brush']:
                    self._stroke_points.append(pos)
                    
                    if len(self._stroke_points) >= 3:
                        last = self._stroke_points[-2]
                        dist = math.hypot(pos.x()-last.x(), pos.y()-last.y())
                        if dist < 3:
                            if not self._quickshape_timer.isActive():
                                self._quickshape_timer.start(self._quickshape_hold_ms)
                        else:
                            self._quickshape_timer.stop()
                
                if not self._quickshape_active:
                    tool.on_move(self, self._stabilize(pos))

        elif event.type() == QEvent.TabletRelease:
            self._pressure = 1.0
            self._drawing = False
            
            if self._quickshape_active:
                self._commit_quickshape()
            else:
                # Composite overlay to layer
                if self._stroke_overlay_visible:
                    self._composite_overlay_to_layer()
                
                if tool:
                    tool.on_release(self, pos)
                self._quickshape_timer.stop()
                self._clear_stroke_state()
            
            self._reset_stabilizer()
            QTimer.singleShot(80, self._clear_tablet_flag)

        event.accept()

    def _clear_tablet_flag(self):
        self._tablet_in_use = False

    # ------------------------------------------------------------------
    # Mouse (fallback cuando no hay tableta)
    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        # Escape: Cancelar QuickShape o Deseleccionar
        if event.key() == Qt.Key_Escape:
            if self._quickshape_active:
                self._cancel_quickshape()
            else:
                self.clear_selection()
                tool = self.tools.get(self.current_tool)
                if tool and hasattr(tool, '_cancel'):
                    tool._cancel(self)
            return
        
        # Ctrl+D: Deseleccionar
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
            self.clear_selection()
            return
        
        # Enter: Confirmar QuickShape o cerrar lazo
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self._quickshape_active:
                self._commit_quickshape()
                return
            
            tool = self.tools.get(self.current_tool)
            if tool and hasattr(tool, '_finalize') and getattr(tool, '_is_drawing', False):
                tool._finalize(self)
                return
            
            if tool and hasattr(tool, '_is_drawing') and tool._is_drawing:
                pos = self._canvas_pos(self.mapFromGlobal(self.cursor().pos()))
                tool.on_release(self, pos)
            
            self.reset_clip_region()
            self.overlay_image.fill(Qt.transparent)
            self.update()
            return
        
        # Flechas para navegar frames de referencia
        if event.key() == Qt.Key_Right:
            self.next_ref_frame()
            event.accept()
            return
        if event.key() == Qt.Key_Left:
            self.prev_ref_frame()
            event.accept()
            return
        
        super().keyPressEvent(event)
    
    def next_ref_frame(self):
        """Avanza al siguiente frame de referencia."""
        main = self.window()
        if main and hasattr(main, 'ref_frames') and main.ref_frames:
            main.ref_idx = (main.ref_idx + 1) % len(main.ref_frames)
            self.ref_image = main.ref_frames[main.ref_idx]
            self.update()
            self._update_ref_label()
    
    def prev_ref_frame(self):
        """Retrocede al frame de referencia anterior."""
        main = self.window()
        if main and hasattr(main, 'ref_frames') and main.ref_frames:
            main.ref_idx = (main.ref_idx - 1) % len(main.ref_frames)
            self.ref_image = main.ref_frames[main.ref_idx]
            self.update()
            self._update_ref_label()
    
    def _update_ref_label(self):
        """Actualiza etiqueta de frame de referencia."""
        main = self.window()
        if main and hasattr(main, 'lbl_ref_frame'):
            main.lbl_ref_frame.setText(f"Ref: {main.ref_idx + 1}/{len(main.ref_frames)}")

    def mousePressEvent(self, event):
        # Si hay un QuickShape pendiente, confirmarlo
        if hasattr(self, '_pending_quickshape') and self._pending_quickshape:
            self._commit_quickshape()
            return
            
        if self._tablet_in_use:
            return
        self.setFocus()
        
        # Check for mouse shortcuts first (don't draw)
        mw = self.window()
        if hasattr(mw, '_mouse_shortcuts'):
            btn = ""
            if event.button() == Qt.LeftButton:
                btn = "LeftButton"
            elif event.button() == Qt.RightButton:
                btn = "RightButton"
            elif event.button() == Qt.MiddleButton:
                btn = "MiddleButton"
            
            if btn:
                # Check if any modifier is held
                mods = event.modifiers()
                if mods & Qt.ControlModifier:
                    btn = "Ctrl+" + btn
                elif mods & Qt.AltModifier:
                    btn = "Alt+" + btn
                elif mods & Qt.ShiftModifier:
                    btn = "Shift+" + btn
                
                if btn in mw._mouse_shortcuts:
                    mw._mouse_shortcuts[btn]()
                    return
        
        if event.button() == Qt.LeftButton:
            self._drawing = True
            self._reset_stabilizer()
            pos  = self._canvas_pos(event.pos())
            tool = self.tools.get(self.current_tool)
            
            # Auto-deselect when clicking outside selection with non-selection tools
            if self.selection_active and tool:
                tool_name = getattr(tool, 'name', '')
                if not tool_name.startswith('select') and not tool_name.startswith('lasso'):
                    if not self._is_point_in_selection(pos):
                        self.clear_selection()
            
            # Iniciar QuickShape
            if self._quickshape_enabled and tool and self.current_tool in ['pencil', 'brush']:
                self._stroke_points = [pos]
                self._stroke_tool = tool
                self._stroke_start_pos = pos
                self._quickshape_active = False
                self._quickshape_preview = None
                self._quickshape_timer.stop()
                
                # Ghost canvas: dibujar al overlay, no a la capa
                self._stroke_overlay.fill(Qt.transparent)
                self._drawing_target = self._stroke_overlay
                self._stroke_overlay_visible = True
            else:
                self._stroke_points = []
                self._stroke_tool = None
                self._stroke_start_pos = None
                self._drawing_target = None
            
            if tool:
                tool.on_press(self, pos)
        elif event.button() == Qt.RightButton:
            tool = self.tools.get(self.current_tool)
            pos = self._canvas_pos(event.pos())
            if tool:
                tool.on_press(self, pos)
        elif event.button() == Qt.MiddleButton:
            tool = self.tools.get("move")
            pos = self._canvas_pos(event.pos())
            if tool:
                tool.on_press(self, pos)

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.pos()
        if self._show_brush_cursor:
            self.update()
        if self._tablet_in_use:
            return
        raw_pos = self._canvas_pos(event.pos())
        mw = self.window()
        if hasattr(mw, "lbl_coords"):
            mw.lbl_coords.setText(f"x: {raw_pos.x()}  y: {raw_pos.y()}")

        if event.buttons() & Qt.LeftButton and self._drawing:
            pos  = self._stabilize(raw_pos)
            tool = self.tools.get(self.current_tool)
            
            # QuickShape logic
            if self._quickshape_enabled and self._stroke_tool and self.current_tool in ['pencil', 'brush']:
                if self._quickshape_active:
                    # User is editing detected shape live
                    self._quickshape_last_mouse = raw_pos
                    self._update_live_shape(raw_pos)
                else:
                    # Still collecting stroke points
                    self._stroke_points.append(pos)
                    
                    if len(self._stroke_points) >= 3:
                        last = self._stroke_points[-2]
                        dist = math.hypot(pos.x()-last.x(), pos.y()-last.y())
                        if dist < 3:  # User stopped moving
                            if not self._quickshape_timer.isActive():
                                self._quickshape_timer.start(self._quickshape_hold_ms)
                        else:
                            self._quickshape_timer.stop()  # Reset timer on movement
            
            if tool and not self._quickshape_active:
                tool.on_move(self, pos)
        
        elif event.buttons() & Qt.RightButton:
            tool = self.tools.get(self.current_tool)
            if tool:
                pos = self._stabilize(raw_pos)
                tool.on_move(self, pos)
        
        elif event.buttons() & Qt.MiddleButton:
            tool = self.tools.get(self.current_tool)
            if tool:
                pos = self._stabilize(raw_pos)
                tool.on_move(self, pos)

    def mouseReleaseEvent(self, event):
        if self._tablet_in_use:
            return
        if event.button() == Qt.LeftButton:
            pos  = self._canvas_pos(event.pos())
            tool = self.tools.get(self.current_tool)
            
            if self._quickshape_active:
                self._commit_quickshape()
            else:
                # Normal release: composite ghost overlay to layer
                if self._stroke_overlay_visible:
                    self._composite_overlay_to_layer()
                
                if tool:
                    tool.on_release(self, pos)
                self._quickshape_timer.stop()
                self._clear_stroke_state()
            
            self._drawing = False
            self._reset_stabilizer()
            
        elif event.button() == Qt.RightButton:
            tool = self.tools.get(self.current_tool)
            pos = self._canvas_pos(event.pos())
            if tool:
                tool.on_release(self, pos)
            self._drawing = False
            self._reset_stabilizer()
        
        elif event.button() == Qt.MiddleButton:
            tool = self.tools.get("move")
            pos = self._canvas_pos(event.pos())
            if tool:
                tool.on_release(self, pos)
            self._drawing = False
            self._reset_stabilizer()

    # ------------------------------------------------------------------
    # QuickShape - Procreate-like shape detection
    # ------------------------------------------------------------------
    def _trigger_quickshape(self):
        """Called when hold timer fires - detect shape and enter edit mode."""
        if not self._stroke_points or not self._stroke_tool:
            return
        
        shape_info = self._quickshape_detector.detect_shape(self._stroke_points)
        
        if shape_info:
            # Hide the ghost canvas overlay (trazo a pulso desaparece)
            self._stroke_overlay_visible = False
            self._drawing_target = None
            
            self._quickshape_active = True
            self._quickshape_preview = shape_info
            self._quickshape_last_mouse = self._stroke_points[-1] if self._stroke_points else None
            
            self.update()
            
            mw = self.window()
            if hasattr(mw, 'statusBar'):
                shape_names = {'line': 'Línea', 'rect': 'Rectángulo', 'circle': 'Círculo', 'ellipse': 'Elipse', 'curve': 'Curva'}
                name = shape_names.get(shape_info['type'], shape_info['type'])
                mw.statusBar().showMessage(f"QuickShape: {name} (mueve para editar, Shift=snap, Enter=confirmar, Esc=cancelar)", 3000)
        else:
            # No shape detected - resume normal drawing on ghost canvas
            self._drawing = True
    
    def _update_live_shape(self, current_pos: QPoint):
        """Update the detected shape based on current mouse position."""
        if not self._quickshape_preview or not self._stroke_start_pos:
            return
        
        shift_held = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
        
        self._quickshape_preview = self._quickshape_detector.update_shape_params(
            self._quickshape_preview, current_pos, self._stroke_start_pos, shift_held
        )
        self.update()
    
    def _commit_quickshape(self):
        """Commit the QuickShape to the layer."""
        if not self._quickshape_preview:
            self._cancel_quickshape()
            return
        
        layer = self._active_layer()
        if not layer:
            self._cancel_quickshape()
            return
        
        color = QColor(255, 0, 0)
        width = 3
        if hasattr(self._stroke_tool, 'color'):
            color = QColor(self._stroke_tool.color)
        if hasattr(self._stroke_tool, 'width'):
            width = self._stroke_tool.width
        
        # Draw the perfect shape to the layer (la capa está limpia, sin trazo a pulso)
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter = QPainter(layer.image)
        painter.setRenderHint(QPainter.Antialiasing)
        QuickShapeRenderer.draw_shape(painter, self._quickshape_preview, pen)
        painter.end()
        
        self._clear_quickshape_state()
        self.update()
        
        mw = self.window()
        if hasattr(mw, 'statusBar'):
            shape_names = {'line': 'Línea', 'rect': 'Rectángulo', 'circle': 'Círculo', 'ellipse': 'Elipse', 'curve': 'Curva'}
            name = shape_names.get(self._quickshape_preview.get('type', ''), '')
            mw.statusBar().showMessage(f"{name} creada", 1500)
    
    def _cancel_quickshape(self):
        """Cancel QuickShape and restore the freehand stroke (ghost overlay)."""
        # Show the ghost overlay again (el trazo a pulso reaparece)
        self._drawing_target = self._stroke_overlay
        self._stroke_overlay_visible = True
        
        self._clear_quickshape_state()
        self._drawing = True
        self.update()
        
        mw = self.window()
        if hasattr(mw, 'statusBar'):
            mw.statusBar().showMessage("QuickShape cancelado", 1000)
    
    def _composite_overlay_to_layer(self):
        """Composite the ghost overlay onto the active layer."""
        layer = self._active_layer()
        if not layer:
            return
        
        painter = QPainter(layer.image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.drawImage(0, 0, self._stroke_overlay)
        painter.end()
        
        # Clear overlay
        self._stroke_overlay.fill(Qt.transparent)
        self._stroke_overlay_visible = False
        self._drawing_target = None
    
    def _clear_stroke_state(self):
        """Reset all stroke-related state variables."""
        self._stroke_points = []
        self._stroke_tool = None
        self._stroke_start_pos = None
        self._drawing_target = None
        self._stroke_overlay_visible = False
        self._stroke_overlay.fill(Qt.transparent)
    
    def _clear_quickshape_state(self):
        """Reset all QuickShape state variables."""
        self._quickshape_active = False
        self._quickshape_preview = None
        self._stroke_points = []
        self._stroke_tool = None
        self._stroke_start_pos = None
        self._quickshape_last_mouse = None
        self._quickshape_timer.stop()
        self._drawing_target = None
        self._stroke_overlay_visible = False
        self._stroke_overlay.fill(Qt.transparent)
    
    def _draw_quickshape_preview(self, painter):
        """Draw QuickShape preview overlay."""
        if not self._quickshape_preview:
            return
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom != 1.0)
        painter.scale(self.zoom, self.zoom)
        
        # Get tool color and width for preview
        color = QColor(255, 0, 0)
        width = 3
        if hasattr(self._stroke_tool, 'color'):
            color = QColor(self._stroke_tool.color)
        if hasattr(self._stroke_tool, 'width'):
            width = self._stroke_tool.width
        
        # Draw with dashed preview style
        pen = QPen(color, width, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        c = QColor(color)
        c.setAlpha(180)
        pen.setColor(c)
        
        QuickShapeRenderer.draw_shape(painter, self._quickshape_preview, pen)
        
        # Draw control point indicators
        params = self._quickshape_preview['params']
        if self._quickshape_last_mouse:
            # Draw a small circle at the control point
            ctrl_pen = QPen(QColor(100, 180, 255), 2, Qt.SolidLine)
            ctrl_pen.setColor(QColor(100, 180, 255, 200))
            painter.setPen(ctrl_pen)
            painter.setBrush(QColor(100, 180, 255, 100))
            painter.drawEllipse(self._quickshape_last_mouse, 4, 4)
        
        painter.restore()

    def _draw_brush_cursor(self, painter: QPainter) -> None:
        """Draw brush cursor at mouse position (Photoshop style)."""
        tool = self.tools.get(self.current_tool)
        if not tool:
            return
        
        pressure = getattr(self, '_pressure', 1.0)
        size = getattr(tool, 'size', 20) * pressure
        
        pos = self._mouse_pos
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_tool == 'bristle' and hasattr(tool, '_last') and tool._last:
            # Elliptical brush for bristle - oriented to stroke direction
            aspect = getattr(tool, 'aspect', 3.0)
            radius_w = size * aspect * 0.5
            radius_h = size * 0.5
            angle = tool._angle if hasattr(tool, '_angle') else 0.0
            
            pen = QPen(QColor(200, 200, 200, 180), 1.0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.translate(x, y)
            painter.rotate(math.degrees(angle))
            painter.drawEllipse(QPointF(0, 0), radius_w, radius_h)
        else:
            # Circular brush for other tools
            radius = size * 0.5
            pen = QPen(QColor(200, 200, 200, 180), 1.0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, y), radius, radius)
            
            cross_size = max(3, radius * 0.15)
            cross_pen = QPen(QColor(200, 200, 200, 120), 0.8)
            painter.setPen(cross_pen)
            painter.drawLine(QPointF(x - cross_size, y), QPointF(x + cross_size, y))
            painter.drawLine(QPointF(x, y - cross_size), QPointF(x, y + cross_size))
        
        painter.restore()

    def _active_layer(self):
        """Obtiene la capa activa."""
        if self.project:
            frame = self.project.get_current_frame()
            if frame and frame.layers:
                return frame.current_layer  # Usar la propiedad current_layer
        return None
    
    def set_reference_color(self, color):
        """Recibe color del reference window."""
        mw = self.window()
        if hasattr(mw, "color_picker"):
            mw.color_picker.set_color(color)
    
    def enterEvent(self, event):
        if self._show_brush_cursor:
            self.setCursor(Qt.BlankCursor)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._mouse_pos = None
        if self._show_brush_cursor:
            self.update()
        super().leaveEvent(event)
