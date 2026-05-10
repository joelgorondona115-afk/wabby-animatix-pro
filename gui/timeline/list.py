# gui/timeline/list.py
"""TimelineListWidget - Horizontal timeline with thumbnails (Ibis Dark style)."""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QDrag


CELL_SIZE = 80
CELL_HEIGHT = 60
THUMB_SIZE = 72


class TimelineFrameCell(QListWidgetItem):
    """Custom cell for each frame with thumbnail."""
    
    def __init__(self, frame, index, parent=None):
        super().__init__(parent)
        self.frame = frame
        self.frame_index = index
        from PySide6.QtCore import QSize
        self.setSizeHint(QSize(CELL_SIZE, CELL_HEIGHT))
        self._update_thumbnail()
    
    def _update_thumbnail(self):
        """Render thumbnail from frame image."""
        if self.frame:
            img = self.frame.composite()
            if img and not img.isNull():
                thumb = img.scaled(
                    THUMB_SIZE, THUMB_SIZE - 8,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.setData(Qt.DecorationRole, QPixmap.fromImage(thumb))
            else:
                self.setData(Qt.DecorationRole, QPixmap())


class TimelineListWidget(QListWidget):
    frame_moved = Signal(int, int)  # from_idx, to_idx
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_frame_idx = 0
        
        self.setFlow(QListWidget.LeftToRight)
        self.setViewMode(QListWidget.IconMode)
        self.setSpacing(2)
        self.setMinimumHeight(CELL_HEIGHT + 10)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)
        
        self.setStyleSheet("""
            QListWidget {
                background-color: #000000;
                border: none;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #121212;
                border: 1px solid #1a1a1a;
                border-radius: 2px;
            }
            QListWidget::item:selected {
                background-color: #121212;
                border: 2px solid #00ff00;
            }
            QListWidget::item:hover {
                border: 1px solid #333333;
            }
        """)
        
        self.currentRowChanged.connect(self._on_selection_changed)
    
    def _on_rows_moved(self, parent, start, end, destination, row):
        """Handle internal reordering."""
        if start != row:
            self.frame_moved.emit(start, row)
    
    def set_frames(self, frames, current_idx=0):
        """Set frames and render thumbnails."""
        self.clear()
        for i, frame in enumerate(frames):
            cell = TimelineFrameCell(frame, i)
            cell.setText(str(i + 1))
            self.addItem(cell)
        
        if 0 <= current_idx < len(frames):
            self.setCurrentRow(current_idx)
            self.current_frame_idx = current_idx
    
    def update_thumbnail(self, frame_idx):
        """Update single frame thumbnail."""
        if 0 <= frame_idx < self.count():
            item = self.item(frame_idx)
            if isinstance(item, TimelineFrameCell):
                item._update_thumbnail()
    
    def update_all_thumbnails(self, frames):
        """Refresh all thumbnails."""
        for i in range(min(self.count(), len(frames))):
            self.item(i).frame = frames[i]
            if isinstance(self.item(i), TimelineFrameCell):
                self.item(i)._update_thumbnail()
    
    def _on_selection_changed(self, row):
        """Handle frame selection."""
        if row >= 0:
            self.current_frame_idx = row
            self.viewport().update()
    
    def set_current_frame(self, idx):
        """Set current frame visually."""
        if 0 <= idx < self.count():
            self.setCurrentRow(idx)
            self.current_frame_idx = idx
            self.viewport().update()
    
    def paintEvent(self, event):
        """Draw playhead line."""
        super().paintEvent(event)
        if 0 <= self.current_frame_idx < self.count():
            item = self.item(self.current_frame_idx)
            if item:
                painter = QPainter(self.viewport())
                pen = painter.pen()
                pen.setColor(QColor("#00ff00"))
                pen.setWidth(2)
                painter.setPen(pen)
                rect = self.visualRect(self.model().index(self.current_frame_idx, 0))
                painter.drawRect(rect.adjusted(0, 0, -1, -1))