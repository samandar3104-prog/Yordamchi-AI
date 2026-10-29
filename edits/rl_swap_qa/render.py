#!/usr/bin/env python3
"""Neuropsychologist Q&A reel: 50/50 + varied expert framing + flat cartoon panels.

usage: render.py SRC.mov OUT_PREFIX START END | render.py SRC.mov OUT preview T1,T2
"""
import math
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
SW, SH = 480, 854
N = 1468
HALF = H // 2

BG0 = (16, 8, 6); BG1 = (52, 22, 14)
CREAM = (247, 233, 210); MUTED = (150, 118, 98)
AMBER = (232, 160, 58); GOLD = (246, 198, 92); TERRA = (217, 119, 87); WARN = (205, 92, 66)
SKIN = (238, 192, 158); SKIN_D = (214, 160, 126); HAIR = (46, 30, 24); SHIRT = (88, 120, 168)
WOOD = (120, 74, 50); WOOD_D = (92, 54, 36); PAPER = (250, 240, 222)

FD = "/usr/share/fonts/opentype/inter/"
@lru_cache(None)
def font(w, s): return ImageFont.truetype(FD + f"Inter-{w}.otf", s)
@lru_cache(None)
def dfont(w, s): return ImageFont.truetype(FD + f"InterDisplay-{w}.otf", s)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def spring(t, w=12.0, z=0.6):
    if t <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in(t): t = clamp(t); return t ** 3
def ease_io(t): t = clamp(t); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def rgba(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))

def radial(w, h, cx, cy, r, c0, c1):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = np.clip(1 - np.sqrt(((xx - cx) / r) ** 2 + ((yy - cy) / r) ** 2), 0, 1) ** 1.5
    img = np.array(c0, np.float32)[None, None] + (np.array(c1, np.float32) - np.array(c0, np.float32))[None, None] * g[..., None]
    return Image.fromarray(np.uint8(np.clip(img, 0, 255))).convert("RGBA")
BG = radial(W, H, 320, 600, 1100, BG0, (70, 30, 18))
PANEL_BG = radial(W, HALF, 540, 760, 820, (22, 11, 8), (84, 38, 22))

def scrim_top(h=780, a=0.7):
    al = np.clip(1 - np.arange(H) / h, 0, 1) ** 1.7 * a * 255
    v = np.zeros((H, W, 4), np.uint8); v[..., :3] = BG0; v[..., 3] = al[:, None].astype(np.uint8)
    return Image.fromarray(v)
SCRIM = scrim_top()

def text_layer(txt, f, fill, pad=10):
    bb = f.getbbox(txt)
    im = Image.new("RGBA", (bb[2] + pad * 2, bb[3] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad, pad), txt, font=f, fill=fill)
    return im

def paste_alpha(canvas, im, x, y, alpha=1.0, scale=1.0):
    if im is None or alpha <= 0.01 or scale <= 0.01: return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(im, (int(x), int(y)))

def shadowed(lay, blur=8, strength=0.9):
    pad = blur * 2
    out = Image.new("RGBA", (lay.width + pad * 2, lay.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, BG0 + (0,))
    a = Image.new("L", out.size, 0); a.paste(lay.getchannel("A"), (pad, pad + 3))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * strength * 1.5))))
    out.alpha_composite(sh); out.alpha_composite(lay, (pad, pad))
    return out

@lru_cache(maxsize=8)
def glow(size, col):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dd = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    v = np.zeros((size, size, 4), np.uint8); v[..., :3] = col; v[..., 3] = (np.clip(1 - dd, 0, 1) ** 2.2 * 180).astype(np.uint8)
    return Image.fromarray(v)

# ---------------- captions ----------------
CAP_X, CAP_Y = 64, 300
STY = {"thin": (lambda: font("Light", 56), 76), "bold": (lambda: dfont("SemiBold", 80), 100)}
CAPTIONS = [  # lines [(text, style, t_in)], t_out
    ([("1 daqiqada", "thin", 0.05), ("1 savolga javob", "bold", 0.64)], 1.95),
    ([("Savollarga oldindan", "thin", 2.02), ("tayyorlanmaganman", "bold", 2.68)], 4.25),
    ([("Assalomu alaykum,", "thin", 4.44), ("o'g'lim 7 yoshda", "bold", 5.40)], 7.00),
    ([("Tengdoshlaridan", "thin", 7.06), ("orqada qolyapti", "bold", 8.18)], 9.35),
    ([("Harflarni", "thin", 9.40), ("eslab qololmayapti", "bold", 10.44)], 11.75),
    ([("Bola harflarni", "thin", 12.22), ("eslab qololmasa", "bold", 13.30)], 14.95),
    ([("faqat «orqada qolyapti»", "thin", 15.06), ("deb xulosa qilmang", "bold", 15.40)], 17.30),
    ([("Boshqa rivojlanish", "thin", 17.42), ("sohalarini tekshiring", "bold", 18.66)], 20.55),
    ([("Intellekt, tafakkur,", "thin", 20.72), ("tasavvur", "bold", 22.48)], 23.85),
    ([("Harflarni eslab qololmasa —", "thin", 23.98), ("xotirasi sust", "bold", 26.68), ("bo'lishi mumkin", "thin", 27.40)], 28.05),
    ([("Buning uchun", "thin", 28.18), ("neyropsixolog", "bold", 29.30), ("mashg'ulotlariga boring", "thin", 30.06)], 31.40),
    ([("Natija —", "thin", 31.52), ("yaxshi va ijobiy", "bold", 31.96)], 33.85),
    ([("Sahifamga hali", "thin", 34.02), ("obuna bo'lmagan bo'lsangiz,", "thin", 35.26), ("tezroq obuna bo'ling", "bold", 36.42)], 37.30),
    ([("chunki ota-onalar uchun", "thin", 37.40), ("foydali tavsiyalar", "bold", 39.46), ("berib boraman", "thin", 40.72)], 99),
]

@lru_cache(maxsize=64)
def cap_layer(txt, style):
    return shadowed(text_layer(txt, STY[style][0](), CREAM, pad=8))

def rise_words(canvas, text, style, x, y, t0, t, out):
    f = STY[style][0](); lh = STY[style][1]
    cx = x
    for i, wd in enumerate(text.split(" ")):
        lay = cap_layer(wd, style)
        tt = t - t0 - i * 0.06
        if tt > 0:
            k = spring(tt, w=14, z=0.82)
            off = (1 - k) * lh * 0.85 + out * 26
            clip = Image.new("RGBA", (lay.width, lay.height + 4), (0, 0, 0, 0))
            clip.alpha_composite(lay, (0, int(max(-lay.height, min(lay.height, off)))))
            paste_alpha(canvas, clip, cx, y, clamp(tt / 0.14) * (1 - out))
        cx += f.getlength(wd + " ")

def draw_captions(canvas, t):
    for lines, t_out in CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.35: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        y = CAP_Y
        x0 = CAP_X + (92 if lines[0][0] == "1 daqiqada" else 0)
        for i, (txt, style, t_in) in enumerate(lines):
            rise_words(canvas, txt, style, x0 if i == 0 else CAP_X, y, t_in, t, out)
            y += STY[style][1]
    stopwatch(canvas, t)

def stopwatch(canvas, t):
    if t > 2.3: return
    out = ease_in((t - 1.95) / 0.3) if t > 1.95 else 0.0
    k = spring(t - 0.02, w=11, z=0.55) * (1 - out)
    if k <= 0.01: return
    s = 160
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; r = 52
    d.rounded_rectangle((c - 10, c - r - 22, c + 10, c - r - 8), 4, fill=CREAM)
    d.ellipse((c - r, c - r, c + r, c + r), outline=CREAM, width=7)
    sweep = (t * 160) % 360
    d.pieslice((c - r + 12, c - r + 12, c + r - 12, c + r - 12), -90, -90 + sweep, fill=TERRA)
    ang = math.radians(-90 + sweep)
    d.line([(c, c), (c + (r - 14) * math.cos(ang), c + (r - 14) * math.sin(ang))], fill=CREAM, width=5)
    d.ellipse((c - 6, c - 6, c + 6, c + 6), fill=CREAM)
    im = im.rotate((1 - k) * 90, Image.BICUBIC)
    sc = 0.62 * k
    paste_alpha(canvas, shadowed(im, 6), CAP_X - 12 - s * sc * 0.0, CAP_Y - 6, clamp(k * 1.5), sc)

# ---------------- expert ----------------
FACE_Y = 337
def expert_crop(src, w, h, z=1.0, face_at=0.40, dx=0.0):
    a = w / h
    cw = min(SW, SH * a) / z; ch = cw / a
    cx = SW / 2 + dx
    top = FACE_Y - face_at * ch
    cx = clamp(cx, cw / 2, SW - cw / 2); top = clamp(top, 0, SH - ch)
    return src.resize((int(w), int(h)), Image.BICUBIC, box=(cx - cw / 2, top, cx + cw / 2, top + ch)).convert("RGBA")

# ---------------- cartoon primitives (drawn at 2x then downsampled) ----------------
SS = 2
def P(v): return v * SS

def kid(d, cx, cy, s, t, mood="neutral", look=0.0, blink_t=(), shirt=SHIRT):
    """Flat-style 7-year-old: head + hair + face, shoulders. cx,cy = head centre."""
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    # body
    d.rounded_rectangle((X - S(120), Y + S(92), X + S(120), Y + S(330)), int(S(70)), fill=shirt)
    d.polygon([(X - S(34), Y + S(92)), (X + S(34), Y + S(92)), (X, Y + S(140))], fill=PAPER)
    d.rectangle((X - S(26), Y + S(70), X + S(26), Y + S(104)), fill=SKIN_D)
    # ears
    for sx in (-1, 1):
        d.ellipse((X + sx * S(92) - S(20), Y - S(12), X + sx * S(92) + S(20), Y + S(34)), fill=SKIN_D)
    # head
    d.ellipse((X - S(95), Y - S(105), X + S(95), Y + S(100)), fill=SKIN)
    # hair
    d.chord((X - S(100), Y - S(122), X + S(100), Y + S(40)), 180, 360, fill=HAIR)
    d.polygon([(X - S(96), Y - S(30)), (X - S(40), Y - S(70)), (X + S(10), Y - S(46)), (X + S(60), Y - S(72)), (X + S(98), Y - S(30)), (X + S(98), Y - S(52)), (X - S(96), Y - S(52))], fill=HAIR)
    # eyes
    bl = 1.0
    for bt in blink_t:
        if bt <= t < bt + 0.16: bl = abs(math.cos((t - bt) / 0.16 * math.pi))
    for sx in (-1, 1):
        ex, ey = X + sx * S(36) + S(6) * look, Y + S(12)
        hgt = max(S(2), S(15) * bl)
        d.ellipse((ex - S(11), ey - hgt, ex + S(11), ey + hgt), fill=HAIR)
        if bl > 0.6: d.ellipse((ex - S(3) + S(4), ey - S(8), ex + S(4) + S(4), ey - S(1)), fill=CREAM)
        # brows
        tilt = {"worried": 10, "happy": -4, "neutral": 0, "think": 6 * sx}[mood]
        d.line([(ex - S(16), ey - S(30) - S(tilt * sx * 0.5)), (ex + S(16), ey - S(30) + S(tilt * sx * 0.5))], fill=HAIR, width=int(S(6)))
    # cheeks
    for sx in (-1, 1):
        d.ellipse((X + sx * S(58) - S(16), Y + S(36), X + sx * S(58) + S(16), Y + S(54)), fill=(236, 160, 140))
    # mouth
    if mood == "happy":
        d.chord((X - S(30), Y + S(34), X + S(30), Y + S(80)), 0, 180, fill=(150, 60, 50))
    elif mood == "worried":
        d.arc((X - S(24), Y + S(56), X + S(24), Y + S(86)), 200, 340, fill=(150, 60, 50), width=int(S(6)))
    else:
        d.line([(X - S(16), Y + S(62)), (X + S(16), Y + S(62))], fill=(150, 60, 50), width=int(S(6)))

def finish(layer):
    return layer.resize((layer.width // SS, layer.height // SS), Image.LANCZOS)

def letter_tile(ch, col, size=90):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, size - 1, size - 1), 20, fill=col)
    d.text((size / 2, size / 2 + 2), ch, font=dfont("Black", int(size * 0.58)), fill=BG0, anchor="mm")
    return im

# ---------------- cartoon scenes (top half, 1080 x 960) ----------------
def cart_letters(lt, t):
    """Q: boy at desk, letters rise from the book, wobble, then slip away."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    mood = "worried" if lt > 3.6 else "neutral"
    kid(d, 540, 640, 0.95, t, mood=mood, look=math.sin(lt * 1.3) * 0.6, blink_t=(lt + t - lt + 1.2, t - lt + 3.3, t - lt + 5.6))
    d.rounded_rectangle((P(120), P(820), P(960), P(880)), P(14), fill=WOOD)
    d.rectangle((P(120), P(860), P(960), P(960)), fill=WOOD_D)
    # open book
    d.polygon([(P(400), P(812)), (P(540), P(790)), (P(540), P(834)), (P(400), P(850))], fill=PAPER)
    d.polygon([(P(680), P(812)), (P(540), P(790)), (P(540), P(834)), (P(680), P(850))], fill=(238, 226, 206))
    c.alpha_composite(finish(L))
    letters = [("A", GOLD, 0.6), ("B", TERRA, 1.1), ("D", CREAM, 1.6), ("O", AMBER, 2.1), ("E", GOLD, 2.6)]
    xs = [300, 430, 560, 690, 800]
    for i, (ch, col, t0) in enumerate(letters):
        u = lt - t0
        if u <= 0: continue
        k = spring(u, w=10, z=0.55)
        y = lerp(800, 610 - (i % 2) * 60, k)
        x = lerp(540, xs[i], k) + 10 * math.sin(lt * 2 + i)
        fade = 0.0
        if lt > 3.6 + i * 0.25:  # slip away and fade (forgotten)
            f_ = ease_in((lt - 3.6 - i * 0.25) / 1.1)
            y -= 140 * f_; x += (i - 2) * 80 * f_; fade = f_
        tile = letter_tile(ch, col).rotate(math.sin(lt * 2.2 + i) * 10, Image.BICUBIC, expand=True)
        paste_alpha(c, tile, x - tile.width / 2, y - tile.height / 2, clamp(k * 2) * (1 - fade), lerp(0.4, 1.0, k))
    if lt > 4.3:  # question mark above the head
        k = spring(lt - 4.3, w=12, z=0.45)
        q = shadowed(text_layer("?", dfont("Black", 120), GOLD), 6)
        paste_alpha(c, q, 650 - q.width / 2, 530 - q.height / 2 + 8 * math.sin(lt * 3), clamp(k * 2), lerp(0.3, 1, k))
    return c

def icon_brain(s, col=TERRA):
    im = Image.new("RGBA", (s * SS, s * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    S = s * SS
    for (x, y, r) in ((0.33, 0.42, 0.22), (0.55, 0.32, 0.22), (0.7, 0.5, 0.2), (0.45, 0.6, 0.22), (0.28, 0.6, 0.16)):
        d.ellipse((S * (x - r), S * (y - r), S * (x + r), S * (y + r)), fill=col)
    d.line([(S * 0.5, S * 0.18), (S * 0.5, S * 0.78)], fill=tuple(int(v * 0.75) for v in col), width=int(S * 0.03))
    for (x0, y0, x1, y1) in ((0.3, 0.4, 0.42, 0.48), (0.6, 0.35, 0.7, 0.45), (0.38, 0.55, 0.48, 0.62)):
        d.arc((S * x0, S * y0, S * x1, S * y1), 180, 360, fill=tuple(int(v * 0.75) for v in col), width=int(S * 0.025))
    return finish(im)

def icon_bulb(s, t):
    im = Image.new("RGBA", (s * SS, s * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    S = s * SS
    d.ellipse((S * 0.28, S * 0.18, S * 0.72, S * 0.62), fill=GOLD)
    d.rounded_rectangle((S * 0.4, S * 0.58, S * 0.6, S * 0.76), int(S * 0.04), fill=(180, 160, 140))
    d.line([(S * 0.42, S * 0.66), (S * 0.58, S * 0.66)], fill=(120, 100, 90), width=int(S * 0.02))
    for i in range(7):
        a = math.radians(200 + i * 23)
        r0, r1 = S * 0.3, S * (0.36 + 0.04 * math.sin(t * 6 + i))
        d.line([(S * 0.5 + r0 * math.cos(a), S * 0.4 + r0 * math.sin(a)), (S * 0.5 + r1 * math.cos(a), S * 0.4 + r1 * math.sin(a))], fill=GOLD, width=int(S * 0.03))
    return finish(im)

def icon_cloud(s, t):
    im = Image.new("RGBA", (s * SS, s * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    S = s * SS
    for (x, y, r) in ((0.32, 0.55, 0.16), (0.5, 0.45, 0.22), (0.68, 0.55, 0.16)):
        d.ellipse((S * (x - r), S * (y - r), S * (x + r), S * (y + r)), fill=CREAM)
    d.rectangle((S * 0.2, S * 0.55, S * 0.8, S * 0.71), fill=CREAM)
    cx, cy, r = S * 0.5, S * 0.52, S * 0.09
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36 + t * 40); rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=AMBER)
    return finish(im)

def thought_bubble(c, x, y, w, h, k, tail_to):
    if k <= 0: return
    lay = Image.new("RGBA", (W, HALF), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    s = k
    d.rounded_rectangle((x - w / 2 * s, y - h / 2 * s, x + w / 2 * s, y + h / 2 * s), int(60 * s), fill=(44, 22, 16, 235), outline=(255, 236, 214, 60), width=2)
    tx, ty = tail_to
    for i, f_ in enumerate((0.35, 0.62, 0.85)):
        bx, by = lerp(x, tx, f_), lerp(y + h / 2 * s, ty, f_)
        r = (14 - i * 4) * s
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=(44, 22, 16, 235))
    c.alpha_composite(lay)

def cart_areas(lt, t):
    """Areas to check: intellect (brain), thinking (bulb), imagination (cloud)."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    kid(d, 540, 800, 0.8, t, mood="think", look=math.sin(lt * 1.5), blink_t=(t - lt + 1.4,))
    c.alpha_composite(finish(L))
    items = [(0.12, 240, icon_brain(150)), (1.00, 540, icon_bulb(150, t)), (1.88, 840, icon_cloud(150, t))]
    for t0, x, ic in items:
        k = spring(lt - t0, w=12, z=0.5) if lt > t0 else 0
        y = 590 + 8 * math.sin(lt * 2 + x)
        thought_bubble(c, x, y, 220, 200, k, (540 + (x - 540) * 0.25, 700))
        if k > 0:
            g = glow(300, TERRA if x == 240 else (GOLD if x == 540 else CREAM))
            gg = g.resize((int(300 * k), int(300 * k)))
            gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.35)))
            c.alpha_composite(gg, (int(x - gg.width / 2), int(y - gg.height / 2)))
            paste_alpha(c, ic, x - 75 * k, y - 75 * k, clamp(k * 1.6), k)
    return c

def cart_memory(lt, t):
    """Weak memory: letters flow into the head and leak out; memory gauge drains."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    drain = ease_io((lt - 2.0) / 1.2)
    kid(d, 470, 700, 1.05, t, mood="worried" if drain > 0.5 else "neutral", look=-0.4, blink_t=(t - lt + 0.9, t - lt + 3.4))
    c.alpha_composite(finish(L))
    for i in range(7):
        u = ((lt * 0.55 + i / 7) % 1.0)
        x = lerp(80, 430, u); y = 600 + 26 * math.sin(u * 7 + i)
        a = math.sin(math.pi * u) * (1 - 0.6 * drain)
        leak = u > 0.72
        tile = letter_tile("ABDEOKM"[i], [GOLD, TERRA, CREAM, AMBER][i % 4], 66)
        if leak and drain > 0.2:
            x = 430 + (u - 0.72) * 600; y += (u - 0.72) * 420; a *= 0.5
        paste_alpha(c, tile, x - 33, y - 33, a)
    # memory gauge (no text)
    gx, gy, gw, gh = 780, 520, 120, 300
    ImageDraw.Draw(c).rounded_rectangle((gx, gy, gx + gw, gy + gh), 26, outline=CREAM, width=6)
    ImageDraw.Draw(c).rounded_rectangle((gx + 36, gy - 22, gx + gw - 36, gy), 8, fill=CREAM)
    lvl = lerp(0.9, 0.22, drain)
    col = tuple(int(lerp(a_, b_, drain)) for a_, b_ in zip((98, 190, 110), WARN))
    fh = (gh - 24) * lvl
    ImageDraw.Draw(c).rounded_rectangle((gx + 12, gy + gh - 12 - fh, gx + gw - 12, gy + gh - 12), 16, fill=col)
    if drain > 0.9 and int(lt * 4) % 2 == 0:
        g = glow(260, WARN); c.alpha_composite(g, (gx + gw // 2 - 130, gy + gh - 160))
    return c

def puzzle_piece(s, col):
    S = s * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((S * 0.15, S * 0.25, S * 0.8, S * 0.9), int(S * 0.08), fill=col)
    d.ellipse((S * 0.38, S * 0.05, S * 0.58, S * 0.3), fill=col)
    d.ellipse((S * 0.72, S * 0.47, S * 0.95, S * 0.68), fill=col)
    return finish(im)

def cart_session(lt, t):
    """Neuropsychologist session: puzzle pieces assemble, growth arrow, happy kid."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    happy = lt > 3.4
    kid(d, 300, 690, 0.8, t, mood="happy" if happy else "think", look=0.8, blink_t=(t - lt + 1.1, t - lt + 4.0))
    # therapist (hijab, red shirt)
    X, Y, s = 790 * SS, 660 * SS, 0.82
    def S(v): return v * s * SS
    d.rounded_rectangle((X - S(130), Y + S(100), X + S(130), Y + S(360)), int(S(70)), fill=(210, 40, 52))
    d.ellipse((X - S(108), Y - S(120), X + S(108), Y + S(130)), fill=(118, 118, 124))
    d.ellipse((X - S(78), Y - S(80), X + S(78), Y + S(88)), fill=SKIN)
    for sx in (-1, 1):
        ex, ey = X + sx * S(30) - S(6), Y + S(4)
        d.ellipse((ex - S(22), ey - S(18), ex + S(22), ey + S(18)), outline=(90, 80, 70), width=int(S(4)))
        d.ellipse((ex - S(6), ey - S(6), ex + S(6), ey + S(6)), fill=HAIR)
    d.arc((X - S(22), Y + S(32), X + S(22), Y + S(62)), 20, 160, fill=(170, 60, 60), width=int(S(6)))
    d.rounded_rectangle((P(80), P(850), P(1000), P(900)), P(14), fill=WOOD)
    d.rectangle((P(80), P(890), P(1000), P(960)), fill=WOOD_D)
    c.alpha_composite(finish(L))
    # puzzle pieces fly from the table into a 2x2 brain-board
    tgt = [(490, 650), (590, 650), (490, 750), (590, 750)]
    src = [(300, 860), (790, 860), (380, 900), (700, 900)]
    cols = [TERRA, GOLD, AMBER, CREAM]
    for i in range(4):
        k = ease_out((lt - 0.3 - i * 0.45) / 0.55)
        x = lerp(src[i][0], tgt[i][0], k); y = lerp(src[i][1], tgt[i][1], k) - 120 * math.sin(math.pi * k)
        pc = puzzle_piece(110, cols[i]).rotate((1 - k) * 90 * (1 if i % 2 else -1), Image.BICUBIC, expand=True)
        paste_alpha(c, pc, x - pc.width / 2, y - pc.height / 2, clamp(lt / 0.3))
    done = ease_out((lt - 2.3) / 0.4)
    if done > 0:
        g = glow(420, GOLD); gg = g.resize((int(420 * done), int(420 * done)))
        gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5)))
        c.alpha_composite(gg, (int(540 - gg.width / 2), int(700 - gg.height / 2)))
    # growth arrow at "ijobiy natija"
    ga = ease_out((lt - 3.4) / 0.8)
    if ga > 0:
        dd = ImageDraw.Draw(c)
        pts = [(380, 830), (450, 790), (510, 805), (580, 730), (650, 740), (720, 660), (790, 600)]
        n = max(2, int(len(pts) * ga + 0.999))
        sub = pts[:n]
        if n < len(pts) or ga < 1:
            fr = (ga * (len(pts) - 1)) % 1 if ga < 1 else 1
            sub = pts[:n - 1] + [(lerp(pts[n - 2][0], pts[n - 1][0], fr if fr > 0 else 1), lerp(pts[n - 2][1], pts[n - 1][1], fr if fr > 0 else 1))]
        dd.line(sub, fill=GOLD, width=10, joint="curve")
        ex, ey = sub[-1]; px, py = sub[-2]
        ang = math.atan2(ey - py, ex - px)
        dd.polygon([(ex + 26 * math.cos(ang), ey + 26 * math.sin(ang)),
                    (ex + 22 * math.cos(ang + 2.4), ey + 22 * math.sin(ang + 2.4)),
                    (ex + 22 * math.cos(ang - 2.4), ey + 22 * math.sin(ang - 2.4))], fill=GOLD)
        for j in range(6):
            u = (lt - 3.9 - j * 0.12) / 0.8
            if 0 < u < 1:
                a = math.radians(j * 60); r = 20 + 60 * u
                dd.ellipse((790 + r * math.cos(a) - 6, 600 + r * math.sin(a) - 6, 790 + r * math.cos(a) + 6, 600 + r * math.sin(a) + 6), fill=rgba(CREAM, 1 - u))
    return c

