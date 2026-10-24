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
TOP = (0, 0, W, H / 2 - 4, 0)
BOT = (0, H / 2 + 4, W, H / 2 - 4, 0)
def circle(cx, cy, d): return (cx - d / 2, cy - d / 2, d, d, d / 2)

# segment: start, speaker rect, speaker zoom, media (kind, a, speed) , media rect
SEGS = [
    dict(t=0.0,   spk=circle(540, 1290, 620), z=1.55, media=None),
    dict(t=3.05,  spk=BOT, z=1.05, media=("photo",), mrect=TOP),
    dict(t=8.70,  spk=circle(860, 470, 330), z=1.7, media=("broll", 0.05, 0.53), mrect=FULL),
    dict(t=14.05, spk=(170, 620, 740, 960, 370), z=1.15, media=None),
    dict(t=18.80, spk=TOP, z=1.1, media=("broll", 8.12, 0.37), mrect=BOT),
    dict(t=23.90, spk=circle(230, 470, 330), z=1.7, media=("broll", 2.95, 0.6), mrect=FULL),
    dict(t=28.90, spk=circle(850, 470, 330), z=1.7, media=("broll", 5.98, 0.69), mrect=FULL),
    dict(t=31.90, spk=circle(540, 800, 520), z=1.6, media=None),
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
    cy_t = lerp(250, FACE[1] + 25, clamp((z - 1) / 0.6))
    cx = clamp(FACE[0], rx0 + cw / 2, rx1 - cw / 2)
    cy = clamp(cy_t, ry0 + ch / 2, ry1 - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    im = src.resize((max(2, int(w)), max(2, int(h))), Image.BICUBIC, box=box)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))  # speaker keeps original colors

def rr_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), int(max(0, min(r, (w - 2) / 2, (h - 2) / 2))), fill=255)
    return m

def draw_framed(canvas, im, rect, ring=True, alpha=1.0):
    x, y, w, h, r = rect
    w, h = int(w), int(h)
    if w < 4 or h < 4 or alpha <= 0.01: return
    m = rr_mask(w, h, r)
    if alpha < 1: m = m.point(lambda v: int(v * alpha))
    if r > 4 and ring:   # soft shadow + amber ring for shaped frames
        sh = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((60, 72, 60 + w, 72 + h), int(max(0, min(r, (w - 2) / 2, (h - 2) / 2))), fill=(0, 0, 0, int(150 * alpha)))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)), (int(x) - 60, int(y) - 60))
    canvas.paste(im.convert("RGB"), (int(x), int(y)), m)
    if r > 4 and ring:
        o = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
        ImageDraw.Draw(o).rounded_rectangle((3, 3, w + 12, h + 12), int(max(0, min(r, (w - 2) / 2, (h - 2) / 2))) + 5,
                                            outline=with_alpha(AMBER, alpha), width=6)
        canvas.alpha_composite(o, (int(x) - 8, int(y) - 8))

