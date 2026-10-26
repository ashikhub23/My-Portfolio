"""Build every portrait-derived asset from ONE photo.

    python tools/build_portrait_assets.py

Input : assets_src/portrait.png          (the photo)
        assets_src/portrait_cutout.png   (made on first run with `rembg`;
                                          once it exists rembg is not needed)
Output: public/media/hero.mp4 / hero.webm / hero.jpg + manifest.json
            the packed clip the hero scene composites: colour on the left
            half, alpha matte on the right half (see README)
        public/fin/man.png + public/fin/fin.json
            the figure for the closing scene
        public/media/og.jpg, public/favicon.png
            social preview and favicon

The hero scene was designed around a full-length walking figure. A still photo
is brought to life with a slow breathing push-in and a slight sway, and the
cut-off at the thighs is dissolved into the dark so it reads as a portrait
emerging from the background rather than a cropped photo.
"""
import json
import math
import os
import subprocess

import cv2
import numpy as np
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets_src")
MEDIA = os.path.join(ROOT, "public", "media")
FIN = os.path.join(ROOT, "public", "fin")

W, H, FRAMES, FPS = 720, 1280, 240, 24
HEADROOM = 0.30    # >0 makes the subject render smaller in the hero scene


# ---------------------------------------------------------------- cut-out ---
def make_cutout():
    out = os.path.join(SRC, "portrait_cutout.png")
    if os.path.exists(out):
        return cv2.imread(out, cv2.IMREAD_UNCHANGED)
    from rembg import new_session, remove  # pip install rembg
    from PIL import Image
    im = Image.open(os.path.join(SRC, "portrait.png")).convert("RGB")
    cut = remove(im, session=new_session("u2net_human_seg"))
    cut.save(out)
    return cv2.imread(out, cv2.IMREAD_UNCHANGED)


