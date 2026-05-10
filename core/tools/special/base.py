# core/tools/special/base.py
"""Special tools base class."""

from PySide6.QtCore import Qt

from core.tools.base import DrawingTool


class SpecialToolBase(DrawingTool):
    """Base class for special tools."""

    cursor = Qt.CrossCursor