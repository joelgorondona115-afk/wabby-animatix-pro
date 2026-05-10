# core/tools/quickshape.py
"""QuickShape detector - auto-detects shapes from freehand strokes like Procreate."""

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
import math


class QuickShapeDetector:
    """Analyzes stroke points and detects geometric shapes with Procreate-like accuracy."""
    
    def __init__(self):
        self.min_points = 8
        self.line_threshold = 0.80
        self.rect_threshold = 0.65
        self.ellipse_threshold = 0.70
        self.curve_threshold = 0.80
        self.close_threshold = 0.20  # 20% of bbox diagonal to consider closed
        
    def detect_shape(self, points: list[QPoint], force_closed: bool = False) -> dict | None:
        """Analyze points and return detected shape info."""
        if len(points) < self.min_points:
            return None
        
        # Close gap if shape is nearly closed
        is_closed = self._is_shape_closed(points)
        work_points = self._close_gap(points) if (is_closed or force_closed) else list(points)
        
        # Simplify for analysis
        simplified = self._simplify_points(work_points, tolerance=3.0)
        
        # Try line detection
        line_result = self._detect_line(simplified)
        if line_result and line_result['confidence'] > self.line_threshold:
            return line_result
        
        # Try ellipse/circle first (common user intent)
        ellipse_result = self._detect_ellipse(work_points)
        
        # Try rectangle
        rect_result = self._detect_rectangle(work_points)
        
        # If both pass, prefer the one with higher confidence
        if ellipse_result and ellipse_result['confidence'] > self.ellipse_threshold:
            if rect_result and rect_result['confidence'] > self.rect_threshold:
                if rect_result['confidence'] > ellipse_result['confidence']:
                    return rect_result
            return ellipse_result
        
        if rect_result and rect_result['confidence'] > self.rect_threshold:
            return rect_result
        
        # Try curve for open shapes
        if not is_closed and not force_closed:
            curve_result = self._detect_curve(simplified)
            if curve_result and curve_result['confidence'] > self.curve_threshold:
                return curve_result
        
        return None
    
    def _close_gap(self, points: list[QPoint]) -> list[QPoint]:
        """If start and end are close, interpolate a smooth closure."""
        if len(points) < 2:
            return list(points)
        
        start = points[0]
        end = points[-1]
        dist = math.hypot(end.x() - start.x(), end.y() - start.y())
        
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        diagonal = math.hypot(max_x - min_x, max_y - min_y)
        threshold = max(15, diagonal * self.close_threshold)
        
        if dist < threshold and dist > 1:
            # Interpolate 5 points between end and start to close smoothly
            closed = list(points)
            steps = 5
            for i in range(1, steps):
                t = i / steps
                x = int(end.x() + (start.x() - end.x()) * t)
                y = int(end.y() + (start.y() - end.y()) * t)
                closed.append(QPoint(x, y))
            closed.append(QPoint(start.x(), start.y()))
            return closed
        
        return list(points)
    
    def _is_shape_closed(self, points: list[QPoint]) -> bool:
        """Check if start and end points are close enough."""
        if len(points) < 2:
            return False
        start = points[0]
        end = points[-1]
        dist = math.hypot(end.x() - start.x(), end.y() - start.y())
        
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        diagonal = math.hypot(max_x - min_x, max_y - min_y)
        threshold = max(15, diagonal * self.close_threshold)
        return dist < threshold
    
    def _simplify_points(self, points: list[QPoint], tolerance: float = 5.0) -> list[QPoint]:
        """Ramer-Douglas-Peucker algorithm."""
        if len(points) < 3:
            return list(points)
        
        def perp_dist(point, start, end):
            if start == end:
                return math.hypot(point.x() - start.x(), point.y() - start.y())
            n = abs((end.y() - start.y()) * point.x() - 
                    (end.x() - start.x()) * point.y() + 
                    end.x() * start.y() - end.y() * start.x())
            d = math.hypot(end.y() - start.y(), end.x() - start.x())
            return n / d if d != 0 else 0
        
        def rdp(pts, tol):
            if len(pts) < 3:
                return list(pts)
            max_d = 0
            max_i = 0
            for i in range(1, len(pts) - 1):
                d = perp_dist(pts[i], pts[0], pts[-1])
                if d > max_d:
                    max_d = d
                    max_i = i
            if max_d > tol:
                left = rdp(pts[:max_i + 1], tol)
                right = rdp(pts[max_i:], tol)
                return left[:-1] + right
            return [pts[0], pts[-1]]
        
        return rdp(points, tolerance)
    
    def _detect_line(self, points: list[QPoint]) -> dict | None:
        """Detect straight line."""
        if len(points) < 2:
            return None
        
        start = points[0]
        end = points[-1]
        line_len = math.hypot(end.x() - start.x(), end.y() - start.y())
        
        if line_len < 10:
            return None
        
        # Max deviation from line
        max_dev = 0
        total_dev = 0
        for p in points[1:-1]:
            d = self._point_to_line_distance(p, start, end)
            total_dev += d
            max_dev = max(max_dev, d)
        
        avg_dev = total_dev / max(1, len(points) - 2)
        norm_dev = avg_dev / (line_len * 0.08)
        confidence = max(0, 1.0 - norm_dev)
        
        if confidence > self.line_threshold:
            return {
                'type': 'line',
                'confidence': confidence,
                'params': {
                    'start': QPointF(start),
                    'end': QPointF(end),
                    'original_end': QPointF(end),
                }
            }
        return None
    
    def _detect_rectangle(self, points: list[QPoint]) -> dict | None:
        """Detect rectangle by analyzing point distribution along edges and corners."""
        if len(points) < 12:
            return None
        
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        
        w = max_x - min_x
        h = max_y - min_y
        
        if w < 15 or h < 15:
            return None
        
        # Tolerance based on size
        tol = max(8, min(w, h) * 0.12)
        
        # Count points near each edge
        left_pts = sum(1 for p in points if abs(p.x() - min_x) < tol)
        right_pts = sum(1 for p in points if abs(p.x() - max_x) < tol)
        top_pts = sum(1 for p in points if abs(p.y() - min_y) < tol)
        bottom_pts = sum(1 for p in points if abs(p.y() - max_y) < tol)
        
        total = len(points)
        
        # Rectangle needs points on ALL 4 edges
        edge_ratio = (left_pts + right_pts + top_pts + bottom_pts) / (total * 2)  # Max 2 edges per point
        min_edge_coverage = min(left_pts, right_pts, top_pts, bottom_pts) / total
        
        # Reject if any edge has almost no points (likely a circle/ellipse)
        if min_edge_coverage < 0.05:
            return None
        
        # Also check corner coverage - rectangles have points near corners
        corners = 0
        corner_tol = tol * 1.5
        if any(abs(p.x() - min_x) < corner_tol and abs(p.y() - min_y) < corner_tol for p in points):
            corners += 1
        if any(abs(p.x() - max_x) < corner_tol and abs(p.y() - min_y) < corner_tol for p in points):
            corners += 1
        if any(abs(p.x() - min_x) < corner_tol and abs(p.y() - max_y) < corner_tol for p in points):
            corners += 1
        if any(abs(p.x() - max_x) < corner_tol and abs(p.y() - max_y) < corner_tol for p in points):
            corners += 1
        
        # Need at least 3 corners for rectangle
        if corners < 3:
            return None
        
        confidence = (edge_ratio + corners / 4) / 2
        
        if confidence > self.rect_threshold:
            return {
                'type': 'rect',
                'confidence': confidence,
                'params': {
                    'rect': QRect(min_x, min_y, w, h),
                    'center': QPointF(min_x + w/2, min_y + h/2),
                    'width': w,
                    'height': h,
                }
            }
        return None
    
    def _detect_ellipse(self, points: list[QPoint]) -> dict | None:
        """Detect ellipse/circle using bounding-box normalized distance method."""
        if len(points) < 10:
            return None
        
        # Bounding box
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        radius_x = (max_x - min_x) / 2
        radius_y = (max_y - min_y) / 2
        
        if radius_x < 8 or radius_y < 8:
            return None
        
        # Method 1: Bounding-box normalized distance (good for ellipses)
        bb_errors = []
        for p in points:
            dx = p.x() - center_x
            dy = p.y() - center_y
            if radius_x > 0 and radius_y > 0:
                normalized_dist = math.sqrt((dx/radius_x)**2 + (dy/radius_y)**2)
                bb_errors.append(abs(normalized_dist - 1.0))
        
        avg_bb_error = sum(bb_errors) / len(bb_errors)
        bb_confidence = max(0, 1.0 - avg_bb_error * 2.5)
        
        # Method 2: Center-of-mass (good for circles)
        cx = sum(p.x() for p in points) / len(points)
        cy = sum(p.y() for p in points) / len(points)
        dists = [math.hypot(p.x() - cx, p.y() - cy) for p in points]
        avg_r = sum(dists) / len(dists)
        
        if avg_r < 8:
            return None
        
        variance = sum((d - avg_r) ** 2 for d in dists) / len(dists)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg_r if avg_r > 0 else 1.0
        com_confidence = max(0, 1.0 - cv * 2.0)
        
        # Use the better of the two methods
        confidence = max(bb_confidence, com_confidence)
        
        shape_type = 'circle' if abs(radius_x - radius_y) < min(radius_x, radius_y) * 0.25 else 'ellipse'
        
        if confidence > self.ellipse_threshold:
            return {
                'type': shape_type,
                'confidence': confidence,
                'params': {
                    'center': QPointF(cx, cy),
                    'radius': avg_r,
                    'radius_x': radius_x,
                    'radius_y': radius_y,
                    'original_center': QPointF(cx, cy),
                }
            }
        return None
    
    def _point_to_line_distance(self, point: QPoint, start: QPoint, end: QPoint) -> float:
        """Perpendicular distance from point to line."""
        if start == end:
            return math.hypot(point.x() - start.x(), point.y() - start.y())
        n = abs((end.y() - start.y()) * point.x() - 
                (end.x() - start.x()) * point.y() + 
                end.x() * start.y() - end.y() * start.x())
        d = math.hypot(end.y() - start.y(), end.x() - start.x())
        return n / d if d != 0 else 0
    
    def _detect_curve(self, points: list[QPoint]) -> dict | None:
        """Detect smooth open curve and fit quadratic Bezier."""
        if len(points) < 5:
            return None
        
        start = points[0]
        end = points[-1]
        line_len = math.hypot(end.x() - start.x(), end.y() - start.y())
        
        if line_len < 15:
            return None
        
        # Find max deviation point
        max_dev = 0
        max_idx = 0
        total_dev = 0
        
        for i, p in enumerate(points[1:-1], 1):
            d = self._point_to_line_distance(p, start, end)
            total_dev += d
            if d > max_dev:
                max_dev = d
                max_idx = i
        
        avg_dev = total_dev / max(1, len(points) - 2)
        line_conf = max(0, 1.0 - (avg_dev / (line_len * 0.08)))
        
        # Must have significant curve, not be a line
        if line_conf < 0.75 and max_dev > 12:
            control = points[max_idx]
            return {
                'type': 'curve',
                'confidence': 0.85,
                'params': {
                    'start': QPointF(start),
                    'control': QPointF(control),
                    'end': QPointF(end),
                }
            }
        return None
    
    def snap_angle(self, start: QPointF, end: QPointF) -> QPointF:
        """Snap line to nearest 15° increment (0°, 15°, 30°, 45°, 60°, 75°, 90°)."""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        angle = math.atan2(dy, dx)
        length = math.hypot(dx, dy)
        
        # Snap to nearest 15 degrees (π/12 radians)
        snap_unit = math.pi / 12
        snapped_angle = round(angle / snap_unit) * snap_unit
        
        return QPointF(
            start.x() + length * math.cos(snapped_angle),
            start.y() + length * math.sin(snapped_angle)
        )
    
    def update_shape_params(self, shape_info: dict, current_pos: QPoint, start_pos: QPoint, shift_held: bool = False) -> dict:
        """Update shape params based on live mouse position for editing."""
        params = shape_info['params']
        shape_type = shape_info['type']
        
        if shape_type == 'line':
            new_end = QPointF(current_pos)
            if shift_held:
                new_end = self.snap_angle(start_pos, new_end)
            return {
                **shape_info,
                'params': {
                    'start': QPointF(start_pos),
                    'end': new_end,
                }
            }
        
        elif shape_type in ('circle', 'ellipse'):
            center = params['center']
            dx = current_pos.x() - center.x()
            dy = current_pos.y() - center.y()
            new_radius = max(5, math.hypot(dx, dy))
            
            if shift_held or shape_type == 'circle':
                # Force perfect circle
                return {
                    **shape_info,
                    'type': 'circle',
                    'params': {
                        'center': center,
                        'radius': new_radius,
                        'radius_x': new_radius,
                        'radius_y': new_radius,
                    }
                }
            else:
                # Allow ellipse with different radii
                return {
                    **shape_info,
                    'params': {
                        'center': center,
                        'radius': new_radius,
                        'radius_x': max(5, abs(dx)),
                        'radius_y': max(5, abs(dy)),
                    }
                }
        
        elif shape_type == 'rect':
            center = params['center']
            dx = current_pos.x() - center.x()
            dy = current_pos.y() - center.y()
            half_w = max(5, abs(dx))
            half_h = max(5, abs(dy))
            
            if shift_held:
                # Force square
                size = max(half_w, half_h)
                half_w = size
                half_h = size
            
            return {
                **shape_info,
                'params': {
                    'rect': QRect(int(center.x() - half_w), int(center.y() - half_h), 
                                  int(half_w * 2), int(half_h * 2)),
                    'center': center,
                    'width': half_w * 2,
                    'height': half_h * 2,
                }
            }
        
        return shape_info


