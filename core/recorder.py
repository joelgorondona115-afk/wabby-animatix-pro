# core/recorder.py
"""Time-lapse export: renders project frames and compresses into a fixed duration video."""

import os
import threading
import numpy as np
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QFileDialog, QMessageBox

DURATIONS = {
    10: "10 segundos",
    30: "30 segundos",
    60: "1 minuto",
}

EXPORT_FORMATS = {
    ".mp4": "Video MP4 (*.mp4)",
    ".gif": "GIF animado (*.gif)",
    ".png": "Secuencia PNG (*.png)",
    ".jpg": "Secuencia JPG (*.jpg)",
    ".psd": "Archivo PSD (*.psd)",
}


class TimelapseExporter(QObject):
    """Exports project frames as a compressed time-lapse video."""

    export_started = Signal(int)  # total_frames
    export_progress = Signal(int, int)  # current, total
    export_complete = Signal(str)  # output_path
    export_error = Signal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.duration = 10

    def set_duration(self, seconds: int):
        if seconds in DURATIONS:
            self.duration = seconds

    def export(self):
        """Start export in background thread."""
        if not self.project or not self.project.frames:
            self.export_error.emit("No hay frames en el proyecto.")
            return

        self.export_started.emit(len(self.project.frames))
        thread = threading.Thread(target=self._do_export, daemon=True)
        thread.start()

    def _do_export(self):
        try:
            frames = []
            num_frames = len(self.project.frames)

            for i, frame in enumerate(self.project.frames):
                w, h = frame.size

                # Composite frame layers into clean image
                img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
                img.fill(0)

                p = QPainter(img)
                for layer in reversed(frame.layers):
                    if layer.visible:
                        p.setOpacity(layer.opacity / 255.0)
                        if hasattr(layer, 'is_vector') and layer.is_vector:
                            layer.draw_all(p)
                        else:
                            p.drawImage(0, 0, layer.image)
                p.end()

                rgb = img.convertToFormat(QImage.Format_RGB888)
                arr = np.array(np.frombuffer(rgb.bits(), dtype=np.uint8)).reshape((h, w, 3))
                frames.append(arr)

                self.export_progress.emit(i + 1, num_frames)

            if not frames:
                self.export_error.emit("No se pudieron renderizar los frames.")
                return

            # Ask for save path
            formats = ";;".join(EXPORT_FORMATS.values())
            path, _ = QFileDialog.getSaveFileName(
                None, "Exportar time-lapse", "", formats
            )
            if not path:
                return

            ext = os.path.splitext(path)[1].lower()

            if ext == ".mp4":
                self._save_mp4(path, frames)
            elif ext == ".gif":
                self._save_gif(path, frames)
            elif ext == ".png":
                self._save_sequence(path, frames, "png")
            elif ext == ".jpg":
                self._save_sequence(path, frames, "jpg")
            elif ext == ".psd":
                self._save_psd(path, frames)
            else:
                self.export_error.emit(f"Formato no soportado: {ext}")
                return

        except ImportError as e:
            self.export_error.emit(f"Falta dependencia: {str(e)}")
        except Exception as e:
            self.export_error.emit(f"Error: {str(e)}")

    def _save_mp4(self, path, frames):
        import imageio
        fps = max(1, round(len(frames) / self.duration))
        imageio.mimsave(
            path, frames, fps=fps, codec='libx264',
            quality=8, ffmpeg_params=['-preset', 'fast']
        )
        self.export_complete.emit(path)

    def _save_gif(self, path, frames):
        import imageio
        step = max(1, len(frames) // (12 * self.duration))
        gif_frames = [frames[i] for i in range(0, len(frames), step)]
        imageio.mimsave(path, gif_frames, fps=12, loop=0, quantizer='nq')
        self.export_complete.emit(path)

    def _save_sequence(self, base_path, frames, fmt):
        from PIL import Image

        base = Path(base_path).parent
        name = Path(base_path).stem
        file_ext = "png" if fmt == "png" else "jpg"
        dir_path = base / name
        dir_path.mkdir(parents=True, exist_ok=True)

        total = len(frames)
        for i, frame in enumerate(frames):
            img = Image.fromarray(frame)
            pad = max(4, len(str(total)))
            filename = dir_path / f"{name}_{i+1:0{pad}d}.{file_ext}"
            if fmt == "jpg":
                img = img.convert("RGB")
                img.save(str(filename), "JPEG", quality=95)
            else:
                img.save(str(filename), "PNG")
            self.export_progress.emit(i + 1, total)

        self.export_complete.emit(str(dir_path))

    def _save_psd(self, path, frames):
        try:
            from psd_tools import PSDImage
            from PIL import Image
        except ImportError:
            self.export_error.emit("Falta psd-tools.\nEjecutá: pip install psd-tools")
            return

        base_img = Image.fromarray(frames[0])
        psd = PSDImage.frompil(base_img)

        total = len(frames)
        for i, frame in enumerate(frames[1:], 1):
            img = Image.fromarray(frame)
            layer = psd.create_pixel_layer(img)
            layer.name = f"Frame {i+1}"
            self.export_progress.emit(i + 1, total)

        psd.save(path)
        self.export_complete.emit(path)