def cart_follow(lt, t, src):
    """Profile card with follow button being tapped (top half)."""
    c = PANEL_BG.copy()
    k = spring(lt, w=10, z=0.75)
    cw_, ch_ = 820, 300
    x0, y0 = (W - cw_) // 2, int(690 + (1 - k) * 80)
    lay = Image.new("RGBA", (cw_, ch_), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, cw_ - 1, ch_ - 1), 40, fill=(26, 14, 11, 245), outline=(255, 236, 214, 50), width=2)
    av = expert_crop(src, 160, 160, z=2.4, face_at=0.5).convert("RGB")
    m = Image.new("L", (160, 160), 0); ImageDraw.Draw(m).ellipse((0, 0, 159, 159), fill=255)
    ring = Image.new("RGBA", (176, 176), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse((0, 0, 175, 175), outline=TERRA, width=6)
    lay.alpha_composite(ring, (42, 62)); lay.paste(av, (50, 70), m)
    for j, w_ in enumerate((300, 220)):
        d.rounded_rectangle((250, 92 + j * 46, 250 + w_, 112 + j * 46), 10, fill=(70, 44, 34))
    tap = TAP_T - (t - lt)
    pressed = lt >= tap
    bk = ease_out((lt - tap) / 0.25) if pressed else 0
    bx0, by0, bx1, by1 = 250, 200, 760, 264
    col = tuple(int(lerp(a_, b_, bk)) for a_, b_ in zip(TERRA, (64, 44, 38)))
    sq = 1 - 0.06 * math.sin(math.pi * clamp((lt - tap) / 0.2)) if pressed else 1
    cxb, cyb = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw, hh = (bx1 - bx0) / 2 * sq, (by1 - by0) / 2 * sq
    d.rounded_rectangle((cxb - hw, cyb - hh, cxb + hw, cyb + hh), 20, fill=col)
    # check / plus glyph instead of words
    if bk < 0.5:
        d.line([(cxb - 18, cyb), (cxb + 18, cyb)], fill=CREAM, width=7); d.line([(cxb, cyb - 18), (cxb, cyb + 18)], fill=CREAM, width=7)
    else:
        d.line([(cxb - 20, cyb), (cxb - 4, cyb + 16), (cxb + 22, cyb - 14)], fill=CREAM, width=7, joint="curve")
    c.alpha_composite(lay.rotate(0), (x0, y0)) if k >= 0 else None
    # finger tap ripple
    fx, fy = x0 + cxb + 120, y0 + cyb + 40
    if lt < tap + 0.6:
        appear = ease_out((lt - (tap - 0.7)) / 0.5)
        if appear > 0:
            fx2 = lerp(fx + 120, fx, appear); fy2 = lerp(fy + 160, fy, appear)
            dd = ImageDraw.Draw(c)
            dd.ellipse((fx2 - 34, fy2 - 34, fx2 + 34, fy2 + 34), fill=rgba(CREAM, 0.85 * (1 - clamp((lt - tap - 0.3) / 0.3))))
    if pressed:
        u = clamp((lt - tap) / 0.6)
        r = lerp(20, 140, ease_out(u))
        ImageDraw.Draw(c).ellipse((x0 + cxb - r, y0 + cyb - r, x0 + cxb + r, y0 + cyb + r), outline=rgba(CREAM, 0.6 * (1 - u)), width=4)
    # bell wiggle
    bell_k = spring(lt - tap - 0.35, w=12, z=0.5) if lt > tap + 0.35 else 0
    if bell_k > 0:
        b = Image.new("RGBA", (120, 120), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.pieslice((20, 20, 100, 100), 180, 360, fill=GOLD); bd.rectangle((20, 58, 100, 84), fill=GOLD)
        bd.polygon([(12, 84), (108, 84), (96, 70), (24, 70)], fill=GOLD); bd.ellipse((50, 84, 70, 104), fill=GOLD)
        b = b.rotate(18 * math.sin((lt - tap) * 18) * math.exp(-(lt - tap - 0.35) * 3), Image.BICUBIC)
        paste_alpha(c, b, x0 + cw_ - 130, y0 - 70, clamp(bell_k * 2), bell_k)
    return c

PANELS = {"letters": cart_letters, "areas": cart_areas, "memory": cart_memory, "session": cart_session, "follow": cart_follow}

# ---------------- timeline ----------------
# (start, end, layout, panel, expert zoom)
SEG = [
    (0.00, 4.40, "full", None, 1.10),
    (4.40, 11.80, "split", "letters", 1.00),
    (11.80, 20.60, "full", None, 1.00),
    (20.60, 23.90, "split", "areas", 1.18),
    (23.90, 28.15, "split", "memory", 1.00),
    (28.15, 33.90, "split", "session", 1.14),
    (33.90, 37.35, "split", "follow", 1.00),
    (37.35, 99.0, "full", None, 1.16),
]
def seg_at(t):
    for i, s in enumerate(SEG):
        if s[0] <= t < s[1]: return i
    return len(SEG) - 1

PUNCH = [(15.06, 1.10, 17.40), (39.46, 1.06, 99)]
def full_zoom(t, base):
    z = base * (1 + 0.025 * clamp((t % 8) / 8))
    if t < 0.35: z *= lerp(1.3, 1.0, ease_out(t / 0.35))
    for t0, amt, t1 in PUNCH:
        if t0 <= t < t1: z *= lerp(1.0, amt, spring(t - t0, w=9, z=0.8))
    return z

def expert_layer(src, t, rect, z):
    x, y, w, h = rect
    if h < 4: return None
    return expert_crop(src, int(w), int(h), z=z, face_at=0.40 if h > HALF + 100 else 0.36)

TR = 0.42
def render(i, src):
    t = i / FPS
    si = seg_at(t)
    a, b, lay, panel, zb = SEG[si]
    lt = t - a
    prev = SEG[si - 1] if si > 0 else None
    c = BG.copy()
    # expert rect
    full_r, split_r = (0, 0, W, H), (0, HALF, W, HALF)
    cur_r = full_r if lay == "full" else split_r
    k = ease_io(lt / TR) if prev is not None else 1.0
    if prev is not None and k < 1:
        pr = full_r if prev[2] == "full" else split_r
        rect = tuple(lerp(p, q, k) for p, q in zip(pr, cur_r))
        zz = lerp(prev[4], zb, k)
    else:
        rect = cur_r; zz = zb
    z = full_zoom(t, zz) if lay == "full" and k >= 1 else zz
    # top panel(s)
    ry = rect[1]
    if ry > 2:
        if panel:
            pim = PANELS[panel](lt, t, src) if panel == "follow" else PANELS[panel](lt, t)
            if prev is not None and prev[3] and k < 1 and prev[3] != panel:
                pp = PANELS[prev[3]](t - prev[0], t, src) if prev[3] == "follow" else PANELS[prev[3]](t - prev[0], t)
                c.alpha_composite(pp, (int(-W * k), 0))
                c.alpha_composite(pim, (int(W * (1 - k)), 0))
            else:
                c.alpha_composite(pim, (0, int(ry - HALF)))
        elif prev is not None and prev[3]:
            pp = PANELS[prev[3]](t - prev[0], t, src) if prev[3] == "follow" else PANELS[prev[3]](t - prev[0], t)
            c.alpha_composite(pp, (0, int(ry - HALF)))
    ex = expert_layer(src, t, rect, z)
    if ex is not None:
        c.alpha_composite(ex, (int(rect[0]), int(rect[1])))
        if rect[1] > 2:
            sh = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
            sh.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 40) ** 2 * 110)[:, None], W, 1).astype(np.uint8)))
            c.alpha_composite(sh, (0, int(rect[1]) - 40))
            ImageDraw.Draw(c).line((0, int(rect[1]), W, int(rect[1])), fill=(255, 236, 214, 70), width=2)
    if lay == "full" or (prev is not None and prev[2] == "full" and k < 1):
        sa = 1.0 if lay == "full" else 1 - k
        if sa > 0:
            s_ = SCRIM if sa >= 1 else Image.fromarray(np.dstack([np.array(SCRIM)[..., :3], (np.array(SCRIM)[..., 3] * sa).astype(np.uint8)]))
            c.alpha_composite(s_)
    # hook flash + impact shake
    fl = 0.0
    if t < 0.12: fl = 0.4 * (1 - t / 0.12)
    if 0.64 <= t < 0.84: fl = max(fl, 0.14 * (1 - (t - 0.64) / 0.2))
    if fl > 0: c.alpha_composite(Image.new("RGBA", (W, H), (255, 214, 170, int(255 * fl))))
    draw_captions(c, t)
    return c.convert("RGB")

# ================= v2 overrides =================
import os
HERE = os.path.dirname(os.path.abspath(__file__))
WHITE = (255, 255, 255)
GREEN = (98, 168, 88)

# ---------- adults ----------
def adult(d, cx, cy, s, t, style, mood="neutral", point=None, blink_t=()):
    """style: mom (light scarf), teacher (bun hair, glasses), doc (navy hijab, white coat)."""
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    coat = {"mom": (196, 120, 150), "teacher": (70, 130, 110), "doc": (244, 244, 246)}[style]
    d.rounded_rectangle((X - S(130), Y + S(100), X + S(130), Y + S(420)), int(S(80)), fill=coat)
    if style == "doc":
        d.polygon([(X - S(40), Y + S(100)), (X + S(40), Y + S(100)), (X, Y + S(190))], fill=(40, 60, 110))
        d.line([(X, Y + S(190)), (X, Y + S(400))], fill=(210, 210, 216), width=int(S(4)))
        d.rounded_rectangle((X + S(40), Y + S(200), X + S(96), Y + S(232)), int(S(6)), fill=(80, 130, 200))
        d.arc((X - S(60), Y + S(110), X + S(20), Y + S(230)), 90, 250, fill=(60, 60, 70), width=int(S(6)))
    if style in ("mom", "doc"):
        sc = (232, 214, 196) if style == "mom" else (40, 60, 110)
        d.ellipse((X - S(110), Y - S(124), X + S(110), Y + S(136)), fill=sc)
        d.ellipse((X - S(76), Y - S(84), X + S(76), Y + S(92)), fill=SKIN)
    else:
        d.ellipse((X - S(40), Y - S(170), X + S(40), Y - S(96)), fill=HAIR)
        d.ellipse((X - S(88), Y - S(100), X + S(88), Y + S(96)), fill=SKIN)
        d.chord((X - S(92), Y - S(112), X + S(92), Y + S(30)), 180, 360, fill=HAIR)
    bl = 1.0
    for bt in blink_t:
        if bt <= t < bt + 0.16: bl = abs(math.cos((t - bt) / 0.16 * math.pi))
    for sx in (-1, 1):
        ex, ey = X + sx * S(30), Y + S(8)
        d.ellipse((ex - S(9), ey - max(S(2), S(12) * bl), ex + S(9), ey + max(S(2), S(12) * bl)), fill=HAIR)
        if style == "teacher":
            d.ellipse((ex - S(22), ey - S(18), ex + S(22), ey + S(18)), outline=(60, 50, 40), width=int(S(4)))
        tilt = {"angry": -12, "neutral": 0, "kind": 4}[mood]
        d.line([(ex - S(15), ey - S(26) + S(tilt * sx * 0.5)), (ex + S(15), ey - S(26) - S(tilt * sx * 0.5))], fill=HAIR, width=int(S(6)))
    if mood == "angry":
        op = 0.5 + 0.5 * abs(math.sin(t * 9))
        d.ellipse((X - S(18), Y + S(46), X + S(18), Y + S(46) + S(26) * op + S(4)), fill=(150, 60, 50))
    elif mood == "kind":
        d.arc((X - S(26), Y + S(36), X + S(26), Y + S(70)), 20, 160, fill=(170, 60, 60), width=int(S(6)))
    else:
        op = abs(math.sin(t * 10)) if style == "mom" else 0
        d.ellipse((X - S(16), Y + S(50), X + S(16), Y + S(56) + S(14) * op), fill=(150, 60, 50))
    if point is not None:
        px, py = point[0] * SS, point[1] * SS
        sx_ = X + (S(110) if px > X else -S(110))
        d.line([(sx_, Y + S(160)), (px, py)], fill=coat, width=int(S(40)))
        d.ellipse((px - S(22), py - S(22), px + S(22), py + S(22)), fill=SKIN)

def speech_bubble(c, x, y, w, h, k, tail, fill=(30, 16, 12, 235)):
    if k <= 0: return
    lay = Image.new("RGBA", (W, HALF), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, cy = x + w / 2, y + h / 2
    ww, hh = w * k, h * k
    d.rounded_rectangle((cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2), int(46 * k), fill=fill, outline=(255, 255, 255, 50), width=2)
    tx, ty = tail
    bx = lerp(cx, tx, 0.55)
    d.polygon([(bx - 30 * k, cy + hh / 2 - 2), (bx + 30 * k, cy + hh / 2 - 2), (lerp(bx, tx, k), lerp(cy + hh / 2, ty, k))], fill=fill)
    c.alpha_composite(lay)

def bubble_words(c, text_lines, x, y, t0, t):
    yy = y
    for li, (txt, style, tin) in enumerate(text_lines):
        f = STY[style][0](); lh = STY[style][1]
        cx = x
        for i, wd in enumerate(txt.split(" ")):
            tt = t - tin - i * 0.07
            if tt > 0:
                k = spring(tt, w=14, z=0.8)
                lay = text_layer(wd, f, WHITE, pad=6)
                paste_alpha(c, lay, cx, yy + (1 - k) * 22, clamp(tt / 0.15), lerp(0.9, 1, k))
            cx += f.getlength(wd + " ")
        yy += lh

def cart_ask(lt, t):
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    k = spring(lt, w=9, z=0.8)
    kid(d, 330 - (1 - k) * 200, 780, 0.62, t, mood="worried", look=1.0, blink_t=(t - lt + 1.5, t - lt + 3.6))
    adult(d, 760 + (1 - k) * 220, 650, 0.78, t if t > 4.44 else 0, "mom", mood="neutral", blink_t=(t - lt + 2.2,))
    c.alpha_composite(finish(L))
    bk = spring(t - 4.40, w=11, z=0.7) if t > 4.40 else 0
    speech_bubble(c, 60, 276, 900, 250, bk, (720, 540))
    if bk > 0.5:
        bubble_words(c, [("Assalomu alaykum,", "thin", 4.44), ("o'g'lim 7 yoshda...", "bold", 5.40)], 104, 316, 4.44, t)
    return c

def cart_race(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    for i in range(3):
        dd.line([(0, 720 + i * 90), (W, 720 + i * 90)], fill=(255, 236, 214, 30), width=3)
    # finish flag
    for r_ in range(6):
        for q in range(2):
            col = CREAM if (r_ + q) % 2 == 0 else BG0
            dd.rectangle((960 + q * 26, 600 + r_ * 26, 986 + q * 26, 626 + r_ * 26), fill=col)
    dd.line([(960, 600), (960, 900)], fill=CREAM, width=6)
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    u = clamp(lt / 2.3)
    ax = lerp(300, 860, ease_out(u)); hx = lerp(120, 380, u)
    bob = lambda ph: 12 * abs(math.sin(lt * 11 + ph))
    kid(d, ax, 650 - bob(0), 0.5, t, mood="happy", look=1.0, shirt=GREEN)
    kid(d, hx, 740 - bob(1.3) * 0.6, 0.5, t, mood="worried", look=1.0, blink_t=(t - lt + 1.0,))
    c.alpha_composite(finish(L))
    for j in range(4):  # dust puffs
        ph = (lt * 2 + j / 4) % 1
        for x0, y0 in ((ax - 70, 820), (hx - 70, 900)):
            r = 10 + 24 * ph
            ImageDraw.Draw(c).ellipse((x0 - ph * 80 - r, y0 - r, x0 - ph * 80 + r, y0 + r), fill=rgba(CREAM, 0.25 * (1 - ph)))
    for j in range(3):  # speed lines behind the leader
        yy = 610 + j * 30
        ImageDraw.Draw(c).line([(ax - 160 - j * 20, yy), (ax - 90, yy)], fill=rgba(CREAM, 0.4), width=4)
    # sweat drop on the hero
    ImageDraw.Draw(c).ellipse((hx + 50, 640 + 10 * math.sin(lt * 6), hx + 66, 662 + 10 * math.sin(lt * 6)), fill=(140, 190, 230))
    return c

def cart_teacher(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    dd.rounded_rectangle((60, 580, 470, 820), 18, fill=(36, 70, 56), outline=WOOD, width=12)
    for i, ch in enumerate("ABD"):
        k = ease_out((lt - 0.2 - i * 0.25) / 0.3)
        if k > 0:
            dd.text((140 + i * 110, 700), ch, font=dfont("SemiBold", 110), fill=rgba(CREAM, 0.9 * k), anchor="mm")
    sh = 6 * math.sin(lt * 40) * (1 if 0.6 < lt % 1.2 < 0.9 else 0)
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    adult(d, 610 + sh, 640, 0.72, t, "teacher", mood="angry", point=(430 + sh, 650))
    kid(d, 900, 790, 0.5, t, mood="worried", look=-1.0, blink_t=(t - lt + 0.8, t - lt + 1.9))
    c.alpha_composite(finish(L))
    pk = 1 + 0.12 * abs(math.sin(lt * 8))
    ex = shadowed(text_layer("!", dfont("Black", 90), GOLD), 5)
    paste_alpha(c, ex, 700 - ex.width * pk / 2, 520, 1.0, pk)
    for j in range(3):  # shake lines around the boy
        a = math.radians(200 + j * 25)
        dd2 = ImageDraw.Draw(c)
        dd2.line([(900 + 90 * math.cos(a), 760 + 90 * math.sin(a)), (900 + 120 * math.cos(a), 760 + 120 * math.sin(a))], fill=rgba(CREAM, 0.6), width=4)
    tear = (lt * 0.8) % 1
    ImageDraw.Draw(c).ellipse((924, 800 + tear * 40, 936, 816 + tear * 40), fill=rgba((140, 190, 230), 1 - tear))
    return c

def cart_inspect(lt, t):
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    kid(d, 540, 780, 0.6, t, mood="neutral", look=math.sin(lt * 2), blink_t=(t - lt + 1.2,))
    c.alpha_composite(finish(L))
    lx = 540 + 260 * math.sin(lt * 1.6); ly = 690 + 60 * math.sin(lt * 3.2)
    icons = [icon_brain(110), icon_bulb(110, t), icon_cloud(110, t)]
    idx = int(lt / 0.95) % 3
    g = glow(300, GOLD); gg = g.resize((260, 260)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5)))
    c.alpha_composite(gg, (int(lx - 130), int(ly - 130)))
    paste_alpha(c, icons[idx], lx - 55, ly - 55)
    dd = ImageDraw.Draw(c)
    dd.ellipse((lx - 100, ly - 100, lx + 100, ly + 100), outline=CREAM, width=12)
    dd.line([(lx + 70, ly + 70), (lx + 150, ly + 150)], fill=WOOD, width=26)
    return c

def card_img(sym, col, flip):
    w, h = 110, 140
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if flip < 0.5:
        d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=(70, 90, 150))
        d.rounded_rectangle((12, 12, w - 13, h - 13), 12, outline=(120, 140, 200), width=4)
    else:
        d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=PAPER)
        d.text((w / 2, h / 2), sym, font=dfont("Black", 70), fill=col, anchor="mm")
    sx = abs(math.cos(flip * math.pi))
    return im.resize((max(2, int(w * sx)), h), Image.BICUBIC)

