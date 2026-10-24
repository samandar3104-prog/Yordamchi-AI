#!/usr/bin/env python3
"""ZRR story v2 — warm dark palette, shape-morphing speaker frame, b-roll, per-bullet animations.

usage: render2.py SRC.mov BROLL_DIR PHOTO.jpg OUT_PREFIX START END   (frame range, writes OUT_PREFIX.mp4)
       render2.py ... preview T1,T2,...                            (writes PNGs)
"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, BROLL_DIR, PHOTO, OUT = sys.argv[1:5]
W, H, FPS = 1080, 1920, 30
SW, SH = 854, 480
SRC_FRAMES = 956
N = int(math.ceil((SRC_FRAMES / FPS + 1.05) * FPS))
DUR = N / FPS

# ---------- palette ----------
BG0 = (16, 8, 6)
BG1 = (52, 22, 14)
MAROON = (110, 36, 22)
RUST = (170, 70, 40)
AMBER = (232, 160, 58)
GOLD = (246, 198, 92)
CREAM = (247, 233, 210)
RED = (220, 70, 50)
MUTED = (150, 112, 92)

FD = "/usr/share/fonts/opentype/inter/"
@lru_cache(None)
def font(w, s): return ImageFont.truetype(FD + f"Inter-{w}.otf", s)
@lru_cache(None)
def dfont(w, s): return ImageFont.truetype(FD + f"InterDisplay-{w}.otf", s)

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def spring(t, w=12.0, z=0.6):
    if t <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def lerp_rect(a, b, t): return tuple(lerp(x, y, t) for x, y in zip(a, b))
def with_alpha(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))

# ---------- grading: warm, darker ----------
def make_lut():
    x = np.arange(256) / 255.0
    x = np.clip((x - 0.5) * 1.12 + 0.5, 0, 1) ** 1.12      # contrast + darker mids
    r = np.clip(x * 1.02 + 0.035, 0, 1)
    g = np.clip(x * 0.86 + 0.012, 0, 1)
    b = np.clip(x * 0.66 + 0.0, 0, 1)
    return [int(v * 255) for v in np.concatenate([r, g, b])]
LUT = make_lut()
def grade(im): return im.point(LUT)

# ---------- static layers ----------
def radial_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d1 = np.sqrt(((xx - 250) / 900) ** 2 + ((yy - 380) / 900) ** 2)
    d2 = np.sqrt(((xx - 900) / 800) ** 2 + ((yy - 1650) / 800) ** 2)
    g = np.clip(1 - d1, 0, 1) ** 1.6 * 0.9 + np.clip(1 - d2, 0, 1) ** 1.8 * 0.6
    base = np.array(BG0, np.float32)
    top = np.array(BG1, np.float32) * 1.25
    img = base[None, None] + (top - base)[None, None] * g[..., None]
    return Image.fromarray(np.uint8(np.clip(img, 0, 255)))
BG = radial_bg().convert("RGBA")

def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
    a = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.5 * 200
    v = np.zeros((H, W, 4), np.uint8); v[..., 0:3] = BG0; v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v)
VIG = vignette()

def scrim(y0, y1, amax=0.9):
    a = np.zeros((H, W), np.float32)
    ramp = np.clip((np.arange(H) - y0) / max(1, (y1 - y0)), 0, 1) ** 1.4 * amax * 255
    a[:] = ramp[:, None]
    v = np.zeros((H, W, 4), np.uint8); v[..., 0:3] = BG0; v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v)
SCRIM_BOTTOM = scrim(1050, 1800, 0.92)

def topscrim():
    a = np.clip(1 - np.arange(H) / 620, 0, 1) ** 1.6 * 0.75 * 255
    v = np.zeros((H, W, 4), np.uint8); v[..., 0:3] = BG0; v[..., 3] = a[:, None].astype(np.uint8)
    return Image.fromarray(v)
SCRIM_TOP = topscrim()

PHOTO_IM = grade(Image.open(PHOTO).convert("RGB"))

@lru_cache(maxsize=12)
def broll_frame(idx):
    idx = max(1, min(240, idx))
    return grade(Image.open(os.path.join(BROLL_DIR, f"{idx:04d}.jpg")).convert("RGB"))

def broll_at(src_t):
    f = src_t * 24 + 1
    i0 = int(math.floor(f)); fr = f - i0
    a = broll_frame(i0)
    if fr < 0.05: return a
    return Image.blend(a, broll_frame(i0 + 1), fr)

# ---------- layouts ----------
FULL = (0, 0, W, H, 0)
# Expert is either the lower half of a clean 50/50 split or hidden (voice-over).
# In the lower half the face sits around y≈1230, well clear of Instagram's top/bottom UI zones.
TOPH = (0, 0, W, H / 2, 0)
BOTH = (0, H / 2, W, H / 2, 0)
OFF = (0, H, W, H / 2, 0)
def circle(cx, cy, d): return (cx - d / 2, cy - d / 2, d, d, d / 2)

# segment: start, speaker rect, speaker zoom, media (kind, a, speed) , media rect
T_OUTRO = 29.85   # expert holds the final 3+ seconds
SEGS = [
    dict(t=0.0,   spk=BOTH, z=1.0,  media=None),
    dict(t=3.05,  spk=BOTH, z=1.0,  media=("photo",), mrect=TOPH),
    dict(t=8.70,  spk=OFF,  z=1.0,  media=("broll", 0.05, 0.53), mrect=FULL),
    dict(t=14.05, spk=BOTH, z=1.06, media=("neuro", 5.0, 1.0), mrect=TOPH),
    dict(t=18.80, spk=FULL, z=1.0,  media=None),
    dict(t=23.90, spk=BOTH, z=1.03, media=("broll", 2.95, 0.6), mrect=TOPH),
    dict(t=28.90, spk=OFF,  z=1.03, media=("broll", 6.90, 0.8), mrect=FULL),
    dict(t=T_OUTRO, spk=FULL, z=1.0, media=None),   # always end on the expert
]
def seg_index(t):
    k = 0
    for i, s in enumerate(SEGS):
        if t >= s["t"]: k = i
    return k

# ---------- speaker ----------
SPK_REGION = (0, 0, 368, 480)
FACE = (186, 178)
def speaker_crop(src, w, h, z):
    a = w / h
    rx0, ry0, rx1, ry1 = SPK_REGION
    rw, rh = rx1 - rx0, ry1 - ry0
    if a < rw / rh: ch = rh; cw = ch * a
    else: cw = rw; ch = cw / a
    cw /= z; ch /= z
    cy_t = 205 if a > 1.2 else lerp(250, FACE[1] + 25, clamp((z - 1) / 0.6))
    cx = clamp(FACE[0], rx0 + cw / 2, rx1 - cw / 2)
    cy = clamp(cy_t, ry0 + ch / 2, ry1 - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    im = src.resize((max(2, int(w)), max(2, int(h))), Image.BICUBIC, box=box)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))  # speaker keeps original colors

def rr_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), int(max(0, min(r, (w - 2) / 2, (h - 2) / 2))), fill=255)
    return m

@lru_cache(maxsize=64)
def window_shadow(w, h, r):
    pad = 110
    sh = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    rr = int(max(0, min(r, (w - 2) / 2, (h - 2) / 2)))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 26, pad + w, pad + h + 26), rr, fill=(4, 1, 0, 175))
    small = sh.resize((sh.width // 4, sh.height // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    return small.resize(sh.size, Image.BILINEAR)

def glass_layer():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = (xx / W + yy / H * 0.55)
    a = np.clip(1 - d / 0.55, 0, 1) ** 2 * 30
    v = np.zeros((H, W, 4), np.uint8); v[..., 0:3] = 255; v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v)
GLASS = glass_layer()

def float_offset(t, phase=0.0, amp=7.0):
    return 3.0 * math.sin(t * 0.9 + phase), amp * math.sin(t * 2 * math.pi / 3.4 + phase)

def draw_window(canvas, im, rect, alpha=1.0, shadow=True):
    """Floating glass window: soft deep shadow, hairline light border, faint glass sheen."""
    x, y, w, h, r = rect
    w, h = int(w), int(h)
    if w < 4 or h < 4 or alpha <= 0.01: return
    rr = int(max(0, min(r, (w - 2) / 2, (h - 2) / 2)))
    m = rr_mask(w, h, rr)
    if alpha < 1: m = m.point(lambda v: int(v * alpha))
    if shadow and rr > 2:
        sh = window_shadow(w, h, rr)
        if alpha < 1:
            sh = sh.copy(); sh.putalpha(sh.getchannel("A").point(lambda v: int(v * alpha)))
        canvas.alpha_composite(sh, (int(x) - 110, int(y) - 110))
    canvas.paste(im.convert("RGB"), (int(x), int(y)), m)
    if rr > 2:
        g = GLASS.crop((0, 0, w, h)).copy()
        g.putalpha(Image.fromarray(np.minimum(np.array(g.getchannel("A")), np.array(m))))
        canvas.alpha_composite(g, (int(x), int(y)))
        o = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        ImageDraw.Draw(o).rounded_rectangle((1, 1, w + 2, h + 2), rr + 1, outline=(255, 236, 214, int(70 * alpha)), width=2)
        canvas.alpha_composite(o, (int(x) - 2, int(y) - 2))

def media_image(seg, t, w, h):
    kind = seg["media"]
    nxt = [x["t"] for x in SEGS if x["t"] > seg["t"]]
    local = min(t, (nxt[0] - 0.12) if nxt else t) - seg["t"]
    kb = 1.0 + 0.06 * clamp(local / 5.5)
    if kind[0] == "photo":
        return photo_half(local, w, h)
    if kind[0] == "photo_cover":
        src = PHOTO_IM; sw, sh = src.size
        a = w / h
        if a > sw / sh: cw = sw; ch = cw / a
        else: ch = sh; cw = ch * a
        cw /= kb; ch /= kb
        cx, cy = sw * 0.5, sh * 0.3
        cx = clamp(cx, cw / 2, sw - cw / 2); cy = clamp(cy, ch / 2, sh - ch / 2)
        return src.resize((w, h), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    if kind[0] == "graphic":
        return graphic_network(t, local, w, h)
    if kind[0] == "neuro":
        return neuro_frame(kind[1] + local * kind[2], w, h)
    _, a0, speed = kind
    st = min(a0 + local * speed, 9.95)
    src = broll_at(st); sw, sh = src.size
    a = w / h
    if a > sw / sh: cw = sw; ch = cw / a
    else: ch = sh; cw = ch * a
    cw /= kb; ch /= kb
    cx, cy = sw / 2, sh * (0.45 if h > H * 0.75 else 0.36)
    cx = clamp(cx, cw / 2, sw - cw / 2); cy = clamp(cy, ch / 2, sh - ch / 2)
    return src.resize((w, h), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))

# ---------- text helpers ----------
def text_layer(txt, f, fill, pad=6):
    bb = f.getbbox(txt)
    im = Image.new("RGBA", (bb[2] + pad * 2, bb[3] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad), txt, font=f, fill=fill)
    return im

def paste_alpha(canvas, im, x, y, alpha=1.0, scale=1.0):
    if alpha <= 0.01 or scale <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(x), int(y)))

def reveal_words(canvas, words, f, x, y, t0, t, fill, stagger=0.07, exit_t=None, line_w=920, lh=None):
    """Words rise from a clip line, staggered (mask reveal). Exit: rise out + fade."""
    lh = lh or int(f.size * 1.18)
    cx, cy = x, y
    for i, wd in enumerate(words):
        lay = text_layer(wd + " ", f, fill)
        if cx + lay.width - x > line_w and cx > x:
            cx = x; cy += lh
        k = spring(t - t0 - i * stagger, w=14, z=0.75)
        off = (1 - k) * lh
        a = clamp((t - t0 - i * stagger) / 0.12)
        if exit_t is not None and t > exit_t:
            e = ease_in((t - exit_t - i * 0.03) / 0.3)
            off -= e * lh * 0.8; a *= 1 - e
        if a > 0:
            clip = Image.new("RGBA", (lay.width, lh + 12), (0, 0, 0, 0))
            clip.alpha_composite(lay, (0, int(max(-lay.height, min(lh + 12, off)))))
            paste_alpha(canvas, clip, cx, cy - 6, a)
        cx += lay.width
    return cy + lh

# ---------- captions (thin, one side, same place every time) ----------
BULLETS = [
    (3.05, "01", "Lug'at boyligi kam"),
    (8.70, "02", "Grammatik muammolar"),
    (14.05, "03", "Til tizimi buzilishi"),
    (18.80, "04", "Ijtimoiy aloqa yaxshi"),
    (23.90, "05", "O'yin faoliyati shakllangan"),
    (28.90, "06", "Ko'z bilan aloqa mavjud"),
]
CAP_X, CAP_Y = 72, 300

@lru_cache(maxsize=8)
def caption_block(num, title):
    f_title = font("Light", 62)
    f_small = font("Light", 30)
    lay = Image.new("RGBA", (960, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((0, 0), num, font=f_small, fill=GOLD)
    d.line([(62, 21), (170, 21)], fill=(246, 198, 92, 210), width=2)
    d.text((186, 0), "ZRR belgisi", font=f_small, fill=(247, 233, 210, 190))
    # wrap title
    words, lines, cur = title.split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if f_title.getlength(test) > 900 and cur: lines.append(cur); cur = wd
        else: cur = test
    lines.append(cur)
    for li, ln in enumerate(lines):
        d.text((0, 52 + li * 76), ln, font=f_title, fill=CREAM)
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.75)))
    out = Image.new("RGBA", (lay.width + 20, lay.height + 20), (0, 0, 0, 0))
    out.alpha_composite(sh, (4, 6)); out.alpha_composite(lay, (0, 0))
    return out

def caption(canvas, idx, t):
    t0, num, title = BULLETS[idx]
    end = BULLETS[idx + 1][0] if idx + 1 < len(BULLETS) else T_OUTRO
    if t < t0 + 0.15 or t > end: return
    blk = caption_block(num, title)
    kin = ease_out((t - t0 - 0.15) / 0.7)          # wipe in from the left edge
    kout = ease_in((t - (end - 0.45)) / 0.38) if t > end - 0.45 else 0.0
    reveal = kin * (1 - kout)
    if reveal <= 0.002: return
    wv = int(blk.width * reveal)
    piece = blk.crop((0, 0, max(1, wv), blk.height))
    # soft wipe edge
    edge = min(60, wv)
    if edge > 1:
        a = np.array(piece.getchannel("A"), np.float32)
        a[:, wv - edge:] *= np.linspace(1, 0, edge)[None, :]
        piece.putalpha(Image.fromarray(np.uint8(a)))
    dx = -36 * (1 - kin) - 24 * kout
    paste_alpha(canvas, piece, CAP_X + dx, CAP_Y, 1.0)

# ---------- photo for the upper half ----------
@lru_cache(maxsize=2)
def feather_top(w, h, f):
    a = np.clip(np.arange(h, dtype=np.float32) / f, 0, 1) ** 1.6 * 255
    return Image.fromarray(np.repeat(a[:, None], w, 1).astype(np.uint8))

def photo_half(local, w, h):
    out = BG.crop((0, 0, w, h)).convert("RGB")
    ph = int(h * 0.56)
    kb = 1.0 + 0.05 * clamp(local / 5.5)
    src = PHOTO_IM; sw, sh = src.size
    cw = sw / kb; ch = cw * ph / w
    cx, cy = sw * 0.5, sh * 0.27
    cy = clamp(cy, ch / 2, sh - ch / 2)
    im = src.resize((w, ph), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    out.paste(im, (0, h - ph), feather_top(w, ph, 170))
    return out

# ---------- neuron / brain footage (Ijtimoiy aloqa) ----------
NEURO_DIR = os.path.join(os.path.dirname(BROLL_DIR.rstrip("/")) or ".", "nf")
def _gmap():
    stops = [(0.0, (6, 3, 2)), (0.3, (70, 24, 12)), (0.62, (214, 120, 44)), (0.85, (246, 196, 100)), (1.0, (255, 240, 214))]
    lut = [[], [], []]
    for v in range(256):
        x = (v / 255) ** 0.95
        for k in range(len(stops) - 1):
            if stops[k][0] <= x <= stops[k + 1][0]:
                u = (x - stops[k][0]) / (stops[k + 1][0] - stops[k][0]); break
        c = [lerp(stops[k][1][ch], stops[k + 1][1][ch], u) for ch in range(3)]
        for ch in range(3): lut[ch].append(int(c[ch]))
    return lut
GMAP = _gmap()

@lru_cache(maxsize=8)
def neuro_src(idx):
    idx = max(1, min(301, idx))
    g = Image.open(os.path.join(NEURO_DIR, f"{idx:04d}.jpg")).convert("L")
    return Image.merge("RGB", [g.point(GMAP[c]) for c in range(3)])

@lru_cache(maxsize=1)
def neuro_mask(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ex = np.clip(np.minimum(xx, w - 1 - xx) / (w * 0.16), 0, 1)
    ey = np.clip(np.minimum(yy, h - 1 - yy) / (h * 0.12), 0, 1)
    return Image.fromarray(np.uint8((ex * ey) ** 1.3 * 255))

def neuro_frame(st, w, h):
    f = st * 30 + 1
    i0 = int(f); fr = f - i0
    src = neuro_src(i0)
    if fr > 0.05: src = Image.blend(src, neuro_src(i0 + 1), fr)
    sw, sh = src.size
    cw = sw; ch = cw * h / w
    if ch > sh: ch = sh; cw = ch * w / h
    cy = clamp(sh * (0.5 if h > H * 0.75 else 0.44), ch / 2, sh - ch / 2)
    return src.resize((w, h), Image.LANCZOS, box=((sw - cw) / 2, cy - ch / 2, (sw + cw) / 2, cy + ch / 2))

# ---------- generated animation: connection (Ijtimoiy aloqa) ----------
@lru_cache(maxsize=4)
def panel_bg(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w * 0.5) / (w * 0.8)) ** 2 + ((yy - h * 0.62) / (h * 0.8)) ** 2)
    g = np.clip(1 - d, 0, 1) ** 1.4
    img = np.array(BG0, np.float32)[None, None] + (np.array((78, 32, 20), np.float32) - np.array(BG0, np.float32))[None, None] * g[..., None]
    return Image.fromarray(np.uint8(np.clip(img, 0, 255))).convert("RGBA")

@lru_cache(maxsize=2)
def glow_sprite(size, col):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - d, 0, 1) ** 2.2 * 200
    v = np.zeros((size, size, 4), np.uint8); v[..., 0:3] = col; v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v)

def graphic_network(t, local, w, h):
    im = panel_bg(w, h).copy()
    lines = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    come = ease_io(local / 2.2)
    fl = 10 * math.sin(local * 1.7)
    L = (w * lerp(0.2, 0.27, come), h * 0.6 + fl)
    R = (w * lerp(0.8, 0.73, come), h * 0.6 - fl)
    n = 11
    for j in range(n):
        p = ease_out((local - 0.25 - j * 0.06) / 1.1)
        if p <= 0: continue
        off = (j - (n - 1) / 2) * h * 0.045 * (1 + 0.35 * math.sin(local * 0.9 + j * 0.7))
        cx, cy = (L[0] + R[0]) / 2, (L[1] + R[1]) / 2 + off * 2.2
        pts = []
        steps = 48
        for k in range(int(steps * p) + 1):
            u = k / steps
            x = (1 - u) ** 2 * L[0] + 2 * (1 - u) * u * cx + u * u * R[0]
            y = (1 - u) ** 2 * L[1] + 2 * (1 - u) * u * cy + u * u * R[1]
            pts.append((x, y))
        if len(pts) > 1:
            col = AMBER if j % 2 else GOLD
            d.line(pts, fill=with_alpha(col, 0.32 + 0.25 * (1 - abs(j - n / 2) / (n / 2))), width=2)
        if p >= 1:
            u = (local * 0.32 + j * 0.137) % 1.0
            x = (1 - u) ** 2 * L[0] + 2 * (1 - u) * u * cx + u * u * R[0]
            y = (1 - u) ** 2 * L[1] + 2 * (1 - u) * u * cy + u * u * R[1]
            a = math.sin(math.pi * u)
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=with_alpha(CREAM, 0.9 * a))
    glow = lines.resize((w // 3, h // 3), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((w, h), Image.BILINEAR)
    im.alpha_composite(glow); im.alpha_composite(lines)
    pulse = 1 + 0.06 * math.sin(local * 3.2)
    for P, col in ((L, GOLD), (R, AMBER)):
        g = glow_sprite(300, col)
        gs = int(300 * pulse)
        im.alpha_composite(g.resize((gs, gs), Image.BILINEAR), (int(P[0] - gs / 2), int(P[1] - gs / 2)))
        ImageDraw.Draw(im).ellipse((P[0] - 15, P[1] - 15, P[0] + 15, P[1] + 15), fill=CREAM)
    return im.convert("RGB")

# ---------- generated animation: speech waveform lines (Til tizimi) ----------
def draw_waves(canvas, t, t0, end):
    lt = t - t0
    if lt < 0 or t > end: return
    a_all = clamp(lt / 0.5) * (1 - ease_in((t - (end - 0.4)) / 0.35))
    if a_all <= 0: return
    sw_, sh_ = W // 2, H // 2
    lay = Image.new("RGBA", (sw_, sh_), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    glitch = 0.0
    g0 = 16.05
    if g0 <= t <= g0 + 0.45: glitch = 1 - (t - g0) / 0.45
    rng = np.random.default_rng(int(t * 30))
    for band_y, amp in ((300, 30), (410, 36)):
        for j in range(6):
            pts = []
            ph = lt * (1.2 + j * 0.15) + j * 0.9
            for xi in range(0, sw_ + 6, 6):
                u = xi / sw_
                env = math.sin(math.pi * u) ** 1.5
                y = band_y + (j - 2.5) * 7 + amp * env * math.sin(u * (7 + j) + ph) * (0.6 + 0.4 * math.sin(ph * 0.5 + j))
                if glitch > 0 and (xi // 30) % 3 == int(t * 40) % 3:
                    y += rng.uniform(-18, 18) * glitch
                pts.append((xi, y))
            col = RED if glitch > 0.3 and j % 2 == 0 else (AMBER if j % 2 else GOLD)
            d.line(pts, fill=with_alpha(col, (0.28 + 0.1 * (j % 3)) * a_all), width=1)
    glow = lay.filter(ImageFilter.GaussianBlur(4))
    big = Image.alpha_composite(glow, lay).resize((W, H), Image.BILINEAR)
    canvas.alpha_composite(big)

# ---------- intro / outro ----------
def intro(canvas, t):
    if t > 3.1: return
    ex = ease_in((t - 2.55) / 0.4) if t > 2.55 else 0
    tag = Image.new("RGBA", (330, 64), (0, 0, 0, 0))
    td = ImageDraw.Draw(tag)
    td.rounded_rectangle((0, 0, 329, 63), 32, fill=MAROON)
    td.text((165, 33), "TASHXIS  2 / 5", font=font("Bold", 28), fill=GOLD, anchor="mm")
    k = spring(t - 0.15, w=12, z=0.6)
    paste_alpha(canvas, tag, 540 - 165, 330 + (1 - k) * 40 - ex * 60, clamp(k * 2) * (1 - ex))
    # Z R R letters drop with stagger
    f = dfont("Black", 270)
    xs = [255, 470, 690]
    for i, ch in enumerate("ZRR"):
        kk = spring(t - 0.35 - i * 0.1, w=13, z=0.48)
        lay = text_layer(ch, f, AMBER if i == 0 else CREAM, pad=10)
        sc = lerp(1.8, 1.0, kk) * (1 + 0.5 * ex)
        a = clamp(kk * 2) * (1 - ex)
        paste_alpha(canvas, lay, xs[i] - lay.width * sc / 2 + 50, 420 - (lay.height * (sc - 1)) / 2 - ex * 40, a, sc)
    reveal_words(canvas, "nutq rivojlanishi kechikishi".split(), font("SemiBold", 50), 175, 760, 0.95, t, GOLD,
                 exit_t=2.55)
    # name under speaker circle
    k = spring(t - 1.1, w=12, z=0.7)
    nm = text_layer("Muslima Usmaan", font("Regular", 40), CREAM)
    rl = text_layer("Defektolog-Logoped, ABA-terapist", font("Light", 30), MUTED)
    a = clamp(k * 2) * (1 - ex)
    paste_alpha(canvas, nm, 540 - nm.width / 2, 862 + (1 - k) * 30, a)
    paste_alpha(canvas, rl, 540 - rl.width / 2, 918 + (1 - k) * 30, a)

SCRIM_SUB = scrim(900, 1640, 0.93)

def shadowed(lay, blur=9, strength=0.85):
    """Soft dark halo behind light text so it reads over a light jacket."""
    pad = blur * 2
    out = Image.new("RGBA", (lay.width + pad * 2, lay.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, BG0 + (0,))
    a = Image.new("L", out.size, 0); a.paste(lay.getchannel("A"), (pad, pad + 3))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * strength * 1.6))))
    out.alpha_composite(sh); out.alpha_composite(lay, (pad, pad))
    return out

SUBS = {
    3: dict(label="04  ——  ZRR belgisi", line1=[("Ijtimoiy", 19.20), ("aloqa", 19.55)], line2=("yaxshi", 20.00),
            start=19.0, exit=23.35, end=23.9),
    5: dict(label="06  ——  ZRR belgisi", line1=[("Ko'z", 29.05), ("bilan", 29.30), ("aloqa", 29.55)], line2=("mavjud", 30.00),
            start=28.95, exit=31.0, end=31.45),
}
def kinetic_sub(canvas, t, spec):
    if t < spec["start"] or t > spec["end"]: return
    out = ease_in((t - spec["exit"]) / 0.4) if t > spec["exit"] else 0.0
    ka = ease_out((t - spec["start"] - 0.05) / 0.4) * (1 - out)
    lbl = shadowed(text_layer(spec["label"], font("Regular", 32), GOLD), 6)
    paste_alpha(canvas, lbl, 540 - lbl.width / 2, 1170 - 10 * (1 - ka), ka)
    f1 = font("Light", 96)
    l1 = [shadowed(text_layer(wd, f1, CREAM, pad=12)) for wd, _ in spec["line1"]]
    gap = -10
    tot = sum(l.width for l in l1) + gap * (len(l1) - 1)
    x = 540 - tot / 2
    for lay, (wd, t0) in zip(l1, spec["line1"]):
        k = spring(t - t0, w=13, z=0.72)
        if k > 0:
            sc = lerp(0.82, 1.0, k)
            a = clamp((t - t0) / 0.18) * (1 - out)
            lay2 = lay.filter(ImageFilter.GaussianBlur(6 * (1 - clamp((t - t0) / 0.25)))) if t - t0 < 0.25 else lay
            paste_alpha(canvas, lay2, x + lay.width * (1 - sc) / 2, 1215 + 30 * (1 - k) - 40 * out + lay.height * (1 - sc) / 2, a, sc)
        x += lay.width + gap
    wd, t0 = spec["line2"]
    k = spring(t - t0, w=12, z=0.5)
    if k > 0:
        lay = shadowed(text_layer(wd, font("Regular", 118), GOLD, pad=14))
        sc = lerp(1.35, 1.0, k)
        a = clamp((t - t0) / 0.15) * (1 - out)
        paste_alpha(canvas, lay, 540 - lay.width * sc / 2, 1335 - 40 * out + lay.height * (1 - sc) / 2, a, sc)
        u = ease_out((t - t0 - 0.2) / 0.5) * (1 - out)
        if u > 0:
            ImageDraw.Draw(canvas).line((540 - 150 * u, 1490, 540 + 150 * u, 1490), fill=with_alpha(GOLD, 0.9), width=3)

T_NAME = 31.35
def outro(canvas, t):
    t0 = T_NAME - 0.4
    if t < T_NAME - 0.1: return
    k = spring(t - t0 - 0.4, w=12, z=0.7)
    nm = shadowed(text_layer("Muslima Usmaan", font("Light", 68), CREAM, pad=10))
    rl = shadowed(text_layer("Defektolog-Logoped, ABA-terapist", font("Regular", 34), GOLD), 6)
    paste_alpha(canvas, nm, 540 - nm.width / 2, 1290 + (1 - k) * 30, clamp(k * 2))
    k2 = spring(t - t0 - 0.55, w=12, z=0.7)
    paste_alpha(canvas, rl, 540 - rl.width / 2, 1390 + (1 - k2) * 30, clamp(k2 * 2))
    kk = ease_out((t - t0 - 0.7) / 0.45)
    ImageDraw.Draw(canvas).line((540 - 130 * kk, 1462, 540 + 130 * kk, 1462), fill=GOLD, width=2)

# ---------- frame ----------
TRANS = 0.55
def render(i, src):
    t = i / FPS
    si = seg_index(t)
    seg = SEGS[si]
    prev = SEGS[si - 1] if si > 0 else seg
    lt = t - seg["t"]
    k = spring(lt, w=14, z=0.82) if si > 0 else 1.0
    canvas = BG.copy()

    # media: previous (fading) underneath, then current
    fade_in = ease_io(lt / 0.25) if si > 0 else 1.0
    if prev is not seg and prev["media"] is not None and fade_in < 1:
        x, y, w, h, r = prev["mrect"]
        pm = media_image(prev, t, int(w), int(h))
        if r > 0:
            fx, fy = float_offset(t, 1.3, 3.0)
            draw_window(canvas, pm, (x + fx, y + fy, w, h, r), 1 - fade_in, shadow=False)
        else:
            canvas.paste(pm, (int(x), int(y)))
    if seg["media"] is not None:
        x, y, w, h, r = seg["mrect"]
        pre = prev["mrect"] if (prev["media"] is not None and prev is not seg) else seg["mrect"]
        rect = lerp_rect(pre, seg["mrect"], clamp(k))   # moves in lockstep with the expert half
        x, y, w, h, r = rect
        sc = lerp(1.12, 1.0, ease_out(lt / 0.6))
        mi = media_image(seg, t, int(w), int(h))
        if sc != 1.0:
            mi = mi.resize((int(w * sc), int(h * sc)), Image.BILINEAR).crop(
                (int(w * (sc - 1) / 2), int(h * (sc - 1) / 2), int(w * (sc - 1) / 2) + int(w), int(h * (sc - 1) / 2) + int(h)))
        if r > 0.5:
            fx, fy = float_offset(t, 1.3, 3.0)
            draw_window(canvas, mi, (x + fx, y + fy, w, h, r), fade_in)
        else:
            m = Image.new("L", (int(w), int(h)), int(255 * fade_in))
            canvas.paste(mi, (int(x), int(y)), m)
        if seg["mrect"] == FULL:
            canvas.alpha_composite(SCRIM_BOTTOM)
        if seg["mrect"] in (FULL, TOPH) and seg["media"][0] != "photo":
            canvas.alpha_composite(SCRIM_TOP)
        canvas.alpha_composite(VIG)

    # speaker frame morph
    srect = lerp_rect(prev["spk"], seg["spk"], k)
    z = lerp(prev["z"], seg["z"], k)
    if si == 0:  # intro: expert half slides up into place
        k0 = spring(t - 0.05, w=9, z=0.85)
        srect = (0, lerp(H, H / 2, k0), W, H / 2, 0)
    x, y, w, h, r = srect
    if seg["spk"] == FULL:
        z *= 1 + 0.05 * clamp(lt / 5.0)
    if y < H - 2:
        spk = speaker_crop(src, int(w), int(h), z)
        # soft shadow cast upward onto the upper half, then a hairline seam
        sh = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        sh.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 60) ** 2 * 120)[:, None], W, 1).astype(np.uint8)))
        canvas.alpha_composite(sh, (0, int(y) - 60))
        canvas.paste(spk.convert("RGB"), (int(x), int(y)))
        if y > 4:
            ImageDraw.Draw(canvas).line((0, int(y), W, int(y)), fill=(255, 236, 214, 70), width=2)
        if seg["spk"] == FULL and y < 200:
            sa = clamp(lt / 0.5)
            sc = SCRIM_SUB if sa >= 1 else Image.fromarray(np.dstack([np.array(SCRIM_SUB)[..., :3], (np.array(SCRIM_SUB)[..., 3] * sa).astype(np.uint8)]))
            canvas.alpha_composite(sc)

    bi = None
    for j, (bt, _, _) in enumerate(BULLETS):
        if t >= bt: bi = j
    if bi is not None:
        end = BULLETS[bi + 1][0] if bi + 1 < len(BULLETS) else T_OUTRO
        if bi in SUBS: kinetic_sub(canvas, t, SUBS[bi])
        elif t < T_OUTRO: caption(canvas, bi, t)

    intro(canvas, t)
    outro(canvas, t)
    return canvas.convert("RGB")

# ---------- run ----------
def decode(start_frame):
    ss = start_frame / FPS
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-i", SRC, "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

if sys.argv[5] == "preview":
    times = [float(x) for x in sys.argv[6].split(",")]
    for tt in times:
        fi = int(tt * FPS)
        p = decode(min(fi, SRC_FRAMES - 1))
        img = Image.frombytes("RGB", (SW, SH), p.stdout.read(SW * SH * 3)); p.kill()
        render(fi, img).save(f"{OUT}_{tt:05.2f}.png")
    sys.exit(0)

a, b = int(sys.argv[5]), min(int(sys.argv[6]), N)
dec = decode(a) if a < SRC_FRAMES else None
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", OUT + ".mp4"], stdin=subprocess.PIPE)
last = None
for i in range(a, b):
    if dec is not None and i < SRC_FRAMES:
        buf = dec.stdout.read(SW * SH * 3)
        if len(buf) == SW * SH * 3: last = Image.frombytes("RGB", (SW, SH), buf)
    if last is None:
        p = decode(SRC_FRAMES - 2); last = Image.frombytes("RGB", (SW, SH), p.stdout.read(SW * SH * 3)); p.kill()
    enc.stdin.write(render(i, last).tobytes())
enc.stdin.close(); enc.wait()
if dec: dec.kill()
print("done", a, b)
