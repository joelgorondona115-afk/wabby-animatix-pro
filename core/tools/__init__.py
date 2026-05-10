# core/tools/__init__.py
"""Drawing tools for animation application."""

from .base import DrawingTool, _active_layer, _push_undo, _draw_on_layer
from .stabilizer import Stabilizer, PressureSmoother, get_shared_stabilizer
from .stroke import StrokeHandler, PencilStroke, BrushStroke, EraserStroke
from .parsers import parse_abr

# Drawing tools
from .drawing import PencilTool, BrushTool, EraserTool, WatercolorTool, BristleTool

# Shape tools
from .shape import LineTool, RectangleTool, EllipseTool, CurveTool, PolylineTool, PolyFillTool

# Special tools
from .special import TextTool, BlurTool, AirbrushTool, CustomBrushTool

# Fill tools
from .fill import FillTool, EyedropperTool

# Lasso tools
from .lasso import (
    LassoBase,
    LassoFillTool,
    LassoFillRectTool,
    LassoFillEllipseTool,
    LassoEraserTool,
    RectSelectTool,
    LassoSelectTool,
    EllipseSelectTool,
    LassoMarqueeTool,
    MoveSelectionTool,
    MoveTool,
)

__all__ = [
    # Base
    'DrawingTool',
    'Stabilizer',
    'PressureSmoother',
    'get_shared_stabilizer',
    'StrokeHandler',
    'PencilStroke',
    'BrushStroke',
    'EraserStroke',
    '_active_layer',
    '_push_undo',
    '_draw_on_layer',
    # Drawing
    'PencilTool',
    'BrushTool',
    'EraserTool',
    'WatercolorTool',
    'BristleTool',
    # Shape
    'LineTool',
    'RectangleTool',
    'EllipseTool',
    'CurveTool',
    'PolylineTool',
    'PolyFillTool',
    # Special
    'TextTool',
    'BlurTool',
    'AirbrushTool',
    'CustomBrushTool',
    # Fill
    'FillTool',
    'EyedropperTool',
    # Lasso
    'LassoBase',
    'LassoFillTool',
    'LassoFillRectTool',
    'LassoFillEllipseTool',
    'LassoEraserTool',
    'RectSelectTool',
    'LassoSelectTool',
    'EllipseSelectTool',
    'LassoMarqueeTool',
    'MoveSelectionTool',
    'MoveTool',
]