def media_image(seg, t, w, h):
    kind = seg["media"]
    nxt = [x["t"] for x in SEGS if x["t"] > seg["t"]]
    local = min(t, (nxt[0] - 0.12) if nxt else t) - seg["t"]
    kb = 1.0 + 0.06 * clamp(local / 5.5)
    if kind[0] == "photo":
        src = PHOTO_IM; sw, sh = src.size
        a = w / h
        if a > sw / sh: cw = sw; ch = cw / a
        else: ch = sh; cw = ch * a
        cw /= kb; ch /= kb
        cx, cy = sw * 0.42, sh * 0.36
        cx = clamp(cx, cw / 2, sw - cw / 2); cy = clamp(cy, ch / 2, sh - ch / 2)
        return src.resize((w, h), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    _, a0, speed = kind
    st = min(a0 + local * speed, 9.95)
    src = broll_at(st); sw, sh = src.size
    a = w / h
    if a > sw / sh: cw = sw; ch = cw / a
    else: ch = sh; cw = ch * a
    cw /= kb; ch /= kb
    cx, cy = sw / 2, sh * 0.45
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

# ---------- headline (bullet) ----------
BULLETS = [
    (3.05, "01", "Lug'at boyligi kam"),
    (8.70, "02", "Grammatik muammolar"),
    (14.05, "03", "Til tizimi buzilishi"),
    (18.80, "04", "Ijtimoiy aloqa yaxshi"),
    (23.90, "05", "O'yin faoliyati shakllangan"),
    (28.90, "06", "Ko'z bilan aloqa mavjud"),
]
# where each headline sits (x, y)
HPOS = {0: (70, 640), 1: (70, 1470), 2: (70, 1600), 3: (70, 1000), 4: (70, 1470), 5: (70, 1470)}

def headline(canvas, idx, t):
    t0, num, title = BULLETS[idx]
    end = BULLETS[idx + 1][0] if idx + 1 < len(BULLETS) else 31.9
    exit_t = end - 0.42
    if t < t0 or t > end: return
    x, y = HPOS[idx]
    # number badge: scales in with spin-free pop
    k = spring(t - t0, w=13, z=0.55)
    e = ease_in((t - exit_t) / 0.3) if t > exit_t else 0
    badge = Image.new("RGBA", (150, 96), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.rounded_rectangle((0, 0, 149, 95), 30, fill=AMBER)
    bd.text((75, 49), num, font=dfont("Black", 58), fill=BG0, anchor="mm")
    sc = lerp(0.3, 1.0, k) * (1 - 0.4 * e)
    paste_alpha(canvas, badge, x + 75 - 75 * sc, y + 48 - 48 * sc, clamp(k * 2) * (1 - e), sc)
    # amber rule sweeping
    kk = ease_out((t - t0 - 0.15) / 0.5) * (1 - e)
    ImageDraw.Draw(canvas).rounded_rectangle((x + 172, y + 44, x + 172 + 560 * kk, y + 52), 4,
                                             fill=with_alpha(GOLD, 0.9 * (1 - e)))
    lbl = text_layer("ZRR BELGISI", font("Bold", 28), with_alpha(GOLD, 1))
    paste_alpha(canvas, lbl, x + 172, y - 2, clamp((t - t0 - 0.2) / 0.2) * (1 - e))
    reveal_words(canvas, title.split(), dfont("ExtraBold", 76), x, y + 116, t0 + 0.12, t, CREAM,
                 exit_t=exit_t)

# ---------- bullet animations ----------
def chip(txt, fill, tc, f=None):
    f = f or font("Bold", 44)
    bb = f.getbbox(txt)
    w, h = bb[2] + 56, 86
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 43, fill=fill)
    d.text((w / 2, h / 2 + 2), txt, font=f, fill=tc, anchor="mm")
    return im

def anim_vocab(canvas, t, t0, end):
    """Lug'at boyligi kam: word bubbles appear, most fade out, level meter stays low."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.4)) / 0.35)
    words = ["ona", "olma", "mashina", "kitob", "uy", "suv", "it", "qush", "non", "to'p"]
    pos = [(110, 300), (430, 270), (720, 320), (150, 430), (520, 410), (830, 450), (320, 520), (650, 500), (110, 490), (880, 480)]
    keep = {0, 5, 8}
    for i, (wd, (px, py)) in enumerate(zip(words, pos)):
        k = spring(lt - 0.3 - i * 0.09, w=14, z=0.5)
        fade = 1.0
        if i not in keep:
            fade = 1 - ease_io((lt - 2.0 - i * 0.05) / 0.45)
        a = clamp(k * 1.5) * fade * (1 - out)
        c = chip(wd, with_alpha(BG0, 0.82), CREAM) if i not in keep else chip(wd, AMBER, BG0)
        sc = lerp(0.4, 1.0, k)
        bob = 6 * math.sin(lt * 2.4 + i)
        paste_alpha(canvas, c, px + c.width * (1 - sc) / 2, py + bob + c.height * (1 - sc) / 2, a, sc)
    # meter in the seam card
    k = clamp((lt - 2.4) / 0.4)
    if k > 0:
        x0, y0 = 70, 885
        lbl = text_layer("so'z zaxirasi", font("SemiBold", 34), MUTED)
        paste_alpha(canvas, lbl, x0, y0 - 6, k * (1 - out))
        d = ImageDraw.Draw(canvas)
        for j in range(10):
            on = j < 2
            kj = spring(lt - 2.5 - j * 0.05, w=16, z=0.6)
            col = AMBER if on else (90, 50, 40)
            h = 34 * kj
            bx = x0 + 250 + j * 58
            d.rounded_rectangle((bx, y0 + 20 - h / 2, bx + 40, y0 + 20 + h / 2), 10,
                                fill=with_alpha(col, (1 - out)))

def anim_grammar(canvas, t, t0, end):
    """Grammatik: chips drop in correct order, two swap, last one turns red & shakes."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.4)) / 0.35)
    words = ["Men", "maktabga", "bordim"]
    chips = [chip(w, CREAM, BG0, font("Bold", 50)) for w in words]
    gap = 22
    total = sum(c.width for c in chips) + gap * 2
    xs = []; x = (W - total) / 2
    for c in chips: xs.append(x); x += c.width + gap
    y = 1260
    swap = ease_io((lt - 1.8) / 0.55)
    order_x = list(xs)
    # swap chip0 and chip1 positions (wrong word order)
    tgt0 = xs[0] + chips[1].width + gap
    tgt1 = xs[0]
    order_x[0] = lerp(xs[0], tgt0, swap); order_x[1] = lerp(xs[1], tgt1, swap)
    for i, c in enumerate(chips):
        k = spring(lt - 0.3 - i * 0.12, w=13, z=0.5)
        dy = (1 - k) * -160
        arc = 0
        if i == 0: arc = -70 * math.sin(math.pi * swap)
        if i == 1: arc = 70 * math.sin(math.pi * swap)
        im = c
        if i == 2 and lt > 2.6:
            im = chip("bordi", RED, CREAM, font("Bold", 50))
        shake = 10 * math.sin(lt * 40) * math.exp(-(lt - 2.6) * 4) if (i == 2 and lt > 2.6) else 0
        paste_alpha(canvas, im, order_x[i] + shake, y + dy + arc, clamp(k * 2) * (1 - out))
    if lt > 2.7:
        k = spring(lt - 2.7, w=14, z=0.45)
        xmark = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
        dd = ImageDraw.Draw(xmark)
        dd.ellipse((0, 0, 89, 89), fill=RED)
        dd.line([(28, 28), (62, 62)], fill=CREAM, width=10); dd.line([(62, 28), (28, 62)], fill=CREAM, width=10)
        paste_alpha(canvas, xmark, xs[2] + chips[2].width - 30, y - 50, clamp(k) * (1 - out), lerp(0.3, 1, k))

def anim_chain(canvas, t, t0, end):
    """Til tizimi: tovush — so'z — gap chain; last link breaks."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.4)) / 0.35)
    labels = ["tovush", "so'z", "gap"]
    cxs = [230, 540, 850]; cy = 430
    brk = ease_out((lt - 2.0) / 0.5)
    d = ImageDraw.Draw(canvas)
    # links
    for i in range(2):
        kl = ease_out((lt - 0.6 - i * 0.25) / 0.35)
        x0, x1 = cxs[i] + 95, cxs[i + 1] - 95
        if i == 1 and brk > 0:
            mid = (x0 + x1) / 2
            gap = 40 * brk
            col = with_alpha(RED, 1 - out)
            d.line([(x0, cy), (mid - gap, cy - 18 * brk)], fill=col, width=10)
            d.line([(mid + gap, cy + 18 * brk), (x1, cy)], fill=col, width=10)
        elif kl > 0:
            d.line([(x0, cy), (lerp(x0, x1, kl), cy)], fill=with_alpha(AMBER, 1 - out), width=10)
    for i, (lab, cx) in enumerate(zip(labels, cxs)):
        k = spring(lt - 0.2 - i * 0.18, w=13, z=0.5)
        jit = 0
        if i == 2 and lt > 2.0: jit = 8 * math.sin(lt * 45) * math.exp(-(lt - 2.0) * 3)
        r = 92 * k
        col = RED if (i == 2 and brk > 0.2) else AMBER
        ov = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.ellipse((100 - r, 100 - r, 100 + r, 100 + r), fill=with_alpha(BG1, 0.95), outline=col, width=7)
        if k > 0.6:
            od.text((100, 102), lab, font=font("Bold", 36), fill=CREAM, anchor="mm")
        paste_alpha(canvas, ov, cx - 100 + jit, cy - 100, 1 - out)

def person_icon(col, size=170):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, size - 1, size - 1), fill=with_alpha(BG1, 0.96), outline=col, width=7)
    d.ellipse((size * .36, size * .2, size * .64, size * .48), fill=col)
    d.pieslice((size * .22, size * .52, size * .78, size * 1.05), 180, 360, fill=col)
    return im

def anim_social(canvas, t, t0, end):
    """Ijtimoiy aloqa: two people, dots travel between them, heart pops."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.4)) / 0.35)
    y = 1580
    for i, x in enumerate([250, 830]):
        k = spring(lt - 0.3 - i * 0.15, w=13, z=0.5)
        p = person_icon(GOLD if i == 0 else AMBER)
        paste_alpha(canvas, p, x - 85 * k, y - 85 * k, clamp(k * 2) * (1 - out), k)
    d = ImageDraw.Draw(canvas)
    if lt > 0.9:
        for j in range(6):
            ph = ((lt - 0.9) * 0.8 + j / 6) % 1.0
            px = lerp(350, 730, ph)
            py = y - 30 * math.sin(math.pi * ph)
            a = math.sin(math.pi * ph) * (1 - out)
            d.ellipse((px - 9, py - 9, px + 9, py + 9), fill=with_alpha(GOLD, a))
    if lt > 1.8:
        k = spring(lt - 1.8, w=14, z=0.4)
        s = 70 * k * (1 + 0.06 * math.sin(lt * 7))
        hx, hy = 540, y - 120
        heart = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        hd = ImageDraw.Draw(heart)
        hd.ellipse((100 - s, 100 - s * 0.9, 100, 100 + s * 0.1), fill=RED)
        hd.ellipse((100, 100 - s * 0.9, 100 + s, 100 + s * 0.1), fill=RED)
        hd.polygon([(100 - s * 0.97, 100 - s * 0.2), (100 + s * 0.97, 100 - s * 0.2), (100, 100 + s * 0.95)], fill=RED)
        paste_alpha(canvas, heart, hx - 100, hy - 100, 1 - out)

def anim_blocks(canvas, t, t0, end):
    """O'yin faoliyati: toy blocks drop and stack (bounce)."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.4)) / 0.35)
    base_y = 760; cx = 800
    blocks = [(AMBER, 200, "A"), (RUST, 170, "B"), (GOLD, 140, "C"), (CREAM, 110, "★")]
    y = base_y
    for i, (col, s, ch) in enumerate(blocks):
        st = 0.4 + i * 0.45
        if lt < st: break
        k = spring(lt - st, w=15, z=0.42)
        yy = lerp(y - s - 700, y - s, k)
        rot = (1 - k) * (20 if i % 2 else -20)
        b = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        bd = ImageDraw.Draw(b)
        bd.rounded_rectangle((0, 0, s - 1, s - 1), int(s * 0.18), fill=col)
        bd.text((s / 2, s / 2 + 2), ch, font=dfont("Black", int(s * 0.5)), fill=BG0, anchor="mm")
        b = b.rotate(rot, Image.BICUBIC, expand=True)
        paste_alpha(canvas, b, cx - b.width / 2 + (i % 2) * 14 - 7, yy - (b.height - s) / 2, 1 - out)
        y -= s + 6

def anim_eye(canvas, t, t0, end):
    """Ko'z bilan aloqa: eye opens, iris looks around, blinks; sparkle rays."""
    lt = t - t0
    if lt < 0 or t > end: return
    out = ease_in((t - (end - 0.35)) / 0.3)
    cx, cy = 330, 520
    k = spring(lt - 0.2, w=12, z=0.55)
    blink = 1.0
    for bt in (1.3, 2.3):
        if bt < lt < bt + 0.22: blink = abs(math.cos((lt - bt) / 0.22 * math.pi))
    ew, eh = 300 * k, 170 * k * blink
    im = Image.new("RGBA", (400, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 200, 150
    if ew > 4 and eh > 2:
        d.ellipse((ox - ew / 2, oy - eh / 2, ox + ew / 2, oy + eh / 2), fill=CREAM, outline=AMBER, width=8)
        look = 30 * math.sin(lt * 1.6)
        ir = min(62 * k, eh / 2 - 2)
        if ir > 2:
            d.ellipse((ox + look - ir, oy - ir, ox + look + ir, oy + ir), fill=RUST)
            d.ellipse((ox + look - ir * .45, oy - ir * .45, ox + look + ir * .45, oy + ir * .45), fill=BG0)
            d.ellipse((ox + look + ir * .15, oy - ir * .55, ox + look + ir * .45, oy - ir * .25), fill=CREAM)
    for j in range(7):
        ang = math.pi + j * math.pi / 6
        kr = ease_out((lt - 0.6 - j * 0.04) / 0.3)
        r0, r1 = 190, 190 + 40 * kr
        d.line([(ox + r0 * math.cos(ang) * 0.95, oy + r0 * math.sin(ang) * 0.75),
                (ox + r1 * math.cos(ang) * 0.95, oy + r1 * math.sin(ang) * 0.75)], fill=with_alpha(GOLD, kr), width=8)
    paste_alpha(canvas, im, cx - 200, cy - 150, 1 - out)

ANIMS = [anim_vocab, anim_grammar, anim_chain, anim_social, anim_blocks, anim_eye]

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
    nm = text_layer("Muslima Usmaan", font("Bold", 44), CREAM)
    rl = text_layer("Defektolog-Logoped, ABA-terapist", font("Medium", 32), MUTED)
    a = clamp(k * 2) * (1 - ex)
    paste_alpha(canvas, nm, 540 - nm.width / 2, 1630 + (1 - k) * 40, a)
    paste_alpha(canvas, rl, 540 - rl.width / 2, 1690 + (1 - k) * 40, a)

def outro(canvas, t):
    t0 = 31.9
    if t < t0: return
    k = spring(t - t0 - 0.2, w=12, z=0.65)
    nm = text_layer("Muslima Usmaan", font("Bold", 58), CREAM)
    rl = text_layer("Defektolog-Logoped, ABA-terapist", font("Medium", 36), GOLD)
    paste_alpha(canvas, nm, 540 - nm.width / 2, 1110 + (1 - k) * 50, clamp(k * 2))
    k2 = spring(t - t0 - 0.35, w=12, z=0.65)
    paste_alpha(canvas, rl, 540 - rl.width / 2, 1195 + (1 - k2) * 50, clamp(k2 * 2))
    kk = ease_out((t - t0 - 0.45) / 0.4)
    ImageDraw.Draw(canvas).rounded_rectangle((540 - 160 * kk, 1270, 540 + 160 * kk, 1278), 4, fill=AMBER)

# ---------- frame ----------
TRANS = 0.55
def render(i, src):
    t = i / FPS
    si = seg_index(t)
    seg = SEGS[si]
    prev = SEGS[si - 1] if si > 0 else seg
    lt = t - seg["t"]
    k = spring(lt, w=10, z=0.78) if si > 0 else 1.0
    canvas = BG.copy()

    # media: previous (fading) underneath, then current
    fade_in = ease_io(lt / 0.35) if si > 0 else 1.0
    if prev is not seg and prev["media"] is not None and fade_in < 1:
        x, y, w, h, r = prev["mrect"]
        canvas.paste(media_image(prev, t, int(w), int(h)), (int(x), int(y)))
    if seg["media"] is not None:
        x, y, w, h, r = seg["mrect"]
        pre = prev["mrect"] if (prev["media"] is not None and prev is not seg) else seg["mrect"]
        rect = lerp_rect(pre, seg["mrect"], ease_io(lt / 0.45))
        x, y, w, h, r = rect
        sc = lerp(1.12, 1.0, ease_out(lt / 0.6))
        mi = media_image(seg, t, int(w), int(h))
        if sc != 1.0:
            mi = mi.resize((int(w * sc), int(h * sc)), Image.BILINEAR).crop(
                (int(w * (sc - 1) / 2), int(h * (sc - 1) / 2), int(w * (sc - 1) / 2) + int(w), int(h * (sc - 1) / 2) + int(h)))
        m = Image.new("L", (int(w), int(h)), int(255 * fade_in))
        canvas.paste(mi, (int(x), int(y)), m)
        if seg["mrect"] == FULL:
            canvas.alpha_composite(SCRIM_BOTTOM)
            canvas.alpha_composite(SCRIM_TOP)
        canvas.alpha_composite(VIG)

    # speaker frame morph
    srect = lerp_rect(prev["spk"], seg["spk"], k)
    z = lerp(prev["z"], seg["z"], k)
    if si == 0:  # intro pop
        k0 = spring(t - 0.05, w=11, z=0.6)
        cx, cy, d = 540, 1290, 620 * lerp(0.6, 1.0, k0)
        srect = circle(cx, cy + (1 - k0) * 80, d)
    x, y, w, h, r = srect
    spk = speaker_crop(src, int(w), int(h), z)
    ring = r > 4
    draw_framed(canvas, spk, (x, y, w, h, r), ring=ring, alpha=1.0 if si > 0 else clamp((t - 0.05) / 0.2))

    # seam between 50/50 halves
    if seg["spk"] in (TOP, BOT) and k > 0.3:
        kk = ease_out((lt - 0.2) / 0.4)
        ImageDraw.Draw(canvas).rectangle((W / 2 - W / 2 * kk, H / 2 - 4, W / 2 + W / 2 * kk, H / 2 + 4), fill=AMBER)

    # 50/50 headline card at the seam
    bi = None
    for j, (bt, _, _) in enumerate(BULLETS):
        if t >= bt: bi = j
    if bi is not None and bi in (0, 3) and t < (BULLETS[bi + 1][0] if bi + 1 < len(BULLETS) else 99):
        end = BULLETS[bi + 1][0]
        ka = ease_out((t - BULLETS[bi][0]) / 0.35) * (1 - ease_in((t - end + 0.42) / 0.35))
        if ka > 0:
            card_h = 362 if bi == 0 else 300
            cy0 = 596 if bi == 0 else 964
            ov = Image.new("RGBA", (W, card_h), with_alpha(BG0, 0.86 * ka))
            canvas.alpha_composite(ov, (0, int(cy0)))
            ImageDraw.Draw(canvas).rectangle((0, cy0, W * ka, cy0 + 6), fill=AMBER)

    if bi is not None:
        end = BULLETS[bi + 1][0] if bi + 1 < len(BULLETS) else 31.9
        ANIMS[bi](canvas, t, BULLETS[bi][0], end)
        headline(canvas, bi, t)

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
