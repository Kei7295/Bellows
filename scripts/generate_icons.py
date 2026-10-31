"""Generate the Bellows app icon set (PNG + Windows ICO) with Pillow.

Design: brass bellows blowing embers into a chat bubble, on a dark rounded tile.
Run from the repo root: python3 scripts/generate_icons.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "desktop" / "src-tauri" / "icons"
WEB_PUBLIC = ROOT / "apps" / "web" / "public"

S = 2048  # supersampled canvas


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def cubic(p0, p1, p2, p3, steps=48):
    points = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt ** 3 * p0[0] + 3 * mt ** 2 * t * p1[0] + 3 * mt * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = mt ** 3 * p0[1] + 3 * mt ** 2 * t * p1[1] + 3 * mt * t ** 2 * p2[1] + t ** 3 * p3[1]
        points.append((x, y))
    return points


def build_icon() -> Image.Image:
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Rounded tile with a vertical dark gradient.
    tile = Image.new("RGBA", (S, S), rgba("#0B0F14"))
    gradient = Image.new("RGBA", (S, S))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(S):
        t = y / (S - 1)
        color = (
            int(11 + 13 * t),
            int(15 + 12 * t),
            int(20 + 14 * t),
            255,
        )
        gdraw.line([(0, y), (S, y)], fill=color)
    tile = gradient
    draw.bitmap((0, 0), tile, fill=None)

    # Ember glow behind the icon.
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius, alpha in ((760, 26), (600, 34), (430, 44), (280, 56)):
        gd.ellipse((1420 - radius, 760 - radius, 1420 + radius, 760 + radius),
                   fill=rgba("#FF6A00", alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    canvas.alpha_composite(glow)

    # Bellows body: hinged leather bulb tapering into the brass nozzle.
    top = cubic((520, 1195), (740, 950), (1080, 975), (1300, 1060))
    bottom = cubic((1300, 1320), (1080, 1430), (740, 1420), (520, 1295))
    hinge = cubic((520, 1295), (455, 1278), (455, 1212), (520, 1195))
    bulb = top + bottom + hinge
    draw.polygon(bulb, fill=rgba("#262C35"))
    draw.line(bulb, fill=rgba("#3B4350"), width=26, joint="curve")

    # Leather highlight along the top edge.
    highlight = []
    for i in range(len(top)):
        highlight.append((top[i][0], top[i][1] + 34))
    draw.line(highlight, fill=rgba("#4A5464", 190), width=14)

    # Brass bands.
    for x_top, x_bottom, color in ((600, 650, "#C08A43"), (920, 975, "#D9A353")):
        y1 = 1000 + (x_top - 520) * 0.10
        y2 = 1285 + (x_bottom - 520) * 0.10
        draw.line([(x_top, y1), (x_bottom, y2)], fill=rgba(color), width=42)
        draw.line([(x_top, y1), (x_bottom, y2)], fill=rgba("#F3C878", 120), width=14)

    # Brass nozzle.
    draw.polygon([(1260, 1070), (1450, 975), (1505, 1018), (1315, 1112)], fill=rgba("#C9924A"))
    draw.polygon([(1275, 1074), (1440, 990), (1472, 1012), (1305, 1095)], fill=rgba("#E7B467"))
    draw.ellipse((1435, 962, 1515, 1035), fill=rgba("#8A5A25"))
    draw.ellipse((1452, 978, 1500, 1020), fill=rgba("#FFB066"))

    # Chat bubble.
    draw.rounded_rectangle((1460, 400, 1900, 790), radius=105, fill=rgba("#FF8A3D", 26))
    draw.rounded_rectangle((1460, 400, 1900, 790), radius=105, outline=rgba("#FF9A52"), width=46)
    draw.polygon([(1520, 760), (1452, 905), (1625, 800)], fill=rgba("#FF9A52"))

    # Ember core inside the bubble.
    draw.ellipse((1595, 505, 1755, 665), fill=rgba("#FF6A18"))
    draw.ellipse((1623, 533, 1727, 637), fill=rgba("#FFC46B"))
    draw.ellipse((1649, 559, 1701, 611), fill=rgba("#FFF0C8"))

    # Sparks from nozzle to bubble.
    sparks = [(1440, 965, 19), (1505, 920, 14), (1438, 872, 10), (1385, 1010, 8), (1470, 800, 7)]
    for x, y, r in sparks:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=rgba("#FFB066"))

    # Clip to a rounded tile and add a subtle border.
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=430, fill=255)
    canvas.putalpha(mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((10, 10, S - 11, S - 11), radius=420, outline=rgba("#FFFFFF", 26), width=10)

    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)

    icon = build_icon().resize((1024, 1024), Image.LANCZOS)
    icon.save(OUT / "icon.png")
    icon.save(WEB_PUBLIC / "icon.png")

    for size in (32, 128, 256, 512):
        icon.resize((size, size), Image.LANCZOS).save(OUT / f"{size}x{size}.png")

    icon.resize((256, 256), Image.LANCZOS).save(
        OUT / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"icons written to {OUT}")


if __name__ == "__main__":
    main()
