# core/tools/stabilizer.py
"""Catmull-Rom spline stabilizer for smooth strokes with signal support."""

from collections import deque
from typing import Optional
from PySide6.QtCore import QObject, Signal, QPoint, QPointF, QTimer
import math


class StabilizerSignals(QObject):
    """Signals for stabilizer changes."""
    stability_changed = Signal(int)
    reset_requested = Signal()


class Stabilizer(QObject):
    """
    Point stabilizer using Catmull-Rom spline interpolation with signal support.

    Signals:
        stability_changed: Emitted when stability value changes (0-10)
        reset_requested: Emitted when stabilizer should reset

    Attributes:
        stability: 0-10, higher = more smoothing
        buffer_size: number of points to buffer (default 4)
    """

    def __init__(self, stability: int = 0, buffer_size: int = 4):
        super().__init__()
        self.stability = stability
        self.buffer_size = buffer_size
        self._points: deque = deque(maxlen=buffer_size)
        self._pressures: deque = deque(maxlen=buffer_size)
        self._last_output: Optional[QPoint] = None

        # Delay mechanism for lag effect
        self._pending_pos: Optional[QPoint] = None
        self._delay_timer = QTimer()
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._process_delayed_point)
        self._max_delay_ms = 120  # Maximum delay at stability 10 (more lag)

        # Signals
        self.signals = StabilizerSignals(self)

    def reset(self) -> None:
        """Clear all buffered points."""
        self._points.clear()
        self._pressures.clear()
        self._last_output = None
        self._pending_pos = None
        self._delay_timer.stop()

    def add_point(self, x: float, y: float, pressure: float = 1.0) -> None:
        """Add a point to the buffer."""
        self._points.append((float(x), float(y)))
        self._pressures.append(float(pressure))

    def get_smooth_point(self, x: float, y: float) -> QPoint:
        """Get smoothed point based on stability setting with lag effect."""
        if self.stability == 0:
            self._last_output = QPoint(int(x), int(y))
            return self._last_output

        # Calculate delay based on stability (more aggressive at higher values)
        delay_ms = int(((self.stability / 10) ** 2) * self._max_delay_ms)

        # Store pending point
        self._pending_pos = QPoint(int(x), int(y))

        # If there's a previous output, smooth towards it
        if self._last_output:
            # More aggressive smoothing at higher stability (exponential curve)
            factor = (self.stability / 10) ** 2 * 0.3  # 0 at 0, 0.3 at 10
            self._last_output = QPoint(
                int(self._last_output.x() * factor + x * (1 - factor)),
                int(self._last_output.y() * factor + y * (1 - factor))
            )

        # Apply delay for lag effect
        if delay_ms > 0:
            if not self._delay_timer.isActive():
                self._delay_timer.start(delay_ms)
            # Return last known position while waiting
            if self._last_output:
                return self._last_output

        return self._last_output or QPoint(int(x), int(y))

    def _process_delayed_point(self):
        """Process the delayed point after timer fires."""
        if self._pending_pos and self.stability > 0:
            if self._last_output is None:
                self._last_output = self._pending_pos
                self._pending_pos = None
                return
            factor = (self.stability / 10) ** 2 * 0.3
            self._last_output = QPoint(
                int(self._last_output.x() * factor + self._pending_pos.x() * (1 - factor)),
                int(self._last_output.y() * factor + self._pending_pos.y() * (1 - factor))
            )

    def interpolate(self) -> list[tuple[float, float, float]]:
        """Get Catmull-Rom interpolated points."""
        if len(self._points) < 0:
            return []

        results: list[tuple[float, float, float]] = []

        if len(self._points) == 1:
            p1 = self._points[0]
            p2 = self._points[0]  # Use the same point for botsh
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            steps = max(1, int(dist / 2))

            for i in range(steps + 1):
                t = i / steps
                px = p1[0] + (p2[0] - p1[0]) * t
                py = p1[1] + (p2[1] - p1[1]) * t
                pressure = self._pressures[0] * (1 - t) + self._pressures[1] * t
                results.append((px, py, pressure))

        elif len(self._points) == 3:
            p1, p2, p3 = self._points
            dist = math.hypot(p3[0] - p2[0], p3[1] - p2[1])
            steps = max(1, int(dist / 2))

            for i in range(1, steps + 1):
                t = i / steps
                px = p1[0] + (p2[0] - p1[0]) * t
                py = p1[1] + (p2[1] - p1[1]) * t
                pressure = self._pressures[1] * (1 - t) + self._pressures[2] * t
                results.append((px, py, pressure))

        elif len(self._points) >= 4:
            p0, p1, p2, p3 = (
                self._points[-4], self._points[-3],
                self._points[-2], self._points[-1]
            )
            dist = math.hypot(p3[0] - p2[0], p3[1] - p2[1])
            steps = max(1, int(dist / 2))

            for i in range(1, steps + 1):
                t = i / steps
                tt = t * t
                ttt = tt * t

                q0 = -0.5 * ttt + tt - 0.5 * t
                q1 = 1.5 * ttt - 2.5 * tt + 1.0
                q2 = -1.5 * ttt + 2.0 * tt + 0.5 * t
                q3 = 0.5 * ttt - 0.5 * tt

                px = q0 * p0[0] + q1 * p1[0] + q2 * p2[0] + q3 * p3[0]
                py = q0 * p0[1] + q1 * p1[1] + q2 * p2[1] + q3 * p3[1]

                pressure = self._pressures[-2] * (1 - t) + self._pressures[-1] * t
                results.append((px, py, pressure))

        return results

    def set_stability(self, value: int) -> None:
        """Update stability (0-10) and emit signal."""
        self.stability = max(0, min(10, value))
        self.signals.stability_changed.emit(self.stability)


# Instancia global compartida
_shared_stabilizer: Optional[Stabilizer] = None


def get_shared_stabilizer() -> Stabilizer:
    """Get the global shared stabilizer instance."""
    global _shared_stabilizer
    if _shared_stabilizer is None:
        _shared_stabilizer = Stabilizer()
    return _shared_stabilizer


def reset_shared_stabilizer() -> None:
    """Reset the global shared stabilizer."""
    global _shared_stabilizer
    if _shared_stabilizer:
        _shared_stabilizer.reset()


class PressureSmoother:
    """Pressure value smoother to prevent jitter."""

    def __init__(self, smoothing: float = 0.3):
        self.smoothing = smoothing
        self._last = 1.0

    def get_pressure(self, pressure: float = 1.0) -> float:
        """Get smoothed pressure value."""
        self._last = self._last * self.smoothing + pressure * (1 - self.smoothing)
        return self._last

    def reset(self) -> None:
        self._last = 1.0