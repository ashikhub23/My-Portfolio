"""Redraw the twelve gallery card sprites from public/data/projects.json.

    python tools/build_project_cards.py

Each card is a perspective "screen" placed where the gallery composition wants
it (`tools/data/card_quads.json`: sprite box + screen outline in the 1600x900
reference frame). The screen - title, kicker, tech chips and a small motif - is
drawn flat, warped into that outline, and given a dark glass bezel, a rim light
and a soft tinted glow. Output: public/projects/<id>.png at 2x.
"""
import json
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "public", "projects")
FONTS = os.path.join(ROOT, "tools", "fonts")

# card order = order in layout4.js CARDS (and in projects.json)
TINT = [(.309, .334, .382), (.249, .267, .295), (.414, .291, .291), (.322, .278, .261),
        (.39, .303, .234), (.336, .324, .333), (.336, .243, .217), (.26, .32, .366),
        (.336, .283, .269), (.448, .305, .235), (.311, .339, .263), (.31, .317, .302)]
CREAM, GREY = (244, 232, 218), (160, 146, 136)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), int(size))


def tracked(d, xy, text, f, fill, track=0.0):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + track
    return x


def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


# ------------------------------------------------------------------ motifs --
def motif(d, kind, b, ac):
    x, y, w, h = b
    cx, cy = x + w / 2, y + h / 2
    lw = max(2, int(w * 0.012))
    dim = tuple(int(c * 0.45) for c in ac)
    if kind == "face":
        r = min(w, h) * 0.30
        d.ellipse([cx - r * .78, cy - r, cx + r * .78, cy + r], outline=CREAM, width=lw)
        for dx in (-.3, .3):
            d.ellipse([cx + dx * r - 5, cy - r * .25 - 3, cx + dx * r + 5, cy - r * .25 + 3], outline=CREAM, width=lw)
        d.arc([cx - r * .3, cy + r * .05, cx + r * .3, cy + r * .5], 20, 160, fill=CREAM, width=lw)
        bx = r * 1.25
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            px, py = cx + sx * bx * .85, cy + sy * bx * 1.1
            d.line([(px, py), (px - sx * r * .35, py)], fill=ac, width=lw + 2)
            d.line([(px, py), (px, py - sy * r * .35)], fill=ac, width=lw + 2)
    elif kind == "crack":
        for i in range(5):
            d.line([(x, y + h * (.15 + i * .18)), (x + w, y + h * (.15 + i * .18))], fill=dim, width=lw)
        pts = [(cx - w * .12, y + h * .1), (cx - w * .02, y + h * .32), (cx - w * .14, y + h * .5),
               (cx + w * .04, y + h * .68), (cx - w * .04, y + h * .9)]
        d.line(pts, fill=CREAM, width=lw + 1)
        d.rectangle([cx - w * .27, y + h * .2, cx + w * .2, y + h * .8], outline=ac, width=lw + 1)
    elif kind == "kpi":
        for i in range(3):
            tx = x + i * (w / 3)
            d.rounded_rectangle([tx + 4, y, tx + w / 3 - 8, y + h * .3], 8, outline=dim, width=lw)
            d.rectangle([tx + 14, y + h * .09, tx + w / 3 - 26, y + h * .15], fill=ac if i == 1 else dim)
        pts = [(x + w * k / 6, y + h * (.95 - v)) for k, v in enumerate([.05, .22, .12, .34, .28, .5, .44])]
        d.line(pts, fill=ac, width=lw + 2)
        for p in pts:
            d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill=CREAM)
    elif kind == "pipeline":
        n = 4
        bw = w * .2
        for i in range(n):
            bx = x + i * (w - bw) / (n - 1)
            d.rounded_rectangle([bx, cy - h * .16, bx + bw, cy + h * .16], 8,
                                outline=ac if i in (0, 3) else CREAM, width=lw)
            if i < n - 1:
                ax = bx + bw
                d.line([(ax + 4, cy), (ax + (w - bw) / (n - 1) - bw - 4, cy)], fill=dim, width=lw)
    elif kind == "scan":
        for i in range(4):
            for j in range(3):
                px, py = x + w * (.12 + i * .25), y + h * (.15 + j * .3)
                d.ellipse([px - 14, py - 14, px + 14, py + 14], outline=ac if (i + j) % 3 == 0 else dim, width=lw)
        d.line([(x, cy), (x + w, cy)], fill=ac, width=lw + 1)
    elif kind == "plant":
        d.line([(cx, y + h), (cx, cy - h * .05)], fill=CREAM, width=lw + 2)
        for sx in (-1, 1):
            d.ellipse([cx + (0 if sx > 0 else -w * .3), cy - h * .22, cx + (w * .3 if sx > 0 else 0), cy + h * .08],
                      outline=ac, width=lw + 1)
        for k in (1, 2, 3):
            d.arc([cx - w * .12 * k - w * .05, y, cx + w * .12 * k + w * .05, y + h * .5 * 1.0], 300, 60, fill=dim, width=lw)
    elif kind == "qr":
        n, s = 9, min(w, h) * .09
        rng = np.random.default_rng(4)
        ox, oy = cx - n * s / 2, cy - n * s / 2
        for i in range(n):
            for j in range(n):
                corner = (i < 3 and j < 3) or (i > 5 and j < 3) or (i < 3 and j > 5)
                if corner or rng.random() > .55:
                    d.rectangle([ox + i * s, oy + j * s, ox + (i + 1) * s - 3, oy + (j + 1) * s - 3],
                                fill=ac if corner else CREAM)
    elif kind == "automation":
        d.rounded_rectangle([x, y, x + w, y + h], 10, outline=dim, width=lw)
        d.line([(x, y + h * .14), (x + w, y + h * .14)], fill=dim, width=lw)
        for i in range(4):
            ry = y + h * (.26 + i * .2)
            d.line([(x + w * .1, ry + 8), (x + w * .16, ry + 16), (x + w * .24, ry)], fill=ac, width=lw + 1)
            d.rectangle([x + w * .34, ry + 2, x + w * (.62 + .08 * (i % 3)), ry + 12], fill=dim)
    elif kind == "matrix":
        rng = np.random.default_rng(8)
        n, m = 7, 7
        s = min(w / n, h / m)
        for i in range(n):
            for j in range(m):
                v = rng.random()
                col = tuple(int(c * (.35 + .65 * v)) for c in ac) if v > .55 else None
                d.rectangle([x + i * s, y + j * s, x + (i + 1) * s - 4, y + (j + 1) * s - 4],
                            fill=col, outline=dim if col is None else None)
    elif kind == "bars":
        vals = [.35, .55, .42, .72, .6, .9]
        bw = w / (len(vals) * 1.5)
        for i, v in enumerate(vals):
            bx = x + i * bw * 1.5
            d.rectangle([bx, y + h * (1 - v), bx + bw, y + h], fill=ac if i == 5 else dim)
        d.line([(x + bw / 2 + i * bw * 1.5, y + h * (1 - v) - 22) for i, v in enumerate(vals)], fill=CREAM, width=lw)
    elif kind == "badge":
        r = min(w, h) * .3
        d.ellipse([cx - r, cy - r * 1.1, cx + r, cy + r * .9], outline=ac, width=lw + 2)
        d.ellipse([cx - r * .6, cy - r * .7, cx + r * .6, cy + r * .5], outline=CREAM, width=lw)
        d.polygon([(cx - r * .5, cy + r * .75), (cx - r * .8, cy + r * 1.5), (cx - r * .3, cy + r * 1.25), (cx, cy + r * 1.5), (cx - r * .05, cy + r * .85)], outline=dim)
        d.polygon([(cx + r * .5, cy + r * .75), (cx + r * .8, cy + r * 1.5), (cx + r * .3, cy + r * 1.25), (cx, cy + r * 1.5), (cx + r * .05, cy + r * .85)], outline=dim)
    elif kind == "star":
        r = min(w, h) * .38
        pts = []
        for k in range(10):
            a = -np.pi / 2 + k * np.pi / 5
            rr = r if k % 2 == 0 else r * .42
            pts.append((cx + rr * np.cos(a), cy + rr * np.sin(a)))
        d.polygon(pts, outline=ac, width=lw + 2)
        d.line([(cx - r * .6, cy + r * 1.25), (cx + r * .6, cy + r * 1.25)], fill=CREAM, width=lw + 1)


