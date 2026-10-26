"""Draw the closing scene's plate: red furnace fog with the name in real type.

    python tools/build_finale_plate.py [WORD]

The finale shader gates this image by luminance: the dim red fog fades up
first, then the bright wordmark surfaces through it. So the fog is kept below
~0.30 luminance and the letters above ~0.58.  Output: public/fin/plate.jpg
(1600x900).  Fonts are converted copies of public/fonts/*.woff2 in tools/fonts.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1600, 900
WORD = (sys.argv[1] if len(sys.argv) > 1 else "ASHIK").upper()
BOX = (300, 40, 1000, 735)          # x, y, w, h of the wordmark


def noise(shape, scale, seed):
    rng = np.random.default_rng(seed)
    n = rng.random((max(2, int(shape[0] / scale)), max(2, int(shape[1] / scale))))
    return cv2.resize(n.astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)


def letters():
    f = ImageFont.truetype(os.path.join(ROOT, "tools", "fonts", "anton-400.ttf"), 600)
    probe = Image.new("L", (6000, 1000), 0)
    d = ImageDraw.Draw(probe)
    d.text((40, 40), WORD, font=f, fill=255)
    bb = probe.getbbox()
    glyphs = probe.crop(bb)
    x, y, w, h = BOX
    return np.array(glyphs.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def main():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # ---- fog ---------------------------------------------------------------
    r = np.hypot((xx - 800) / 900, (yy - 400) / 620)
    glow = np.clip(1.0 - r, 0, 1) ** 1.25
    lo = noise((H, W), 160, 3)
    mid = noise((H, W), 70, 4)
    billow = 0.72 + 0.55 * (0.6 * lo + 0.4 * mid)
    fog = glow * billow
    bg = np.stack([fog * 215, fog * 14, fog * 10], -1)     # BGR-less: R,G,B order

    # ---- letters -----------------------------------------------------------
    mask = np.zeros((H, W), np.float32)
    g = letters()
    x, y, w, h = BOX
    mask[y:y + h, x:x + w] = g
    # worn paint: wrap the extracted grunge tile over the letters
    tile = cv2.imread(os.path.join(ROOT, "public", "tex", "grunge.png"), 0).astype(np.float32) / 255.0
    tile = np.tile(tile, (3, 4))[:H, :W]
    wear = np.clip(1.0 + (tile - 0.5) * 0.45, 0.92, 1.1)
    speck = (noise((H, W), 3, 9) > 0.86).astype(np.float32)
    t = np.clip((yy - y) / h, 0, 1)
    cream = np.array([255, 240, 226], np.float32)
    rose = np.array([240, 205, 196], np.float32)
    red = np.array([205, 52, 44], np.float32)
    col = np.where(t[..., None] < 0.5,
                   cream + (rose - cream) * (t[..., None] / 0.5),
                   rose + (red - rose) * np.clip((t[..., None] - 0.5) / 0.5, 0, 1) ** 1.3)
    col = col * wear[..., None] * (1 - 0.12 * speck[..., None])

    # ---- red bloom around the letters, then composite -----------------------
    bloom = cv2.GaussianBlur(mask, (0, 0), 38)
    bg = bg + bloom[..., None] * np.array([150, 10, 8], np.float32)
    bg = np.minimum(bg, np.array([200, 20, 16], np.float32))   # stay "fog" (< 0.30 lum)
    out = bg * (1 - mask[..., None]) + col * mask[..., None]
    # edge falloff so nothing hits the frame edge hard
    vig = np.clip(1.15 - np.hypot((xx - 800) / 1000, (yy - 450) / 640) * 0.75, 0, 1)
    out = out * vig[..., None]
    out += (np.random.default_rng(1).random((H, W, 1)) - 0.5) * 3.0
    out = np.clip(out, 0, 255).astype(np.uint8)
    path = os.path.join(ROOT, "public", "fin", "plate.jpg")
    Image.fromarray(out).save(path, quality=90)
    print("wrote", path)


if __name__ == "__main__":
    main()