def cart_session(lt, t):
    """New neuropsychologist (navy hijab, white coat) playing a memory-pairs game with the boy."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    happy = lt > 3.4
    kid(d, 190, 720, 0.62, t, mood="happy" if happy else "think", look=1.0, blink_t=(t - lt + 1.1, t - lt + 4.0))
    adult(d, 890, 640, 0.7, t, "doc", mood="kind", blink_t=(t - lt + 2.0,))
    d.rounded_rectangle((P(60), P(860), P(1020), P(910)), P(14), fill=WOOD)
    d.rectangle((P(60), P(900), P(1020), P(960)), fill=WOOD_D)
    c.alpha_composite(finish(L))
    syms = [("A", TERRA), ("B", GOLD), ("A", TERRA), ("D", GREEN), ("B", GOLD), ("D", GREEN)]
    order = [(0, 2, 0.4), (1, 4, 1.4), (3, 5, 2.4)]   # pairs and when they are flipped
    for i, (sym, col) in enumerate(syms):
        x = 330 + (i % 3) * 140; y = 640 + (i // 3) * 160
        flip = 0.0; matched = 0.0
        for a, b, tf in order:
            if i in (a, b):
                flip = clamp((lt - tf - (0.25 if i == b else 0)) / 0.3)
                matched = ease_out((lt - tf - 0.6) / 0.3)
        ci = card_img(sym, col, flip)
        lift = 14 * matched
        if matched > 0:
            g = glow(220, col); gg = g.resize((200, 200)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.45 * matched)))
            c.alpha_composite(gg, (int(x - 100), int(y - 100 - lift)))
        paste_alpha(c, ci, x - ci.width / 2, y - 70 - lift)
    if lt > 3.4:  # rising stars on "ijobiy natija"
        for j in range(8):
            u = (lt - 3.4 - j * 0.12) / 1.0
            if 0 < u < 1:
                x = 330 + j * 40; y = lerp(760, 560, ease_out(u))
                r = 10 * (1 - u) + 4
                pts = [(x + (r if q % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + q * 36)),
                        y + (r if q % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + q * 36))) for q in range(10)]
                ImageDraw.Draw(c).polygon(pts, fill=rgba(GOLD, 1 - u))
    return c

# ---------- Instagram profile (real account) ----------
PROFILE_SRC = Image.open(os.path.join(HERE, "profile_ig.png")).convert("RGB")
def ig_avatar(size):
    av = PROFILE_SRC.resize((size, size), Image.LANCZOS, box=(112, 190, 412, 490))
    m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0)); out.paste(av, (0, 0), m)
    return out
AVATAR = ig_avatar(170)

def verified(d, x, y, r=16):
    pts = [(x + (r if i % 2 == 0 else r * 0.82) * math.cos(math.radians(i * 22.5)), y + (r if i % 2 == 0 else r * 0.82) * math.sin(math.radians(i * 22.5))) for i in range(16)]
    d.polygon(pts, fill=(0, 149, 246))
    d.line([(x - 7, y), (x - 2, y + 6), (x + 8, y - 6)], fill=WHITE, width=4, joint="curve")

def cart_follow(lt, t, src):
    c = PANEL_BG.copy()
    k = spring(lt, w=10, z=0.78)
    cw_, ch_ = 960, 360
    x0, y0 = (W - cw_) // 2, int(575 + (1 - k) * 80)
    lay = Image.new("RGBA", (cw_, ch_), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, cw_ - 1, ch_ - 1), 36, fill=(12, 16, 20, 248), outline=(255, 255, 255, 40), width=2)
    ring = Image.new("RGBA", (186, 186), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse((0, 0, 185, 185), outline=(80, 80, 80), width=5)
    lay.alpha_composite(ring, (28, 28)); lay.alpha_composite(AVATAR, (36, 36))
    nf = font("SemiBold", 36)
    d.text((240, 52), "logoped_muslimausman", font=nf, fill=WHITE, anchor="lm")
    verified(d, 240 + nf.getlength("logoped_muslimausman") + 26, 52)
    d.text((240, 96), "DEFEKTOLOG | LOGOPED | ABA - TERAPIST", font=font("Regular", 24), fill=(220, 220, 220), anchor="lm")
    tap = TAP_T - (t - lt)
    fol = 40.2 + (0.1 if lt > tap + 0.2 else 0)
    stats = [("393", "nashr"), (f"{fol:.1f}K".replace(".", ","), "obunachi"), ("293", "obuna")]
    sx = 240
    for val, lab in stats:
        d.text((sx, 146), val, font=font("SemiBold", 28), fill=WHITE, anchor="lm")
        sx += font("SemiBold", 28).getlength(val) + 8
        d.text((sx, 147), lab, font=font("Regular", 26), fill=(200, 200, 200), anchor="lm")
        sx += font("Regular", 26).getlength(lab) + 34
    d.text((36, 250), "ZPR, ZRR, Autizm tashxisli bolalarga yordam", font=font("Regular", 25), fill=(225, 225, 225), anchor="lm")
    pressed = lt >= tap
    bk = ease_out((lt - tap) / 0.25) if pressed else 0
    bx0, by0, bx1, by1 = 36, 286, 470, 340
    col = tuple(int(lerp(a_, b_, bk)) for a_, b_ in zip((0, 149, 246), (54, 54, 58)))
    sq = 1 - 0.05 * math.sin(math.pi * clamp((lt - tap) / 0.2)) if pressed else 1
    cxb, cyb = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw, hh = (bx1 - bx0) / 2 * sq, (by1 - by0) / 2 * sq
    d.rounded_rectangle((cxb - hw, cyb - hh, cxb + hw, cyb + hh), 14, fill=col)
    d.text((cxb, cyb), "Obuna bo'lish" if bk < 0.5 else "Obuna bo'lingan  ✓", font=font("SemiBold", 26), fill=WHITE, anchor="mm")
    d.rounded_rectangle((486, 286, 920, 340), 14, fill=(54, 54, 58))
    d.text((703, 313), "Xabar yozish", font=font("SemiBold", 26), fill=WHITE, anchor="mm")
    c.alpha_composite(lay, (x0, y0))
    fx, fy = x0 + cxb + 60, y0 + cyb + 20
    appear = ease_out((lt - (tap - 0.7)) / 0.5)
    if appear > 0 and lt < tap + 0.6:
        fx2 = lerp(fx + 140, fx, appear); fy2 = lerp(fy + 180, fy, appear)
        ImageDraw.Draw(c).ellipse((fx2 - 32, fy2 - 32, fx2 + 32, fy2 + 32), fill=rgba(WHITE, 0.8 * (1 - clamp((lt - tap - 0.3) / 0.3))))
    if pressed:
        u = clamp((lt - tap) / 0.6); r = lerp(20, 150, ease_out(u))
        ImageDraw.Draw(c).ellipse((x0 + cxb - r, y0 + cyb - r, x0 + cxb + r, y0 + cyb + r), outline=rgba(WHITE, 0.6 * (1 - u)), width=4)
    return c

PANELS.update({"ask": cart_ask, "race": cart_race, "teacher": cart_teacher, "inspect": cart_inspect,
               "session": cart_session, "follow": cart_follow})

SEG[:] = [
    (0.00, 2.00, "full", None, 1.10),
    (2.00, 7.05, "split", "ask", 1.00),
    (7.05, 9.38, "split", "race", 1.12),
    (9.38, 11.80, "split", "teacher", 1.00),
    (11.80, 14.75, "full", None, 1.00),
    (14.75, 17.35, "split", "inspect", 1.15),
    (17.35, 20.30, "full", None, 1.04),
    (20.30, 23.90, "split", "areas", 1.18),
    (23.90, 28.15, "split", "memory", 1.00),
    (28.15, 33.90, "split", "session", 1.12),
    (33.90, 38.80, "split", "follow", 1.00),
    (38.80, 99.0, "full", None, 1.12),
]
PUNCH[:] = [(12.22, 1.06, 14.75), (39.46, 1.06, 99)]

CAPTIONS[:] = [
    ([("1 daqiqada", "thin", 0.05), ("1 savolga javob", "bold", 0.64)], 1.90),
    ([("Savollarga oldindan", "thin", 2.02), ("tayyorlanmaganman", "bold", 2.68)], 4.25),
    ([("Tengdoshlaridan", "thin", 7.10), ("orqada qolyapti", "bold", 8.18)], 9.30),
    ([("Harflarni", "thin", 9.42), ("eslab qololmayapti", "bold", 10.44)], 11.72),
    ([("Bola harflarni", "thin", 12.22), ("eslab qololmasa", "bold", 13.30)], 14.68),
    ([("faqat «orqada qolyapti»", "thin", 15.06), ("deb xulosa qilmang", "bold", 15.40)], 17.28),
    ([("Boshqa rivojlanish", "thin", 17.42), ("sohalarini tekshiring", "bold", 18.66)], 20.22),
    ([("Intellekt, tafakkur,", "thin", 20.72), ("tasavvur", "bold", 22.48)], 23.85),
    ([("Harflarni eslab qololmasa —", "thin", 23.98), ("xotirasi sust", "bold", 26.68), ("bo'lishi mumkin", "thin", 27.40)], 28.05),
    ([("Buning uchun", "thin", 28.18), ("neyropsixolog", "bold", 29.30), ("mashg'ulotlariga boring", "thin", 30.06)], 31.40),
    ([("Natija —", "thin", 31.52), ("yaxshi va ijobiy", "bold", 31.96)], 33.85),
    ([("Sahifamga hali", "thin", 34.02), ("obuna bo'lmagan bo'lsangiz,", "thin", 35.26), ("tezroq obuna bo'ling", "bold", 36.42)], 37.30),
    ([("chunki ota-onalar", "thin", 37.40), ("uchun", "thin", 37.90)], 38.72),
    ([("foydali tavsiyalar", "bold", 39.46), ("berib boraman", "thin", 40.72)], 99),
]

@lru_cache(maxsize=96)
def cap_layer(txt, style):
    return shadowed(text_layer(txt, STY[style][0](), WHITE, pad=8))

FULL_CAP_Y = 1390   # below the neck, in front of the chest
def rise_words_c(canvas, text, style, y, t0, t, out):
    f = STY[style][0](); lh = STY[style][1]
    total = f.getlength(text)
    cx = (W - total) / 2 - 16
    for i, wd in enumerate(text.split(" ")):
        lay = cap_layer(wd, style)
        tt = t - t0 - i * 0.06
        if tt > 0:
            k = spring(tt, w=14, z=0.82)
            off = (1 - k) * lh * 0.85 + out * 26
            clip = Image.new("RGBA", (lay.width, lay.height + 4), (0, 0, 0, 0))
            clip.alpha_composite(lay, (0, int(max(-lay.height, min(lay.height, off)))))
            paste_alpha(canvas, clip, cx, y, clamp(tt / 0.14) * (1 - out))
        cx += f.getlength(wd + " ")

def draw_captions(canvas, t):
    for lines, t_out in CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.35: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        full = SEG[seg_at(lines[0][2])][2] == "full"
        y = FULL_CAP_Y if full else CAP_Y
        for txt, style, t_in in lines:
            if full: rise_words_c(canvas, txt, style, y, t_in, t, out)
            else: rise_words(canvas, txt, style, CAP_X, y, t_in, t, out)
            y += STY[style][1]
    stopwatch(canvas, t)

def stopwatch(canvas, t):
    if t > 2.2: return
    out = ease_in((t - 1.9) / 0.3) if t > 1.9 else 0.0
    k = spring(t - 0.02, w=11, z=0.55) * (1 - out)
    if k <= 0.01: return
    s = 160
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; r = 52
    d.rounded_rectangle((c - 10, c - r - 22, c + 10, c - r - 8), 4, fill=WHITE)
    d.ellipse((c - r, c - r, c + r, c + r), outline=WHITE, width=7)
    sweep = (t * 160) % 360
    d.pieslice((c - r + 12, c - r + 12, c + r - 12, c + r - 12), -90, -90 + sweep, fill=TERRA)
    ang = math.radians(-90 + sweep)
    d.line([(c, c), (c + (r - 14) * math.cos(ang), c + (r - 14) * math.sin(ang))], fill=WHITE, width=5)
    im = im.rotate((1 - k) * 90, Image.BICUBIC)
    paste_alpha(canvas, shadowed(im, 6), W / 2 - s * k / 2 - 12, FULL_CAP_Y - 150, clamp(k * 1.5), k)

def bottom_scrim():
    al = np.clip((np.arange(H) - 1000) / 600, 0, 1) ** 1.4 * 0.55 * 255
    v = np.zeros((H, W, 4), np.uint8); v[..., :3] = BG0; v[..., 3] = al[:, None].astype(np.uint8)
    return Image.fromarray(v)
SCRIM = bottom_scrim()

# ================= stuttering reel overrides =================
import sys as _sys
_sys.path.insert(0, HERE)
import story
SEG[:] = story.SEG
TAP_T = story.TAP_T
PUNCH[:] = [(15.36, 1.06, 16.30), (40.12, 1.06, 41.20), (55.58, 1.05, 99)]
PINK = (226, 130, 160)

# ---------- new type system: serif italic typewriter + ExtraBold blur-in ----------
SERIF_I = "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf"
@lru_cache(None)
def serif(s): return ImageFont.truetype(SERIF_I, s)
STY = {"thin": (lambda: serif(70), 88), "bold": (lambda: dfont("ExtraBold", 84), 104)}

@lru_cache(maxsize=512)
def glyph(ch, style):
    return shadowed(text_layer(ch, STY[style][0](), WHITE, pad=6), 6)

@lru_cache(maxsize=256)
def word_img(wd, style):
    return shadowed(text_layer(wd, STY[style][0](), WHITE, pad=8))

def line_width(text, style): return STY[style][0]().getlength(text)

def anim_line(canvas, text, style, x, y, t0, t, out):
    f = STY[style][0]()
    if out > 0:   # exit: drift up + fade
        y -= 24 * out
    a_out = 1 - out
    if style == "thin":            # typewriter, letter by letter
        cps = 34.0
        for i, ch in enumerate(text):
            if ch == " ": continue
            u = (t - t0) * cps - i
            if u <= 0: break
            a = clamp(u / 2.5) * a_out
            g = glyph(ch, style)
            paste_alpha(canvas, g, x + f.getlength(text[:i]) - 12, y + (1 - clamp(u / 2.5)) * 8, a)
    else:                          # words blur-in and settle from a larger scale
        cx = x
        for i, wd in enumerate(text.split(" ")):
            tt = t - t0 - i * 0.09
            lay = word_img(wd, style)
            if tt > 0:
                k = spring(tt, w=13, z=0.78)
                sc = lerp(1.14, 1.0, k)
                im = lay
                if tt < 0.3: im = lay.filter(ImageFilter.GaussianBlur(9 * (1 - tt / 0.3)))
                paste_alpha(canvas, im, cx - 16 - lay.width * (sc - 1) / 2, y - 16 - lay.height * (sc - 1) / 2, clamp(tt / 0.18) * a_out, sc)
            cx += f.getlength(wd + " ")

def draw_captions(canvas, t):
    for lines, t_out, where in story.CAPTIONS:
        if where == "bubble": continue
        if t < lines[0][2] or t > t_out + 0.32: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        full = SEG[seg_at(lines[0][2])][2] == "full"
        total_h = sum(STY[s][1] for _, s, _ in lines)
        y = min(FULL_CAP_Y, 1580 - total_h) if full else CAP_Y
        for txt, style, t_in in lines:
            x = (W - line_width(txt, style)) / 2 if full else CAP_X
            anim_line(canvas, txt, style, x, y, t_in, t, out)
            y += STY[style][1]

def stopwatch(canvas, t): return

# ---------- girl ----------
def girl(d, cx, cy, s, t, mood="neutral", look=0.0, blink_t=(), mouth=None):
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    for sx in (-1, 1):   # pigtails behind the head
        d.ellipse((X + sx * S(118) - S(36), Y - S(10), X + sx * S(118) + S(36), Y + S(90)), fill=HAIR)
    kid(d, cx, cy, s, t, mood=mood, look=look, blink_t=blink_t, shirt=PINK)
    for sx in (-1, 1):
        bx, by = X + sx * S(96), Y - S(40)
        d.polygon([(bx, by), (bx + sx * S(30), by - S(20)), (bx + sx * S(30), by + S(20))], fill=TERRA)
    if mouth == "o":
        d.ellipse((X - S(14), Y + S(52), X + S(14), Y + S(80)), fill=(150, 60, 50))
    elif mouth == "talk":
        op = abs(math.sin(t * 14))
        d.ellipse((X - S(16), Y + S(54), X + S(16), Y + S(60) + S(18) * op), fill=(150, 60, 50))

def adult2(d, cx, cy, s, t, style, **kw):
    if style != "doctor": return adult(d, cx, cy, s, t, style, **kw)
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    d.rounded_rectangle((X - S(130), Y + S(100), X + S(130), Y + S(420)), int(S(80)), fill=(244, 244, 246))
    d.polygon([(X - S(40), Y + S(100)), (X + S(40), Y + S(100)), (X, Y + S(190))], fill=(90, 130, 190))
    d.arc((X - S(60), Y + S(110), X + S(30), Y + S(240)), 80, 260, fill=(60, 60, 70), width=int(S(7)))
    d.ellipse((X - S(86), Y - S(98), X + S(86), Y + S(96)), fill=SKIN)
    d.chord((X - S(90), Y - S(110), X + S(90), Y + S(20)), 180, 360, fill=(70, 60, 56))
    for sx in (-1, 1):
        ex, ey = X + sx * S(30), Y + S(8)
        d.ellipse((ex - S(9), ey - S(11), ex + S(9), ey + S(11)), fill=HAIR)
        d.line([(ex - S(15), ey - S(26)), (ex + S(15), ey - S(26))], fill=(70, 60, 56), width=int(S(6)))
    d.arc((X - S(24), Y + S(38), X + S(24), Y + S(70)), 20, 160, fill=(150, 60, 50), width=int(S(6)))

def panel_layer(): return Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0))

def bubble_small(c, x, y, w, h, k, tail):
    speech_bubble(c, x, y, w, h, k, tail, fill=(250, 240, 222, 245))

# ---------- scenes ----------
def cart_ask(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    k = spring(lt, w=9, z=0.8)
    girl(d, 320 - (1 - k) * 200, 800, 0.6, t, mood="worried", look=1.0, blink_t=(t - lt + 1.3, t - lt + 3.4))
    adult(d, 770 + (1 - k) * 220, 700, 0.74, t if t > 3.78 else 0, "mom", mood="neutral", blink_t=(t - lt + 2.0,))
    c.alpha_composite(finish(L))
    bk = spring(t - 3.72, w=11, z=0.7) if t > 3.72 else 0
    speech_bubble(c, 60, 250, 900, 320, bk, (740, 590))
    if bk > 0.5:
        lines = story.CAPTIONS[2][0]
        y = 282
        for txt, style, tin in lines:
            anim_line(c, txt, style, 104, y, tin, t, 0.0)
            y += STY[style][1]
    return c

def stutter_tiles(c, lt, x0, y0, n=3, size=78):
    for j in range(n):
        u = (lt * 1.6 - j * 0.3) % 1.6
        if u > 1.2: continue
        k = spring(u, w=16, z=0.4)
        jit = 6 * math.sin(lt * 40 + j) * (1 - clamp(u / 0.4))
        tile = letter_tile("M", [GOLD, TERRA, AMBER][j % 3], size)
        paste_alpha(c, tile, x0 + j * (size + 18) + jit, y0, clamp(k * 2) * (1 - clamp((u - 0.9) / 0.3)), lerp(0.5, 1, k))

def cart_stutter(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 300, 780, 0.66, t, mood="worried", look=0.8, blink_t=(t - lt + 1.0, t - lt + 2.6), mouth="talk")
    c.alpha_composite(finish(L))
    k = spring(lt - 0.2, w=11, z=0.7)
    bubble_small(c, 500, 600, 500, 190, k, (390, 760))
    if k > 0.6:
        stutter_tiles(c, lt, 560, 650)
    if lt > 2.3:   # question on mom's mind: "will it pass?" — dots pulse
        for j in range(3):
            a = 0.4 + 0.6 * abs(math.sin(t * 5 + j))
            ImageDraw.Draw(c).ellipse((640 + j * 50, 840, 664 + j * 50, 864), fill=rgba(CREAM, a))
    return c

def syrup_bottle(gray=0.0):
    im = Image.new("RGBA", (120 * SS, 200 * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = tuple(int(lerp(a, b, gray)) for a, b in zip((196, 110, 50), (110, 100, 96)))
    d.rounded_rectangle((P(20), P(50), P(100), P(196)), P(22), fill=col)
    d.rectangle((P(42), P(16), P(78), P(54)), fill=(240, 240, 240))
    d.rounded_rectangle((P(36), P(0), P(84), P(22)), P(6), fill=(230, 80, 70) if gray < 0.5 else (140, 140, 140))
    d.rounded_rectangle((P(30), P(100), P(90), P(150)), P(8), fill=PAPER)
    d.line([(P(42), P(118)), (P(78), P(118))], fill=col, width=P(5)); d.line([(P(42), P(132)), (P(70), P(132))], fill=col, width=P(5))
    return finish(im)

def cart_syrup(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 280, 790, 0.6, t, mood="worried" if lt > 2.8 else "neutral", look=1.0, blink_t=(t - lt + 0.8, t - lt + 3.1), mouth="talk" if lt > 3.0 else None)
    adult2(d, 830, 690, 0.72, t, "doctor")
    c.alpha_composite(finish(L))
    k = ease_out((lt - 1.4) / 0.6)
    gray = ease_io((lt - 2.8) / 0.6)
    bx = lerp(760, 520, k); by = lerp(740, 700, k) - 60 * math.sin(math.pi * k)
    b = syrup_bottle(gray)
    if gray > 0: b = b.rotate(8 * math.sin(lt * 18) * (1 - clamp((lt - 3.4) / 0.4)), Image.BICUBIC, expand=True)
    paste_alpha(c, b, bx - b.width / 2, by - b.height / 2, clamp((lt - 1.2) / 0.3))
    if lt > 3.0:
        kk = spring(lt - 3.0, w=11, z=0.7)
        bubble_small(c, 60, 600, 300, 150, kk, (240, 740))
        if kk > 0.6: stutter_tiles(c, lt, 92, 636, n=2, size=70)
    return c

def storm_cloud(t, size=220):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for (x, y, r) in ((0.3, 0.45, 0.18), (0.52, 0.36, 0.24), (0.72, 0.47, 0.17)):
        d.ellipse((S * (x - r), S * (y - r), S * (x + r), S * (y + r)), fill=(96, 92, 110))
    d.rectangle((S * 0.16, S * 0.45, S * 0.86, S * 0.62), fill=(96, 92, 110))
    if int(t * 6) % 3 != 0:
        d.polygon([(S * 0.52, S * 0.6), (S * 0.42, S * 0.8), (S * 0.52, S * 0.8), (S * 0.44, S * 0.98), (S * 0.66, S * 0.72), (S * 0.55, S * 0.72), (S * 0.62, S * 0.6)], fill=GOLD)
    return finish(im)

def cart_causes(lt, t):
    c = PANEL_BG.copy()
    tf, tn = 19.04 - (t - lt), 20.86 - (t - lt)
    scared = lt > tf
    shake = 5 * math.sin(lt * 50) if tf < lt < tf + 1.5 else 0
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 540 + shake, 790, 0.62, t, mood="worried" if scared else "think", look=-1 if scared and lt < tn else (1 if lt > tn else 0), blink_t=(t - lt + 0.8,))
    c.alpha_composite(finish(L))
    dd = ImageDraw.Draw(c)
    for x in (230, 850):   # placeholders that wait for the causes
        k = ease_out((lt - 0.8) / 0.4)
        if k > 0:
            for a in range(0, 360, 20):
                if (a // 20) % 2: continue
                r = 110
                dd.arc((x - r, 690 - r, x + r, 690 + r), a + lt * 30, a + 10 + lt * 30, fill=rgba(CREAM, 0.35 * k), width=4)
    if lt > tf:
        k = spring(lt - tf, w=11, z=0.5)
        if scared and int(lt * 6) % 3 != 0 and lt < tf + 1.5:
            g = glow(360, GOLD); c.alpha_composite(g.resize((300, 300)), (80, 540))
        paste_alpha(c, storm_cloud(t), 230 - 110 * k, 690 - 110 * k, clamp(k * 2), k)
    if lt > tn:
        k = spring(lt - tn, w=11, z=0.5)
        br = icon_brain(170)
        g = glow(300, TERRA); gg = g.resize((max(1, int(280 * k)), max(1, int(280 * k)))); c.alpha_composite(gg, (int(850 - gg.width / 2), int(690 - gg.height / 2)))
        paste_alpha(c, br, 850 - 85 * k, 690 - 85 * k, clamp(k * 2), k)
        if int(lt * 8) % 2 == 0:
            dd.line([(800, 640), (830, 680), (812, 690), (850, 740)], fill=rgba(GOLD, 0.9), width=6)
    return c

def cart_home(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    dd.rounded_rectangle((90, 590, 330, 800), 16, fill=(30, 40, 70), outline=WOOD, width=10)
    dd.line([(210, 590), (210, 800)], fill=WOOD, width=8); dd.line([(90, 695), (330, 695)], fill=WOOD, width=8)
    dd.ellipse((240, 616, 290, 666), fill=CREAM); dd.ellipse((256, 608, 302, 654), fill=(30, 40, 70))
    pulse = 0.85 + 0.15 * math.sin(lt * 2.2)
    g = glow(520, GOLD); gg = g.resize((int(520 * pulse), int(520 * pulse)))
    c.alpha_composite(gg, (int(900 - gg.width / 2), int(640 - gg.height / 2)))
    dd.polygon([(860, 600), (940, 600), (960, 650), (840, 650)], fill=GOLD)
    dd.line([(900, 650), (900, 900)], fill=WOOD_D, width=8)
    dd.rounded_rectangle((300, 800, 820, 930), 40, fill=(120, 60, 50))
    dd.rounded_rectangle((280, 760, 340, 930), 26, fill=(140, 72, 60)); dd.rounded_rectangle((780, 760, 840, 930), 26, fill=(140, 72, 60))
    L = panel_layer(); d = ImageDraw.Draw(L)
    adult(d, 640, 690, 0.62, t, "mom", mood="kind", blink_t=(t - lt + 1.8, t - lt + 3.9))
    girl(d, 450, 760, 0.52, t, mood="happy", look=1.0, blink_t=(t - lt + 1.0, t - lt + 3.2))
    c.alpha_composite(finish(L))
    for j in range(10):   # calm floating motes
        u = (lt * 0.18 + j / 10) % 1
        x = 120 + j * 90 + 20 * math.sin(lt + j); y = lerp(930, 580, u)
        ImageDraw.Draw(c).ellipse((x - 4, y - 4, x + 4, y + 4), fill=rgba(GOLD, 0.5 * math.sin(math.pi * u)))
    return c

def item_icon(kind, t):
    S = 150 * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if kind == "wand":
        d.line([(S * 0.25, S * 0.8), (S * 0.68, S * 0.37)], fill=(60, 50, 60), width=int(S * 0.08))
        d.line([(S * 0.62, S * 0.43), (S * 0.68, S * 0.37)], fill=CREAM, width=int(S * 0.08))
        cx, cy, r = S * 0.74, S * 0.28, S * 0.14
        pts = [(cx + (r if q % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + q * 36 + t * 60)),
                cy + (r if q % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + q * 36 + t * 60))) for q in range(10)]
        d.polygon(pts, fill=GOLD)
    elif kind == "pills":
        d.rounded_rectangle((S * 0.15, S * 0.4, S * 0.65, S * 0.62), int(S * 0.11), fill=CREAM)
        d.rounded_rectangle((S * 0.4, S * 0.4, S * 0.65, S * 0.62), int(S * 0.11), fill=TERRA)
        d.ellipse((S * 0.55, S * 0.6, S * 0.85, S * 0.9), fill=(230, 230, 236))
        d.line([(S * 0.58, S * 0.75), (S * 0.82, S * 0.75)], fill=(190, 190, 196), width=int(S * 0.03))
    elif kind == "bolt":
        d.polygon([(S * 0.56, S * 0.08), (S * 0.24, S * 0.56), (S * 0.48, S * 0.56), (S * 0.4, S * 0.92), (S * 0.78, S * 0.4), (S * 0.54, S * 0.4)], fill=GOLD)
    elif kind == "scissors":
        for sx in (-1, 1):
            d.ellipse((S * (0.5 + sx * 0.18) - S * 0.12, S * 0.62, S * (0.5 + sx * 0.18) + S * 0.12, S * 0.86), outline=TERRA, width=int(S * 0.06))
        ang = 0.25 + 0.15 * abs(math.sin(t * 6))
        for sx in (-1, 1):
            d.line([(S * 0.5, S * 0.56), (S * 0.5 + sx * S * 0.4 * math.sin(ang), S * 0.56 - S * 0.46 * math.cos(ang))], fill=(210, 210, 220), width=int(S * 0.06))
            d.line([(S * 0.5, S * 0.56), (S * (0.5 + sx * 0.18), S * 0.66)], fill=(210, 210, 220), width=int(S * 0.06))
    return finish(im)

def desat(im, amt):
    if amt <= 0: return im
    g = im.convert("LA").convert("RGBA")
    g.putalpha(im.getchannel("A"))
    return Image.blend(im, g, amt)

def cart_nomagic(lt, t):
    c = PANEL_BG.copy()
    base = t - lt
    items = [("wand", 30.36), ("syrup", 31.22), ("pills", 31.90), ("bolt", 32.84), ("scissors", 34.58)]
    xs = [150, 345, 540, 735, 930]
    fall = ease_in((t - 36.94) / 0.9) if t > 36.94 else 0
    for (kind, ti), x in zip(items, xs):
        u = t - ti
        if u <= 0: continue
        k = spring(u, w=12, z=0.5)
        dead = ease_io((u - 0.9) / 0.5)
        im = syrup_bottle(dead) if kind == "syrup" else item_icon(kind, t)
        if kind == "syrup": im = im.resize((int(im.width * 0.75), int(im.height * 0.75)))
        im = desat(im, dead * 0.9)
        sh = 6 * math.sin(u * 30) * (1 - clamp((u - 0.9) / 0.5)) if 0.9 < u < 1.4 else 0
        y = 700 + 40 * (1 - k) + fall * 300
        if dead < 1:
            g = glow(260, GOLD); gg = g.resize((max(1, int(220 * k)), max(1, int(220 * k))))
            gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5 * (1 - dead))))
            c.alpha_composite(gg, (int(x - gg.width / 2), int(y - gg.height / 2)))
        paste_alpha(c, im, x - im.width * k / 2 + sh, y - im.height * k / 2, clamp(k * 2) * (1 - 0.45 * dead) * (1 - fall), k)
    return c

def pinwheel(t, spin, size=200):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = cy = S / 2
    cols = [TERRA, GOLD, AMBER, CREAM]
    for i in range(4):
        a = math.radians(spin + i * 90)
        p1 = (cx + S * 0.45 * math.cos(a), cy + S * 0.45 * math.sin(a))
        p2 = (cx + S * 0.3 * math.cos(a + 1.2), cy + S * 0.3 * math.sin(a + 1.2))
        d.polygon([(cx, cy), p1, p2], fill=cols[i])
    d.ellipse((cx - S * 0.05, cy - S * 0.05, cx + S * 0.05, cy + S * 0.05), fill=WOOD_D)
    return finish(im)

def cart_exercise(lt, t):
    c = PANEL_BG.copy()
    base = t - lt
    speech = t > 44.48
    L = panel_layer(); d = ImageDraw.Draw(L)
    blow = 42.0 <= t < 44.2 and (t * 0.9) % 1 < 0.6
    girl(d, 290, 790, 0.62, t, mood="happy" if speech else "neutral", look=1.0, blink_t=(base + 1.0,), mouth="o" if blow else ("talk" if speech else None))
    if speech:
        adult(d, 860, 700, 0.66, t, "doc", mood="kind", blink_t=(base + 4.0,))
    c.alpha_composite(finish(L))
    if not speech or t < 44.9:
        fade = 1 - ease_io((t - 44.48) / 0.4)
        spin = (t * 40) + (t - 42.0) * 420 * (1 if t > 42 else 0)
        paste_alpha(c, pinwheel(t, spin), 620, 600, fade)
        ImageDraw.Draw(c).line([(720, 800), (720, 940)], fill=rgba(WOOD, fade), width=10)
        if blow:
            for j in range(5):
                u = ((t * 1.6) + j / 5) % 1
                x = lerp(380, 640, u); y = 770 - 40 * u + 10 * math.sin(u * 9 + j)
                ImageDraw.Draw(c).arc((x - 20, y - 10, x + 20, y + 10), 300, 60, fill=rgba(CREAM, 0.7 * (1 - u)), width=4)
    if speech:
        u = t - 44.48
        for j, syl in enumerate(("MA", "MA")):
            k = spring(u - 0.3 - j * 0.45, w=13, z=0.55) if u > 0.3 + j * 0.45 else 0
            tile = Image.new("RGBA", (130, 110), (0, 0, 0, 0)); td = ImageDraw.Draw(tile)
            td.rounded_rectangle((0, 0, 129, 109), 22, fill=[GOLD, TERRA][j])
            td.text((65, 57), syl, font=dfont("Black", 54), fill=BG0, anchor="mm")
            paste_alpha(c, tile, 470 + j * 160, 620, clamp(k * 2), lerp(0.4, 1, k))
        wk = ease_out((u - 1.4) / 0.8)
        if wk > 0:   # smooth (fluent) speech wave
            pts = [(lerp(450, 780, q / 60), 790 + 22 * math.sin(q / 60 * 12 + t * 4)) for q in range(int(60 * wk) + 1)]
            if len(pts) > 1: ImageDraw.Draw(c).line(pts, fill=GOLD, width=6, joint="curve")
    return c

def cart_logoped(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 300, 790, 0.6, t, mood="happy", look=1.0, blink_t=(t - lt + 1.2, t - lt + 3.4), mouth="talk")
    adult(d, 820, 690, 0.7, t, "doc", mood="kind", blink_t=(t - lt + 2.2,))
    c.alpha_composite(finish(L))
    # clipboard with a ticking plan
    k = spring(lt - 0.2, w=11, z=0.7)
    cb = Image.new("RGBA", (220, 280), (0, 0, 0, 0)); cd = ImageDraw.Draw(cb)
    cd.rounded_rectangle((0, 10, 219, 279), 18, fill=(150, 100, 70)); cd.rounded_rectangle((16, 30, 203, 263), 10, fill=PAPER)
    cd.rounded_rectangle((70, 0, 150, 30), 8, fill=(90, 90, 96))
    for j in range(3):
        yy = 70 + j * 62
        tk = ease_out((lt - 0.8 - j * 0.6) / 0.3)
        cd.rounded_rectangle((34, yy - 16, 66, yy + 16), 6, outline=(120, 110, 100), width=3)
        if tk > 0: cd.line([(40, yy), (48, yy + 9), (62, yy - 10)], fill=rgba(GREEN, tk), width=5)
        cd.rounded_rectangle((80, yy - 6, 80 + 100 * (0.6 + 0.4 * (j % 2)), yy + 6), 6, fill=(200, 186, 170))
    paste_alpha(c, cb, 540 - 110 * k, 640 - 140 * k + (1 - k) * 60, clamp(k * 2), k)
    # fluent speech wave from the girl
    pts = [(lerp(380, 520, q / 40), 720 + 16 * math.sin(q / 40 * 10 + t * 5)) for q in range(41)]
    ImageDraw.Draw(c).line(pts, fill=rgba(GOLD, clamp((lt - 1.2) / 0.4)), width=5, joint="curve")
    return c

PANELS.update({"ask": cart_ask, "stutter": cart_stutter, "syrup": cart_syrup, "causes": cart_causes, "home": cart_home,
               "nomagic": cart_nomagic, "exercise": cart_exercise, "logoped": cart_logoped})

# ---------- bigger characters (head-top kept, body grows downward) ----------
BOOST = 1.3
_kid_raw, _girl_raw, _adult_raw, _adult2_raw = kid, girl, adult, adult2
def kid(d, cx, cy, s, t, **kw): return _kid_raw(d, cx, cy + 105 * s * (BOOST - 1), s * BOOST, t, **kw)
def girl(d, cx, cy, s, t, **kw):
    global kid
    k_ = kid; kid = _kid_raw
    try: _girl_raw(d, cx, cy + 105 * s * (BOOST - 1), s * BOOST, t, **kw)
    finally: kid = k_
def adult(d, cx, cy, s, t, style, **kw): return _adult_raw(d, cx, cy + 124 * s * (BOOST - 1), s * BOOST, t, style, **kw)
def adult2(d, cx, cy, s, t, style, **kw):
    if style != "doctor": return adult(d, cx, cy, s, t, style, **kw)
    return _adult2_raw(d, cx, cy + 110 * s * (BOOST - 1), s * BOOST, t, style, **kw)

# ================= v5: rigged characters, gradient objects, new type + transitions =================
import wave as _wave
_Draw0 = ImageDraw.Draw
def _DrawBlend(im, mode=None): return _Draw0(im, mode or ("RGBA" if im.mode == "RGBA" else None))
ImageDraw.Draw = _DrawBlend
SEG[:] = story.SEG
TAP_T = story.TAP_T
PUNCH[:] = [(12.90, 1.06, 14.30), (26.34, 1.06, 27.30), (38.70, 1.05, 39.80), (52.34, 1.05, 99)]

# ---------- lip-sync envelope from the voice track ----------
def _env():
    w = _wave.open(os.path.join(HERE, "a16.wav"))
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = 16000 // 30
    r = np.array([np.sqrt((x[i * hop:(i + 1) * hop] ** 2).mean()) for i in range(len(x) // hop)])
    r = r / (np.percentile(r, 95) + 1e-6)
    sm = np.convolve(np.clip(r, 0, 1), np.ones(3) / 3, "same")
    return sm
ENV = _env()
def voice(t):
    i = int(t * 30)
    return float(ENV[i]) if 0 <= i < len(ENV) else 0.0

# ---------- type: Inter Display Light tracking-in + Black on a terracotta plate ----------
STY = {"thin": (lambda: dfont("Light", 58), 80), "bold": (lambda: dfont("Black", 74), 104)}

@lru_cache(maxsize=512)
def glyph5(ch): return shadowed(text_layer(ch, dfont("Light", 58), WHITE, pad=6), 6)

@lru_cache(maxsize=64)
def bold_img(text): return text_layer(text, dfont("Black", 74), WHITE, pad=6)

def anim_line(canvas, text, style, x, y, t0, t, out, center=False):
    f = STY[style][0]()
    u = t - t0
    if u <= 0: return
    total = f.getlength(text)
    if style == "thin":
        k = ease_out(u / 0.75)
        track = lerp(16, 0, k)
        width = total + track * (len(text) - 1)
        x0 = (W - width) / 2 if center else x
        lay = Image.new("RGBA", (int(width) + 80, 120), (0, 0, 0, 0))
        for i, ch in enumerate(text):
            if ch == " ": continue
            lay.alpha_composite(glyph5(ch), (int(f.getlength(text[:i]) + track * i) + 10, 0))
        b = (1 - clamp(u / 0.45)) * 7
        if b > 0.4: lay = lay.filter(ImageFilter.GaussianBlur(b))
        paste_alpha(canvas, lay, x0 - 28, y - 14 - 26 * out, clamp(u / 0.35) * (1 - out))
    else:
        x0 = (W - total) / 2 if center else x
        pad, bh = 22, int(f.size * 1.32)
        bk = ease_out(u / 0.42)
        bar = Image.new("RGBA", (int(total) + pad * 2 + 4, bh), (0, 0, 0, 0))
        bw = max(8, int((total + pad * 2) * bk))
        ImageDraw.Draw(bar).rounded_rectangle((0, 0, bw, bh - 1), 18, fill=TERRA + (240,))
        paste_alpha(canvas, bar, x0 - pad, y - 4 - 26 * out, 1 - out)
        tk = spring(u - 0.1, w=13, z=0.8) if u > 0.1 else 0
        if tk > 0:
            lay = bold_img(text)
            off = int((1 - tk) * lay.height * 0.9)
            if off < lay.height:
                clip = Image.new("RGBA", lay.size, (0, 0, 0, 0))
                clip.alpha_composite(lay.crop((0, 0, lay.width, lay.height - off)), (0, off))
                paste_alpha(canvas, clip, x0 - 6, y + 2 - 26 * out, 1 - out)

def draw_captions(canvas, t):
    for lines, t_out in story.CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.32: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        full = SEG[seg_at(lines[0][2])][2] == "full"
        total_h = sum(STY[s][1] for _, s, _ in lines)
        y = min(FULL_CAP_Y, 1586 - total_h) if full else CAP_Y
        for txt, style, t_in in lines:
            anim_line(canvas, txt, style, CAP_X, y, t_in, t, out, center=full)
            y += STY[style][1]

# ---------- rigged characters ----------
def shade(c, f): return tuple(int(clamp(v * f, 0, 255)) for v in c)
LOOK = {
    "mom":   dict(skin=(232, 186, 152), top=(176, 92, 120), head=("hijab", (226, 206, 184)), fem=True),
    "boy":   dict(skin=(238, 196, 160), top=(70, 120, 190), head=("boy", (52, 34, 26)), child=True),
    "gran":  dict(skin=(222, 178, 146), top=(110, 84, 140), head=("gran", (190, 70, 70)), fem=True),
    "logo":  dict(skin=(236, 192, 160), top=(56, 132, 128), head=("hijab", (40, 58, 96)), fem=True, glasses=True),
    "neuro": dict(skin=(214, 170, 136), top=(240, 242, 246), head=("man", (40, 30, 26)), coat=True),
}

def head_img(look, H_, t, talk, mood, eye, blink, seed):
    HS = int(2.6 * H_)
    im = Image.new("RGBA", (HS, HS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = HS / 2, HS * 0.46
    skin = look["skin"]; kind, hc = look["head"]
    child = look.get("child", False)
    fw, fh = (0.5 if child else 0.41) * H_, (0.57 if child else 0.52) * H_
    if kind in ("hijab", "gran"):
        d.ellipse((cx - 0.64 * H_, cy - 0.66 * H_, cx + 0.64 * H_, cy + 0.72 * H_), fill=hc)
        d.polygon([(cx - 0.62 * H_, cy + 0.2 * H_), (cx + 0.62 * H_, cy + 0.2 * H_), (cx + 0.86 * H_, HS), (cx - 0.86 * H_, HS)], fill=hc)
        d.ellipse((cx - 0.62 * H_ + 6, cy + 0.3 * H_, cx + 0.62 * H_ - 6, cy + 1.1 * H_), fill=shade(hc, 0.9))
    if kind not in ("hijab", "gran"):
        for sx in (-1, 1):
            d.ellipse((cx + sx * fw - 0.09 * H_, cy - 0.05 * H_, cx + sx * fw + 0.09 * H_, cy + 0.17 * H_), fill=shade(skin, 0.9))
    d.ellipse((cx - fw, cy - fh, cx + fw, cy + fh), fill=skin)
    d.ellipse((cx - fw * 0.95, cy + fh * 0.25, cx + fw * 0.95, cy + fh * 1.02), fill=shade(skin, 0.97))
    if kind in ("hijab", "gran"):
        d.chord((cx - 0.47 * H_, cy - 0.66 * H_, cx + 0.47 * H_, cy - 0.02 * H_), 180, 360, fill=hc)
        if kind == "gran":
            for j in range(6):
                a = math.radians(200 + j * 28)
                d.ellipse((cx + 0.5 * H_ * math.cos(a) - 6, cy - 0.15 * H_ + 0.5 * H_ * math.sin(a) - 6, cx + 0.5 * H_ * math.cos(a) + 6, cy - 0.15 * H_ + 0.5 * H_ * math.sin(a) + 6), fill=(250, 220, 180))
            d.chord((cx - 0.38 * H_, cy - 0.44 * H_, cx + 0.38 * H_, cy - 0.12 * H_), 180, 360, fill=(220, 220, 224))
    elif kind == "boy":
        d.chord((cx - fw * 1.06, cy - fh * 1.12, cx + fw * 1.06, cy + fh * 0.4), 180, 360, fill=hc)
        d.polygon([(cx - fw, cy - fh * 0.3), (cx - fw * 0.4, cy - fh * 0.62), (cx + fw * 0.1, cy - fh * 0.42), (cx + fw * 0.7, cy - fh * 0.64), (cx + fw * 1.02, cy - fh * 0.3), (cx + fw * 1.02, cy - fh * 0.5), (cx - fw, cy - fh * 0.5)], fill=hc)
    elif kind == "man":
        d.chord((cx - fw * 1.04, cy - fh * 1.1, cx + fw * 1.04, cy + fh * 0.2), 180, 360, fill=hc)
        d.rectangle((cx - fw * 1.04, cy - fh * 0.5, cx - fw * 0.86, cy - fh * 0.05), fill=hc)
        d.rectangle((cx + fw * 0.86, cy - fh * 0.5, cx + fw * 1.04, cy - fh * 0.05), fill=hc)
    # eyes
    ey = cy + 0.02 * H_
    es = (1.25 if child else 1.0)
    for sx in (-1, 1):
        ex = cx + sx * 0.17 * H_
        ww, hh = 0.085 * H_ * es, 0.062 * H_ * es * max(0.08, blink)
        d.ellipse((ex - ww, ey - hh, ex + ww, ey + hh), fill=(250, 246, 240))
        if blink > 0.3:
            px = ex + eye * 0.035 * H_
            pr = 0.046 * H_ * es
            d.ellipse((px - pr, ey - pr, px + pr, ey + pr), fill=(58, 40, 32))
            d.ellipse((px - pr * 0.35 + pr * 0.3, ey - pr * 0.75, px + pr * 0.35 + pr * 0.3, ey - pr * 0.05), fill=(255, 255, 255))
        d.arc((ex - ww * 1.1, ey - hh * 1.4 - 2, ex + ww * 1.1, ey + hh * 1.2), 200, 340, fill=shade(skin, 0.55), width=max(2, int(0.018 * H_)))
        bt = {"worried": 8, "happy": -3, "neutral": 0, "think": 5 * sx, "angry": -8}.get(mood, 0)
        by = ey - 0.13 * H_ * es
        d.line([(ex - 0.08 * H_, by - bt * sx * 0.4), (ex + 0.08 * H_, by + bt * sx * 0.4)], fill=shade(hc if kind in ("boy", "man") else (70, 46, 36), 1.0), width=max(3, int(0.03 * H_)))
    if look.get("glasses"):
        for sx in (-1, 1):
            ex = cx + sx * 0.17 * H_
            d.rounded_rectangle((ex - 0.12 * H_, ey - 0.09 * H_, ex + 0.12 * H_, ey + 0.09 * H_), int(0.04 * H_), outline=(70, 60, 60), width=max(2, int(0.02 * H_)))
        d.line([(cx - 0.05 * H_, ey), (cx + 0.05 * H_, ey)], fill=(70, 60, 60), width=max(2, int(0.02 * H_)))
    d.arc((cx - 0.04 * H_, cy + 0.06 * H_, cx + 0.04 * H_, cy + 0.17 * H_), 300, 80, fill=shade(skin, 0.75), width=max(2, int(0.02 * H_)))
    for sx in (-1, 1):
        d.ellipse((cx + sx * 0.25 * H_ - 0.06 * H_, cy + 0.12 * H_, cx + sx * 0.25 * H_ + 0.06 * H_, cy + 0.2 * H_), fill=(240, 150, 140, 120))
    my = cy + 0.29 * H_
    op = clamp(talk)
    if op > 0.08:
        mw, mh = 0.075 * H_ * (1 - 0.25 * op), 0.012 * H_ + 0.07 * H_ * op
        d.ellipse((cx - mw, my - mh, cx + mw, my + mh), fill=(120, 40, 40))
        if op > 0.3: d.rectangle((cx - mw * 0.7, my - mh, cx + mw * 0.7, my - mh + 0.02 * H_), fill=(250, 246, 240))
    elif mood == "happy":
        d.chord((cx - 0.09 * H_, my - 0.05 * H_, cx + 0.09 * H_, my + 0.07 * H_), 0, 180, fill=(140, 50, 46))
    elif mood == "worried":
        d.arc((cx - 0.07 * H_, my, cx + 0.07 * H_, my + 0.07 * H_), 200, 340, fill=(140, 50, 46), width=max(3, int(0.025 * H_)))
    else:
        d.arc((cx - 0.07 * H_, my - 0.04 * H_, cx + 0.07 * H_, my + 0.03 * H_), 20, 160, fill=(140, 50, 46), width=max(3, int(0.025 * H_)))
    return im, (cx, cy)

def arm(d, sx, sy, a, e, L1, L2, wdt, sleeve, skin, side):
    ex, ey = sx + side * L1 * math.sin(math.radians(a)), sy + L1 * math.cos(math.radians(a))
    hx, hy = ex + side * L2 * math.sin(math.radians(a + e)), ey + L2 * math.cos(math.radians(a + e))
    d.line([(sx, sy), (ex, ey)], fill=sleeve, width=int(wdt))
    d.ellipse((ex - wdt / 2, ey - wdt / 2, ex + wdt / 2, ey + wdt / 2), fill=sleeve)
    d.line([(ex, ey), (hx, hy)], fill=shade(sleeve, 0.95), width=int(wdt * 0.9))
    d.ellipse((hx - wdt * 0.5, hy - wdt * 0.5, hx + wdt * 0.5, hy + wdt * 0.5), fill=skin)
    return hx, hy

def pose_at(keys, t):
    if not keys: return {}
    if t <= keys[0][0]: return dict(keys[0][1])
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t < t1:
            u = ease_io((t - t0) / max(1e-3, t1 - t0))
            return {k: lerp(p0.get(k, 0), p1.get(k, 0), u) for k in set(p0) | set(p1)}
    return dict(keys[-1][1])

def person(L, who, x, y, hu, t, keys=(), talk=0.0, mood="neutral", seed=0, eye=None):
    """Rigged half-figure. x,y = neck base in panel px. Breathing, idle sway, blinking, saccades, lip-sync."""
    look = LOOK[who]
    y += hu * 0.3 * 0.85; hu *= 1.3
    p = pose_at(list(keys), t)
    d = ImageDraw.Draw(L)
    H_ = hu * SS
    br = math.sin(t * 1.6 + seed) * 0.025 * H_
    sway = math.sin(t * 0.7 + seed * 1.3) * 0.03 * H_ + p.get("lean", 0) * SS
    X, Y = x * SS + sway * 0.4, y * SS + br
    sw = 0.92 * H_ * (0.78 if look.get("child") else 1.0)
    top, skin = look["top"], look["skin"]
    # back shadow
    d.ellipse((X - sw * 1.3, Y + 3.4 * H_, X + sw * 1.3, Y + 3.9 * H_), fill=(0, 0, 0, 60))
    # torso with cel shading
    d.rounded_rectangle((X - sw, Y - 0.05 * H_, X + sw, Y + 4.4 * H_), int(0.5 * H_), fill=top)
    d.polygon([(X + sw * 0.35, Y + 0.05 * H_), (X + sw * 0.9, Y + 0.2 * H_), (X + sw, Y + 4.4 * H_), (X + sw * 0.5, Y + 4.4 * H_)], fill=shade(top, 0.88))
    if look.get("coat"):
        d.polygon([(X - 0.3 * H_, Y - 0.02 * H_), (X + 0.3 * H_, Y - 0.02 * H_), (X, Y + 0.6 * H_)], fill=(90, 130, 190))
        d.line([(X, Y + 0.6 * H_), (X, Y + 4.4 * H_)], fill=(210, 212, 218), width=max(2, int(0.03 * H_)))
        d.arc((X - 0.5 * H_, Y + 0.1 * H_, X + 0.15 * H_, Y + 1.2 * H_), 80, 260, fill=(60, 60, 70), width=max(3, int(0.05 * H_)))
    elif look["head"][0] not in ("hijab", "gran"):
        d.polygon([(X - 0.26 * H_, Y - 0.02 * H_), (X + 0.26 * H_, Y - 0.02 * H_), (X, Y + 0.42 * H_)], fill=shade(skin, 0.92))
    # neck
    if look["head"][0] not in ("hijab", "gran"):
        d.rectangle((X - 0.15 * H_, Y - 0.32 * H_, X + 0.15 * H_, Y + 0.05 * H_), fill=shade(skin, 0.9))
    # arms
    L1, L2, wd = 1.3 * H_, 1.2 * H_, 0.34 * H_
    hands = []
    for side, k_a, k_e, d_a in ((-1, "la", "le", 8), (1, "ra", "re", 8)):
        a = p.get(k_a, d_a) + 2 * math.sin(t * 1.6 + seed + side)
        e = p.get(k_e, 10)
        hands.append(arm(d, X + side * sw * 0.86, Y + 0.28 * H_, a, e, L1, L2, wd, shade(top, 0.96), skin, side))
    # head
    blink = 1.0
    per = 3.3 + (seed % 3) * 0.4
    ph = (t + seed * 0.77) % per
    if ph < 0.16: blink = abs(math.cos(ph / 0.16 * math.pi))
    if eye is None:
        eye = 0.6 * math.sin(t * 0.55 + seed) + 0.4 * math.sin(t * 1.7 + seed * 2)
    tilt = p.get("tilt", 0) + 2.2 * math.sin(t * 0.9 + seed)
    hi, (hcx, hcy) = head_img(look, H_, t, talk, mood, clamp(eye + p.get("eye", 0), -1, 1), blink, seed)
    piv = (hcx, hcy + 0.62 * H_)
    hi = hi.rotate(tilt, Image.BICUBIC, center=piv)
    hx = X + p.get("hx", 0) * SS
    L.alpha_composite(hi, (int(hx - piv[0]), int(Y - 0.06 * H_ - piv[1] + br * 0.5)))
    return [(hx_ / SS, hy_ / SS) for hx_, hy_ in hands]

# ---------- modern objects (gradients, highlights, soft shadows) ----------
@lru_cache(maxsize=64)
def grad_card(w, h, r, c0, c1, hl=True):
    yy = np.linspace(0, 1, h)[:, None]
    arr = (np.array(c0, np.float32) + (np.array(c1, np.float32) - np.array(c0, np.float32)) * yy[..., None]).repeat(w, 1)
    im = Image.fromarray(np.uint8(np.clip(arr, 0, 255))).convert("RGBA")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    im.putalpha(m)
    if hl:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((4, 4, w - 5, h * 0.45), r, fill=(255, 255, 255, 34))
        g.putalpha(Image.fromarray(np.minimum(np.array(g.getchannel("A")), np.array(m))))
        im.alpha_composite(g)
    return im

def with_shadow(im, blur=14, dy=14, a=0.55):
    pad = blur * 2
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2 + dy), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    al = Image.new("L", out.size, 0); al.paste(im.getchannel("A"), (pad, pad + dy))
    sh.putalpha(al.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * a)))
    out.alpha_composite(sh); out.alpha_composite(im, (pad, pad))
    return out

@lru_cache(maxsize=16)
def r_tile(size=170, mode="warm"):
    c0, c1 = {"warm": ((246, 186, 96), (214, 104, 70)), "green": ((140, 214, 140), (60, 150, 90)), "gray": ((150, 144, 140), (96, 92, 90))}[mode]
    im = grad_card(size, size, int(size * 0.24), c0, c1).copy()
    ImageDraw.Draw(im).text((size / 2, size / 2 + 4), "R", font=dfont("Black", int(size * 0.62)), fill=WHITE, anchor="mm")
    return with_shadow(im, 12, 12)

@lru_cache(maxsize=8)
def icon_card(kind, size=210):
    im = grad_card(size, size, 40, (68, 40, 32), (40, 22, 18)).copy()
    d = ImageDraw.Draw(im); s = size
    if kind == "mouth":
        d.chord((s * 0.22, s * 0.3, s * 0.78, s * 0.74), 0, 180, fill=(220, 80, 90))
        d.chord((s * 0.22, s * 0.26, s * 0.78, s * 0.56), 180, 360, fill=(236, 110, 116))
        d.rectangle((s * 0.3, s * 0.5, s * 0.7, s * 0.55), fill=(250, 246, 240))
    elif kind == "brain":
        for (x, y, r) in ((0.36, 0.42, 0.18), (0.54, 0.34, 0.19), (0.66, 0.5, 0.16), (0.46, 0.6, 0.18), (0.32, 0.6, 0.13)):
            d.ellipse((s * (x - r), s * (y - r), s * (x + r), s * (y + r)), fill=(236, 140, 160))
        d.line([(s * 0.5, s * 0.22), (s * 0.5, s * 0.74)], fill=(200, 100, 124), width=int(s * 0.025))
    elif kind == "pill":
        d.rounded_rectangle((s * 0.2, s * 0.4, s * 0.8, s * 0.62), int(s * 0.11), fill=(250, 246, 240))
        d.rounded_rectangle((s * 0.5, s * 0.4, s * 0.8, s * 0.62), int(s * 0.11), fill=(230, 100, 90))
    elif kind == "q":
        d.text((s / 2, s / 2 + 4), "?", font=dfont("Black", int(s * 0.6)), fill=(246, 198, 92), anchor="mm")
    return with_shadow(im, 14, 16)

@lru_cache(maxsize=4)
def room_bg(kind):
    h = HALF
    yy = np.linspace(0, 1, h)[:, None, None]
    wall0, wall1 = np.array((58, 30, 22), np.float32), np.array((34, 18, 13), np.float32)
    arr = (wall0 + (wall1 - wall0) * yy).repeat(W, 1)
    fl = int(h * 0.86)
    arr[fl:] = np.array((26, 14, 10), np.float32)
    im = Image.fromarray(np.uint8(arr)).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.line([(0, fl), (W, fl)], fill=(255, 236, 214, 30), width=2)
    if kind == "clinic":
        for x in range(0, W, 120):
            d.line([(x, 0), (x, fl)], fill=(255, 236, 214, 8), width=2)
        d.rounded_rectangle((20, 600, 100, 760), 14, fill=(46, 70, 56))
        for j in range(5):
            d.ellipse((22 + j * 12, 520 + (j % 2) * 26, 70 + j * 6, 620), fill=(60, 120, 80))
    if kind == "home":
        d.polygon([(120, 0), (340, 0), (560, fl), (180, fl)], fill=(255, 220, 160, 18))
    g = glow(700, (120, 54, 30)); im.alpha_composite(g.resize((1100, 1100)), (-10, 200))
    return im

# ---------- scenes ----------
def bgL(kind="room"):
    return room_bg(kind).copy(), Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0))

def float_card(c, img, x, y, k, rot=0.0, a=1.0):
    if k <= 0: return
    im = img.rotate(rot, Image.BICUBIC, expand=True) if rot else img
    paste_alpha(c, im, x - im.width * k / 2, y - im.height * k / 2, clamp(k * 1.6) * a, k)

def cart_intro(lt, t):
    c, _ = bgL()
    for j, (x, y, ph) in enumerate(((260, 720, 0), (540, 650, 1.2), (820, 730, 2.3))):
        k = spring(lt - 0.15 - j * 0.18, w=10, z=0.6)
        bob = 14 * math.sin(t * 1.4 + ph)
        float_card(c, icon_card("q", 200 + 30 * (j == 1)), x, y + bob, k, rot=6 * math.sin(t * 0.9 + ph))
    return c

def cart_choice(lt, t):
    c, L = bgL("clinic")
    look_lr = -1 if lt < 1.0 else (1 if lt < 2.0 else 0)
    keys = [(0, dict(ra=8, re=10, tilt=0)), (0.6, dict(ra=-22, re=-150, tilt=-6, hx=-6)), (1.6, dict(ra=-22, re=-150, tilt=6, hx=6)), (2.6, dict(ra=-20, re=-145, tilt=0))]
    person(L, "mom", 540, 770, 118, t, keys=keys, talk=voice(t) * 1.1, mood="think", seed=1, eye=look_lr * 0.9)
    c.alpha_composite(finish(L))
    for j, (kind, x) in enumerate((("mouth", 190), ("brain", 890))):
        k = spring(lt - 0.25 - j * 0.3, w=11, z=0.6)
        hot = (lt < 1.0 and j == 0) or (1.0 <= lt < 2.0 and j == 1)
        if hot:
            g = glow(320, GOLD); gg = g.resize((300, 300)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.6)))
            c.alpha_composite(gg, (x - 150, 640 - 150))
        float_card(c, icon_card(kind), x, 650 + 8 * math.sin(t * 1.3 + j), k * (1.06 if hot else 1.0))
    return c

def cart_family(lt, t):
    c, L = bgL("home")
    wave_keys = [(0, dict(ra=8, re=10)), (2.0, dict(ra=8, re=10)), (2.3, dict(ra=-120, re=-60)), (2.6, dict(ra=-110, re=-20)), (2.9, dict(ra=-120, re=-60)), (3.2, dict(ra=-110, re=-20)), (3.5, dict(ra=-120, re=-60)), (3.9, dict(ra=8, re=10))]
    person(L, "gran", 860, 760, 104, t, keys=wave_keys, mood="happy" if lt > 2.0 else "neutral", seed=4, eye=-0.8)
    person(L, "mom", 560, 760, 112, t, keys=[(0, dict(la=20, le=30, tilt=-4))], talk=voice(t), mood="worried", seed=2, eye=-0.9)
    try_r = lt < 2.2
    person(L, "boy", 240, 830, 96, t, keys=[(0, dict(ra=30, re=40))], talk=(abs(math.sin(t * 9)) * 0.8 if try_r and lt > 0.3 else 0), mood="worried", seed=3, eye=0.6)
    c.alpha_composite(finish(L))
    k = spring(lt - 0.3, w=11, z=0.5)
    sh = 7 * math.sin(lt * 42) if 0.5 < lt < 2.2 else 0
    tile = r_tile(150, "warm" if lt < 1.4 else "gray")
    float_card(c, tile, 380 + sh, 610, k * (1 - 0.15 * clamp((lt - 1.4) / 0.4)))
    return c

def mirror_img():
    im = Image.new("RGBA", (180, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((78, 200, 102, 300), 10, fill=(150, 100, 70))
    d.ellipse((0, 0, 179, 220), fill=(200, 160, 110))
    g = grad_card(156, 196, 78, (210, 226, 236), (130, 150, 170), hl=False)
    im.alpha_composite(g, (12, 12))
    ImageDraw.Draw(im).line([(50, 50), (90, 30)], fill=(255, 255, 255, 140), width=10)
    return with_shadow(im, 12, 12)
MIRROR = None

def cart_practice(lt, t):
    global MIRROR
    if MIRROR is None: MIRROR = mirror_img()
    c, L = bgL("clinic")
    lp_keys = [(0, dict(la=-60, le=-40, ra=8)), (1.0, dict(la=-70, le=-60, ra=8)), (2.0, dict(la=-60, le=-40, ra=-40, re=-60)), (3.0, dict(la=-60, le=-40, ra=8))]
    person(L, "logo", 790, 740, 118, t, keys=lp_keys, talk=voice(t), mood="happy", seed=5, eye=-0.8)
    boy_talk = max(0, voice(t - 0.25) * 0.8) if lt > 0.8 else 0
    person(L, "boy", 280, 820, 98, t, keys=[(0, dict(la=-30, le=-50))], talk=boy_talk, mood="think" if lt < 1.7 else "happy", seed=6, eye=0.7)
    c.alpha_composite(finish(L))
    paste_alpha(c, MIRROR, 470 - MIRROR.width / 2, 600, clamp(lt / 0.3))
    if lt > 1.7:
        k = spring(lt - 1.7, w=12, z=0.5)
        g = glow(300, (120, 220, 140)); gg = g.resize((max(1, int(280 * k)), max(1, int(280 * k)))); c.alpha_composite(gg, (int(470 - gg.width / 2), int(610 - gg.height / 2)))
        float_card(c, r_tile(120, "green"), 470, 600, k)
    tn = 17.26 - (t - lt)
    if lt > tn:
        k = spring(lt - tn, w=11, z=0.7)
        out = ease_in((lt - tn - 1.1) / 0.5)
        card = icon_card("brain", 160)
        im = desat_img(card, clamp((lt - tn - 0.6) / 0.4))
        float_card(c, im, 1000 + 300 * out, 600, k, a=1 - out)
    return c

def desat_img(im, amt):
    if amt <= 0: return im
    g = im.convert("LA").convert("RGBA"); g.putalpha(im.getchannel("A"))
    return Image.blend(im, g, amt)

@lru_cache(maxsize=2)
def cake_base():
    im = Image.new("RGBA", (380, 300), (0, 0, 0, 0))
    im.alpha_composite(grad_card(360, 120, 30, (250, 226, 200), (226, 186, 150)), (10, 170))
    im.alpha_composite(grad_card(300, 110, 28, (236, 130, 150), (200, 90, 110)), (40, 80))
    d = ImageDraw.Draw(im)
    for j in range(7): d.ellipse((50 + j * 42, 70, 80 + j * 42, 100), fill=(250, 240, 230))
    return im

def cart_age(lt, t):
    c, L = bgL("home")
    speak = lt > 2.24
    person(L, "boy", 830, 800, 104, t, keys=[(0, dict(la=8, ra=8)), (1.4, dict(la=-140, le=-10, ra=-140, re=-10)), (2.0, dict(la=8, ra=8))], talk=(voice(t) if speak else 0), mood="happy" if not speak else "neutral", seed=7, eye=-0.6)
    c.alpha_composite(finish(L))
    k = spring(lt - 0.2, w=10, z=0.7)
    cb = cake_base()
    paste_alpha(c, with_shadow(cb, 14, 14), 320 - cb.width / 2 - 28, 900 - cb.height - 28 + (1 - k) * 60, clamp(k * 2))
    lit = 20.56 - (t - lt)
    d = ImageDraw.Draw(c)
    for j in range(5):
        x = 210 + j * 55; y0 = 900 - 300 + 80 + (1 - k) * 60
        d.rounded_rectangle((x - 8, y0 - 70, x + 8, y0), 6, fill=[GOLD, TERRA, (120, 180, 230), (140, 210, 140), (230, 140, 200)][j])
        if t > lit + j * 0.12:
            fl = 1 + 0.15 * math.sin(t * 20 + j)
            g = glow(120, GOLD); c.alpha_composite(g, (int(x - 60), int(y0 - 130)))
            d.ellipse((x - 9 * fl, y0 - 104 * fl + 30 * (fl - 1) * 0, x + 9 * fl, y0 - 76), fill=(255, 214, 120))
    if speak:   # distorted speech wave (sounds come out wrong)
        u = lt - 2.24
        pts = [(lerp(470, 740, q / 50), 640 + (26 * math.sin(q * 0.9 + t * 8) + 18 * math.sin(q * 2.7)) * clamp(u / 0.4)) for q in range(51)]
        d.line(pts, fill=WARN, width=6, joint="curve")
    return c

def tablet_img(t, warn):
    im = grad_card(260, 190, 24, (40, 40, 46), (24, 24, 30)).copy()
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((12, 12, 247, 177), 14, fill=(18, 26, 34))
    pts = [(20 + q * 4.5, 95 + (30 if not warn else 46) * math.sin(q * 0.5 + t * 6) * math.exp(-((q - 26) / 18) ** 2)) for q in range(50)]
    d.line(pts, fill=(250, 170, 80) if warn else (120, 210, 160), width=4, joint="curve")
    return with_shadow(im, 10, 10)

def cart_exam(lt, t):
    c, L = bgL("clinic")
    hands = person(L, "logo", 780, 740, 118, t, keys=[(0, dict(la=-40, le=-70, ra=8))], talk=voice(t), mood="think" if lt < 1.8 else "neutral", seed=5, eye=-0.7)
    person(L, "boy", 260, 830, 96, t, keys=[(0, dict())], talk=0, mood="neutral", seed=6, eye=0.6)
    c.alpha_composite(finish(L))
    hx, hy = hands[0]
    paste_alpha(c, tablet_img(t, lt > 1.8), hx - 150, hy - 140, clamp(lt / 0.3))
    if lt > 1.8:   # floating brain hologram with a soft warning pulse
        k = spring(lt - 1.8, w=10, z=0.6)
        pulse = 0.6 + 0.4 * abs(math.sin(t * 4))
        g = glow(320, AMBER); gg = g.resize((max(1, int(300 * k * pulse)), max(1, int(300 * k * pulse))))
        c.alpha_composite(gg, (int(260 - gg.width / 2), int(620 - gg.height / 2)))
        float_card(c, icon_card("brain", 150), 260, 610 + 8 * math.sin(t * 2), k)
    tp = 32.94 - (t - lt)
    if lt > tp:
        k = spring(lt - tp, w=12, z=0.5)
        float_card(c, icon_card("pill", 140), 520, 640, k, rot=8 * math.sin(t * 2))
    return c

def envelope_img():
    im = grad_card(170, 120, 14, (250, 240, 222), (226, 210, 188)).copy()
    d = ImageDraw.Draw(im)
    d.polygon([(4, 8), (85, 66), (166, 8)], outline=(190, 170, 150), width=3)
    d.ellipse((72, 54, 98, 80), fill=TERRA)
    return with_shadow(im, 10, 10)
ENV_IMG = None

def cart_refer(lt, t):
    global ENV_IMG
    if ENV_IMG is None: ENV_IMG = envelope_img()
    c, L = bgL("clinic")
    give = [(0, dict(ra=8)), (0.4, dict(ra=-95, re=-10)), (1.2, dict(ra=-95, re=-10)), (1.6, dict(ra=8))]
    person(L, "logo", 260, 740, 112, t, keys=give, talk=voice(t), mood="happy", seed=5, eye=0.8)
    catch = [(0, dict(la=8)), (1.3, dict(la=8)), (1.7, dict(la=-100, le=-10, tilt=-4)), (2.6, dict(la=-60, le=-50, tilt=3))]
    person(L, "neuro", 820, 730, 116, t, keys=catch, mood="happy" if lt > 1.8 else "neutral", seed=8, eye=-0.8)
    c.alpha_composite(finish(L))
    f = ease_io((lt - 0.8) / 0.9)
    x = lerp(420, 680, f); y = lerp(720, 700, f) - 90 * math.sin(math.pi * f)
    paste_alpha(c, ENV_IMG.rotate(-12 * math.sin(math.pi * f), Image.BICUBIC, expand=True), x - 100, y - 80, clamp((lt - 0.4) / 0.3))
    return c

def cart_success(lt, t):
    c, L = bgL("clinic")
    jump = abs(math.sin(lt * 5)) * 30 * clamp((lt - 0.6) / 0.3) * (1 - clamp((lt - 2.0) / 0.3))
    person(L, "boy", 300, 830 - jump, 100, t, keys=[(0, dict(la=8, ra=8)), (0.6, dict(la=-160, le=-10, ra=-160, re=-10))], talk=0.2 if lt > 0.3 else 0, mood="happy", seed=6, eye=0.5)
    clap = [(0, dict(la=-60, le=-70, ra=-60, re=-70))]
    for j in range(8): clap.append((0.4 + j * 0.25, dict(la=-55 + (12 if j % 2 else 0), le=-80, ra=-55 + (12 if j % 2 else 0), re=-80)))
    person(L, "logo", 800, 740, 116, t, keys=clap, talk=voice(t), mood="happy", seed=5, eye=-0.7)
    c.alpha_composite(finish(L))
    k = spring(lt - 0.2, w=10, z=0.5)
    g = glow(360, (120, 220, 140)); gg = g.resize((max(1, int(340 * k)), max(1, int(340 * k)))); c.alpha_composite(gg, (int(540 - gg.width / 2), int(640 - gg.height / 2)))
    float_card(c, r_tile(170, "green"), 540, 640, k)
    d = ImageDraw.Draw(c)
    rk = ease_out((lt - 0.4) / 1.2)
    d.arc((420, 520, 660, 760), -90, -90 + 360 * rk, fill=(140, 220, 150), width=10)
    rng = np.random.default_rng(5)
    for j in range(26):   # confetti
        u = lt - 0.5 - rng.uniform(0, 0.4)
        if u <= 0: continue
        ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(240, 520)
        x = 540 + math.cos(ang) * sp * u; y = 640 + math.sin(ang) * sp * u + 380 * u * u
        if y > 950: continue
        col = [GOLD, TERRA, (120, 180, 230), (140, 210, 140)][j % 4]
        r = 9
        d.rectangle((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=rgba(col, 1 - clamp(u / 1.6)))
    return c

def flash_card(icon, flip):
    w, h = 190, 240
    sx = abs(math.cos(flip * math.pi))
    if flip < 0.5:
        im = grad_card(w, h, 24, (90, 110, 170), (60, 74, 128)).copy()
        ImageDraw.Draw(im).text((w / 2, h / 2), "R", font=dfont("Black", 110), fill=(255, 255, 255, 90), anchor="mm")
    else:
        im = grad_card(w, h, 24, (252, 246, 236), (232, 222, 206)).copy()
        d = ImageDraw.Draw(im)
        if icon == "rocket":
            d.polygon([(95, 40), (130, 110), (130, 170), (60, 170), (60, 110)], fill=(230, 100, 90))
            d.ellipse((80, 90, 110, 120), fill=(120, 180, 230))
            d.polygon([(60, 140), (30, 190), (60, 175)], fill=GOLD); d.polygon([(130, 140), (160, 190), (130, 175)], fill=GOLD)
            d.polygon([(70, 172), (120, 172), (95, 215)], fill=AMBER)
        else:
            for j in range(5):
                d.arc((30 + j * 6, 60 + j * 6, 160 - j * 6, 190 - j * 6), 180, 360, fill=[(230, 90, 90), (240, 160, 70), (240, 210, 90), (120, 190, 120), (110, 150, 220)][j], width=12)
    im = im.resize((max(2, int(w * sx)), h), Image.BICUBIC)
    return with_shadow(im, 10, 10)

def cart_home(lt, t):
    c, L = bgL("home")
    d0 = ImageDraw.Draw(c)
    d0.rounded_rectangle((120, 820, 960, 960), 40, fill=(110, 56, 46)); d0.rounded_rectangle((100, 760, 170, 960), 30, fill=(128, 66, 54)); d0.rounded_rectangle((910, 760, 980, 960), 30, fill=(128, 66, 54))
    hold = [(0, dict(ra=-70, re=-60)), (1.8, dict(ra=-70, re=-60)), (2.1, dict(ra=-90, re=-40)), (4.0, dict(ra=-90, re=-40))]
    hands = person(L, "mom", 680, 720, 110, t, keys=hold, talk=voice(t), mood="happy", seed=2, eye=-0.8)
    person(L, "boy", 390, 790, 94, t, keys=[(0, dict(la=8))], talk=max(0, voice(t - 0.3) * 0.7), mood="happy", seed=3, eye=0.8)
    c.alpha_composite(finish(L))
    hx, hy = hands[1]
    which = "rocket" if lt < 2.1 else "rainbow"
    fl = clamp((lt - 0.4) / 0.35) if lt < 2.1 else clamp((lt - 2.3) / 0.35)
    fc = flash_card(which, 0.5 + 0.5 * fl)
    paste_alpha(c, fc, hx - fc.width / 2 + 10, max(520, hy - fc.height + 30), 1.0)
    return c

PANELS.update({"intro": cart_intro, "choice": cart_choice, "family": cart_family, "practice": cart_practice, "age": cart_age,
               "exam": cart_exam, "refer": cart_refer, "success": cart_success, "home": cart_home})

# ---------- new 50/50 transitions: panel reveal-in-place, spring seam, whip-pan between panels ----------
def _panel(name, t0, t, src):
    return PANELS[name](t - t0, t, src) if name == "follow" else PANELS[name](t - t0, t)

def render(i, src):
    t = i / FPS
    si = seg_at(t)
    a, b, lay, panel, zb = SEG[si]
    lt = t - a
    prev = SEG[si - 1] if si > 0 else None
    c = BG.copy()
    full_r, split_r = (0, 0, W, H), (0, HALF, W, HALF)
    cur_r = full_r if lay == "full" else split_r
    if prev is not None and lt < 1.2:
        k = spring(lt, w=10, z=0.68)
        pr = full_r if prev[2] == "full" else split_r
        y = lerp(pr[1], cur_r[1], k)
        zz = lerp(prev[4], zb, clamp(k))
    else:
        y = cur_r[1]; zz = zb
    y = clamp(y, 0, HALF + 60)
    z = full_zoom(t, zz) if lay == "full" else zz
    if y > 2:
        if panel and prev is not None and prev[3] and prev[3] != panel and lt < 0.42:
            p = ease_io(lt / 0.42)
            A = _panel(prev[3], prev[0], t, src); B = _panel(panel, a, t, src)
            comp = Image.new("RGBA", (W, HALF), (0, 0, 0, 255))
            comp.alpha_composite(A, (int(-W * p), 0)); comp.alpha_composite(B, (int(W * (1 - p)), 0))
            bl = math.sin(math.pi * p)
            if bl > 0.08:
                f_ = 1 + int(bl * 16)
                comp = comp.resize((max(8, W // f_), HALF), Image.BILINEAR).resize((W, HALF), Image.BILINEAR)
            c.alpha_composite(comp)
        else:
            name = panel or (prev[3] if prev is not None else None)
            if name:
                t0 = a if panel else prev[0]
                pim = _panel(name, t0, t, src)
                reveal = clamp(y / HALF)
                sc = lerp(1.08, 1.0, ease_out(reveal))
                if sc > 1.001:
                    pw_, ph_ = int(W * sc), int(HALF * sc)
                    pim = pim.resize((pw_, ph_), Image.BILINEAR).crop(((pw_ - W) // 2, (ph_ - HALF) // 2, (pw_ - W) // 2 + W, (ph_ - HALF) // 2 + HALF))
                c.alpha_composite(pim)
                if reveal < 1:
                    c.alpha_composite(Image.new("RGBA", (W, HALF), rgba(BG0, 0.5 * (1 - reveal))))
    hgt = H - y
    ex = expert_crop(src, W, int(hgt), z=z, face_at=0.40 if hgt > HALF + 100 else 0.36)
    c.alpha_composite(ex, (0, int(y)))
    if y > 2:
        sh = Image.new("RGBA", (W, 46), (0, 0, 0, 0))
        sh.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 46) ** 2 * 120)[:, None], W, 1).astype(np.uint8)))
        c.alpha_composite(sh, (0, int(y) - 46))
        moving = prev is not None and lt < 0.6
        ImageDraw.Draw(c).line((0, int(y), W, int(y)), fill=TERRA + (int(200 if moving else 90),) if moving else (255, 236, 214, 70), width=3 if moving else 2)
    if lay == "full" or (prev is not None and prev[2] == "full" and lt < 0.5):
        sa = 1.0 if lay == "full" else 1 - clamp(lt / 0.5)
        if sa > 0:
            s_ = SCRIM if sa >= 1 else Image.fromarray(np.dstack([np.array(SCRIM)[..., :3], (np.array(SCRIM)[..., 3] * sa).astype(np.uint8)]))
            c.alpha_composite(s_)
    fl = 0.4 * (1 - t / 0.12) if t < 0.12 else 0.0
    if 0.84 <= t < 1.04: fl = max(fl, 0.14 * (1 - (t - 0.84) / 0.2))
    if fl > 0: c.alpha_composite(Image.new("RGBA", (W, H), (255, 214, 170, int(255 * fl))))
    draw_captions(c, t)
    return c.convert("RGB")

from PIL import ImageChops
# ================= v6: illustrated Uzbek characters (shaded sprites + live face rig) =================
def _hash(n, seed):
    x = math.sin(n * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)

def saccade(t, seed):
    """Eyes jump between fixation points (fast 70ms moves, holds of ~0.6-1.4s)."""
    period = 0.95
    k = math.floor((t + seed * 0.37) / period)
    tk = k * period - seed * 0.37
    tgt = _hash(k, seed) * 2 - 1
    prv = _hash(k - 1, seed) * 2 - 1
    u = clamp((t - tk) / 0.07)
    return lerp(prv, tgt, ease_out(u)) * 0.8

def blink_amt(t, seed):
    k = math.floor((t + seed) / 1.7)
    if _hash(k, seed + 3) > 0.45: return 1.0
    start = k * 1.7 - seed + _hash(k, seed + 5) * 1.2
    u = (t - start) / 0.15
    return abs(math.cos(u * math.pi)) if 0 <= u <= 1 else 1.0

def _np_grad(w, h, top, bot, side=0.18):
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :, None]
    base = np.array(top, np.float32) * (1 - yy) + np.array(bot, np.float32) * yy
    return base * (1 - side * np.clip(xx, 0, 1)) * (1 + 0.06 * np.clip(-xx, 0, 1))

def _ikat(w, h, cols, scale=1.0):
    y = np.arange(h, dtype=np.float32)[:, None]; x = np.arange(w, dtype=np.float32)[None, :]
    rng = np.random.default_rng(7)
    jit = rng.uniform(-4, 4, size=(h, 1)).astype(np.float32) * scale
    zig = np.abs(((y / scale) % 90) - 45) * 0.9 * scale
    band = (((x + zig + jit) / (34 * scale)).astype(int)) % len(cols)
    arr = np.array(cols, np.float32)[band]
    return arr

def _layer(mask, rgb):
    a = np.array(mask, np.float32)
    out = np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def _soft(im, r): return im.filter(ImageFilter.GaussianBlur(r))

LOOK = {
    "mom":   dict(skin=(234, 190, 160), top="ikat", ikat=[(70, 52, 140), (210, 60, 110), (240, 190, 70), (40, 120, 160), (210, 60, 110)],
                  head=("romol", (236, 222, 200)), fem=True, hair=(40, 26, 20), lips=(196, 104, 104)),
    "gran":  dict(skin=(222, 178, 150), top="nimcha", vest=(54, 30, 52), trim=(214, 170, 80), blouse=(244, 240, 232),
                  head=("romol_w", (246, 244, 240)), fem=True, hair=(190, 186, 182), lips=(178, 104, 100), age=True),
    "boy":   dict(skin=(240, 200, 170), top=(78, 128, 196), head=("doppi", (34, 24, 20)), child=True, hair=(34, 24, 20), lips=(204, 120, 112)),
    "logo":  dict(skin=(236, 194, 166), top="coat", inner=(56, 132, 128), head=("hijab", (36, 52, 90)), fem=True, glasses=True, hair=(40, 26, 20), lips=(190, 100, 100)),
    "neuro": dict(skin=(212, 168, 136), top="coat", inner=(90, 130, 190), tie=(120, 40, 50), head=("man", (40, 30, 26)), glasses=True, hair=(40, 30, 26), lips=(170, 104, 96)),
}

def face_poly(cx, cy, fw, fh, child):
    pts = []
    taper = 0.1 if child else 0.24
    for i in range(72):
        a = i / 72 * 2 * math.pi
        x = fw * math.sin(a); y = -fh * math.cos(a)
        if y > 0: x *= 1 - taper * (y / fh) ** 2
        pts.append((cx + x, cy + y))
    return pts

@lru_cache(maxsize=24)
def head_base(who, H):
    """Static head sprite (no eyes/brows/mouth), H = head height in px. Returns (img, cx, cy, fw, fh)."""
    lk = LOOK[who]; child = lk.get("child", False)
    S = int(H * 2.9)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx, cy = S / 2, S * 0.47
    fw, fh = (0.47 if child else 0.39) * H, (0.5 if child else 0.5) * H
    skin = lk["skin"]; kind, hc = lk["head"]
    def put(mask, rgb): im.alpha_composite(_layer(mask, rgb))
    def M(): return Image.new("L", (S, S), 0)
    # back layer: scarf/hijab volume
    if kind in ("romol", "romol_w", "hijab"):
        m = M(); d = ImageDraw.Draw(m)
        d.ellipse((cx - fw * 1.3, cy - fh * 1.26, cx + fw * 1.3, cy + fh * (1.45 if kind == "hijab" else 0.62)), fill=255)
        if kind == "hijab":
            d.polygon([(cx - fw * 1.3, cy + fh * 0.4), (cx + fw * 1.3, cy + fh * 0.4), (cx + fw * 1.9, S), (cx - fw * 1.9, S)], fill=255)
        put(m, _np_grad(S, S, shade(hc, 1.05), shade(hc, 0.8), 0.3))
    if kind == "man":
        m = M(); ImageDraw.Draw(m).ellipse((cx - fw * 1.05, cy - fh * 1.12, cx + fw * 1.05, cy + fh * 0.3), fill=255)
        put(m, _np_grad(S, S, shade(hc, 1.1), shade(hc, 0.8)))
    if kind == "doppi":
        m = M(); ImageDraw.Draw(m).ellipse((cx - fw * 1.03, cy - fh * 1.05, cx + fw * 1.03, cy + fh * 0.2), fill=255)
        put(m, _np_grad(S, S, shade(hc, 1.2), shade(hc, 0.85)))
    # ears
    if kind in ("doppi", "man"):
        m = M(); d = ImageDraw.Draw(m)
        for sx in (-1, 1):
            d.ellipse((cx + sx * fw - 0.085 * H, cy - 0.02 * H, cx + sx * fw + 0.085 * H, cy + 0.2 * H), fill=255)
        put(m, _np_grad(S, S, shade(skin, 0.96), shade(skin, 0.86), 0.2))
    # face with soft shading
    m = M(); ImageDraw.Draw(m).polygon(face_poly(cx, cy, fw, fh, child), fill=255)
    rgb = _np_grad(S, S, shade(skin, 1.04), shade(skin, 0.93), 0.22)
    face = _layer(m, rgb)
    # cheek blush, under-hairline shadow, chin shadow
    fx = Image.new("RGBA", (S, S), (0, 0, 0, 0)); fd = ImageDraw.Draw(fx)
    for sx in (-1, 1):
        fd.ellipse((cx + sx * fw * 0.55 - 0.1 * H, cy + 0.12 * H, cx + sx * fw * 0.55 + 0.1 * H, cy + 0.24 * H), fill=(236, 140, 130, 110 if child else 70))
    fd.ellipse((cx - fw * 0.5, cy + fh * 0.78, cx + fw * 0.5, cy + fh * 1.06), fill=shade(skin, 0.86) + (90,))
    fx = _soft(fx, H * 0.04)
    fa = Image.new("RGBA", (S, S), (0, 0, 0, 0)); fa.alpha_composite(fx)
    fa.putalpha(ImageChops.multiply(fa.getchannel("A"), m))
    face.alpha_composite(fa)
    im.alpha_composite(face)
    # nose: soft side shadow + tip highlight + nostrils
    nz = Image.new("RGBA", (S, S), (0, 0, 0, 0)); nd = ImageDraw.Draw(nz)
    ny = cy + (0.12 if not child else 0.1) * H
    nd.ellipse((cx + 0.005 * H, ny - 0.11 * H, cx + 0.05 * H, ny + 0.03 * H), fill=shade(skin, 0.8) + (120,))
    nd.ellipse((cx - 0.035 * H, ny - 0.005 * H, cx + 0.035 * H, ny + 0.035 * H), fill=shade(skin, 0.82) + (90,))
    im.alpha_composite(_soft(nz, H * 0.015))
    nd2 = ImageDraw.Draw(im)
    for sx in (-1, 1):
        nd2.ellipse((cx + sx * 0.026 * H - 0.012 * H, ny + 0.01 * H, cx + sx * 0.026 * H + 0.012 * H, ny + 0.026 * H), fill=shade(skin, 0.62) + (200,))
    # front hair / scarf framing
    if kind in ("romol", "romol_w"):
        hm = M(); d = ImageDraw.Draw(hm)   # thin band of hair under the scarf edge
        d.chord((cx - fw * 0.86, cy - fh * 0.98, cx + fw * 0.86, cy - fh * 0.4), 180, 360, fill=255)
        put(hm, _np_grad(S, S, shade(lk["hair"], 1.3), lk["hair"]))
        sm = M(); d = ImageDraw.Draw(sm)
        d.ellipse((cx - fw * 1.3, cy - fh * 1.26, cx + fw * 1.3, cy + fh * 0.62), fill=255)
        d.polygon(face_poly(cx, cy + fh * 0.14, fw * 1.02, fh * 0.9, child), fill=0)
        sc = _np_grad(S, S, shade(hc, 1.06), shade(hc, 0.84), 0.3)
        if kind == "romol":
            yy, xx = np.mgrid[0:S, 0:S]
            st = max(4, int(H * 0.09))
            dots = (((xx // st) + (yy // st)) % 2 == 0) & ((xx % st) < st * 0.35) & ((yy % st) < st * 0.35)
            sc[dots] = sc[dots] * 0.8 + np.array((190, 80, 90), np.float32) * 0.2
        put(sm, sc)
        edge = M(); ImageDraw.Draw(edge).polygon(face_poly(cx, cy + fh * 0.14, fw * 1.06, fh * 0.94, child), fill=255)
        ImageDraw.Draw(edge).polygon(face_poly(cx, cy + fh * 0.14, fw * 1.02, fh * 0.9, child), fill=0)
        ed = np.array(edge, np.float32) * (np.array(sm, np.float32) > 0)
        put(Image.fromarray(ed.astype(np.uint8)), np.full((S, S, 3), shade(hc, 0.78), np.float32))
        hl = M(); ImageDraw.Draw(hl).arc((cx - fw * 1.2, cy - fh * 1.2, cx + fw * 1.2, cy + fh * 0.4), 200, 260, fill=255, width=int(H * 0.05))
        put(_soft(hl, H * 0.02), np.full((S, S, 3), 255, np.float32) * 0.98)
    elif kind == "hijab":
        sm = M(); d = ImageDraw.Draw(sm)
        d.ellipse((cx - fw * 1.32, cy - fh * 1.28, cx + fw * 1.32, cy + fh * 1.45), fill=255)
        d.polygon(face_poly(cx, cy + fh * 0.03, fw * 1.03, fh * 1.0, child), fill=0)
        d.chord((cx - fw * 1.05, cy - fh * 1.15, cx + fw * 1.05, cy - fh * 0.45), 180, 360, fill=255)
        put(sm, _np_grad(S, S, shade(hc, 1.15), shade(hc, 0.82), 0.3))
        fold = M(); ImageDraw.Draw(fold).arc((cx - fw * 1.15, cy - fh * 0.2, cx + fw * 1.15, cy + fh * 1.5), 30, 150, fill=255, width=int(H * 0.04))
        put(_soft(fold, H * 0.02), np.full((S, S, 3), shade(hc, 0.65), np.float32))
    elif kind == "doppi":
        hm = M(); d = ImageDraw.Draw(hm)
        d.chord((cx - fw * 1.02, cy - fh * 1.0, cx + fw * 1.02, cy + fh * 0.1), 180, 360, fill=255)
        d.polygon([(cx - fw * 0.98, cy - fh * 0.38), (cx - fw * 0.5, cy - fh * 0.62), (cx - fw * 0.1, cy - fh * 0.48), (cx + fw * 0.35, cy - fh * 0.66), (cx + fw * 0.98, cy - fh * 0.36), (cx + fw, cy - fh * 0.6), (cx - fw, cy - fh * 0.6)], fill=255)
        put(hm, _np_grad(S, S, shade(hc, 1.5), hc))
        # Chust doppi: black square cap with four white "qalampir" (pepper) motifs
        dm = M(); d = ImageDraw.Draw(dm)
        top, bot = cy - fh * 1.22, cy - fh * 0.62
        d.polygon([(cx - fw * 0.98, bot), (cx - fw * 0.82, top + fh * 0.12), (cx - fw * 0.5, top), (cx + fw * 0.5, top), (cx + fw * 0.82, top + fh * 0.12), (cx + fw * 0.98, bot)], fill=255)
        put(dm, _np_grad(S, S, (44, 42, 46), (18, 16, 20), 0.3))
        dd = ImageDraw.Draw(im)
        for j, px in enumerate((-0.55, 0.0, 0.55)):
            x0 = cx + px * fw; y0 = (top + bot) / 2 + 0.02 * H
            w_ = 0.12 * H
            dd.chord((x0 - w_, y0 - w_ * 0.9, x0 + w_, y0 + w_ * 0.9), 200, 520 if False else 340, fill=(240, 238, 232))
            dd.polygon([(x0 + w_ * 0.6, y0 - w_ * 0.2), (x0 + w_ * 1.1, y0 - w_ * 0.9), (x0 + w_ * 0.9, y0 + w_ * 0.1)], fill=(240, 238, 232))
        dd.line([(cx - fw * 0.98, bot), (cx + fw * 0.98, bot)], fill=(240, 238, 232), width=max(2, int(H * 0.018)))
    elif kind == "man":
        hm = M(); d = ImageDraw.Draw(hm)
        d.chord((cx - fw * 1.04, cy - fh * 1.12, cx + fw * 1.04, cy - fh * 0.1), 180, 360, fill=255)
        d.polygon([(cx - fw * 1.0, cy - fh * 0.42), (cx - fw * 0.2, cy - fh * 0.78), (cx + fw * 1.02, cy - fh * 0.5), (cx + fw * 1.02, cy - fh * 0.8), (cx - fw, cy - fh * 0.8)], fill=255)
        put(hm, _np_grad(S, S, shade(hc, 1.35), hc))
    if kind == "romol_w":
        gm = M(); ImageDraw.Draw(gm).chord((cx - fw * 0.92, cy - fh * 0.98, cx + fw * 0.92, cy - fh * 0.5), 190, 350, fill=255)
        put(gm, _np_grad(S, S, (214, 210, 206), (170, 166, 162)))
    if lk.get("age"):
        ad = ImageDraw.Draw(im)
        for sx in (-1, 1):
            ad.arc((cx + sx * fw * 0.5 - 0.09 * H, cy + 0.1 * H, cx + sx * fw * 0.5 + 0.09 * H, cy + 0.32 * H), 200 if sx < 0 else 250, 290 if sx < 0 else 340, fill=shade(skin, 0.78), width=max(2, int(H * 0.012)))
    return im, cx, cy, fw, fh

def draw_eye(d, ex, ey, ew, eh, iris_r, look_x, blink, lk, side, H):
    skin = lk["skin"]
    if blink < 0.15:
        d.arc((ex - ew, ey - eh * 0.6, ex + ew, ey + eh * 1.4), 200, 340, fill=shade(skin, 0.45), width=max(3, int(H * 0.018)))
        return
    up = [(ex - ew + 2 * ew * i / 16, ey - eh * blink * math.sin(math.pi * i / 16) * (1.0 + 0.15 * side * (i / 16 - 0.5))) for i in range(17)]
    lo = [(ex + ew - 2 * ew * i / 16, ey + eh * 0.55 * math.sin(math.pi * i / 16)) for i in range(17)]
    poly = up + lo
    d.polygon(poly, fill=(248, 244, 238))
    ix = ex + look_x * ew * 0.42
    iy = ey + eh * 0.05
    top_clip = ey - eh * blink
    d.ellipse((ix - iris_r, iy - iris_r, ix + iris_r, iy + iris_r), fill=(84, 52, 34))
    d.ellipse((ix - iris_r * 0.7, iy - iris_r * 0.7, ix + iris_r * 0.7, iy + iris_r * 0.7), fill=(62, 38, 26))
    d.ellipse((ix - iris_r * 0.42, iy - iris_r * 0.42, ix + iris_r * 0.42, iy + iris_r * 0.42), fill=(18, 12, 10))
    d.ellipse((ix + iris_r * 0.15, iy - iris_r * 0.62, ix + iris_r * 0.55, iy - iris_r * 0.22), fill=(255, 255, 255))
    if top_clip > iy - iris_r:   # eyelid covers the top of the iris
        d.polygon([(ex - ew, ey - eh * 1.6)] + up + [(ex + ew, ey - eh * 1.6)], fill=shade(skin, 0.96))
    lw = max(3, int(H * (0.024 if lk.get("fem") else 0.018)))
    d.line(up, fill=(36, 24, 20), width=lw, joint="curve")
    if lk.get("fem"):
        d.line([up[-1], (up[-1][0] + side * ew * 0.18, up[-1][1] - eh * 0.25)], fill=(36, 24, 20), width=lw)
    d.line(lo[4:13], fill=shade(skin, 0.7), width=max(1, int(H * 0.008)))
    d.arc((ex - ew * 1.05, ey - eh * 1.9, ex + ew * 1.05, ey + eh * 0.4), 205, 335, fill=shade(skin, 0.82), width=max(2, int(H * 0.01)))

def draw_mouth(d, cx, my, H, talk, mood, lk, tongue=False):
    lips = lk["lips"]
    w = (0.085 if lk.get("child") else 0.095) * H
    op = clamp(talk)
    smile = {"happy": 1.0, "neutral": 0.25, "think": 0.0, "worried": -0.6, "angry": -0.4}.get(mood, 0)
    if op > 0.07:
        h = 0.012 * H + 0.075 * H * op
        ww = w * (1 - 0.22 * op)
        pts = [(cx + ww * math.cos(a), my + h * math.sin(a) - smile * 0.012 * H * abs(math.cos(a))) for a in np.linspace(0, 2 * math.pi, 28)]
        d.polygon(pts, fill=(96, 32, 36))
        if op > 0.25: d.chord((cx - ww * 0.8, my - h, cx + ww * 0.8, my - h + 0.05 * H), 180, 360, fill=(248, 244, 238))
        if tongue:
            d.ellipse((cx - ww * 0.5, my - h * 0.9, cx + ww * 0.5, my - h * 0.1), fill=(214, 100, 110))
        else:
            d.chord((cx - ww * 0.6, my + h * 0.1, cx + ww * 0.6, my + h * 1.1), 180, 360, fill=(190, 86, 96))
        d.line(pts[:15], fill=shade(lips, 0.95), width=max(3, int(H * 0.02)))
        d.line(pts[14:] + [pts[0]], fill=shade(lips, 1.05), width=max(4, int(H * 0.028)))
    else:
        cy_ = -smile * 0.03 * H
        upper = [(cx - w, my + cy_), (cx - w * 0.45, my - 0.018 * H), (cx, my - 0.008 * H), (cx + w * 0.45, my - 0.018 * H), (cx + w, my + cy_)]
        lower = [(cx + w, my + cy_), (cx + w * 0.5, my + 0.03 * H), (cx, my + 0.038 * H), (cx - w * 0.5, my + 0.03 * H), (cx - w, my + cy_)]
        d.polygon(upper + [(cx + w * 0.5, my + 0.004 * H), (cx - w * 0.5, my + 0.004 * H)], fill=shade(lips, 0.9))
        d.polygon(lower, fill=lips)
        d.line([(cx - w, my + cy_), (cx, my + 0.004 * H), (cx + w, my + cy_)], fill=shade(lips, 0.55), width=max(2, int(H * 0.012)), joint="curve")
        d.ellipse((cx - w * 0.3, my + 0.012 * H, cx + w * 0.2, my + 0.026 * H), fill=shade(lips, 1.15))

def head_img(look_key, H_, t, talk, mood, eye, blink, seed, tongue=False):
    base, cx, cy, fw, fh = head_base(look_key, int(H_))
    im = base.copy(); d = ImageDraw.Draw(im)
    lk = LOOK[look_key]; child = lk.get("child", False); H = H_
    ey = cy + (0.04 if child else 0.0) * H
    ew, eh = (0.1 if child else 0.088) * H, (0.06 if child else 0.042) * H
    ir = (0.058 if child else 0.046) * H
    for side in (-1, 1):
        draw_eye(d, cx + side * (0.19 if child else 0.175) * H, ey, ew, eh, ir, eye, blink, lk, side, H)
    raise_ = {"worried": 0.03, "happy": -0.01, "think": 0.015, "neutral": 0.0, "angry": -0.02}.get(mood, 0) * H
    bcol = shade(lk["hair"], 0.9)
    for side in (-1, 1):
        bx = cx + side * (0.19 if child else 0.175) * H; by = ey - (0.12 if child else 0.11) * H
        inner = -raise_ if mood == "worried" else raise_ * 0.5
        pts = [(bx - side * 0.09 * H, by + inner), (bx, by - 0.018 * H), (bx + side * 0.1 * H, by + 0.01 * H),
               (bx + side * 0.1 * H, by + 0.022 * H), (bx, by - 0.002 * H), (bx - side * 0.09 * H, by + inner + 0.022 * H)]
        d.polygon(pts, fill=bcol)
    if lk.get("glasses"):
        for side in (-1, 1):
            gx = cx + side * 0.175 * H
            d.rounded_rectangle((gx - 0.12 * H, ey - 0.085 * H, gx + 0.12 * H, ey + 0.08 * H), int(0.035 * H), outline=(60, 50, 50), width=max(3, int(0.016 * H)))
        d.line([(cx - 0.055 * H, ey - 0.02 * H), (cx + 0.055 * H, ey - 0.02 * H)], fill=(60, 50, 50), width=max(3, int(0.014 * H)))
    draw_mouth(d, cx, cy + (0.3 if child else 0.3) * H, H, talk, mood, lk, tongue)
    return im, (cx, cy + fh)

# ---------- torso sprites ----------
@lru_cache(maxsize=24)
def torso_base(who, H):
    lk = LOOK[who]; child = lk.get("child", False)
    sw = (0.74 if child else 0.98) * H
    Wd, Hd = int(sw * 2.6), int(H * 4.6)
    im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    cx, y0 = Wd / 2, H * 0.35
    def M(): return Image.new("L", (Wd, Hd), 0)
    skin = lk["skin"]
    # neck
    nm = M(); ImageDraw.Draw(nm).rounded_rectangle((cx - 0.15 * H, 0, cx + 0.15 * H, y0 + 0.2 * H), int(0.06 * H), fill=255)
    im.alpha_composite(_layer(nm, _np_grad(Wd, Hd, shade(skin, 0.84), shade(skin, 0.95), 0.25)))
    m = M(); d = ImageDraw.Draw(m)
    d.ellipse((cx - sw, y0, cx - sw + 0.75 * H, y0 + 0.8 * H), fill=255)
    d.ellipse((cx + sw - 0.75 * H, y0, cx + sw, y0 + 0.8 * H), fill=255)
    d.polygon([(cx - sw + 0.3 * H, y0 + 0.02 * H), (cx + sw - 0.3 * H, y0 + 0.02 * H), (cx + sw, y0 + 0.45 * H), (cx + sw * 1.02, Hd), (cx - sw * 1.02, Hd), (cx - sw, y0 + 0.45 * H)], fill=255)
    top = lk["top"]
    if top == "ikat":
        rgb = _ikat(Wd, Hd, lk["ikat"], scale=H / 150)
        rgb = rgb * (1 - 0.28 * np.clip(np.linspace(-1, 1, Wd)[None, :, None], 0, 1)) * (1 - 0.18 * np.linspace(0, 1, Hd)[:, None, None])
    elif top in ("coat", "nimcha"):
        rgb = _np_grad(Wd, Hd, (248, 248, 250), (214, 216, 222), 0.25) if top == "coat" else _np_grad(Wd, Hd, shade(lk["vest"], 1.25), shade(lk["vest"], 0.85), 0.3)
    else:
        rgb = _np_grad(Wd, Hd, shade(top, 1.12), shade(top, 0.82), 0.3)
    im.alpha_composite(_layer(m, rgb))
    d2 = ImageDraw.Draw(im)
    if top == "ikat":   # round neckline with gold trim
        d2.chord((cx - 0.3 * H, y0 - 0.2 * H, cx + 0.3 * H, y0 + 0.32 * H), 0, 180, fill=shade(skin, 0.9))
        d2.arc((cx - 0.3 * H, y0 - 0.2 * H, cx + 0.3 * H, y0 + 0.32 * H), 0, 180, fill=(226, 180, 90), width=max(3, int(0.03 * H)))
    elif top == "nimcha":
        d2.polygon([(cx - 0.34 * H, y0), (cx + 0.34 * H, y0), (cx + 0.12 * H, Hd), (cx - 0.12 * H, Hd)], fill=lk["blouse"])
        d2.chord((cx - 0.2 * H, y0 - 0.12 * H, cx + 0.2 * H, y0 + 0.2 * H), 0, 180, fill=shade(skin, 0.9))
        for sx in (-1, 1):
            d2.line([(cx + sx * 0.34 * H, y0), (cx + sx * 0.12 * H, Hd)], fill=lk["trim"], width=max(4, int(0.035 * H)))
            for j in range(6):
                yy = y0 + 0.4 * H + j * 0.45 * H
                xx = cx + sx * (0.34 - (yy - y0) / (Hd - y0) * 0.22) * H + sx * 0.06 * H
                d2.ellipse((xx - 0.025 * H, yy - 0.025 * H, xx + 0.025 * H, yy + 0.025 * H), fill=lk["trim"])
    elif top == "coat":
        d2.polygon([(cx - 0.32 * H, y0), (cx + 0.32 * H, y0), (cx + 0.18 * H, y0 + 1.4 * H), (cx - 0.18 * H, y0 + 1.4 * H)], fill=lk["inner"])
        if lk.get("tie"):
            d2.polygon([(cx - 0.06 * H, y0 + 0.05 * H), (cx + 0.06 * H, y0 + 0.05 * H), (cx + 0.09 * H, y0 + 1.0 * H), (cx, y0 + 1.12 * H), (cx - 0.09 * H, y0 + 1.0 * H)], fill=lk["tie"])
        for sx in (-1, 1):
            d2.polygon([(cx + sx * 0.32 * H, y0 - 0.02 * H), (cx + sx * 0.55 * H, y0 + 0.2 * H), (cx + sx * 0.18 * H, y0 + 1.4 * H)], fill=(232, 233, 238))
            d2.line([(cx + sx * 0.18 * H, y0 + 1.4 * H), (cx + sx * 0.16 * H, Hd)], fill=(196, 198, 206), width=max(2, int(0.012 * H)))
        d2.rounded_rectangle((cx + 0.42 * H, y0 + 0.9 * H, cx + 0.72 * H, y0 + 1.06 * H), int(0.03 * H), fill=(90, 140, 210))
    else:
        d2.chord((cx - 0.26 * H, y0 - 0.16 * H, cx + 0.26 * H, y0 + 0.26 * H), 0, 180, fill=shade(skin, 0.9))
        d2.arc((cx - 0.28 * H, y0 - 0.18 * H, cx + 0.28 * H, y0 + 0.28 * H), 0, 180, fill=shade(top, 0.8), width=max(3, int(0.035 * H)))
    # soft folds + head shadow on chest
    fm = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0)); fd = ImageDraw.Draw(fm)
    for j in range(3):
        x = cx + (j - 1) * 0.45 * H
        fd.line([(x, y0 + 1.0 * H), (x + 0.08 * H, Hd)], fill=(0, 0, 0, 40), width=int(0.05 * H))
    fd.ellipse((cx - 0.5 * H, y0 - 0.1 * H, cx + 0.5 * H, y0 + 0.35 * H), fill=(0, 0, 0, 70))
    fm = _soft(fm, 0.05 * H)
    fm.putalpha(ImageChops.multiply(fm.getchannel("A"), m))
    im.alpha_composite(fm)
    return im, cx, y0, sw

def arm_seg(d, a, b, w0, w1, col):
    ax, ay = a; bx, by = b
    ang = math.atan2(by - ay, bx - ax); nx, ny = -math.sin(ang), math.cos(ang)
    poly = [(ax + nx * w0 / 2, ay + ny * w0 / 2), (bx + nx * w1 / 2, by + ny * w1 / 2), (bx - nx * w1 / 2, by - ny * w1 / 2), (ax - nx * w0 / 2, ay - ny * w0 / 2)]
    d.polygon(poly, fill=col)
    d.ellipse((ax - w0 / 2, ay - w0 / 2, ax + w0 / 2, ay + w0 / 2), fill=col)
    d.ellipse((bx - w1 / 2, by - w1 / 2, bx + w1 / 2, by + w1 / 2), fill=col)
    d.line([(ax - nx * w0 * 0.25, ay - ny * w0 * 0.25), (bx - nx * w1 * 0.25, by - ny * w1 * 0.25)], fill=shade(col, 1.12), width=max(2, int(w1 * 0.18)))

def sleeve_col(lk, side):
    top = lk["top"]
    if top == "ikat": return lk["ikat"][1 if side < 0 else 0]
    if top == "coat": return (236, 237, 242) if side < 0 else (222, 224, 230)
    if top == "nimcha": return shade(lk["blouse"], 0.97 if side < 0 else 0.9)
    return shade(top, 1.02 if side < 0 else 0.9)

def person(L, who, x, y, hu, t, keys=(), talk=0.0, mood="neutral", seed=0, eye=None, tongue=False):
    lk = LOOK[who]; child = lk.get("child", False)
    y += hu * 0.3 * 0.85; hu *= 1.3
    if child: y += hu * 0.08
    p = pose_at(list(keys), t)
    d = ImageDraw.Draw(L)
    H = int(hu * SS)
    br = math.sin(t * 1.5 + seed) * 0.018 * H
    sway = math.sin(t * 0.6 + seed * 1.3) * 0.02 * H + p.get("lean", 0) * SS
    X, Y = x * SS + sway * 0.5, y * SS
    tb, tcx, ty0, sw = torso_base(who, H)
    ox, oy = X - tcx, Y - ty0 + br * 0.6
    # arms: back of shoulders, drawn after torso so gestures read clearly
    L.alpha_composite(tb, (int(ox), int(oy)))
    L1, L2 = (1.0 if child else 1.25) * H, (0.95 if child else 1.15) * H
    w0, w1 = (0.32 if child else 0.36) * H, (0.26 if child else 0.28) * H
    hands = []
    for side, ka, ke in ((-1, "la", "le"), (1, "ra", "re")):
        a = p.get(ka, 8) + 2.5 * math.sin(t * 1.5 + seed + side)
        e = p.get(ke, 12)
        sx, sy = X + side * (sw - 0.2 * H), Y + 0.32 * H + br * 0.6
        ex = sx + side * L1 * math.sin(math.radians(a)); ey = sy + L1 * math.cos(math.radians(a))
        hx = ex + side * L2 * math.sin(math.radians(a + e)); hy = ey + L2 * math.cos(math.radians(a + e))
        col = sleeve_col(lk, side)
        arm_seg(d, (sx, sy), (ex, ey), w0, w0 * 0.88, col)
        arm_seg(d, (ex, ey), (hx, hy), w0 * 0.86, w1, shade(col, 0.96))
        hr = 0.15 * H
        d.ellipse((hx - hr, hy - hr * 0.9, hx + hr, hy + hr * 1.1), fill=lk["skin"])
        d.ellipse((hx - hr * 0.7 + side * hr * 0.5, hy - hr * 0.9, hx + hr * 0.1 + side * hr * 0.5, hy - hr * 0.1), fill=shade(lk["skin"], 1.04))
        d.arc((hx - hr, hy - hr * 0.9, hx + hr, hy + hr * 1.1), 20, 160, fill=shade(lk["skin"], 0.8), width=max(2, int(H * 0.012)))
        hands.append((hx / SS, hy / SS))
    blink = blink_amt(t, seed)
    e_ = saccade(t, seed) if eye is None else clamp(eye + 0.25 * saccade(t, seed), -1, 1)
    tilt = p.get("tilt", 0) + 2.0 * math.sin(t * 0.8 + seed) + 1.2 * math.sin(t * 2.1 + seed * 2)
    hi, piv = head_img(who, H, t, talk, mood, clamp(e_ + p.get("eye", 0), -1, 1), blink, seed, tongue)
    hi = hi.rotate(tilt, Image.BICUBIC, center=piv)
    hx = X + p.get("hx", 0) * SS
    L.alpha_composite(hi, (int(hx - piv[0]), int(Y - (0.06 if child else 0.1) * H - piv[1] + br * 0.4)))
    return hands

# ================= v7: reference-character puppets (cv2 mesh warp) + realistic brain + new scenario =================
import cv2 as _cv2
AV = os.path.join(HERE, "av")

def _load(name):
    return np.array(Image.open(os.path.join(AV, name + ".png")).convert("RGBA"))

# anchors in sprite px (measured on the cut sprites)
RIGS = {
    "boy":  dict(img="boy_cut", eyes=[(126, 242, 36, 31), (231, 239, 36, 31)], mouth=(182, 306, 52), head=(182, 215, 165), neck=(185, 380),
                 skin=(246, 196, 168), lips=(205, 110, 100)),
    "mom":  dict(img="mom_cut", eyes=[(176, 220, 31, 24), (281, 232, 31, 24)], mouth=(220, 311, 42), head=(225, 220, 160), neck=(228, 380),
                 skin=(246, 200, 170), lips=(214, 120, 110)),
    "logo": dict(img="logo_cut", eyes=[(114, 113, 17, 14), (171, 100, 17, 14)], mouth=(158, 150, 24), head=(140, 115, 105), neck=(150, 215),
                 skin=(246, 206, 180), lips=(205, 110, 110), arm=((324, 254), (461, 103))),
}
_SPR = {}
def sprite(who):
    if who not in _SPR: _SPR[who] = _load(RIGS[who]["img"])
    return _SPR[who]

@lru_cache(maxsize=32)
def scaled(who, s100):
    s = s100 / 100.0
    im = sprite(who)
    h, w = im.shape[:2]
    return _cv2.resize(im, (int(w * s), int(h * s)), interpolation=_cv2.INTER_AREA)

def _overlay_face(img, rig, s, blink, talk):
    """Eyelids and an opening mouth painted on the scaled sprite before warping, so they move with the head."""
    pil = Image.fromarray(img, "RGBA"); d = ImageDraw.Draw(pil)
    if blink < 0.98:
        close = 1 - blink
        for (ex, ey, rx, ry) in rig["eyes"]:
            ex, ey, rx, ry = ex * s, ey * s, rx * s * 1.12, ry * s * 1.25
            lid = Image.new("L", pil.size, 0); ld = ImageDraw.Draw(lid)
            ld.ellipse((ex - rx, ey - ry, ex + rx, ey + ry), fill=255)
            cut = Image.new("L", pil.size, 0)
            ImageDraw.Draw(cut).rectangle((ex - rx - 2, ey - ry - 2, ex + rx + 2, ey - ry + 2 * ry * close), fill=255)
            m = ImageChops.multiply(lid, cut).filter(ImageFilter.GaussianBlur(max(0.6, s * 1.2)))
            col = Image.new("RGBA", pil.size, rig["skin"] + (255,))
            pil.paste(col, (0, 0), m)
            yl = ey - ry + 2 * ry * close
            d.arc((ex - rx * 0.95, yl - ry * 0.5, ex + rx * 0.95, yl + ry * 0.35), 15, 165, fill=(60, 36, 28), width=max(2, int(s * 4)))
    if talk > 0.1:
        mx, my, mw = rig["mouth"]; mx, my, mw = mx * s, my * s, mw * s
        h = mw * (0.08 + 0.42 * clamp(talk)); w = mw * (0.55 - 0.12 * clamp(talk))
        d.ellipse((mx - w, my - h * 0.35, mx + w, my + h), fill=(110, 36, 40))
        d.chord((mx - w * 0.8, my - h * 0.35, mx + w * 0.8, my + h * 0.3), 180, 360, fill=(250, 244, 238))
        d.chord((mx - w * 0.6, my + h * 0.2, mx + w * 0.6, my + h * 1.0), 180, 360, fill=(200, 92, 100))
        d.arc((mx - w * 1.05, my - h * 0.45, mx + w * 1.05, my + h * 1.1), 0, 180, fill=rig["lips"], width=max(2, int(s * 5)))
    return np.array(pil)

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None):
    rig = RIGS[who]
    base = scaled(who, int(round(s * 100)))
    h, w = base.shape[:2]
    blink = blink_amt(t, seed)
    img = _overlay_face(base, rig, s, blink, talk) if (blink < 0.98 or talk > 0.1) else base
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    # global: breathing (vertical stretch from the feet) + slow sway around the feet
    b = 0.006 * math.sin(t * 1.5 + seed)
    th = math.radians(0.7 * math.sin(t * 0.55 + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    # head: rotation around the neck + nod, smooth falloff
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.25 - dist) / (hr * 0.45), 0, 1) * np.clip((ny + hr * 0.15 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = math.radians(2.4 * math.sin(t * 0.9 + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 + seed)) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    # optional forearm gesture (logoped's pointer taps)
    if "arm" in rig and arm:
        (ex, ey), (tx, ty) = [(a * s, b_ * s) for a, b_ in rig["arm"]]
        vx, vy = tx - ex, ty - ey; L2 = vx * vx + vy * vy
        u = np.clip(((xx - ex) * vx + (yy - ey) * vy) / L2, -0.2, 1.2)
        px, py = ex + u * vx, ey + u * vy
        dd = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
        aw = np.clip((70 * s - dd) / (30 * s), 0, 1) * np.clip(u / 0.15, 0, 1)
        an = math.radians(arm)
        rx_ = ex + (xx - ex) * math.cos(an) + (yy - ey) * math.sin(an)
        ry_ = ey - (xx - ex) * math.sin(an) + (yy - ey) * math.cos(an)
        sx = sx + aw * (rx_ - xx); sy = sy + aw * (ry_ - yy)
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

def place(c, im, cx, top, shadow=True):
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.35)))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (int(cx - im.width / 2) + 14, int(top) + 10))
    c.alpha_composite(im, (int(cx - im.width / 2), int(top)))

# ---------- realistic brain (side view, gyri from warped noise, lit) ----------
@lru_cache(maxsize=4)
def real_brain(size=300):
    W_, H_ = size, int(size * 0.8)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    u, v = xx / W_, yy / H_
    m = Image.new("L", (W_, H_), 0); d = ImageDraw.Draw(m)
    d.ellipse((W_ * 0.04, H_ * 0.05, W_ * 0.96, H_ * 0.82), fill=255)          # cerebrum
    d.ellipse((W_ * 0.5, H_ * 0.55, W_ * 0.86, H_ * 0.9), fill=255)            # cerebellum
    d.polygon([(W_ * 0.5, H_ * 0.7), (W_ * 0.6, H_ * 0.7), (W_ * 0.6, H_ * 1.0), (W_ * 0.52, H_ * 1.0)], fill=255)   # stem
    m = m.filter(ImageFilter.GaussianBlur(2))
    rng = np.random.default_rng(3)
    n = np.zeros_like(u)
    for k in range(6):
        fq = 3 + k * 2.2; ph = rng.uniform(0, 6.28, 2); a = rng.uniform(0.6, 1.0) / (1 + k * 0.6)
        n += a * np.sin(fq * u * 6.28 + 2.0 * np.sin(fq * 0.7 * v * 6.28 + ph[0])) * np.cos(fq * v * 6.28 + 1.5 * np.sin(fq * 0.6 * u * 6.28 + ph[1]))
    f = n * 3.2
    sulci = np.abs(np.sin(f * math.pi))
    height = np.clip(sulci, 0, 1) ** 0.6
    gx = np.gradient(height, axis=1); gy = np.gradient(height, axis=0)
    light = np.clip(0.65 + (-gx * 0.6 - gy * 0.9) * 6, 0.35, 1.25)
    base = np.array((232, 170, 172), np.float32)
    rgb = base[None, None] * light[..., None]
    rgb *= (0.55 + 0.45 * height)[..., None]
    # global shading: top-left light, bottom-right falloff
    rgb *= (1.08 - 0.35 * np.clip((u + v - 0.6), 0, 1))[..., None]
    # lateral (Sylvian) fissure + cerebellum stripes + stem tone
    fis = np.exp(-((v - (0.52 - 0.18 * (u - 0.3))) / 0.012) ** 2) * ((u > 0.28) & (u < 0.72))
    rgb *= (1 - 0.6 * fis)[..., None]
    cb = ((u - 0.68) ** 2 / 0.033 + (v - 0.73) ** 2 / 0.03) < 1
    stripes = 0.75 + 0.25 * np.abs(np.sin(v * 90))
    rgb[cb] = (np.array((214, 150, 156), np.float32) * stripes[cb][:, None])
    stem = (u > 0.5) & (u < 0.6) & (v > 0.8)
    rgb[stem] = np.array((206, 150, 140), np.float32)
    im = Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).convert("RGBA")
    im.putalpha(m)
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((W_ * 0.12, H_ * 0.08, W_ * 0.6, H_ * 0.4), fill=(255, 240, 240, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(18)); hl.putalpha(ImageChops.multiply(hl.getchannel("A"), m))
    im.alpha_composite(hl)
    return with_shadow(im, 14, 16, 0.5)

@lru_cache(maxsize=4)
def brain_card(size=210):
    card = grad_card(size, size, 40, (68, 40, 32), (40, 22, 18)).copy()
    b = real_brain(int(size * 0.92))
    b = b.resize((int(size * 0.92), int(b.height * size * 0.92 / b.width)))
    card.alpha_composite(b, ((size - b.width) // 2, (size - b.height) // 2 + 6))
    return with_shadow(card, 14, 16)

@lru_cache(maxsize=2)
def speech_card(size=210):
    card = grad_card(size, size, 40, (68, 40, 32), (40, 22, 18)).copy()
    d = ImageDraw.Draw(card); s = size
    d.rounded_rectangle((s * 0.18, s * 0.24, s * 0.82, s * 0.66), int(s * 0.12), fill=(250, 240, 222))
    d.polygon([(s * 0.3, s * 0.64), (s * 0.44, s * 0.64), (s * 0.28, s * 0.8)], fill=(250, 240, 222))
    for j in range(5):
        hh = [0.08, 0.16, 0.22, 0.14, 0.07][j] * s
        x = s * (0.32 + j * 0.09)
        d.rounded_rectangle((x - s * 0.025, s * 0.45 - hh / 2, x + s * 0.025, s * 0.45 + hh / 2), int(s * 0.02), fill=TERRA)
    return with_shadow(card, 14, 16)

@lru_cache(maxsize=2)
def clinic_door():
    im = Image.new("RGBA", (260, 420), (0, 0, 0, 0))
    im.alpha_composite(grad_card(240, 400, 18, (236, 236, 240), (196, 198, 206)), (10, 10))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 220, 200), 12, fill=(170, 200, 224))
    d.ellipse((190, 230, 210, 250), fill=(150, 150, 160))
    d.rounded_rectangle((70, 260, 190, 340), 14, fill=(60, 130, 200))
    d.rectangle((122, 272, 138, 328), fill=WHITE); d.rectangle((102, 292, 158, 308), fill=WHITE)
    return with_shadow(im, 14, 14)

def chat_bubble(w=220, h=96):
    im = grad_card(w, h, 40, (92, 84, 80), (70, 64, 62)).copy()
    d = ImageDraw.Draw(im)
    for j in range(3): d.ellipse((w / 2 - 40 + j * 40 - 9, h / 2 - 9, w / 2 - 40 + j * 40 + 9, h / 2 + 9), fill=(230, 226, 220))
    return with_shadow(im, 10, 10)
CHAT = None

# ---------- backgrounds (no plant) ----------
@lru_cache(maxsize=4)
def room_bg(kind):
    h = HALF
    yy = np.linspace(0, 1, h)[:, None, None]
    wall0, wall1 = np.array((62, 32, 22), np.float32), np.array((36, 19, 13), np.float32)
    arr = (wall0 + (wall1 - wall0) * yy).repeat(W, 1)
    im = Image.fromarray(np.uint8(arr)).convert("RGBA")
    d = ImageDraw.Draw(im)
    if kind == "home":
        d.polygon([(120, 0), (340, 0), (560, h), (180, h)], fill=(255, 220, 160, 16))
        d.rounded_rectangle((760, 520, 1000, 760), 16, fill=(44, 30, 26), outline=(110, 72, 50), width=10)
        d.ellipse((900, 560, 950, 610), fill=(240, 226, 200))
    g = glow(700, (130, 58, 32)); im.alpha_composite(g.resize((1200, 1200)), (-60, 160))
    return im

def board_img(t, green):
    im = grad_card(300, 230, 20, (40, 70, 58), (28, 52, 42)).copy()
    d = ImageDraw.Draw(im); d.rounded_rectangle((0, 0, 299, 229), 20, outline=(150, 100, 64), width=12)
    tile = r_tile(130, "green" if green else "warm")
    im.alpha_composite(tile, (150 - tile.width // 2, 115 - tile.height // 2))
    return with_shadow(im, 14, 14)

# ---------- new scenario ----------
def scene(kind="room"): return room_bg(kind).copy()

def cart_intro(lt, t):
    c = scene()
    k = ease_out(lt / 0.8)
    m = puppet("mom", t, 0.62, seed=1)
    place(c, m, lerp(1250, 720, k), 560)
    for j, (x, y, ph) in enumerate(((250, 700, 0), (420, 620, 1.3))):
        kk = spring(lt - 0.5 - j * 0.25, w=10, z=0.6)
        float_card(c, icon_card("q", 170 + 30 * j), x, y + 12 * math.sin(t * 1.4 + ph), kk, rot=6 * math.sin(t * 0.9 + ph))
    return c

def cart_choice(lt, t):
    c = scene()
    tl = -9 if lt < 1.1 else (9 if lt < 2.1 else 0)
    tilt = lerp(0, tl, ease_io(((lt % 1.1) if lt < 2.2 else 1) / 0.35))
    m = puppet("mom", t, 0.62, talk=voice(t), seed=1, tilt=tilt)
    place(c, m, 540, 560)
    for j, (img, x) in enumerate(((speech_card(), 160), (brain_card(), 920))):
        k = spring(lt - 0.25 - j * 0.3, w=11, z=0.6)
        hot = (lt < 1.1 and j == 0) or (1.1 <= lt < 2.2 and j == 1)
        if hot:
            g = glow(320, GOLD); gg = g.resize((300, 300)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.6)))
            c.alpha_composite(gg, (x - 150, 700 - 150))
        float_card(c, img, x, 700 + 8 * math.sin(t * 1.3 + j), k * (1.06 if hot else 1.0))
    return c

def cart_family(lt, t):
    global CHAT
    if CHAT is None: CHAT = chat_bubble()
    c = scene("home")
    b = puppet("boy", t, 0.66, talk=(abs(math.sin(t * 9)) * 0.8 if 0.3 < lt < 2.2 else 0), seed=3)
    place(c, b, 300, 600)
    m = puppet("mom", t, 0.58, talk=voice(t), seed=2, tilt=-6)
    place(c, m, 640, 570)
    k = spring(lt - 0.3, w=11, z=0.5)
    sh = 7 * math.sin(lt * 42) if 0.5 < lt < 2.2 else 0
    float_card(c, r_tile(140, "warm" if lt < 1.4 else "gray"), 470 + sh, 640, k * (1 - 0.15 * clamp((lt - 1.4) / 0.4)))
    for j in range(3):   # relatives' comments sliding in from the right edge
        tj = 2.0 + j * 0.45
        if lt < tj: continue
        kk = ease_out((lt - tj) / 0.4)
        paste_alpha(c, CHAT, lerp(1100, 860, kk), 600 + j * 110, clamp(kk * 1.5))
    return c

def cart_practice(lt, t):
    c = scene()
    tap = 6 * abs(math.sin(lt * 3.2)) if lt < 3.0 else 0
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5, arm=-tap)
    place(c, lg, 250, 560)
    green = lt > 1.7
    paste_alpha(c, board_img(t, green), 520, 580, clamp(lt / 0.3))
    if green and lt < 2.6:
        g = glow(360, (120, 220, 140)); c.alpha_composite(g, (520 + 150 - 180, 580 + 130 - 180))
    b = puppet("boy", t, 0.6, talk=max(0, voice(t - 0.25) * 0.8) if lt > 0.8 else 0, seed=6)
    place(c, b, 930, 640)
    tn = 17.26 - (t - lt)
    if lt > tn:
        k = spring(lt - tn, w=11, z=0.7); out = ease_in((lt - tn - 1.1) / 0.5)
        float_card(c, desat_img(brain_card(150), clamp((lt - tn - 0.6) / 0.4)), 980 + 300 * out, 600, k, a=1 - out)
    return c

def cart_age(lt, t):
    c = scene("home")
    speak = lt > 2.24
    b = puppet("boy", t, 0.66, talk=(voice(t) if speak else 0), seed=7, nod=1.0 if lt < 1.5 else 0)
    place(c, b, 800, 590)
    k = spring(lt - 0.2, w=10, z=0.7)
    cb = cake_base()
    paste_alpha(c, with_shadow(cb, 14, 14), 320 - cb.width / 2 - 28, 900 - cb.height - 28 + (1 - k) * 60, clamp(k * 2))
    lit = 20.56
    d = ImageDraw.Draw(c)
    for j in range(5):
        x = 210 + j * 55; y0 = 680 + (1 - k) * 60
        d.rounded_rectangle((x - 8, y0 - 70, x + 8, y0), 6, fill=[GOLD, TERRA, (120, 180, 230), (140, 210, 140), (230, 140, 200)][j])
        if t > lit + j * 0.12:
            fl = 1 + 0.15 * math.sin(t * 20 + j)
            g = glow(120, GOLD); c.alpha_composite(g, (int(x - 60), int(y0 - 130)))
            d.ellipse((x - 9 * fl, y0 - 104 * fl, x + 9 * fl, y0 - 76), fill=(255, 214, 120))
    if speak:
        u = lt - 2.24
        pts = [(lerp(450, 650, q / 50), 640 + (26 * math.sin(q * 0.9 + t * 8) + 18 * math.sin(q * 2.7)) * clamp(u / 0.4)) for q in range(51)]
        d.line(pts, fill=WARN, width=6, joint="curve")
    return c

def cart_exam(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5, tilt=4 if lt > 1.8 else 0)
    place(c, lg, 230, 560)
    b = puppet("boy", t, 0.6, seed=6)
    place(c, b, 900, 640)
    if lt > 1.8:
        k = spring(lt - 1.8, w=10, z=0.6)
        pulse = 0.6 + 0.4 * abs(math.sin(t * 4))
        g = glow(340, AMBER); gg = g.resize((max(1, int(320 * k * pulse)), max(1, int(320 * k * pulse))))
        c.alpha_composite(gg, (int(600 - gg.width / 2), int(700 - gg.height / 2)))
        br = real_brain(360)
        float_card(c, br, 600, 730 + 8 * math.sin(t * 2), k)
    tp = 32.94 - (t - lt)
    if lt > tp:
        k = spring(lt - tp, w=12, z=0.5)
        float_card(c, icon_card("pill", 130), 650, 880, k, rot=8 * math.sin(t * 2))
    return c

def cart_refer(lt, t):
    global ENV_IMG
    if ENV_IMG is None: ENV_IMG = envelope_img()
    c = scene()
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5)
    place(c, lg, 230, 560)
    door = clinic_door()
    k = spring(lt - 0.2, w=10, z=0.7)
    paste_alpha(c, door, 860 - door.width / 2, 560 + (1 - k) * 80, clamp(k * 2))
    f = ease_io((lt - 0.8) / 0.9)
    x = lerp(420, 800, f); y = lerp(720, 690, f) - 90 * math.sin(math.pi * f)
    if lt < 1.9:
        paste_alpha(c, ENV_IMG.rotate(-12 * math.sin(math.pi * f), Image.BICUBIC, expand=True), x - 100, y - 80, clamp((lt - 0.4) / 0.3) * (1 - clamp((lt - 1.7) / 0.2)))
    if lt > 1.7:
        u = clamp((lt - 1.7) / 0.6)
        g = glow(360, (90, 150, 220)); gg = g.resize((max(1, int(380 * (0.6 + 0.4 * u))),) * 2)
        gg.putalpha(gg.getchannel("A").point(lambda v: int(v * (1 - 0.5 * u))))
        c.alpha_composite(gg, (int(860 - gg.width / 2), int(860 - 80 - gg.height / 2)))
    return c

def cart_success(lt, t):
    c = scene()
    jump = -abs(math.sin(lt * 5)) * 36 * clamp((lt - 0.6) / 0.3) * (1 - clamp((lt - 2.0) / 0.3))
    b = puppet("boy", t, 0.64, talk=0.25 if lt > 0.3 else 0, seed=6)
    place(c, b, 300, 600 + jump)
    lg = puppet("logo", t, 0.94, seed=5, arm=-6 * abs(math.sin(lt * 4)))
    place(c, lg, 820, 570)
    k = spring(lt - 0.2, w=10, z=0.5)
    g = glow(360, (120, 220, 140)); gg = g.resize((max(1, int(340 * k)),) * 2); c.alpha_composite(gg, (int(560 - gg.width / 2), int(660 - gg.height / 2)))
    float_card(c, r_tile(170, "green"), 560, 660, k)
    d = ImageDraw.Draw(c)
    rk = ease_out((lt - 0.4) / 1.2)
    d.arc((440, 540, 680, 780), -90, -90 + 360 * rk, fill=(140, 220, 150), width=10)
    rng = np.random.default_rng(5)
    for j in range(26):
        u = lt - 0.5 - rng.uniform(0, 0.4)
        if u <= 0: continue
        ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(240, 520)
        x = 560 + math.cos(ang) * sp * u; y = 660 + math.sin(ang) * sp * u + 380 * u * u
        if y > 950 or y < 560: continue
        col = [GOLD, TERRA, (120, 180, 230), (140, 210, 140)][j % 4]
        d.rectangle((x - 9, y - 4.5, x + 9, y + 4.5), fill=rgba(col, 1 - clamp(u / 1.6)))
    return c

def cart_home(lt, t):
    c = scene("home")
    d0 = ImageDraw.Draw(c)
    d0.rounded_rectangle((60, 840, 1020, 960), 40, fill=(110, 56, 46))
    m = puppet("mom", t, 0.6, talk=voice(t), seed=2, tilt=-4)
    place(c, m, 330, 560)
    b = puppet("boy", t, 0.6, talk=max(0, voice(t - 0.3) * 0.7), seed=3, nod=0.6)
    place(c, b, 800, 640)
    which = "rocket" if lt < 2.1 else "rainbow"
    fl = clamp((lt - 0.4) / 0.35) if lt < 2.1 else clamp((lt - 2.3) / 0.35)
    fc = flash_card(which, 0.5 + 0.5 * fl)
    paste_alpha(c, fc, 560 - fc.width / 2, 600 + 10 * math.sin(t * 1.5), 1.0)
    return c

PANELS.update({"intro": cart_intro, "choice": cart_choice, "family": cart_family, "practice": cart_practice, "age": cart_age,
               "exam": cart_exam, "refer": cart_refer, "success": cart_success, "home": cart_home})


def _chaikin(pts, it=4):
    for _ in range(it):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts

def _curve(pts, it=4):
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(pts[-1]); pts = q
    return pts

import cv2
@lru_cache(maxsize=4)
def real_brain(size=300):
    """Anatomical lateral view of a human brain (frontal lobe left): Turing-pattern gyri on a lit dome,
    Sylvian fissure, central sulcus, temporal lobe, cerebellum folia and brainstem."""
    S = 2
    W_, H_ = size * S, int(size * 0.80) * S
    def P(pts): return [(x * W_, y * H_) for x, y in pts]
    def mask_poly(pts):
        m = Image.new("L", (W_, H_), 0); ImageDraw.Draw(m).polygon(P(_chaikin(pts)), fill=255)
        return np.asarray(m, np.float32) / 255
    cer = mask_poly([(0.03, 0.47), (0.06, 0.26), (0.18, 0.09), (0.38, 0.02), (0.60, 0.03), (0.79, 0.11), (0.93, 0.26),
                     (0.98, 0.44), (0.94, 0.58), (0.84, 0.64), (0.70, 0.64), (0.60, 0.72), (0.44, 0.77), (0.31, 0.74),
                     (0.24, 0.64), (0.19, 0.60), (0.10, 0.62), (0.04, 0.57)])
    cbm = mask_poly([(0.62, 0.66), (0.76, 0.60), (0.90, 0.62), (0.93, 0.72), (0.84, 0.82), (0.70, 0.84), (0.60, 0.77)])
    stm = mask_poly([(0.55, 0.70), (0.64, 0.70), (0.66, 0.86), (0.64, 0.99), (0.57, 0.99), (0.56, 0.84)])
    cbm = cbm * (1 - cer); stm = stm * (1 - cer) * (1 - cbm)

    # dome height from distance to silhouette
    def dome(m, r):
        d = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / (r * W_)
        return np.sqrt(np.clip(1 - (1 - np.clip(d, 0, 1)) ** 2, 0, 1))
    hc, hb, hs = dome(cer, 0.16), dome(cbm, 0.07), dome(stm, 0.03)

    # gyri: labyrinth via difference-of-Gaussians iteration, biased so crests are wide and sulci narrow
    rng = np.random.default_rng(11)
    x = rng.standard_normal((H_, W_)).astype(np.float32)
    s1 = W_ * 0.0068; s2 = s1 * 2.0
    for _ in range(16):
        x = cv2.GaussianBlur(x, (0, 0), s1) - cv2.GaussianBlur(x, (0, 0), s2)
        x = np.tanh(x / (np.abs(x).mean() + 1e-6) * 2.0)
    g = cv2.GaussianBlur((x + 1) * 0.5, (0, 0), s1 * 0.35)
    g = np.clip((g - 0.0) / 0.5, 0, 1) ** 0.55

    # deep fissures drawn as soft grooves
    fis = Image.new("L", (W_, H_), 0); fd = ImageDraw.Draw(fis)
    fd.line(P(_curve([(0.22, 0.62), (0.34, 0.56), (0.48, 0.50), (0.60, 0.44), (0.66, 0.36)])), fill=255, width=int(W_ * 0.016))
    fd.line(P(_curve([(0.55, 0.03), (0.52, 0.14), (0.54, 0.22), (0.49, 0.32), (0.47, 0.42), (0.44, 0.50)])), fill=230, width=int(W_ * 0.010))
    fd.line(P(_curve([(0.30, 0.66), (0.42, 0.66), (0.55, 0.62)])), fill=170, width=int(W_ * 0.008))
    fis = cv2.GaussianBlur(np.asarray(fis, np.float32) / 255, (0, 0), W_ * 0.004)

    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32); u, v = xx / W_, yy / H_
    folia = 0.5 + 0.5 * np.cos((np.hypot(u - 0.66, (v - 0.40) * 0.8)) * 2 * math.pi * 55)
    folia = folia ** 0.6

    relief = np.where(cbm > 0.5, folia * 0.7, g * (1 - fis * 0.95))
    H = hc * 0.55 * cer + hb * 0.45 * cbm + hs * 0.35 * stm + relief * 0.10 * np.clip(cer + cbm, 0, 1)
    gx = cv2.Sobel(H, cv2.CV_32F, 1, 0, ksize=3) * (W_ / 60)
    gy = cv2.Sobel(H, cv2.CV_32F, 0, 1, ksize=3) * (W_ / 60)
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array((-0.5, -0.65, 0.58)); L /= np.linalg.norm(L)
    diff = np.clip((n * L).sum(2), 0, 1)
    hv = L + np.array((0, 0, 1.0)); hv /= np.linalg.norm(hv)
    spec = np.clip((n * hv).sum(2), 0, 1) ** 40 * 0.45
    ao = np.where(stm > 0.5, 1.0, 0.6 + 0.4 * np.clip(relief, 0, 1))

    crest = np.array((232, 186, 182), np.float32)
    deep = np.array((150, 88, 94), np.float32)
    t = np.clip(relief, 0, 1)[..., None]
    rgb = deep + (crest - deep) * t
    rgb = np.where((cbm > 0.5)[..., None], rgb * np.array((0.93, 0.86, 0.88)), rgb)
    rgb = np.where((stm > 0.5)[..., None], np.array((210, 166, 156), np.float32), rgb)
    rgb = rgb * (0.30 + 0.85 * diff)[..., None] * ao[..., None] + spec[..., None] * 255 * ao[..., None]
    rgb += np.array((40, 8, 14)) * (1 - diff)[..., None] * 0.4       # warm subsurface in shadow

    a = np.clip(cer + cbm + stm, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.8 * S)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA").resize((size, int(size * 0.80)), Image.LANCZOS)
    return with_shadow(im, 14, 16, 0.5)

# ================= v8: no lip movement; emotions (happy / sad) + body motion (arms, hands, head, blinks) =================
# limb rigs in sprite px
LIMBS = {
    "boy":  dict(arm=((318, 470), (335, 770), 46), hand=(118, 470, 70), brows=[(150, 168), (210, 168)], brow_r=48),
    "mom":  dict(hand=(232, 680, 120), brows=[(205, 172), (262, 176)], brow_r=46),
    "logo": dict(arm=((324, 254), (461, 103), 70), hand=(110, 360, 80), brows=[(126, 90), (160, 86)], brow_r=24),
}
MOUTH = {"boy": (176, 300, 54), "mom": (220, 312, 46), "logo": (158, 150, 24)}

# who feels what, by story time
MOODS = [  # (t0, t1, {who: mood})
    (1.8, 4.5, {"mom": "sad"}),
    (4.5, 7.05, {"mom": "calm"}),
    (7.05, 11.5, {"mom": "sad", "boy": "calm"}),
    (14.3, 19.0, {"logo": "happy", "boy": "happy"}),
    (19.0, 24.4, {"boy": "sad"}),
    (27.3, 33.9, {"logo": "calm", "boy": "sad"}),
    (33.9, 37.4, {"logo": "calm"}),
    (39.8, 42.2, {"logo": "happy", "boy": "happy"}),
    (42.2, 46.4, {"mom": "happy", "boy": "happy"}),
]
def mood_at(who, t):
    for a, b, m in MOODS:
        if a <= t < b:
            md = m.get(who, "calm")
            k = clamp((t - a) / 0.5)           # ease into the emotion at scene start
            return md, k
    return "calm", 1.0

def _field_seg(xx, yy, p0, p1, wid, ang):
    """Sample-offset for rotating a limb segment around p0 by ang degrees, smooth falloff."""
    (ex, ey), (tx, ty) = p0, p1
    vx, vy = tx - ex, ty - ey; L2 = vx * vx + vy * vy
    u = np.clip(((xx - ex) * vx + (yy - ey) * vy) / L2, -0.3, 1.3)
    px, py = ex + u * vx, ey + u * vy
    dd = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
    aw = np.clip((wid - dd) / (wid * 0.45), 0, 1) * np.clip(u / 0.25, 0, 1)
    aw = aw * aw * (3 - 2 * aw)
    an = math.radians(ang)
    rx_ = ex + (xx - ex) * math.cos(an) + (yy - ey) * math.sin(an)
    ry_ = ey - (xx - ex) * math.sin(an) + (yy - ey) * math.cos(an)
    return aw * (rx_ - xx), aw * (ry_ - yy)

def _field_blob(xx, yy, cx, cy, r, dx, dy):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    w_ = np.clip((r - d) / (r * 0.6), 0, 1); w_ = w_ * w_ * (3 - 2 * w_)
    return -w_ * dx, -w_ * dy

@lru_cache(maxsize=96)
def _expr_sprite(who, s100, sad_q):
    """Sad expression baked by a local warp: mouth corners pulled down (smile flattens), inner brows raised."""
    base = scaled(who, s100)
    if sad_q == 0: return base
    s = s100 / 100.0; a = sad_q / 10.0
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ox = np.zeros_like(xx); oy = np.zeros_like(yy)
    mx, my, mw = [v * s for v in MOUTH[who]]
    nx = (xx - mx) / (mw * 1.7)
    reg = np.clip(1 - nx ** 2, 0, 1) ** 1.5 * np.clip(1 - ((yy - my) / (mw * 0.8)) ** 2, 0, 1)
    oy -= a * reg * ((nx * 1.7) ** 2) * mw * 0.32 - a * reg * mw * 0.10   # corners down, centre up: smile -> frown
    L = LIMBS[who]
    for (bx, by) in L["brows"]:
        bx, by, br = bx * s, by * s, L["brow_r"] * s
        d = np.sqrt((xx - bx) ** 2 + (yy - by) ** 2)
        wb = np.clip((br * 0.8 - d) / (br * 0.5), 0, 1); wb = wb * wb * (3 - 2 * wb)
        oy += a * wb * br * 0.38                                     # sample from below = move up
    out = _cv2.remap(base, xx + ox, yy + oy, _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_REPLICATE)
    return out

def _lids(img, rig, s, close):
    if close <= 0.02: return img
    pil = Image.fromarray(img, "RGBA"); d = ImageDraw.Draw(pil)
    for (ex, ey, rx, ry) in rig["eyes"]:
        ex, ey, rx, ry = ex * s, ey * s, rx * s * 1.12, ry * s * 1.25
        lid = Image.new("L", pil.size, 0); ImageDraw.Draw(lid).ellipse((ex - rx, ey - ry, ex + rx, ey + ry), fill=255)
        cut = Image.new("L", pil.size, 0)
        ImageDraw.Draw(cut).rectangle((ex - rx - 2, ey - ry - 2, ex + rx + 2, ey - ry + 2 * ry * close), fill=255)
        m = ImageChops.multiply(lid, cut).filter(ImageFilter.GaussianBlur(max(0.6, s * 1.2)))
        pil.paste(Image.new("RGBA", pil.size, rig["skin"] + (255,)), (0, 0), m)
        yl = ey - ry + 2 * ry * close
        d.arc((ex - rx * 0.95, yl - ry * 0.5, ex + rx * 0.95, yl + ry * 0.35), 15, 165, fill=(60, 36, 28), width=max(2, int(s * 4)))
    return np.array(pil)

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None):
    """Body-only acting: mouth never moves. Emotion from MOODS drives posture, head, arms, lids and a baked sad face."""
    rig = RIGS[who]; L = LIMBS[who]
    mood, mk = mood_at(who, t)
    sad = mk if mood == "sad" else 0.0
    happy = mk if mood == "happy" else 0.0
    s100 = int(round(s * 100))
    base = _expr_sprite(who, s100, int(round(sad * 10)))
    h, w = base.shape[:2]
    # lids: normal blinks, heavier when sad
    blink = blink_amt(t, seed)
    close = max(1 - blink, 0.14 * sad)
    img = _lids(base, rig, s, close)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    # whole body: breathing + weight shift; happy = bouncier, sad = slumped & slow
    sp = 1.0 + 0.6 * happy - 0.35 * sad
    b = (0.006 + 0.004 * happy) * math.sin(t * 1.5 * sp + seed) - 0.012 * sad
    th = math.radians((0.8 + 0.8 * happy) * math.sin(t * 0.55 * sp + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    # head around the neck
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.25 - dist) / (hr * 0.45), 0, 1) * np.clip((ny + hr * 0.15 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = (2.4 * math.sin(t * 0.9 * sp + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt
          + happy * 3.5 * math.sin(t * 3.1 + seed) + sad * (5.0 + 1.0 * math.sin(t * 0.7)))
    ht = math.radians(ht)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 * sp + seed) + happy * 5 * abs(math.sin(t * 3.1 + seed)) - sad * 10) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    # arms / hands
    if "arm" in L:
        p0, p1, wid = L["arm"]
        p0 = (p0[0] * s, p0[1] * s); p1 = (p1[0] * s, p1[1] * s)
        if who == "logo":
            ang = arm + 3.0 * math.sin(t * 1.7 + seed) + happy * 7 * math.sin(t * 4.2)
        else:   # boy's free arm swings; happy = little waves, sad = hangs still
            ang = (3.5 * math.sin(t * 1.3 + seed)) * (1 - 0.7 * sad) + happy * 8 * math.sin(t * 4.5)
        ox, oy = _field_seg(xx, yy, p0, p1, wid * s, ang)
        sx += ox; sy += oy
    if "hand" in L:
        hx_, hy_, hr_ = L["hand"]
        hdx = 4 * math.sin(t * 1.1 + seed) * s
        hdy2 = (5 * math.sin(t * 1.6 + seed * 1.3) + happy * 9 * abs(math.sin(t * 5.0)) + sad * 8) * s
        ox, oy = _field_blob(xx, yy, hx_ * s, hy_ * s, hr_ * s, hdx, hdy2)
        sx += ox; sy += oy
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR,
                     borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

# backgrounds: no wall board/frame
@lru_cache(maxsize=4)
def room_bg(kind):
    h = HALF
    yy = np.linspace(0, 1, h)[:, None, None]
    wall0, wall1 = np.array((62, 32, 22), np.float32), np.array((36, 19, 13), np.float32)
    arr = (wall0 + (wall1 - wall0) * yy).repeat(W, 1)
    im = Image.fromarray(np.uint8(arr)).convert("RGBA")
    if kind == "home":
        ImageDraw.Draw(im).polygon([(120, 0), (340, 0), (560, h), (180, h)], fill=(255, 220, 160, 16))
    g = glow(700, (130, 58, 32)); im.alpha_composite(g.resize((1200, 1200)), (-60, 160))
    return im

def cart_home(lt, t):
    """Mom and boy at home together, both happy — no flashcards."""
    c = scene("home")
    ImageDraw.Draw(c).rounded_rectangle((60, 840, 1020, 960), 40, fill=(110, 56, 46))
    m = puppet("mom", t, 0.62, seed=2, tilt=-4)
    place(c, m, 400, 555)
    b = puppet("boy", t, 0.62, seed=3)
    place(c, b, 730, 630)
    return c

PANELS.update({"home": cart_home})

# ================= v9: new cast (girl, mom in blue) + "R/L at 2 y.o." scenario =================
RIGS.update({
    "girl": dict(img="girl_cut", eyes=[(255, 275, 48, 42), (452, 275, 48, 42)], mouth=(350, 380, 70), head=(350, 250, 230), neck=(350, 445),
                 skin=(246, 202, 180), lips=(205, 110, 100)),
    "mom3": dict(img="mom3_cut", eyes=[(140, 192, 30, 22), (238, 192, 30, 22)], mouth=(190, 262, 38), head=(190, 190, 125), neck=(195, 320),
                 skin=(240, 192, 162), lips=(200, 110, 100)),
    "mom2": dict(img="mom2_cut", eyes=[(152, 212, 26, 24), (277, 212, 26, 24)], mouth=(217, 285, 40), head=(215, 215, 150), neck=(215, 345),
                 skin=(240, 194, 166), lips=(205, 120, 110)),
})
LIMBS = {
    "girl": dict(arms=[((205, 455), (55, 300), 72, 1), ((495, 455), (650, 300), 72, -1)], brows=[(270, 182), (430, 182)], brow_r=55),
    "mom3": dict(arms=[((95, 400), (78, 555), 46, 1)], hand=(255, 565, 70), brows=[(170, 146), (218, 146)], brow_r=30),
    "mom2": dict(arms=[((105, 450), (62, 690), 48, 1), ((322, 450), (337, 700), 48, -1)], brows=[(187, 158), (247, 155)], brow_r=32),
    "logo": dict(arms=[((324, 254), (461, 103), 70, 0)], hand=(110, 360, 80), brows=[(126, 90), (160, 86)], brow_r=24),
}
MOUTH = {"mom3": (190, 262, 38), "girl": (350, 380, 70), "mom2": (217, 285, 40), "logo": (158, 150, 24)}
MOODS = [
    (0.0, 6.9, {"mom3": "sad", "girl": "calm"}),
    (6.9, 12.2, {"logo": "happy"}),
    (14.8, 17.0, {"logo": "happy"}),
    (17.0, 21.3, {"girl": "happy"}),
    (21.3, 25.4, {"mom3": "sad", "girl": "calm"}),
    (25.4, 28.2, {"mom3": "happy", "girl": "happy"}),
    (28.2, 32.4, {"mom3": "happy", "girl": "happy"}),
    (32.4, 36.6, {"girl": "happy"}),
    (39.0, 40.3, {"mom3": "calm", "girl": "calm"}),
    (40.3, 42.0, {"mom3": "happy", "girl": "happy"}),
]

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None, wave=0.0):
    """Body-only acting (mouth never moves): breathing, sway, head, arms, lids; sad face baked by warp."""
    rig = RIGS[who]; L = LIMBS[who]
    mood, mk = mood_at(who, t)
    sad = mk if mood == "sad" else 0.0
    happy = mk if mood == "happy" else 0.0
    s100 = int(round(s * 100))
    base = _expr_sprite(who, s100, int(round(sad * 10)))
    h, w = base.shape[:2]
    blink = blink_amt(t, seed)
    img = _lids(base, rig, s, max(1 - blink, 0.14 * sad))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    sp = 1.0 + 0.6 * happy - 0.35 * sad
    b = (0.006 + 0.004 * happy) * math.sin(t * 1.5 * sp + seed) - 0.012 * sad
    th = math.radians((0.8 + 0.8 * happy) * math.sin(t * 0.55 * sp + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.15 - dist) / (hr * 0.4), 0, 1) * np.clip((ny + hr * 0.12 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = (2.4 * math.sin(t * 0.9 * sp + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt
          + happy * 3.5 * math.sin(t * 3.1 + seed) + sad * (5.0 + 1.0 * math.sin(t * 0.7)))
    ht = math.radians(ht)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 * sp + seed) + happy * 5 * abs(math.sin(t * 3.1 + seed)) - sad * 10) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    for j, (p0, p1, wid, side) in enumerate(L.get("arms", [])):
        p0 = (p0[0] * s, p0[1] * s); p1 = (p1[0] * s, p1[1] * s)
        if who == "logo":
            ang = arm + 3.0 * math.sin(t * 1.7 + seed) + happy * 7 * math.sin(t * 4.2)
        else:
            ph = seed + j * 1.9
            ang = (3.0 * math.sin(t * 1.3 + ph)) * (1 - 0.7 * sad)
            ang += side * (happy * 7 * math.sin(t * 4.5 + j * math.pi) + wave * 12 * math.sin(t * 7.0 + j * math.pi))
            ang -= side * sad * 4
        ox, oy = _field_seg(xx, yy, p0, p1, wid * s, ang)
        sx += ox; sy += oy
    if "hand" in L:
        hx_, hy_, hr_ = L["hand"]
        ox, oy = _field_blob(xx, yy, hx_ * s, hy_ * s, hr_ * s, 4 * math.sin(t * 1.1 + seed) * s,
                             (5 * math.sin(t * 1.6 + seed * 1.3) + happy * 9 * abs(math.sin(t * 5.0))) * s)
        sx += ox; sy += oy
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR,
                     borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

# ---------- objects ----------
@lru_cache(maxsize=32)
def letter_tile(ch, size=150, mode="warm"):
    c0, c1 = {"warm": ((246, 186, 96), (214, 104, 70)), "green": ((140, 214, 140), (60, 150, 90)),
              "gray": ((150, 144, 140), (96, 92, 90)), "blue": ((150, 196, 236), (78, 124, 196)),
              "cream": ((252, 244, 228), (226, 210, 186))}[mode]
    im = grad_card(size, size, int(size * 0.24), c0, c1).copy()
    col = (90, 52, 38) if mode == "cream" else WHITE
    ImageDraw.Draw(im).text((size / 2, size / 2 + 4), ch, font=dfont("Black", int(size * (0.6 if len(ch) == 1 else 0.46))), fill=col, anchor="mm")
    return with_shadow(im, 12, 12)

@lru_cache(maxsize=4)
def check_badge(size=120):
    S2 = size * 3
    im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, S2 - 1, S2 - 1), fill=(84, 186, 116))
    d.ellipse((S2 * 0.06, S2 * 0.04, S2 * 0.94, S2 * 0.6), fill=(255, 255, 255, 30))
    d.line([(S2 * 0.27, S2 * 0.52), (S2 * 0.44, S2 * 0.68), (S2 * 0.74, S2 * 0.34)], fill=WHITE, width=int(S2 * 0.11), joint="curve")
    return with_shadow(im.resize((size, size), Image.LANCZOS), 10, 10)

def note_img(size, col, double=False):
    S2 = size * 3
    im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((S2 * 0.08, S2 * 0.66, S2 * 0.42, S2 * 0.92), fill=col)
    d.rectangle((S2 * 0.36, S2 * 0.12, S2 * 0.43, S2 * 0.8), fill=col)
    if double:
        d.ellipse((S2 * 0.56, S2 * 0.56, S2 * 0.9, S2 * 0.82), fill=col)
        d.rectangle((S2 * 0.84, S2 * 0.04, S2 * 0.91, S2 * 0.7), fill=col)
        d.polygon([(S2 * 0.36, S2 * 0.12), (S2 * 0.91, S2 * 0.02), (S2 * 0.91, S2 * 0.16), (S2 * 0.36, S2 * 0.26)], fill=col)
    else:
        d.polygon([(S2 * 0.43, S2 * 0.12), (S2 * 0.7, S2 * 0.3), (S2 * 0.66, S2 * 0.4), (S2 * 0.43, S2 * 0.28)], fill=col)
    return im.resize((size, size), Image.LANCZOS)
NOTES = None

@lru_cache(maxsize=8)
def bubble_img(ch, mode, flip=False):
    w_, h_ = 230, 190
    im = Image.new("RGBA", (w_, h_ + 40), (0, 0, 0, 0))
    im.alpha_composite(grad_card(w_, h_, 46, (252, 246, 236), (232, 220, 204)), (0, 0))
    d = ImageDraw.Draw(im)
    tx = 50 if not flip else w_ - 50
    d.polygon([(tx - 22, h_ - 4), (tx + 22, h_ - 4), (tx - 30 if not flip else tx + 30, h_ + 36)], fill=(232, 220, 204))
    t_ = letter_tile(ch, 120, mode)
    im.alpha_composite(t_, ((w_ - t_.width) // 2, (h_ - t_.height) // 2 + 4))
    return with_shadow(im, 12, 12)

def age_ruler(c, x0, x1, y, p):
    """Rounded track 2→5 years, progress p 0..1."""
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((x0, y - 10, x1, y + 10), 10, fill=(80, 50, 40))
    xp = lerp(x0, x1, clamp(p))
    if xp > x0 + 20: d.rounded_rectangle((x0, y - 10, xp, y + 10), 10, fill=(130, 208, 140))
    f = dfont("Black", 38)
    for j, yr in enumerate((2, 3, 4, 5)):
        x = lerp(x0, x1, j / 3)
        on = p >= j / 3 - 0.01
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(130, 208, 140) if on else (110, 74, 60))
        d.text((x, y + 52), str(yr), font=f, fill=WHITE if on else (170, 140, 126), anchor="mm")
    d.text((x1 + 18, y + 52), "yosh", font=dfont("Light", 34), fill=(220, 200, 186), anchor="lm") if x1 + 120 < W else None

@lru_cache(maxsize=8)
def age_chip(text):
    f = dfont("Black", 44)
    w_ = int(f.getlength(text)) + 64; h_ = 78
    im = grad_card(w_, h_, 39, (255, 214, 120), (232, 150, 60)).copy()
    ImageDraw.Draw(im).text((w_ / 2, h_ / 2 + 2), text, font=f, fill=(70, 34, 20), anchor="mm")
    return with_shadow(im, 10, 10)

# ---------- scenes ----------
def cart_question(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=1)
    place(c, m, 235, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 840, 620)
    # R and L swap places (she mixes them), then L gets "eaten"
    k = spring(lt - 0.4, w=10, z=0.6)
    sw = ease_io(((lt - 3.1) % 1.4) / 0.7) if lt > 3.1 else 0
    flip = int(max(0, lt - 3.1) // 1.4) % 2 == 1
    u = 1 - sw if flip else sw
    pr = (lerp(470, 640, u), 700 - 60 * math.sin(math.pi * u))
    pl = (lerp(640, 470, u), 700 + 60 * math.sin(math.pi * u))
    eat = clamp((lt - 4.15) / 0.6)
    float_card(c, letter_tile("R", 140, "warm"), pr[0], pr[1], k)
    float_card(c, letter_tile("L", 140, "gray" if eat > 0.3 else "blue"), pl[0], pl[1], k * (1 - 0.45 * eat), a=1 - 0.6 * eat)
    if lt > 0.44:
        float_card(c, age_chip("2 yosh 8 oy"), 555, 890, spring(lt - 0.44, w=12, z=0.5) * (1 - clamp((lt - 2.6) / 0.3)))
    if lt > 5.5:
        kk = spring(lt - 5.5, w=11, z=0.55)
        float_card(c, icon_card("q", 130), 430, 610 + 8 * math.sin(t * 2), kk, rot=8 * math.sin(t * 1.3))
    return c

def cart_normal(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, seed=5, arm=-5 * abs(math.sin(lt * 2.5)) if lt < 2.5 else 0)
    place(c, lg, 230, 560)
    k = spring(lt - 0.35, w=10, z=0.6)
    float_card(c, letter_tile("L", 170, "blue"), 680, 690 + 8 * math.sin(t * 1.6), k)
    if lt > 1.9:
        kb = spring(lt - 1.9, w=12, z=0.45)
        float_card(c, check_badge(96), 770, 610, kb)
    if lt > 2.9:
        a = clamp((lt - 2.9) / 0.4)
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0)); age_ruler(lay, 470, 880, 850, ease_io((lt - 3.3) / 1.6))
        paste_alpha(c, lay, 0, (1 - a) * 30, a)
    return c

def cart_same(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, seed=5)
    place(c, lg, 230, 560)
    k = spring(lt - 0.2, w=10, z=0.6)
    u = ease_io(clamp((lt - 0.4) / 0.8))
    float_card(c, letter_tile("R", 140, "warm"), lerp(560, 840, u), 720 - 70 * math.sin(math.pi * u), k)
    float_card(c, letter_tile("L", 140, "blue"), lerp(840, 560, u), 720 + 70 * math.sin(math.pi * u), k)
    if lt > 0.08:
        float_card(c, age_chip("2 yosh 8 oy"), 700, 880, spring(lt - 0.08, w=12, z=0.5))
    if lt > 0.66:
        kb = spring(lt - 0.66, w=12, z=0.45)
        g = glow(320, (120, 220, 140)); gg = g.resize((max(1, int(260 * kb)),) * 2)
        c.alpha_composite(gg, (int(700 - gg.width / 2), int(620 - gg.height / 2)))
        float_card(c, check_badge(110), 700, 620, kb)
    return c

def cart_sounds(lt, t):
    c = scene("home")
    g = puppet("girl", t, 0.5, seed=3)
    place(c, g, 830, 600)
    if lt > 0.18:
        ka = spring(lt - 0.18, w=12, z=0.5)
        float_card(c, age_chip("3 yosh" if lt < 1.2 else "3 yoshdan keyin"), 330, 625, ka)
    letters = "ABLRS"
    rng = np.random.default_rng(4)
    placed = lt > 3.1
    for j, ch in enumerate(letters):
        sx_, sy_ = 90 + j * 118, 760
        d = ImageDraw.Draw(c); d.rounded_rectangle((sx_ - 52, sy_ - 52, sx_ + 52, sy_ + 52), 22, outline=(120, 80, 62), width=4)
        st = 0.3 + j * 0.42
        if lt < st: continue
        f = ease_out(clamp((lt - st) / 0.7))
        x0, y0 = rng.uniform(60, 640), rng.uniform(600, 920)
        r0 = rng.uniform(-40, 40)
        x = lerp(x0, sx_, f); y = lerp(y0, sy_, f) - 50 * math.sin(math.pi * f)
        float_card(c, letter_tile(ch, 104, "green" if placed else "cream"), x, y, clamp((lt - st) / 0.2), rot=r0 * (1 - f))
    if placed:
        kb = spring(lt - 3.1, w=12, z=0.45)
        float_card(c, check_badge(90), 330, 640, kb)
    return c

def cart_ok(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=1, tilt=-3)
    place(c, m, 235, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    wob = clamp((lt - 3.3) / 0.3) * (1 - clamp((lt - 4.3) / 0.3))
    tiles = (("Sh", "warm", 0.56, 480, 680), ("J", "warm", 0.86, 585, 680), ("Ch", "warm", 1.16, 690, 680),
             ("R", "warm", 1.46, 530, 795), ("L", "blue", 2.54, 640, 795))
    for j, (ch, mode, st, x, y) in enumerate(tiles):
        if lt < st: continue
        k = spring(lt - st, w=12, z=0.55)
        sh = wob * 8 * math.sin(lt * 38 + j)
        rot = wob * 10 * math.sin(lt * 21 + j * 2)
        float_card(c, letter_tile(ch, 100, mode), x + sh, y + 5 * math.sin(t * 1.5 + j), k, rot=rot)
    if lt > 5.38:
        float_card(c, age_chip("3 yosh"), 585, 895, spring(lt - 5.38, w=12, z=0.5))
    if lt > 4.3:
        kb = spring(lt - 4.3, w=12, z=0.45)
        g2 = glow(320, (120, 220, 140)); gg = g2.resize((max(1, int(280 * kb)),) * 2)
        c.alpha_composite(gg, (int(745 - gg.width / 2), int(770 - gg.height / 2)))
        float_card(c, check_badge(90), 745, 770, kb)
    return c

def cart_tongue(lt, t):
    global MIRROR
    if MIRROR is None: MIRROR = mirror_img()
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=2)
    place(c, m, 220, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    k = spring(lt - 0.2, w=10, z=0.65)
    mi = MIRROR.resize((int(MIRROR.width * 1.25), int(MIRROR.height * 1.25)))
    paste_alpha(c, mi, 545 - mi.width / 2, 610 + (1 - k) * 60, clamp(k * 2))
    if lt > 2.2:
        kk = spring(lt - 2.2, w=11, z=0.55)
        float_card(c, icon_card("mouth", 120), 545, 735 + 6 * math.sin(t * 3), kk)
    return c

def cart_music(lt, t):
    global NOTES
    if NOTES is None: NOTES = [note_img(90, col, j % 2 == 1) for j, col in enumerate((GOLD, (150, 196, 236), (240, 150, 170), (140, 214, 140)))]
    c = scene("home")
    beat = (lt * 2.0) % 1.0
    pulse = math.exp(-beat * 5)
    for r_, a_ in ((260, 0.35), (380, 0.2)):
        rr = int(r_ * (1 + 0.15 * pulse))
        gg = glow(rr, (220, 140, 90)).resize((rr * 2, rr * 2))
        gg.putalpha(gg.getchannel("A").point(lambda v: int(v * (a_ + 0.4 * pulse))))
        c.alpha_composite(gg, (540 - rr, 760 - rr))
    g = puppet("girl", t, 0.52, seed=3, wave=1.0, jump=-14 * pulse)
    place(c, g, 540, 590)
    for j in range(8):
        st = 0.2 + j * 0.45
        u = lt - st
        if u <= 0 or u > 2.6: continue
        side = -1 if j % 2 == 0 else 1
        x = 540 + side * (170 + 110 * u) + 20 * math.sin(u * 5 + j)
        y = 860 - 150 * u
        if y < 560: continue
        paste_alpha(c, NOTES[j % 4].rotate(10 * math.sin(u * 4 + j), Image.BICUBIC, expand=True), x - 45, y - 45,
                    clamp(u / 0.2) * (1 - clamp((u - 2.0) / 0.6)))
    return c

def cart_correct(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=2, tilt=-4)
    place(c, m, 220, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    k1 = spring(lt - 0.2, w=11, z=0.6)
    wrong = lt < 0.78
    sh = 6 * math.sin(lt * 40) if 0.25 < lt < 0.7 else 0
    float_card(c, bubble_img("L", "gray" if wrong else "blue", True), 660 + sh, 640, k1 * (1 - 0.25 * clamp((lt - 0.78) / 0.3)))
    if lt > 0.78:
        k2 = spring(lt - 0.78, w=11, z=0.55)
        float_card(c, bubble_img("L", "green"), 450, 700, k2)
    if lt > 1.3:
        kb = spring(lt - 1.3, w=12, z=0.45)
        float_card(c, check_badge(84), 545, 620, kb)
    return c

PANELS.update({"question": cart_question, "normal": cart_normal, "same": cart_same, "sounds": cart_sounds, "ok": cart_ok,
               "tongue": cart_tongue, "music": cart_music, "correct": cart_correct})

def decode(fi):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{fi / FPS:.4f}", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

if sys.argv[3] == "preview":
    for tt in [float(x) for x in sys.argv[4].split(",")]:
        fi = int(tt * FPS); p = decode(fi)
        img = Image.frombytes("RGB", (SW, SH), p.stdout.read(SW * SH * 3)); p.kill()
        render(fi, img).save(f"{OUT}_{tt:05.2f}.png")
    sys.exit(0)

a_, b_ = int(sys.argv[3]), min(int(sys.argv[4]), N)
dec = decode(a_)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", OUT + ".mp4"], stdin=subprocess.PIPE)
last = None
for i in range(a_, b_):
    buf = dec.stdout.read(SW * SH * 3)
    if len(buf) == SW * SH * 3: last = Image.frombytes("RGB", (SW, SH), buf)
    enc.stdin.write(render(i, last).tobytes())
enc.stdin.close(); enc.wait(); dec.kill()
print("done", a_, b_)
