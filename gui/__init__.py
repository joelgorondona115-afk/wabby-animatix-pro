# gui/__init__.py
"""GUI module for animation application."""

from .main import AnimatixPro
from .dialogs import NewProjectDialog, BrushLibraryDialog
from .reference import ReferenceWindow

__all__ = [
    'AnimatixPro',
    'NewProjectDialog',
    'BrushLibraryDialog',
    'ReferenceWindow',
]
