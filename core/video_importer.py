# core/video_importer.py
"""Simple video importer for rotoscopia."""

from PySide6.QtGui import QImage
from PySide6.QtCore import Qt


class VideoImporter:
    """Importa video frame a frame usando OpenCV."""

    @staticmethod
    def import_video(path: str):
        try:
            import cv2
        except ImportError:
            raise ImportError(
                "Se necesita opencv-python para importar video.\n"
                "Instalalo con:  pip install opencv-python"
            )

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise ValueError(f"No se pudo abrir el video: {path}")

        fps  = int(cap.get(cv2.CAP_PROP_FPS)) or 24
        w    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        size = (w, h)

        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(
                rgb.data, rgb.shape[1], rgb.shape[0],
                rgb.strides[0], QImage.Format_RGB888
            ).copy()
            frames.append(img)

        cap.release()
        if not frames:
            raise ValueError("El video no contiene frames.")
        return frames, fps, size


class GifImporter:
    """Importa GIF animado usando Pillow."""

    @staticmethod
    def import_gif(path: str):
        try:
            from PIL import Image as PILImage
        except ImportError:
            raise ImportError(
                "Se necesita Pillow para importar GIFs.\n"
                "Instalalo con:  pip install Pillow"
            )

        gif = PILImage.open(path)
        frames = []
        size = (gif.width, gif.height)

        try:
            while True:
                frame_rgba = gif.convert("RGBA")
                data  = frame_rgba.tobytes("raw", "RGBA")
                qimg  = QImage(data, frame_rgba.width, frame_rgba.height,
                               QImage.Format_RGBA8888).copy()
                frames.append(qimg)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass

        if not frames:
            raise ValueError("El GIF no contiene frames.")
        return frames, size