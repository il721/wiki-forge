"""Generate assets/wiki-forge.ico from scratch using Qt (no external deps).

Renders a Wiki-Forge mark - a bold accent-blue "W" with a forge spark on a
rounded dark tile that matches the app's Modern Dark theme - at several sizes
and packs them into a multi-resolution .ico (PNG-compressed entries, valid on
Windows Vista+).

Run:  python scripts/make_icon.py
"""
from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

# Theme colors (from cockpit/theme.py)
BG_TOP = QColor(46, 46, 46)
BG_BOTTOM = QColor(26, 26, 26)
ACCENT = QColor("#2B79C2")
ACCENT_LIGHT = QColor("#4FA3E8")
SPARK = QColor("#FFC24B")
BORDER = QColor(64, 64, 64)

SIZES = [256, 128, 64, 48, 32, 16]


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    s = float(size)
    margin = s * 0.06
    radius = s * 0.22
    tile = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)

    # Rounded tile with vertical gradient.
    grad = QLinearGradient(QPointF(0, tile.top()), QPointF(0, tile.bottom()))
    grad.setColorAt(0.0, BG_TOP)
    grad.setColorAt(1.0, BG_BOTTOM)
    path = QPainterPath()
    path.addRoundedRect(tile, radius, radius)
    p.fillPath(path, QBrush(grad))

    # Subtle accent border.
    pen = QPen(BORDER)
    pen.setWidthF(max(1.0, s * 0.012))
    p.setPen(pen)
    p.drawPath(path)

    # Bold "W".
    font = QFont("Segoe UI", int(s * 0.5))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QPen(ACCENT_LIGHT))
    # Nudge up a touch to leave room for the spark.
    text_rect = QRectF(0, -s * 0.04, s, s)
    p.drawText(text_rect, Qt.AlignCenter, "W")

    # Forge spark (small diamond) at upper-right, only on larger sizes.
    if size >= 32:
        c = QPointF(s * 0.74, s * 0.30)
        r = s * 0.07
        spark = QPainterPath()
        spark.moveTo(c.x(), c.y() - r)
        spark.lineTo(c.x() + r * 0.55, c.y())
        spark.lineTo(c.x(), c.y() + r)
        spark.lineTo(c.x() - r * 0.55, c.y())
        spark.closeSubpath()
        p.fillPath(spark, QBrush(SPARK))

    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(ba)


def build_ico(images: list[QImage]) -> bytes:
    entries = [(img.width(), png_bytes(img)) for img in images]
    count = len(entries)

    header = struct.pack("<HHH", 0, 1, count)  # reserved, type=1 (icon), count
    dir_size = 16 * count
    offset = 6 + dir_size

    dir_blob = b""
    data_blob = b""
    for width, data in entries:
        w = 0 if width >= 256 else width  # 0 means 256 in ICO dir
        h = w
        dir_blob += struct.pack(
            "<BBBBHHII",
            w, h, 0, 0,  # width, height, colors, reserved
            1, 32,       # planes, bit depth
            len(data),   # bytes of PNG data
            offset,      # offset from file start
        )
        data_blob += data
        offset += len(data)

    return header + dir_blob + data_blob


def main() -> None:
    # QImage/QPainter need a GUI application instance.
    app = QGuiApplication.instance() or QGuiApplication([])

    images = [render(sz) for sz in SIZES]
    ico = build_ico(images)

    out = Path(__file__).resolve().parent.parent / "assets" / "wiki-forge.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(ico)
    print(f"Wrote {out} ({len(ico)} bytes, sizes: {', '.join(map(str, SIZES))})")

    del app


if __name__ == "__main__":
    main()
