"""Draw the six timeline card illustrations (warm amber line-art on dark).

    python tools/build_year_art.py

One small abstract picture per milestone - network, ratings matrix, detection
boxes, dashboard, spreadsheet, rising path. Output: public/years/<id>.jpg
(528x396, shown at 4:3).
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "years")
W, H = 528, 396
AMBER, RED, CREAM, DIM = (255, 176, 84), (226, 70, 48), (244, 226, 206), (120, 76, 48)


def canvas():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = yy / H
    base = np.stack([20 + 26 * t, 10 + 12 * t, 7 + 6 * t], -1)
    r = np.hypot((xx - W * 0.62) / W, (yy - H * 0.4) / H)
    base += np.clip(0.55 - r, 0, 1)[..., None] * np.array([70, 26, 12], np.float32)
    return base


def finish(base, glow_layer, line_layer, name):
    g = np.array(glow_layer, np.float32)
    l = np.array(line_layer, np.float32)
    bloom = cv2.GaussianBlur(g, (0, 0), 7) * 0.9 + cv2.GaussianBlur(g, (0, 0), 2.5) * 0.5
    out = base + bloom + l
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.55 * np.clip(np.hypot((xx - W / 2) / (W * 0.75), (yy - H / 2) / (H * 0.75)), 0, 1) ** 2
    out *= vig[..., None]
    out += (np.random.default_rng(len(name)).random((H, W, 1)) - 0.5) * 7
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(
        os.path.join(OUT, name + ".jpg"), quality=88)


def layers():
    a, b = Image.new("RGB", (W, H)), Image.new("RGB", (W, H))
    return a, b, ImageDraw.Draw(a), ImageDraw.Draw(b)


def btech():                       # a small neural network
    g, l, dg, dl = layers()
    cols = [(110, [120, 270]), (250, [70, 170, 280]), (390, [100, 200, 300]), (480, [200])]
    cols = [(110, [90, 190, 290]), (240, [60, 140, 230, 320]), (370, [90, 190, 290]), (470, [190])]
    for (x0, ys0), (x1, ys1) in zip(cols, cols[1:]):
        for y0 in ys0:
            for y1 in ys1:
                dl.line([(x0, y0), (x1, y1)], fill=(70, 44, 28), width=1)
    rng = np.random.default_rng(2)
    for x, ys in cols:
        for y in ys:
            hot = rng.random() > 0.55
            c = AMBER if hot else DIM
            dg.ellipse([x - 9, y - 9, x + 9, y + 9], fill=c if hot else (0, 0, 0))
            dl.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(30, 18, 12), outline=c, width=2)
    for (x0, y0), (x1, y1) in [((110, 190), (240, 140)), ((240, 140), (370, 190)), ((370, 190), (470, 190))]:
        dg.line([(x0, y0), (x1, y1)], fill=AMBER, width=3)
        dl.line([(x0, y0), (x1, y1)], fill=AMBER, width=2)
    finish(canvas(), g, l, "btech")


def edvedha():                     # users x items ratings matrix
    g, l, dg, dl = layers()
    rng = np.random.default_rng(5)
    cw, ch, x0, y0 = 38, 30, 90, 62
    for r in range(9):
        for c in range(9):
            v = rng.random()
            x, y = x0 + c * (cw + 3), y0 + r * (ch + 3)
            if v > 0.62:
                k = int(120 + 135 * v)
                col = (k, int(k * .55), int(k * .2))
                dl.rectangle([x, y, x + cw, y + ch], fill=col)
                if v > 0.88:
                    dg.rectangle([x, y, x + cw, y + ch], fill=AMBER)
            else:
                dl.rectangle([x, y, x + cw, y + ch], outline=(66, 42, 28))
    dl.rectangle([x0 - 6, y0 + 3 * (ch + 3) - 4, x0 + 9 * (cw + 3) + 2, y0 + 4 * (ch + 3) + ch + 3],
                 outline=CREAM, width=2)
    finish(canvas(), g, l, "edvedha")


def techshiksha():                 # detection box + text tokens
    g, l, dg, dl = layers()
    for k in range(7):             # perspective floor grid
        y = 250 + k * 22
        dl.line([(30, y), (500, y)], fill=(58, 36, 24), width=1)
    for k in range(11):
        dl.line([(264 + (k - 5) * 20, 250), (264 + (k - 5) * 90, 396)], fill=(58, 36, 24), width=1)
    cx, cy = 190, 170
    dl.ellipse([cx - 52, cy - 62, cx + 52, cy + 62], outline=CREAM, width=2)
    dl.arc([cx - 26, cy - 8, cx + 26, cy + 30], 20, 160, fill=CREAM, width=2)
    for dx in (-18, 18):
        dl.ellipse([cx + dx - 5, cy - 22, cx + dx + 5, cy - 14], outline=CREAM, width=2)
    bx0, by0, bx1, by1 = cx - 78, cy - 90, cx + 78, cy + 90
    for (x, y, sx, sy) in [(bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)]:
        for d in (dg, dl):
            d.line([(x, y), (x + 26 * sx, y)], fill=AMBER, width=3)
            d.line([(x, y), (x, y + 26 * sy)], fill=AMBER, width=3)
    for i, w in enumerate([120, 90, 140, 70, 110, 96]):   # token lines
        y = 90 + i * 34
        dl.rounded_rectangle([330, y, 330 + w, y + 14], 5, fill=(150, 96, 56) if i % 2 else (90, 58, 38))
    dg.rounded_rectangle([330, 90 + 2 * 34, 470, 90 + 2 * 34 + 14], 5, fill=AMBER)
    finish(canvas(), g, l, "techshiksha")


def elevate():                     # dashboard
    g, l, dg, dl = layers()
    dl.rounded_rectangle([40, 40, 488, 356], 12, outline=(80, 52, 34), width=2)
    vals = [0.35, 0.55, 0.42, 0.7, 0.62, 0.88, 0.78]
    for i, v in enumerate(vals):
        x = 70 + i * 36
        top = 330 - v * 190
        dl.rectangle([x, top, x + 22, 330], fill=(170, 104, 52) if i != 5 else AMBER)
    dg.rectangle([70 + 5 * 36, 330 - 0.88 * 190, 70 + 5 * 36 + 22, 330], fill=AMBER)
    pts = [(70 + i * 36 + 11, 330 - v * 190 - 36) for i, v in enumerate(vals)]
    dl.line(pts, fill=CREAM, width=2)
    dg.line(pts, fill=RED, width=3)
    for p in pts:
        dl.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=CREAM)
    cx, cy, R = 410, 150, 52                                   # donut
    dl.pieslice([cx - R, cy - R, cx + R, cy + R], -90, 140, fill=(200, 80, 44))
    dl.pieslice([cx - R, cy - R, cx + R, cy + R], 140, 270, fill=(90, 58, 38))
    dg.pieslice([cx - R, cy - R, cx + R, cy + R], -90, 140, fill=RED)
    dl.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(24, 14, 10))
    for i in range(3):
        dl.rounded_rectangle([360, 236 + i * 26, 360 + 100 - i * 22, 248 + i * 26], 4, fill=(110, 72, 44))
    finish(canvas(), g, l, "elevate")


def nizcare():                     # spreadsheet + tag glyph
    g, l, dg, dl = layers()
    x0, y0, cw, ch = 60, 60, 92, 30
    for r in range(9):
        for c in range(4):
            x, y = x0 + c * cw, y0 + r * ch
            dl.rectangle([x, y, x + cw, y + ch], outline=(74, 48, 32),
                         fill=(60, 36, 24) if r == 0 else None)
            if r > 0 and (r * 3 + c) % 4 != 1:
                dl.rectangle([x + 10, y + 10, x + 10 + 30 + ((r * 17 + c * 11) % 40), y + 18], fill=(130, 84, 50))
    dl.rectangle([x0 + 2 * cw, y0 + 3 * ch, x0 + 3 * cw, y0 + 4 * ch], outline=AMBER, width=2)
    dg.rectangle([x0 + 2 * cw, y0 + 3 * ch, x0 + 3 * cw, y0 + 4 * ch], outline=AMBER, width=3)
    for d in (dg, dl):                                          # </>
        d.line([(430, 300), (410, 320), (430, 340)], fill=AMBER, width=4)
        d.line([(476, 300), (496, 320), (476, 340)], fill=AMBER, width=4)
        d.line([(461, 296), (445, 344)], fill=CREAM if d is dl else AMBER, width=4)
    finish(canvas(), g, l, "nizcare")


def grad():                        # rising path to the horizon
    g, l, dg, dl = layers()
    hz = 210
    dg.ellipse([W / 2 - 60, hz - 60, W / 2 + 60, hz + 60], fill=(255, 140, 70))
    dl.ellipse([W / 2 - 34, hz - 34, W / 2 + 34, hz + 34], fill=(255, 196, 130))
    dl.rectangle([0, hz, W, H], fill=(18, 10, 8))
    for k in range(9):
        y = hz + 6 + (k ** 1.7) * 6
        dl.line([(0, y), (W, y)], fill=(70, 42, 28), width=1)
    for k in range(-8, 9):
        dl.line([(W / 2 + k * 10, hz), (W / 2 + k * 80, H)], fill=(70, 42, 28), width=1)
    dg.polygon([(W / 2 - 6, hz), (W / 2 + 6, hz), (W / 2 + 70, H), (W / 2 - 70, H)], fill=(120, 40, 20))
    for i in range(5):                                          # steps up the path
        y = hz + 22 + i * i * 7 + i * 8
        s = 12 + i * 16
        dl.line([(W / 2 - s, y), (W / 2 + s, y)], fill=AMBER, width=2)
    finish(canvas(), g, l, "grad")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in (btech, edvedha, techshiksha, elevate, nizcare, grad):
        f()
    print("wrote", len(os.listdir(OUT)), "files in", OUT)