# -------------------------------------------------------------- flat screen --
def screen(p, idx, aspect):
    FW = 1200
    FH = int(FW / aspect)
    t = TINT[idx]
    ac = tuple(int(min(255, 120 + 380 * (c - .2))) for c in t)
    ac = (max(ac[0], 190), max(ac[1] * 0.75, 70), max(ac[2] * 0.55, 60))
    ac = tuple(int(c) for c in ac)
    yy, xx = np.mgrid[0:FH, 0:FW].astype(np.float32)
    base = np.stack([12 + 14 * yy / FH, 9 + 6 * yy / FH, 9 + 6 * yy / FH], -1)
    stacked = aspect < 1.2
    gx, gy = (0.5, 0.3) if stacked else (0.78, 0.5)
    r = np.hypot((xx - FW * gx) / FW, (yy - FH * gy) / FH)
    base += np.clip(.55 - r, 0, 1)[..., None] ** 1.6 * np.array(ac, np.float32) * .55
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    pad = FW * .07
    kf = font("oswald-500", FW * (.034 if stacked else .026))
    tf_size = FW * (.095 if stacked else .074)
    tf = font("bodonimoda-500", tf_size)
    maxw = FW * (.86 if stacked else .50)
    # fit the title to at most 3 lines
    while len(wrap(p["title"], tf, maxw)) > 3 and tf_size > FW * .04:
        tf_size *= .92
        tf = font("bodonimoda-500", tf_size)
    if stacked:
        art_box = (FW * .2, FH * .07, FW * .6, FH * .34)
        ty = FH * .46
    else:
        art_box = (FW * .6, FH * .17, FW * .33, FH * .66)
        ty = FH * .22
    motif(d, p["motif"], art_box, ac)
    d.rectangle([pad, ty - FH * .055, pad + FW * .05, ty - FH * .055 + 4], fill=ac)
    tracked(d, (pad, ty - FH * .045), p["kicker"].upper(), kf, ac, FW * .004)
    y = ty + FH * .02
    for ln in wrap(p["title"], tf, maxw):
        d.text((pad, y), ln, font=tf, fill=CREAM)
        y += tf_size * 1.12
    cf = font("oswald-400", FW * (.03 if stacked else .024))
    cx = pad
    cy = FH * (.86 if stacked else .80)
    if p["tech"]:
        for tech in p["tech"][:3 if not stacked else 2]:
            tw = tracked(ImageDraw.Draw(Image.new("RGB", (1, 1))), (0, 0), tech.upper(), cf, GREY, FW * .002)
            if cx + tw + FW * .04 > pad + maxw:
                break
            d.rounded_rectangle([cx, cy, cx + tw + FW * .03, cy + cf.size * 1.9], cf.size, outline=(96, 82, 74), width=2)
            tracked(d, (cx + FW * .015, cy + cf.size * .35), tech.upper(), cf, GREY, FW * .002)
            cx += tw + FW * .05
    else:
        cta = "VIEW DETAILS"
        tw = tracked(ImageDraw.Draw(Image.new("RGB", (1, 1))), (0, 0), cta, cf, CREAM, FW * .003)
        d.rounded_rectangle([cx, cy, cx + tw + FW * .04, cy + cf.size * 1.9], cf.size, fill=ac)
        tracked(d, (cx + FW * .02, cy + cf.size * .35), cta, cf, (20, 10, 8), FW * .003)
    # fine scanlines + grain so it reads as a lit display, not a flat PNG
    arr = np.array(img).astype(np.float32)
    arr *= (0.965 + 0.035 * np.sin(yy * 1.6))[..., None]
    arr += (np.random.default_rng(idx).random((FH, FW, 1)) - .5) * 6
    return np.clip(arr, 0, 255).astype(np.uint8)[:, :, ::-1]      # RGB -> BGR