class QuickShapeRenderer:
    """Renders detected shapes onto the canvas."""
    
    @staticmethod
    def draw_shape(painter: QPainter, shape_info: dict, pen: QPen, fill: QColor = None) -> None:
        """Draw a detected shape."""
        shape_type = shape_info['type']
        params = shape_info['params']
        
        painter.setPen(pen)
        if fill:
            painter.setBrush(fill)
        else:
            painter.setBrush(QColor(0, 0, 0, 0))
        
        if shape_type == 'line':
            painter.drawLine(params['start'], params['end'])
        elif shape_type == 'rect':
            painter.drawRect(params['rect'])
        elif shape_type == 'ellipse':
            rect = QRectF(
                params['center'].x() - params['radius_x'],
                params['center'].y() - params['radius_y'],
                params['radius_x'] * 2,
                params['radius_y'] * 2
            )
            painter.drawEllipse(rect)
        elif shape_type == 'circle':
            r = params['radius']
            painter.drawEllipse(params['center'], r, r)
        elif shape_type == 'curve':
            path = QPainterPath()
            path.moveTo(params['start'])
            path.quadTo(params['control'], params['end'])
            painter.setPen(pen)
            painter.drawPath(path)
    
    @staticmethod
    def draw_preview(painter: QPainter, shape_info: dict, pen: QPen) -> None:
        """Draw shape with dashed preview style."""
        pen.setStyle(Qt.DashLine)
        pen.setWidth(max(1, pen.width()))
        # Make preview slightly transparent
        c = QColor(pen.color())
        c.setAlpha(int(c.alpha() * 0.6))
        pen.setColor(c)
        QuickShapeRenderer.draw_shape(painter, shape_info, pen)
