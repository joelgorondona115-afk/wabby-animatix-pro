# gui/timeline/widget.py
"""TimelineWidget - Main timeline widget (Ibis Dark style)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QScrollArea, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage
from .list import TimelineListWidget
from core.models import AnimationFrame


class TimelineWidget(QWidget):
    frame_changed = Signal(int)
    playback_changed = Signal(bool)
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self._is_playing = False
        self._playback_mode = "Loop"
        self._playback_direction = 1
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_playback_tick)
        self._pending_reorder = None
        self.setFixedHeight(55)
        
        self.setStyleSheet("""
            QWidget { background-color: #000000; }
            QPushButton {
                background-color: #1a1a1a;
                color: #888888;
                border: 1px solid #252525;
                border-radius: 4px;
                font-size: 14px;
                padding: 4px 8px;
            }
            QPushButton:hover { background-color: #252525; color: #aaaaaa; }
            QPushButton:pressed { background-color: #00aa00; color: #fff; }
            QPushButton:checked { background-color: #00aa00; color: #fff; border: 1px solid #00ff00; }
            QSlider::groove:horizontal {
                background: #1a1a1a;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00ff00;
                width: 8px;
                margin: -2px 0;
                border-radius: 4px;
            }
            QLabel { color: #555555; font-size: 10px; }
            QComboBox {
                background-color: #1a1a1a;
                color: #888888;
                border: 1px solid #252525;
                border-radius: 4px;
                padding: 2px 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { color: #555555; }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #000000;")
        toolbar.setFixedHeight(28)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(4, 2, 4, 2)
        tl.setSpacing(4)
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedWidth(32)
        
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(24)
        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(24)
        
        self.lbl_frame = QLabel("1")
        self.lbl_frame.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold;")
        self.lbl_frame.setFixedWidth(20)
        
        self.cmb_playback = QComboBox()
        self.cmb_playback.addItems(["Simple", "Loop", "Ping-Pong"])
        self.cmb_playback.setFixedWidth(70)
        
        self.btn_onion = QPushButton("👁")
        self.btn_onion.setCheckable(True)
        self.btn_onion.setFixedWidth(28)
        self.btn_onion.setToolTip("Papel Cebolla")
        
        self.btn_clone = QPushButton("⧉")
        self.btn_clone.setFixedWidth(24)
        self.btn_clone.setToolTip("Clonar frame")
        
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(1, 60)
        self.fps_slider.setValue(24)
        self.fps_slider.setFixedWidth(60)
        
        self.lbl_fps = QLabel("24")
        self.lbl_fps.setStyleSheet("color: #555555; font-size: 10px;")
        
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedWidth(24)
        self.btn_del = QPushButton("−")
        self.btn_del.setFixedWidth(24)
        
        tl.addWidget(self.btn_play)
        tl.addWidget(self.btn_prev)
        tl.addWidget(self.btn_next)
        tl.addWidget(self.lbl_frame)
        tl.addWidget(self.cmb_playback)
        tl.addStretch()
        tl.addWidget(self.btn_onion)
        tl.addWidget(self.btn_clone)
        tl.addWidget(self.lbl_fps)
        tl.addWidget(self.fps_slider)
        tl.addWidget(self.btn_add)
        tl.addWidget(self.btn_del)
        
        self.timeline_area = QScrollArea()
        self.timeline_area.setWidgetResizable(True)
        self.timeline_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.timeline_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_area.setStyleSheet("""
            QScrollArea {
                background-color: #000000;
                border: none;
            }
            QScrollBar:horizontal {
                background: #0a0a0a;
                height: 8px;
            }
            QScrollBar::handle:horizontal {
                background: #333333;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover { background: #00ff00; }
        """)
        
        self.list = TimelineListWidget()
        self.timeline_area.setWidget(self.list)
        
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.timeline_area, 1)
        
        self.btn_play.toggled.connect(self._on_play_toggled)
        self.btn_prev.clicked.connect(self.prev_frame)
        self.btn_next.clicked.connect(self.next_frame)
        self.btn_add.clicked.connect(self.add_frame)
        self.btn_del.clicked.connect(self.del_frame)
        self.btn_clone.clicked.connect(self.clone_frame)
        self.btn_onion.toggled.connect(self._on_onion_toggled)
        self.fps_slider.valueChanged.connect(self._on_fps_changed)
        self.cmb_playback.currentTextChanged.connect(self._on_playback_mode_changed)
        self.list.currentRowChanged.connect(self._on_frame_selected)
        self.list.frame_moved.connect(self._on_frame_moved)

    def set_project(self, proj):
        self.proj = proj

    def update_ui(self):
        if not self.canvas.project:
            return
        
        proj = self.canvas.project
        frames = proj.frames
        current_idx = proj.current_frame_idx
        
        if self._pending_reorder:
            proj.move_frame(self._pending_reorder[0], self._pending_reorder[1])
            self._pending_reorder = None
        
        self.fps_slider.blockSignals(True)
        self.fps_slider.setValue(proj.fps)
        self.fps_slider.blockSignals(False)
        self.lbl_fps.setText(f"{proj.fps}")
        
        self.list.set_frames(frames, current_idx)
        
        self.btn_del.setEnabled(len(frames) > 1)
        self.btn_prev.setEnabled(current_idx > 0)
        self.btn_next.setEnabled(current_idx < len(frames) - 1)

    def prev_frame(self):
        if self.canvas.project:
            old_idx = self.canvas.project.current_frame_idx
            self.canvas.project.prev_frame()
            new_idx = self.canvas.project.current_frame_idx
            self.list.update_thumbnail(old_idx)
            self.list.update_thumbnail(new_idx)
            self.canvas.update()
            self.frame_changed.emit(new_idx)

    def next_frame(self):
        if self.canvas.project:
            old_idx = self.canvas.project.current_frame_idx
            self.canvas.project.next_frame()
            new_idx = self.canvas.project.current_frame_idx
            self.list.update_thumbnail(old_idx)
            self.list.update_thumbnail(new_idx)
            self.canvas.update()
            self.frame_changed.emit(new_idx)

    def add_frame(self):
        if self.canvas and self.canvas.project:
            self.canvas.project.add_frame()
            self.update_ui()

    def clone_frame(self):
        if self.canvas and self.canvas.project:
            proj = self.canvas.project
            idx = proj.current_frame_idx
            new_frame = AnimationFrame(proj.size)
            new_frame.copy_from(proj.frames[idx])
            proj.frames.insert(idx + 1, new_frame)
            self.update_ui()

    def del_frame(self):
        if self.canvas.project and len(self.canvas.project.frames) > 1:
            idx = self.canvas.project.current_frame_idx
            self.canvas.project.remove_frame(idx)
            self.update_ui()

    def update_active_thumbnail(self):
        """Update thumbnail for current frame."""
        if self.canvas.project:
            idx = self.canvas.project.current_frame_idx
            self.list.update_thumbnail(idx)

    def _on_play_toggled(self, checked):
        self._is_playing = checked
        self.playback_changed.emit(checked)
        if checked:
            if self._play_timer.isActive():
                self._play_timer.stop()
            fps = self.canvas.project.fps if self.canvas.project else 24
            intervalo = max(10, 1000 // fps)
            self._play_timer.start(intervalo)
        else:
            self._play_timer.stop()

    def _on_playback_tick(self):
        if not self.canvas.project:
            return
        
        proj = self.canvas.project
        total = len(proj.frames)
        
        old_idx = proj.current_frame_idx
        
        if self._playback_mode == "Simple":
            if proj.current_frame_idx < total - 1:
                proj.current_frame_idx += 1
            else:
                self._play_timer.stop()
                self.btn_play.setChecked(False)
                self._is_playing = False
        elif self._playback_mode == "Loop":
            proj.current_frame_idx = (proj.current_frame_idx + 1) % total
        elif self._playback_mode == "Ping-Pong":
            proj.current_frame_idx += self._playback_direction
            if proj.current_frame_idx >= total - 1:
                self._playback_direction = -1
            elif proj.current_frame_idx <= 0:
                self._playback_direction = 1
        
        new_idx = proj.current_frame_idx
        self.list.update_thumbnail(old_idx)
        if old_idx != new_idx:
            self.list.update_thumbnail(new_idx)
        
        self.canvas.update()
        self.frame_changed.emit(proj.current_frame_idx)

    def _on_fps_changed(self, val):
        if self.canvas.project:
            self.canvas.project.fps = val
            self.lbl_fps.setText(f"{val}")

    def _on_frame_selected(self, row):
        if row >= 0 and self.canvas.project:
            self.canvas.project.current_frame_idx = row
            self.canvas.update()

    def _on_frame_moved(self, from_idx, to_idx):
        if self.canvas.project:
            self._pending_reorder = (from_idx, to_idx)
            self.update_ui()

    def _on_playback_mode_changed(self, mode):
        self._playback_mode = mode
        self._playback_direction = 1

    def _on_onion_toggled(self, checked):
        if self.canvas.project:
            self.canvas.project.onion_skin = checked
        self.canvas.onion_skin = checked
        self.canvas.update()