def corners(q):
    """Reduce a 4-6 point screen outline to its four corners: TL, TR, BR, BL."""
    pts = np.array(q, np.float32)
    hull = cv2.convexHull(pts).reshape(-1, 2)
    per = cv2.arcLength(hull, True)
    quad = None
    for eps in np.linspace(0.005, 0.2, 40):
        ap = cv2.approxPolyDP(hull, eps * per, True).reshape(-1, 2)
        if len(ap) == 4:
            quad = ap
            break
    if quad is None:                                   # fallback: extreme points
        sm, df = pts.sum(1), pts[:, 0] - pts[:, 1]
        return np.float32([pts[sm.argmin()], pts[df.argmax()], pts[sm.argmax()], pts[df.argmin()]])
    c = quad.mean(0)
    quad = quad[np.argsort(np.arctan2(quad[:, 1] - c[1], quad[:, 0] - c[0]))]   # clockwise from top-left-ish
    start = int(np.argmin(quad.sum(1)))
    return np.float32(np.roll(quad, -start, axis=0))


def main():
    projects = json.load(open(os.path.join(PROJ, "..", "data", "projects.json"), encoding="utf-8"))["projects"]
    quads = json.load(open(os.path.join(ROOT, "tools", "data", "card_quads.json")))["cards"]
    for i, p in enumerate(projects):
        box = quads[i]["box"]
        w, h = int(box[2]), int(box[3])                    # sprite size = card box
        S = 2
        quad = [(qx - box[0], qy - box[1]) for qx, qy in quads[i]["quad"]]
        dst = corners(quad) * S
        tl, tr, br, bl = dst
        qw = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
        qh = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
        flat = screen(p, i, qw / qh)
        FH, FW = flat.shape[:2]
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [FW, 0], [FW, FH], [0, FH]]), dst)
        warped = cv2.warpPerspective(flat, M, (w * S, h * S), flags=cv2.INTER_CUBIC)
        # screen mask = the warped rectangle itself
        scr = cv2.warpPerspective(np.full((FH, FW), 255, np.uint8), M, (w * S, h * S))
        scr = cv2.erode(scr, np.ones((3, 3), np.uint8))
        m = cv2.GaussianBlur(scr.astype(np.float32) / 255, (0, 0), 1.0)[..., None]
        # bezel drawn here: dark glass frame, a thin rim light, a soft tinted glow
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
        band = cv2.dilate(scr, k)
        rim = cv2.subtract(band, cv2.erode(band, np.ones((5, 5), np.uint8)))
        rim = cv2.GaussianBlur(rim.astype(np.float32) / 255, (0, 0), 1.2)[..., None]
        yy = np.linspace(0, 1, h * S, dtype=np.float32)[:, None, None]
        frame_rgb = np.array([22, 20, 20], np.float32) + 10 * (1 - yy)       # BGR
        rimc = np.array([150, 170, 205], np.float32) * (0.35 + 0.65 * (1 - yy))
        t = TINT[i]
        glow_c = np.array([t[2], t[1], t[0]], np.float32)[::-1] * 255 * 1.2   # tint -> BGR
        glow = cv2.GaussianBlur(band.astype(np.float32) / 255, (0, 0), 20)[..., None]
        rgb = frame_rgb * np.ones((h * S, w * S, 1), np.float32)
        rgb = rgb * (1 - rim * .8) + rimc * rim * .8
        rgb = rgb * (1 - m) + warped.astype(np.float32) * m
        bandf = cv2.GaussianBlur(band.astype(np.float32) / 255, (0, 0), 1.2)
        rgb = np.where((bandf[..., None] > 0.02), rgb, glow_c * np.ones_like(rgb))
        alpha = np.maximum(bandf * 255, glow[..., 0] * 255 * 0.28)
        out = np.dstack([rgb, alpha]).astype(np.uint8)
        cv2.imwrite(os.path.join(PROJ, p["id"] + ".png"), out)
    print("wrote", len(projects), "sprites")


if __name__ == "__main__":
    main()
