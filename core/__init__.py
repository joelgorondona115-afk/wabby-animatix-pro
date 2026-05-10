# core/__init__.py
"""Core module for animation application."""

# Importaciones absolutas simples
from core.canvas import CanvasWidget
from core.models import AnimationProject, AnimationFrame

__all__ = [
    'CanvasWidget',
    'AnimationProject',
    'AnimationFrame',
]
