"""Render ``docs/assets/logo.png`` from the same geometry as ``logo.svg``.

The README points at the PNG because PyPI strips SVG from project descriptions, so
an SVG logo silently vanishes there while rendering fine on GitHub.

The raster is drawn here rather than exported with a system tool because macOS's
``qlmanage`` crops its output to the artwork's bounding box, which discarded the
mark's margins and left the bottom row flush against the edge. Drawing from the
geometry keeps the two files in agreement and needs no third-party dependency.

Run with ``make logo`` after editing ``logo.svg``; keep the constants below in step
with it. ``tests/core/test_theme.py`` fails if the two drift apart.
"""

import struct
import zlib
from pathlib import Path

SIZE = 320
SCALE = SIZE / 64
SS = 3  # supersampling factor for antialiasing

PLATE_RADIUS = 14.0
"""Corner radius of the rounded plate, in user units."""

PLATE_ALPHA = 0.07
"""Opacity of the plate wash. A tint rather than an outline: at favicon size a
stroke competes with the dots."""

ROWS = [9.6, 20.8, 32.0, 43.2, 54.4]
COLS = [7.0, 18.85, 30.7, 42.55, 54.4]
NAVY = (0x12, 0x29, 0x4B)
ORANGE = (0xB8, 0x4C, 0x14)
ANSWERED = {0: 3, 1: 1, 3: 4, 4: 2}
CURRENT = (2, 2)


def in_plate(x: float, y: float) -> bool:
    """Whether a point falls inside the rounded plate.

    Args:
        x: Horizontal position in user units.
        y: Vertical position in user units.

    Returns:
        True if the point is on the plate.
    """
    r = PLATE_RADIUS
    cx = min(max(x, r), 64 - r)
    cy = min(max(y, r), 64 - r)
    if x == cx or y == cy:
        return 0 <= x <= 64 and 0 <= y <= 64
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def circles():
    """Yield (cx, cy, r, rgb, alpha) in user units."""
    for r_i, cy in enumerate(ROWS):
        for c_i, cx in enumerate(COLS):
            yield cx, cy, 3.0, NAVY, 0.22
    for r_i, c_i in sorted(ANSWERED.items()):
        yield COLS[c_i], ROWS[r_i], 5.6, NAVY, 1.0
    yield COLS[CURRENT[1]], ROWS[CURRENT[0]], 6.8, ORANGE, 1.0


def render() -> bytes:
    """Draw the mark as straight RGBA rows."""
    n = SIZE * SS
    cov = [[(0.0, (0, 0, 0))] * n for _ in range(n)]
    unit = 64 / n
    for y in range(n):
        row = cov[y]
        uy = (y + 0.5) * unit
        for x in range(n):
            if in_plate((x + 0.5) * unit, uy):
                row[x] = (PLATE_ALPHA, NAVY)
    shapes = [
        (cx * SCALE * SS, cy * SCALE * SS, r * SCALE * SS, rgb, a)
        for cx, cy, r, rgb, a in circles()
    ]
    for y in range(n):
        row = cov[y]
        for cx, cy, r, rgb, a in shapes:
            if abs(cy - y) > r:
                continue
            dy = y - cy
            half = (r * r - dy * dy) ** 0.5
            for x in range(max(0, int(cx - half)), min(n, int(cx + half) + 1)):
                row[x] = (a, rgb)  # later shapes paint over earlier ones
    out = bytearray()
    for y in range(SIZE):
        line = bytearray()
        for x in range(SIZE):
            ar = ag = ab = aa = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    a, rgb = cov[y * SS + sy][x * SS + sx]
                    ar += rgb[0] * a
                    ag += rgb[1] * a
                    ab += rgb[2] * a
                    aa += a
            k = SS * SS
            if aa > 0:
                line += bytes((round(ar / aa), round(ag / aa), round(ab / aa), round(255 * aa / k)))
            else:
                line += b"\x00\x00\x00\x00"
        out += b"\x00" + line
    return bytes(out)


def write_png(path: Path, raw: bytes) -> None:
    """Wrap raw scanlines in a PNG container."""

    def chunk(tag, data):
        body = tag + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


write_png(Path("docs/assets/logo.png"), render())
print("rendered docs/assets/logo.png")
