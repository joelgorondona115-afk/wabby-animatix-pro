# core/tools/parsers.py
"""Parser for Photoshop .abr brush files."""

import struct
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt


def parse_abr(path: str) -> list:
    """
    Parse a Photoshop .abr brush file (versions 1 and 2).
    Returns list of (name: str, tip: QImage).
    """
    results = []
    try:
        with open(path, 'rb') as f:
            data = f.read()
        version = struct.unpack_from('>H', data, 0)[0]
        if version not in (1, 2):
            return results
        count  = struct.unpack_from('>H', data, 2)[0]
        offset = 4
        for i in range(count):
            if offset + 6 > len(data):
                break
            btype  = struct.unpack_from('>H', data, offset)[0]
            blen   = struct.unpack_from('>I', data, offset + 2)[0]
            offset += 6
            end = offset + blen
            if btype == 2:
                o = offset
                o += 4  # misc flags
                o += 2  # spacing
                brush_name = f"Pincel {i + 1}"
                if version == 2:
                    if o + 2 > len(data):
                        offset = end
                        continue
                    nlen = struct.unpack_from('>H', data, o)[0]
                    o += 2
                    try:
                        brush_name = data[o:o + nlen * 2].decode('utf-16-be').rstrip('\x00') or brush_name
                    except Exception:
                        pass
                    o += nlen * 2
                o += 1  # antialiasing
                if o + 8 > len(data):
                    offset = end
                    continue
                top    = struct.unpack_from('>h', data, o)[0]; o += 2
                left   = struct.unpack_from('>h', data, o)[0]; o += 2
                bottom = struct.unpack_from('>h', data, o)[0]; o += 2
                right  = struct.unpack_from('>h', data, o)[0]; o += 2
                w = right - left
                h = bottom - top
                if w > 0 and h > 0 and o + w * h <= len(data):
                    bitmap = data[o:o + w * h]
                    img = QImage(w, h, QImage.Format_ARGB32)
                    img.fill(Qt.transparent)
                    for row in range(h):
                        for col in range(w):
                            alpha = 255 - bitmap[row * w + col]
                            img.setPixel(col, row, QColor(0, 0, 0, alpha).rgba())
                    results.append((brush_name, img))
            offset = end
    except Exception:
        pass
    return results