def refine(rgba):
    """Tighten the matte and replace fringe colour (the old background bleeding
    through at hair and shoulder edges) with colour from just inside the edge."""
    bgr = rgba[:, :, :3].astype(np.float32)
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    a = np.clip((a - 0.30) / 0.60, 0, 1)
    # Hair is near-black. Pale pixels hugging the hair outline are background
    # (wall / foliage) the model counted as hair, so they are removed.
    ys0 = np.nonzero((a > 0.5).any(axis=1))[0].min()
    lum = cv2.cvtColor(np.clip(bgr, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    edge = ndi.distance_transform_edt(a > 0.5)
    rows = np.zeros_like(a, bool)
    rows[ys0:ys0 + 105] = True
    a = np.where(rows & (lum > 85) & (edge < 9), 0.0, a)
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # whatever pale tint survives right at the hair rim is pulled down to hair
    # darkness (texture inside the hair is untouched)
    rim = rows & (ndi.distance_transform_edt(a > 0.5) < 14)
    k = np.where(rim, np.minimum(1.0, 46.0 / np.maximum(lum, 1)), 1.0)
    bgr = bgr * k[..., None]
    filled = ndi.binary_fill_holes(a > 0.5)          # no pin-holes inside the hair
    a = np.where(filled & (a <= 0.5), 1.0, a)
    a = cv2.erode(a, np.ones((3, 3), np.uint8))           # pull the edge in 1px
    a = cv2.GaussianBlur(a, (0, 0), 0.9)
    inner = cv2.erode((a > 0.97).astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
    _, (iy, ix) = ndi.distance_transform_edt(~inner, return_indices=True)
    solid = bgr[iy, ix]
    k = np.where(inner[..., None], 1.0, 0.0)          # edge band = interior colour
    bgr = bgr * k + solid * (1 - k)
    return bgr, a


def crop_to_subject(bgr, a):
    ys, xs = np.nonzero(a > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    pad = 6
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
    y1, x1 = min(a.shape[0], y1 + pad), min(a.shape[1], x1 + pad)
    return bgr[y0:y1, x0:x1], a[y0:y1, x0:x1]


# ------------------------------------------------------------------ video ---
def hero_frames(bgr, a):
    """Yield (packed_frame, track_box) for every frame of the loop."""
    h0, w0 = a.shape
    base_w = 600.0                                  # subject width in the frame
    base = base_w / w0
    pm = bgr * a[..., None]                         # premultiplied colour
    src = np.dstack([pm, a]).astype(np.float32)
    fade_px = 150                                   # thigh cut-off dissolves
    ramp = np.ones(H, np.float32)
    ramp[H - fade_px:] = np.linspace(1, 0, fade_px) ** 1.6
    for f in range(FRAMES):
        ph = 2 * math.pi * f / FRAMES
        breath = 0.5 * (1 - math.cos(ph))           # 0 -> 1 -> 0, seamless loop
        s = base * (1 + 0.022 * breath)
        dx = 6 * math.sin(ph)
        bw, bh = w0 * s, h0 * s
        M = np.float32([[s, 0, (W - bw) / 2 + dx],
                        [0, s, H + 30 - bh + 6 * breath]])   # bleeds past bottom
        fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        m = np.clip(fr[:, :, 3], 0, 1) * ramp[:, None]
        col = np.clip(fr[:, :, :3], 0, 255) * ramp[:, None, None]
        ys, xs = np.nonzero(m > 0.5)
        top = ys.min() / H
        head = (1.0 - top) * HEADROOM          # declared headroom above the hair
        box = [round(xs.min() / W, 4), round(top - head, 4),
               round((xs.max() + 1) / W, 4), 1.0]
        mat = np.repeat((m * 255.0)[..., None], 3, axis=2)
        yield np.concatenate([col, mat], 1).astype(np.uint8), box


def encode(bgr, a):
    os.makedirs(MEDIA, exist_ok=True)
    mp4, webm = os.path.join(MEDIA, "hero.mp4"), os.path.join(MEDIA, "hero.webm")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", "%dx%d" % (W * 2, H), "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-color_range", "pc", "-movflags", "+faststart", mp4,
           "-an", "-c:v", "libvpx-vp9", "-crf", "28", "-b:v", "0", "-row-mt", "1",
           "-cpu-used", "4", "-pix_fmt", "yuv420p", webm]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    track, first = [], None
    for packed, box in hero_frames(bgr, a):
        if first is None:
            first = packed
        p.stdin.write(packed.tobytes())
        track.append(box)
    p.stdin.close()
    p.wait()
    cv2.imwrite(os.path.join(MEDIA, "hero.jpg"), first[:, :W],
                [cv2.IMWRITE_JPEG_QUALITY, 82])
    with open(os.path.join(MEDIA, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"clips": {"hero": {
            "name": "hero", "frames": FRAMES, "w": W, "h": H,
            "mp4": "hero.mp4", "webm": "hero.webm", "poster": "hero.jpg",
            "packed": "side-by-side: colour | matte", "track": track}}}, fh, indent=1)
    print("hero clip: %d frames" % len(track))


# ----------------------------------------------------------------- finale ---
def build_finale_man(bgr, a):
    """Closing-scene figure. Frame is 1600x900; the figure is anchored to the
    bottom edge and dissolves into it."""
    os.makedirs(FIN, exist_ok=True)
    box_h = 540                                   # px in the 1600x900 frame
    scale = box_h / a.shape[0]
    box_w = int(round(a.shape[1] * scale))
    S = 2                                         # texture at 2x for crispness
    tw, th = box_w * S, box_h * S
    pm = cv2.resize(bgr * a[..., None], (tw, th), interpolation=cv2.INTER_AREA)
    aa = cv2.resize(a, (tw, th), interpolation=cv2.INTER_AREA)
    fade = int(th * 0.16)
    ramp = np.ones(th, np.float32)
    ramp[th - fade:] = np.linspace(1, 0, fade) ** 1.5
    aa = aa * ramp[:, None]
    a_raw = cv2.resize(a, (tw, th), interpolation=cv2.INTER_AREA)[..., None]
    col = pm / np.maximum(a_raw, 1e-3)              # back to straight alpha
    out = np.dstack([np.clip(col, 0, 255), aa * 255]).astype(np.uint8)
    cv2.imwrite(os.path.join(FIN, "man.png"), out)
    x = int(round((1600 - box_w) / 2 + 20))
    y = 900 - box_h + 20
    with open(os.path.join(FIN, "fin.json"), "w") as fh:
        json.dump({"man": [x, y, box_w, box_h], "size": [1600, 900]}, fh)
    print("finale figure box", [x, y, box_w, box_h])


def red_ground(w, h, cx=0.5, cy=0.35):
    """Deep red furnace glow, matching the hero (BGR float image)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w * cx) / w, (yy - h * cy) / h)
    g = np.clip(1.05 - r * 1.5, 0, 1) ** 1.4
    return np.stack([8 + 12 * g, 4 + 10 * g, 10 + 150 * g], -1)


def place(canvas, bgr, a, height, bottom, cx):
    """Alpha-composite the cut-out, `height` px tall, bottom edge at `bottom`."""
    s = height / a.shape[0]
    cw, ch = int(a.shape[1] * s), int(height)
    rgb = cv2.resize(bgr, (cw, ch), interpolation=cv2.INTER_AREA)
    al = cv2.resize(a, (cw, ch), interpolation=cv2.INTER_AREA)[..., None]
    x0, y0 = int(cx - cw / 2), int(bottom - ch)
    H_, W_ = canvas.shape[:2]
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(W_, x0 + cw), min(H_, y0 + ch)
    sub = (slice(ys, ye), slice(xs, xe))
    src = (slice(ys - y0, ye - y0), slice(xs - x0, xe - x0))
    canvas[sub] = rgb[src] * al[src] + canvas[sub] * (1 - al[src])


def build_social(bgr, a):
    """Favicon, About-section portrait and social preview card."""
    from PIL import Image, ImageDraw, ImageFont
    fonts = os.path.join(ROOT, "tools", "fonts")
    os.makedirs(os.path.join(ROOT, "public", "img"), exist_ok=True)
    # About portrait, 4:5
    c = red_ground(800, 1000)
    place(c, bgr, a, 940, 1000, 400)
    cv2.imwrite(os.path.join(ROOT, "public", "img", "portrait.jpg"), np.clip(c, 0, 255).astype(np.uint8),
                [cv2.IMWRITE_JPEG_QUALITY, 86])
    # Open Graph card, 1200x630
    c = red_ground(1200, 630, 0.74, 0.45)
    place(c, bgr, a, 590, 630, 900)
    im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)[:, :, ::-1])
    d = ImageDraw.Draw(im)
    d.text((70, 150), "MOHAMED", font=ImageFont.truetype(os.path.join(fonts, "anton-400.ttf"), 150), fill=(244, 232, 218))
    d.text((70, 305), "ASHIK S", font=ImageFont.truetype(os.path.join(fonts, "anton-400.ttf"), 150), fill=(222, 27, 28))
    f = ImageFont.truetype(os.path.join(fonts, "oswald-500.ttf"), 27)
    x = 74
    for ch in "FULL STACK  \u00b7  AI / ML  \u00b7  DATA ANALYTICS":
        d.text((x, 508), ch, font=f, fill=(226, 212, 198))
        x += f.getlength(ch) + 4
    im.save(os.path.join(MEDIA, "og.jpg"), quality=88)
    ys, xs = np.nonzero(a > 0.5)
    top = ys.min()
    # square head-and-shoulders crop for the favicon
    cx = int((xs.min() + xs.max()) / 2)
    size = int((xs.max() - xs.min()) * 0.62)
    x0 = max(0, cx - size // 2)
    y0 = max(0, top - 4)
    crop = bgr[y0:y0 + size, x0:x0 + size]
    ca = a[y0:y0 + size, x0:x0 + size]
    bg = np.zeros_like(crop) + np.array([14, 8, 70], np.float32)  # deep red (BGR)
    comp = crop * ca[..., None] + bg * (1 - ca[..., None])
    cv2.imwrite(os.path.join(ROOT, "public", "favicon.png"),
                cv2.resize(comp, (256, 256), interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    cut = make_cutout()
    bgr, a = refine(cut)
    bgr, a = crop_to_subject(bgr, a)
    encode(bgr, a)
    build_finale_man(bgr, a)
    build_social(bgr, a)
