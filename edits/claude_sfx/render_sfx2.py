#!/usr/bin/env python3
"""Expert talking-head + motion-graphics edit: "Claude + sound effects".

usage: render_sfx.py EXPERT.mov OUT_PREFIX START END      (frame range -> OUT_PREFIX.mp4)
       render_sfx.py EXPERT.mov OUT_PREFIX preview T1,T2,...
"""
import math
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
SW, SH = 720, 1280
N = 977
END = N / FPS

# ---------- palette ----------
BG0 = (16, 8, 6)
BG1 = (52, 22, 14)
PANEL = (28, 14, 10)
PANEL2 = (36, 18, 13)
CREAM = (247, 233, 210)
MUTED = (150, 118, 98)
AMBER = (232, 160, 58)
GOLD = (246, 198, 92)
TERRA = (217, 119, 87)
WARN = (205, 92, 66)

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
def rgba(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))

# ---------- static layers ----------
def radial_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d1 = np.sqrt(((xx - 300) / 950) ** 2 + ((yy - 520) / 950) ** 2)
    d2 = np.sqrt(((xx - 900) / 800) ** 2 + ((yy - 1600) / 800) ** 2)
    g = np.clip(1 - d1, 0, 1) ** 1.6 * 0.9 + np.clip(1 - d2, 0, 1) ** 1.8 * 0.55
    base = np.array(BG0, np.float32); top = np.array(BG1, np.float32) * 1.2
    img = base[None, None] + (top - base)[None, None] * g[..., None]
    return Image.fromarray(np.uint8(np.clip(img, 0, 255))).convert("RGBA")
BG = radial_bg()

def top_scrim(alpha=0.72, h=760):
    a = np.clip(1 - np.arange(H) / h, 0, 1) ** 1.7 * alpha * 255
    v = np.zeros((H, W, 4), np.uint8); v[..., :3] = BG0; v[..., 3] = a[:, None].astype(np.uint8)
    return Image.fromarray(v)
SCRIM_TOP = top_scrim()

def rr(d, box, r, **kw): d.rounded_rectangle(box, int(r), **kw)

@lru_cache(maxsize=16)
def soft_shadow(w, h, r):
    pad = 90
    sh = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 22, pad + w, pad + h + 22), r, fill=(3, 1, 0, 170))
    return sh.resize((sh.width // 4, sh.height // 4)).filter(ImageFilter.GaussianBlur(8)).resize(sh.size, Image.BILINEAR)

def panel(canvas, x, y, w, h, r=28, fill=PANEL, alpha=1.0):
    if alpha <= 0.01: return
    sh = soft_shadow(int(w), int(h), r)
    if alpha < 1:
        sh = sh.copy(); sh.putalpha(sh.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(sh, (int(x) - 90, int(y) - 90))
    lay = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rr(d, (1, 1, w + 1, h + 1), r, fill=rgba(fill, alpha), outline=(255, 236, 214, int(46 * alpha)), width=2)
    canvas.alpha_composite(lay, (int(x) - 1, int(y) - 1))

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

# ---------- captions: always top-left, thin line + optional SemiBold line, wipe from the left ----------
@lru_cache(maxsize=64)
def cap_layer(txt, style):
    f = font("Light", 58) if style == "thin" else dfont("SemiBold", 88)
    return shadowed(text_layer(txt, f, CREAM, pad=8))

CAPTIONS = [  # (lines[(text, style, t_in)], t_out)
    ([("Montajning bitta fishkasi bor —", "thin", 2.10), ("sound effektlar", "bold", 3.10)], 4.25),
    ([("Har qanday motion videoni", "thin", 4.75), ("jonlantiradi", "bold", 7.05)], 9.25),
    ([("To'g'ri, Claude montajni", "thin", 9.65), ("o'zi qiladi", "bold", 10.60)], 11.20),
    ([("Lekin bitta", "thin", 14.62), ("nozik tomoni bor", "bold", 15.05)], 16.00),
    ([("SFX animatsiyaga", "thin", 16.35), ("mos tushmaydi", "bold", 17.05)], 19.45),
    ([("Motion montajchilar ishlatadigan", "thin", 21.95), ("professional SFX", "bold", 22.30)], 23.70),
    ([("Claude agentingizga", "thin", 23.85), ("integratsiya", "bold", 24.65)], 25.45),
    ([("Kontentingiz", "thin", 25.60), ("yangi darajada", "bold", 26.30)], 27.45),
    ([("Buni sizga", "thin", 27.70), ("tekin o'rgataman", "bold", 27.95)], 29.00),
    ([("Faqat bitta", "thin", 29.15), ("kommentariya qoldiring", "bold", 30.45)], 99.0),
]
CAP_X, CAP_Y = 64, 318

def wipe(canvas, lay, x, y, k):
    if k <= 0.002: return
    wv = max(1, int(lay.width * k))
    piece = lay.crop((0, 0, wv, lay.height))
    edge = min(70, wv)
    if edge > 1 and k < 1:
        a = np.array(piece.getchannel("A"), np.float32)
        a[:, wv - edge:] *= np.linspace(1, 0, edge)[None, :]
        piece.putalpha(Image.fromarray(np.uint8(a)))
    paste_alpha(canvas, piece, x - 30 * (1 - k), y)

def draw_captions(canvas, t):
    for lines, t_out in CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.4: continue
        out = ease_in((t - t_out) / 0.35) if t > t_out else 0.0
        y = CAP_Y
        for txt, style, t_in in lines:
            lay = cap_layer(txt, style)
            k = ease_out((t - t_in) / 0.6) * (1 - out)
            if t > t_out:   # exit: wipe back out to the left
                k = 1 - out
            if t >= t_in:
                wipe(canvas, lay, CAP_X, y - 20 * out, k)
            y += 78 if style == "thin" else 108

# ---------- expert ----------
PUNCH = [(3.10, 1.085, 4.40), (14.54, 1.10, 16.10), (27.70, 1.06, END + 1)]
def expert_zoom(t):
    z = 1.0 + 0.03 * (0.5 + 0.5 * math.sin(t * 0.21))
    for t0, amt, t1 in PUNCH:
        if t0 <= t < t1:
            z *= lerp(1.0, amt, spring(t - t0, w=9, z=0.8))
    return z

def expert_frame(src, t):
    z = expert_zoom(t)
    cw, ch = SW / z, SH / z
    cx, cy = SW / 2, SH * 0.47
    cx = clamp(cx, cw / 2, SW - cw / 2); cy = clamp(cy, ch / 2, SH - ch / 2)
    im = src.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).convert("RGBA")
    im.alpha_composite(SCRIM_TOP)
    return im

# ---------- shared timeline graphic ----------
MON = (80, 560, 920, 500)        # monitor card x, y, w, h
TL = (80, 1110, 920, 430)        # timeline card
TX0, TX1 = 190, 960              # track x range

def playhead_x(lt, t_a, t_b): return lerp(TX0, TX1, clamp((lt - t_a) / (t_b - t_a)))

def waveform_block(w, h, col, seed):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rr(d, (0, 0, w - 1, h - 1), 12, fill=rgba(col, 0.28), outline=rgba(col, 0.9), width=2)
    rng = np.random.default_rng(seed)
    n = max(3, int(w // 9))
    for i in range(n):
        x = 8 + i * (w - 16) / n
        a = (0.25 + 0.75 * math.exp(-i / (n * 0.35))) * rng.uniform(0.5, 1)
        bh = (h - 18) * a
        d.line([(x, h / 2 - bh / 2), (x, h / 2 + bh / 2)], fill=rgba(col, 0.95), width=3)
    return im

def diamond(d, x, y, s, col, a=1.0):
    d.polygon([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], fill=rgba(col, a))

def draw_timeline(canvas, lt, hits_x, sfx_x, shown_sfx, connectors, ok=True, alpha=1.0, ph=None):
    x, y, w, h = TL
    panel(canvas, x, y, w, h, 26, PANEL, alpha)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # ruler
    for i in range(0, 33):
        tx = lerp(TX0, TX1, i / 32)
        th = 16 if i % 4 == 0 else 8
        d.line([(tx, y + 34), (tx, y + 34 + th)], fill=rgba(MUTED, 0.6 * alpha), width=2)
    lab = font("Medium", 24)
    for txt, ty in (("V1", y + 112), ("KF", y + 202), ("A1", y + 300)):
        d.text((x + 34, ty), txt, font=lab, fill=rgba(MUTED, alpha), anchor="lm")
    # V1 clips
    for i, (a, b) in enumerate(((TX0, 470), (478, 742), (750, TX1))):
        rr(d, (a, y + 82, b, y + 142), 10, fill=rgba((92, 50, 36), alpha), outline=rgba((140, 84, 60), alpha), width=2)
    # keyframes
    d.line([(TX0, y + 202), (TX1, y + 202)], fill=rgba(MUTED, 0.25 * alpha), width=2)
    for hx in hits_x:
        diamond(d, hx, y + 202, 13, GOLD, alpha)
    # connectors
    for (ax, bx), k in connectors:
        if k <= 0: continue
        col = CREAM if ok else WARN
        if ok:
            d.line([(ax, y + 218), (ax, lerp(y + 218, y + 262, k))], fill=rgba(col, 0.8 * alpha), width=2)
        else:
            yy = y + 236
            for s in range(int(ax), int(lerp(ax, bx, k)), 14):
                d.line([(s, yy), (min(s + 7, bx), yy)], fill=rgba(col, alpha), width=3)
    canvas.alpha_composite(lay)
    # SFX blocks drop into A1
    for i, (sx, k) in enumerate(zip(sfx_x, shown_sfx)):
        if k <= 0: continue
        blk = waveform_block(118, 74, TERRA, 11 + i)
        yy = y + 263 - (1 - k) * 60
        paste_alpha(canvas, blk, sx - 10, yy, clamp(k * 2) * alpha)
    # playhead
    if ph is not None:
        d2 = ImageDraw.Draw(canvas)
        d2.line([(ph, y + 26), (ph, y + h - 22)], fill=rgba(CREAM, alpha), width=3)
        d2.polygon([(ph - 11, y + 18), (ph + 11, y + 18), (ph, y + 34)], fill=rgba(CREAM, alpha))

def monitor(canvas, lt, pops, alpha=1.0, warn_shake=0.0):
    x, y, w, h = MON
    panel(canvas, x, y, w, h, 30, (24, 12, 9), alpha)
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # subtle grid
    for gx in range(0, int(w), 80):
        d.line([(gx, 0), (gx, h)], fill=(255, 236, 214, int(10 * alpha)), width=1)
    for gy in range(0, int(h), 80):
        d.line([(0, gy), (w, gy)], fill=(255, 236, 214, int(10 * alpha)), width=1)
    cx, cy = w / 2, h / 2
    k0, k1, k2, k3 = pops
    if k0 > 0:   # circle pop
        r = 70 * k0
        d.ellipse((cx - 250 - r, cy - r, cx - 250 + r, cy + r), fill=rgba(TERRA, alpha))
    if k1 > 0:   # bar slides in
        bx = lerp(-300, cx - 140, k1)
        rr(d, (bx, cy - 120, bx + 300, cy - 70), 25, fill=rgba(AMBER, alpha))
    if k2 > 0:   # square rotate-pop
        sq = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        rr(ImageDraw.Draw(sq), (20, 20, 140, 140), 26, fill=rgba(CREAM, alpha))
        sq = sq.rotate((1 - k2) * 70, Image.BICUBIC)
        s = max(0.05, k2)
        sq = sq.resize((max(1, int(160 * s)), max(1, int(160 * s))), Image.BICUBIC)
        lay.alpha_composite(sq, (int(cx + 90 - sq.width / 2), int(cy + 40 - sq.height / 2)))
    if k3 > 0:   # ring expand
        rr_ = lerp(20, 120, k3)
        d.ellipse((cx + 260 - rr_, cy - 60 - rr_, cx + 260 + rr_, cy - 60 + rr_), outline=rgba(GOLD, alpha * (1.2 - k3 * 0.4)), width=6)
    ox = int(6 * math.sin(lt * 70) * warn_shake)
    canvas.alpha_composite(lay, (int(x) + ox, int(y)))

def pop_k(lt, th, w=13, z=0.5): return spring(lt - th, w=w, z=z) if lt >= th else 0.0

# ---------- scenes ----------
def scene_A(lt):   # 4.40 – 9.40: SFX lands exactly on every animation beat
    c = BG.copy()
    t_a, t_b = 0.55, 4.7
    hits_t = [1.20, 2.20, 3.20, 4.10]
    hits_x = [playhead_x(h, t_a, t_b) for h in hits_t]
    pops = [pop_k(lt, h) for h in hits_t]
    monitor(c, lt, pops)
    shown = [pop_k(lt, h, w=16, z=0.6) for h in hits_t]
    conn = [((hx, hx), ease_out((lt - h) / 0.25)) for hx, h in zip(hits_x, hits_t)]
    draw_timeline(c, lt, hits_x, hits_x, shown, conn, ok=True, ph=playhead_x(lt, t_a, t_b))
    return c

def scene_C(lt):   # 16.10 – 19.60: SFX arrives late — out of sync
    c = BG.copy()
    t_a, t_b = 0.35, 3.4
    hits_t = [0.70, 1.70, 2.70]
    late = 0.35
    hits_x = [playhead_x(h, t_a, t_b) for h in hits_t]
    sfx_x = [playhead_x(h + late, t_a, t_b) for h in hits_t]
    pops = [pop_k(lt, h) for h in hits_t] + [0.0]
    shake = 0.0
    if 1.45 < lt < 1.85: shake = 1 - (lt - 1.45) / 0.4
    monitor(c, lt, pops, warn_shake=shake)
    shown = [pop_k(lt, h + late, w=16, z=0.6) for h in hits_t]
    conn = [((a, b), ease_out((lt - h) / late)) for a, b, h in zip(hits_x, sfx_x, hits_t)]
    draw_timeline(c, lt, hits_x, sfx_x, shown, conn, ok=False, ph=playhead_x(lt, t_a, t_b))
    # offset labels
    for a, b, h in zip(hits_x, sfx_x, hits_t):
        k = ease_out((lt - h - late) / 0.3)
        if k > 0:
            lab = text_layer("+0.35s", font("Medium", 24), rgba(WARN, 1))
            paste_alpha(c, lab, (a + b) / 2 - lab.width / 2, TL[1] + 236 - 44, k)
    return c

AGENT_ROWS = [("Sound effektlar", "SFX", 11.46), ("Fon musiqasi", "Audio", 12.30), ("Animatsiyalar", "Motion", 12.94)]
def scene_B(lt):   # 11.30 – 14.50: Claude agent doing the edit
    c = BG.copy()
    t = 11.30 + lt
    x, y, w, h = 80, 560, 920, 800
    k = spring(lt, w=10, z=0.8)
    panel(c, x, y + (1 - k) * 60, w, h, 34, PANEL, clamp(lt / 0.25))
    oy = (1 - k) * 60
    d = ImageDraw.Draw(c)
    # header
    d.ellipse((x + 50, y + 58 + oy, x + 98, y + 106 + oy), fill=TERRA)
    d.text((x + 122, y + 82 + oy), "Claude", font=font("SemiBold", 44), fill=CREAM, anchor="lm")
    d.text((x + 288, y + 84 + oy), "· montaj agenti", font=font("Light", 36), fill=MUTED, anchor="lm")
    d.line([(x + 50, y + 150 + oy), (x + w - 50, y + 150 + oy)], fill=(255, 236, 214, 30), width=2)
    done_all = t > 13.80
    status = "Tayyor" if done_all else "Bajarilmoqda" + "." * (1 + int(t * 3) % 3)
    d.text((x + 50, y + 196 + oy), status, font=font("Light", 32), fill=TERRA if done_all else MUTED, anchor="lm")
    for i, (name, tag, t0) in enumerate(AGENT_ROWS):
        if t < t0: continue
        kr = spring(t - t0, w=13, z=0.7)
        ry = y + 270 + i * 150 + oy
        rx = x + 50 + (1 - kr) * 40
        a = clamp((t - t0) / 0.2)
        row = Image.new("RGBA", (w - 100, 120), (0, 0, 0, 0))
        rd = ImageDraw.Draw(row)
        rr(rd, (0, 0, w - 101, 119), 22, fill=rgba(PANEL2, 1), outline=(255, 236, 214, 30), width=2)
        cx, cy = 62, 60
        tc = t - t0 - 0.45
        if tc < 0:   # spinner
            ang = (t * 360 * 1.4) % 360
            rd.arc((cx - 22, cy - 22, cx + 22, cy + 22), ang, ang + 260, fill=TERRA, width=5)
        else:        # check draws itself
            rd.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=rgba(TERRA, 1))
            p = ease_out(tc / 0.3)
            p1 = (cx - 11, cy + 1); p2 = (cx - 3, cy + 10); p3 = (cx + 13, cy - 9)
            if p < 0.4:
                q = p / 0.4; rd.line([p1, (lerp(p1[0], p2[0], q), lerp(p1[1], p2[1], q))], fill=CREAM, width=5)
            else:
                q = (p - 0.4) / 0.6; rd.line([p1, p2, (lerp(p2[0], p3[0], q), lerp(p2[1], p3[1], q))], fill=CREAM, width=5, joint="curve")
        rd.text((116, 60), name, font=font("Regular", 44), fill=CREAM, anchor="lm")
        rd.text((w - 140, 60), tag, font=font("Light", 30), fill=MUTED, anchor="rm")
        paste_alpha(c, row, rx, ry, a)
    return c

SFX_CHIPS = ["Cine Strike", "Cyber Shift", "Glass Shine", "Deep Whoosh", "Riser", "Sparkle"]
NODE = (540, 1420)
def chip_img(name, i):
    im = Image.new("RGBA", (420, 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rr(d, (0, 0, 419, 139), 26, fill=rgba(PANEL2, 1), outline=(255, 236, 214, 40), width=2)
    rng = np.random.default_rng(i + 3)
    for j in range(12):
        bh = rng.uniform(14, 70)
        bx = 34 + j * 9
        d.line([(bx, 70 - bh / 2), (bx, 70 + bh / 2)], fill=TERRA, width=4)
    d.text((158, 52), name, font=font("Regular", 38), fill=CREAM, anchor="lm")
    d.text((158, 96), "SFX", font=font("Light", 26), fill=MUTED, anchor="lm")
    return im
CHIPS = [chip_img(n, i) for i, n in enumerate(SFX_CHIPS)]
CHIP_POS = [(80 + (i % 2) * 500, 580 + (i // 2) * 170) for i in range(6)]

@lru_cache(maxsize=1)
def glow(size, col):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dd = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - dd, 0, 1) ** 2.2 * 190
    v = np.zeros((size, size, 4), np.uint8); v[..., :3] = col; v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v)

def scene_D(lt):   # 21.80 – 27.60: pro SFX -> Claude agent -> aligned, next level
    c = BG.copy()
    t = 21.80 + lt
    # node
    kn = spring(t - 23.55, w=11, z=0.6)
    fly0 = 23.85
    # phase 3 timeline takes over
    k3 = ease_io((t - 25.55) / 0.5)
    if kn > 0 and k3 < 1:
        nx, ny = NODE
        ny = lerp(ny, ny + 400, k3)
        pulse = 1 + 0.05 * math.sin(t * 6)
        absorbed = clamp((t - 24.55) / 0.4)
        g = glow(420, TERRA)
        gs = int(420 * kn * pulse * (1 + 0.25 * absorbed))
        if gs > 4: c.alpha_composite(g.resize((gs, gs)), (int(nx - gs / 2), int(ny - gs / 2)))
        d = ImageDraw.Draw(c)
        r = 86 * kn
        d.ellipse((nx - r, ny - r, nx + r, ny + r), fill=rgba(TERRA, 1 - k3))
        rring = r + 26 + 10 * math.sin(t * 4)
        d.ellipse((nx - rring, ny - rring, nx + rring, ny + rring), outline=rgba(CREAM, 0.35 * kn * (1 - k3)), width=2)
        lab = text_layer("Claude agent", font("Light", 36), CREAM)
        paste_alpha(c, lab, nx - lab.width / 2, ny + r + 40, clamp(kn) * (1 - k3))
    # chips: pop in, then fly into the node
    for i, (im, (px, py)) in enumerate(zip(CHIPS, CHIP_POS)):
        t_in = 21.95 + i * 0.11
        if t < t_in: continue
        k = spring(t - t_in, w=13, z=0.7)
        f = ease_io((t - fly0 - i * 0.08) / 0.55)
        if f >= 1: continue
        tx = lerp(px, NODE[0] - 210, f); ty = lerp(py, NODE[1] - 70, f)
        s = lerp(lerp(0.9, 1.0, k), 0.2, f)
        paste_alpha(c, im, tx + 210 * (1 - s), ty + 70 * (1 - s), clamp((t - t_in) / 0.2) * (1 - f * 0.9), s)
    # phase 3: synced timeline + monitor, quick sweep
    if k3 > 0:
        lt3 = t - 25.55
        t_a, t_b = 0.3, 1.9
        hits_t = [0.55, 0.9, 1.25, 1.6]
        hits_x = [playhead_x(h, t_a, t_b) for h in hits_t]
        pops = [pop_k(lt3, h, w=15) for h in hits_t]
        mon_y_off = (1 - k3) * 120
        monitor(c, lt3, pops, alpha=k3)
        shown = [1.0] * 4
        conn = [((hx, hx), 1.0) for hx in hits_x]
        draw_timeline(c, lt3, hits_x, hits_x, shown, conn, ok=True, alpha=k3, ph=playhead_x(lt3, t_a, t_b))
    return c

# ================= v2 scenes =================
import os
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- Claude logo (spark) ----------
@lru_cache(maxsize=8)
def claude_logo(size):
    s4 = size * 4
    im = Image.new("RGBA", (s4, s4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s4 / 2
    lens = [1.0, 0.82, 0.95, 0.78, 1.0, 0.86, 0.93, 0.8, 0.98, 0.84, 0.9, 0.79]
    for i, L in enumerate(lens):
        ang = math.radians(i * 30 + 8 * math.sin(i * 1.7))
        r = c * 0.96 * L
        x1, y1 = c + r * math.cos(ang), c + r * math.sin(ang)
        wdt = s4 * 0.085
        d.line([(c, c), (x1, y1)], fill=TERRA, width=int(wdt))
        d.ellipse((x1 - wdt / 2, y1 - wdt / 2, x1 + wdt / 2, y1 + wdt / 2), fill=TERRA)
    d.ellipse((c - s4 * 0.1, c - s4 * 0.1, c + s4 * 0.1, c + s4 * 0.1), fill=TERRA)
    return im.resize((size, size), Image.LANCZOS)

def paste_logo(canvas, size, cx, cy, k, rot=0.0, alpha=1.0):
    if k <= 0.01: return
    lg = claude_logo(size)
    if rot: lg = lg.rotate(rot, Image.BICUBIC)
    s = max(0.05, k)
    lg = lg.resize((max(1, int(size * s)), max(1, int(size * s))), Image.BICUBIC)
    paste_alpha(canvas, lg, cx - lg.width / 2, cy - lg.height / 2, clamp(k * 1.5) * alpha)

# ---------- captions (logo-aware) ----------
CAPTIONS = [
    ([("Claude AI videomontajlaridagi", "thin", 0.30, "logo"), ("fishka bu —", "thin", 2.15, None), ("sound effektlar", "bold", 3.10, None)], 4.25),
    ([("Sound effekt har qanday", "thin", 4.75, None), ("videoni jonlantiradi", "bold", 7.05, None)], 9.25),
    ([("To'g'ri, Claude montajni", "thin", 9.65, None), ("o'zi qiladi", "bold", 10.60, None)], 11.20),
    ([("Lekin bitta", "thin", 14.62, None), ("nozik tomoni bor", "bold", 15.05, None)], 16.00),
    ([("Sound effekt", "thin", 16.35, None), ("mos tushmayapti", "bold", 17.05, None)], 19.45),
    ([("Motion montajchilar ishlatadigan", "thin", 21.95, None), ("professional SFX", "bold", 22.30, None)], 23.70),
    ([("Claude agentingizga", "thin", 23.85, None), ("integratsiya", "bold", 24.65, None)], 25.45),
    ([("Kontentingiz", "thin", 25.60, None), ("yangi darajada", "bold", 26.30, None)], 27.45),
    ([("Buni sizga", "thin", 27.70, None), ("tekin o'rgataman", "bold", 27.95, None)], 29.00),
    ([("Kommentariyaga", "thin", 29.15, None), ("1 raqamini qoldiring", "bold", 30.05, None)], 99.0),
]
def draw_captions(canvas, t):
    for lines, t_out in CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.4: continue
        out = ease_in((t - t_out) / 0.35) if t > t_out else 0.0
        y = CAP_Y
        for txt, style, t_in, extra in lines:
            lay = cap_layer(txt, style)
            k = ease_out((t - t_in) / 0.6) * (1 - out)
            if t > t_out: k = 1 - out
            x = CAP_X
            if extra == "logo":
                kl = spring(t - t_in + 0.05, w=10, z=0.55) * (1 - out)
                paste_logo(canvas, 84, CAP_X + 42, y + 44, kl, rot=(1 - kl) * 120)
                x += 100
            if t >= t_in:
                wipe(canvas, lay, x, y - 20 * out, k)
            y += 78 if style == "thin" else 108
    comment_ui(canvas, t)

# ---------- comment input (final CTA) ----------
def comment_ui(canvas, t):
    t0 = 30.25
    if t < t0: return
    k = spring(t - t0, w=12, z=0.75)
    x, y, w, h = 64, 560, 700, 84
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rr(d, (0, 0, w - 1, h - 1), 42, fill=(20, 12, 10, 225), outline=(255, 236, 214, 60), width=2)
    d.ellipse((14, 14, 70, 70), fill=(120, 96, 84))
    d.ellipse((32, 24, 52, 44), fill=(200, 180, 168)); d.pieslice((22, 44, 62, 84), 180, 360, fill=(200, 180, 168))
    typed = t > 30.65
    if typed:
        d.text((92, h / 2), "1", font=font("Medium", 40), fill=CREAM, anchor="lm")
        if int(t * 3) % 2 == 0 and t < 31.2:
            d.line([(122, 24), (122, 60)], fill=CREAM, width=3)
    else:
        d.text((92, h / 2), "Izoh qo'shing...", font=font("Light", 32), fill=MUTED, anchor="lm")
    sent = t > 31.2
    bc = TERRA if typed else (80, 60, 52)
    d.ellipse((w - 74, 12, w - 14, 72), fill=bc)
    d.polygon([(w - 58, 30), (w - 26, 42), (w - 58, 54), (w - 52, 42)], fill=CREAM)
    if sent:
        ks = ease_out((t - 31.2) / 0.3)
        d.text((150, h / 2), "yuborildi", font=font("Light", 28), fill=rgba(MUTED, ks), anchor="lm")
    paste_alpha(canvas, lay, x, y + (1 - k) * 30, clamp(k * 1.5))

# ---------- After Effects style UI ----------
AE_BG = (26, 26, 26); AE_PANEL = (35, 35, 35); AE_HEAD = (43, 43, 43); AE_LINE = (58, 58, 58)
AE_TXT = (178, 178, 178); AE_DIM = (120, 120, 120); AE_BLUE = (45, 140, 235)
LBL = {"purple": (150, 112, 200), "blue": (88, 138, 222), "green": (98, 168, 88), "aqua": (64, 168, 170), "sand": (190, 160, 108), "red": (200, 82, 70)}

def ae_bg():
    c = Image.new("RGBA", (W, H), AE_BG + (255,))
    return c

def ae_panel(c, x, y, w, h, title):
    d = ImageDraw.Draw(c)
    d.rectangle((x, y, x + w, y + h), fill=AE_PANEL, outline=AE_LINE)
    d.rectangle((x, y, x + w, y + 40), fill=AE_HEAD)
    d.rectangle((x + 10, y + 6, x + 22 + font("Medium", 22).getlength(title) + 18, y + 40), fill=AE_PANEL)
    d.text((x + 22, y + 23), title, font=font("Medium", 22), fill=AE_TXT, anchor="lm")
    d.text((x + w - 24, y + 21), "≡", font=font("Medium", 24), fill=AE_DIM, anchor="mm")

def timecode(sec):
    f = int(round(sec * 30)); s = f // 30; fr = f % 30
    return f"0;00;{s:02d};{fr:02d}"

def cursor_img():
    im = Image.new("RGBA", (40, 56), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(2, 2), (2, 44), (13, 33), (21, 52), (28, 49), (20, 30), (35, 30)]
    d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))
    return im
CURSOR = cursor_img()

def ae_wave(d, x0, y0, x1, y1, seed, col, peak_at=0.08, amp=1.0):
    rng = np.random.default_rng(seed)
    mid = (y0 + y1) / 2; hh = (y1 - y0) / 2 - 3
    n = int((x1 - x0) / 3)
    for i in range(n):
        u = i / max(1, n)
        env = math.exp(-max(0, u - peak_at) * 7) * (u >= peak_at * 0.4)
        a = hh * amp * env * rng.uniform(0.35, 1.0)
        x = x0 + i * 3
        d.line([(x, mid - a), (x, mid + a)], fill=col, width=2)

AE_LAYERS = [("T", "Sarlavha", "purple"), ("★", "Shape: Doira", "blue"), ("▣", "expert.mov", "green"),
             ("♪", "SFX_pop.wav", "aqua"), ("♪", "SFX_whoosh.wav", "aqua"), ("♪", "Music.wav", "sand")]

def scene_A(lt, src=None):   # AE: SFX lands on every keyframe
    c = ae_bg()
    t = 4.40 + lt
    # composition viewer
    vx, vy, vw, vh = 40, 560, 1000, 610
    ae_panel(c, vx, vy, vw, vh, "Composition  Reel_final")
    d = ImageDraw.Draw(c)
    d.rectangle((vx + 1, vy + 41, vx + vw - 1, vy + vh - 40), fill=(20, 20, 20))
    ch_ = 500; cw_ = int(ch_ * 9 / 16)
    cx0 = vx + vw // 2 - cw_ // 2; cy0 = vy + 52
    if src is not None:
        fr = src.resize((cw_, ch_), Image.BILINEAR)
        c.paste(fr, (cx0, cy0))
    # animated layers inside the comp (synced to keyframes)
    hits = [1.20, 2.20, 3.20, 4.10]
    k = [pop_k(lt, h) for h in hits]
    comp = Image.new("RGBA", (cw_, ch_), (0, 0, 0, 0))
    cd = ImageDraw.Draw(comp)
    if k[0] > 0:
        f = dfont("SemiBold", 34)
        tx = lerp(-200, 24, k[0])
        rr(cd, (tx - 8, 36, tx + 200, 86), 12, fill=(16, 8, 6, 200))
        cd.text((tx + 4, 61), "Sound effekt", font=f, fill=CREAM, anchor="lm")
    if k[1] > 0:
        r = 26 * k[1]; cd.ellipse((240 - r, 120 - r, 240 + r, 120 + r), fill=TERRA)
    if k[2] > 0:
        bw = 200 * k[2]; rr(cd, (24, 100, 24 + bw, 112), 6, fill=AMBER)
    if k[3] > 0:
        r = lerp(10, 60, k[3]); cd.ellipse((240 - r, 120 - r, 240 + r, 120 + r), outline=rgba(GOLD, 1.2 - k[3] * 0.5), width=3)
    c.alpha_composite(comp, (cx0, cy0))
    # selection transform box around title layer
    if k[0] > 0.3:
        bx0, by0 = cx0 + 16, cy0 + 30; bx1, by1 = cx0 + 232, cy0 + 92
        d.rectangle((bx0, by0, bx1, by1), outline=AE_BLUE, width=1)
        for hx, hy in ((bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1), ((bx0 + bx1) // 2, by0), ((bx0 + bx1) // 2, by1)):
            d.rectangle((hx - 4, hy - 4, hx + 4, hy + 4), fill=(20, 20, 20), outline=AE_BLUE)
    # viewer footer
    d.rectangle((vx + 1, vy + vh - 40, vx + vw - 1, vy + vh - 1), fill=AE_HEAD)
    d.text((vx + 20, vy + vh - 20), "50%   ▾   Full   ▾", font=font("Regular", 20), fill=AE_DIM, anchor="lm")
    d.text((vx + vw - 20, vy + vh - 20), timecode(t), font=font("Medium", 22), fill=AE_BLUE, anchor="rm")
    # timeline
    tx_, ty_, tw_, th_ = 40, 1186, 1000, 390
    ae_panel(c, tx_, ty_, tw_, th_, "Reel_final")
    d.text((tx_ + 24, ty_ + 66), timecode(t), font=font("Medium", 30), fill=AE_BLUE, anchor="lm")
    X0, X1 = 400, 1020
    d.rectangle((X0, ty_ + 48, X1, ty_ + 84), fill=(30, 30, 30))
    for i in range(0, 21):
        xx = lerp(X0, X1, i / 20)
        d.line([(xx, ty_ + 70), (xx, ty_ + 84)], fill=AE_DIM, width=1)
        if i % 4 == 0:
            d.text((xx + 3, ty_ + 58), f"{i // 2:02d}s", font=font("Regular", 16), fill=AE_DIM, anchor="lm")
    d.rectangle((X0, ty_ + 86, X1, ty_ + 92), fill=(70, 70, 70))
    t_a, t_b = 0.5, 4.7
    ph = lerp(X0 + 20, X1 - 20, clamp((lt - t_a) / (t_b - t_a)))
    hx = [lerp(X0 + 20, X1 - 20, clamp((h - t_a) / (t_b - t_a))) for h in hits]
    for r, (ic, name, col) in enumerate(AE_LAYERS):
        ry = ty_ + 100 + r * 46
        d.rectangle((tx_ + 1, ry, tx_ + tw_ - 1, ry + 44), fill=(38, 38, 38) if r % 2 else (34, 34, 34))
        d.text((tx_ + 20, ry + 22), str(r + 1), font=font("Regular", 18), fill=AE_DIM, anchor="lm")
        d.rectangle((tx_ + 46, ry + 14, tx_ + 62, ry + 30), fill=LBL[col])
        d.text((tx_ + 82, ry + 22), ic, font=font("Medium", 20), fill=AE_TXT, anchor="lm")
        d.text((tx_ + 110, ry + 22), name, font=font("Regular", 22), fill=AE_TXT, anchor="lm")
        lc = LBL[col]
        if name.startswith("SFX"):
            # audio clips sit exactly under keyframes
            idxs = [0, 2] if "pop" in name else [1, 3]
            for j in idxs:
                kk = pop_k(lt, hits[j] - 0.5, w=16, z=0.7) if not (j == 0 and "pop" in name) else 1.0
                if j == 0 and "pop" in name:
                    # dragged in by the cursor
                    kk = ease_io((lt - 0.35) / 0.6)
                    bx = lerp(X1 + 60, hx[0], kk)
                else:
                    bx = hx[j]
                if kk <= 0: continue
                d.rectangle((bx, ry + 6, bx + 110, ry + 38), fill=tuple(int(v * 0.45) for v in lc), outline=lc)
                lit = 1.0 if abs(lt - hits[j]) < 0.25 else 0.7
                ae_wave(d, bx + 3, ry + 8, bx + 107, ry + 36, 7 + j, tuple(int(v * lit + 40 * lit) for v in lc))
        elif name == "Music.wav":
            d.rectangle((X0, ry + 6, X1, ry + 38), fill=tuple(int(v * 0.4) for v in lc), outline=lc)
            ae_wave(d, X0 + 3, ry + 8, X1 - 3, ry + 36, 99, tuple(int(v * 0.8) for v in lc), peak_at=0.0, amp=0.45)
        else:
            d.rectangle((X0, ry + 10, X1, ry + 34), fill=tuple(int(v * 0.55) for v in lc), outline=lc)
            if r in (0, 1):
                for j, hxx in enumerate(hx):
                    sel = abs(lt - hits[j]) < 0.25
                    cc = AE_BLUE if sel else (200, 200, 200)
                    d.polygon([(hxx, ry + 12), (hxx + 9, ry + 22), (hxx, ry + 32), (hxx - 9, ry + 22)], fill=cc)
    # playhead
    d.line([(ph, ty_ + 48), (ph, ty_ + th_ - 4)], fill=AE_BLUE, width=2)
    d.polygon([(ph - 9, ty_ + 48), (ph + 9, ty_ + 48), (ph + 9, ty_ + 62), (ph, ty_ + 72), (ph - 9, ty_ + 62)], fill=AE_BLUE)
    # cursor drags the first SFX clip into place, then rests near the playhead
    if lt < 1.1:
        kk = ease_io((lt - 0.35) / 0.6)
        cxp = lerp(X1 + 80, hx[0] + 40, kk); cyp = ty_ + 100 + 3 * 46 + 20
        if lt < 0.35: cxp, cyp = lerp(820, X1 + 80, lt / 0.35), lerp(900, cyp, lt / 0.35)
        paste_alpha(c, CURSOR, cxp, cyp, 1.0)
    # top area behind caption
    c.alpha_composite(SCRIM_TOP)
    return c

def scene_C(lt, src=None):   # AE Graph Editor: animation peaks vs late SFX transients
    c = ae_bg()
    t = 16.10 + lt
    gx, gy, gw, gh = 40, 560, 1000, 700
    ae_panel(c, gx, gy, gw, gh, "Graph Editor")
    d = ImageDraw.Draw(c)
    X0, X1 = 110, 1010
    Y0, Y1 = gy + 70, gy + gh - 40
    for i in range(0, 11):
        yy = lerp(Y0, Y1, i / 10)
        d.line([(X0, yy), (X1, yy)], fill=(48, 48, 48), width=1)
        d.text((gx + 18, yy), f"{(10 - i) * 50}", font=font("Regular", 16), fill=AE_DIM, anchor="lm")
    for i in range(0, 13):
        xx = lerp(X0, X1, i / 12)
        d.line([(xx, Y0), (xx, Y1)], fill=(44, 44, 44), width=1)
    t_a, t_b = 0.35, 3.4
    hits = [0.70, 1.70, 2.70]; late = 0.35
    px = lambda tt: lerp(X0 + 10, X1 - 10, clamp((tt - t_a) / (t_b - t_a)))
    # speed graph: smooth bumps at each animation hit
    pts = []
    for i in range(0, 301):
        u = i / 300
        tt = lerp(t_a, t_b, u)
        v = sum(math.exp(-((tt - h) / 0.16) ** 2) for h in hits)
        pts.append((lerp(X0 + 10, X1 - 10, u), lerp(Y1 - 30, Y0 + 40, v)))
    reveal = clamp((lt - 0.1) / 0.5)
    cut = int(len(pts) * reveal)
    if cut > 1: d.line(pts[:cut], fill=(240, 196, 60), width=4, joint="curve")
    for h in hits:
        x = px(h); y = Y0 + 40
        if reveal < (h - t_a) / (t_b - t_a): continue
        d.line([(x - 60, y), (x + 60, y)], fill=(240, 196, 60), width=2)
        for hx_ in (x - 60, x + 60): d.ellipse((hx_ - 6, y - 6, hx_ + 6, y + 6), fill=(240, 196, 60))
        glow_on = abs(lt - h) < 0.2
        d.rectangle((x - 8, y - 8, x + 8, y + 8), fill=AE_BLUE if glow_on else (230, 230, 230))
    # audio strip
    ax, ay, aw, ah = 40, 1280, 1000, 290
    ae_panel(c, ax, ay, aw, ah, "Audio  ·  SFX_pop.wav")
    d.line([(X0, ay + 165), (X1, ay + 165)], fill=(60, 60, 60), width=1)
    for j, h in enumerate(hits):
        x = px(h + late)
        if lt < h + late - 0.05: continue
        ae_wave(d, x, ay + 70, min(X1, x + 150), ay + 260, 21 + j, (98, 190, 120))
    # sync markers
    for j, h in enumerate(hits):
        xa, xs = px(h), px(h + late)
        k = ease_out((lt - h) / 0.3)
        if k <= 0: continue
        for yy in range(int(Y0), int(ay + ah - 20), 16):
            d.line([(xa, yy), (xa, yy + 8)], fill=rgba(AE_BLUE, k), width=2)
        k2 = ease_out((lt - h - late) / 0.25)
        if k2 > 0:
            d.line([(xs, ay + 50), (xs, ay + ah - 20)], fill=rgba(WARN, k2), width=3)
            d.line([(xa, ay + 56), (xs, ay + 56)], fill=rgba(WARN, k2), width=3)
            d.text(((xa + xs) / 2, ay + 76), "+0.35s", font=font("SemiBold", 22), fill=rgba(WARN, k2), anchor="mm")
    ph = px(lt)
    d.line([(ph, gy + 44), (ph, ay + ah - 4)], fill=AE_BLUE, width=2)
    c.alpha_composite(SCRIM_TOP)
    return c

# ---------- SFX video carousel / Claude agent / Reels growth ----------
@lru_cache(maxsize=48)
def sfx_card_frame(i, fi):
    d_ = os.path.join(HERE, f"cf{i + 1}")
    n = len(os.listdir(d_))
    fi = (fi % n) + 1
    return Image.open(os.path.join(d_, f"{fi:04d}.jpg")).convert("RGB")

@lru_cache(maxsize=4)
def card_mask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), r * 2, fill=255)
    return m.resize((w, h), Image.LANCZOS)

def fmt_count(v):
    if v >= 1e6: return f"{v / 1e6:.1f}M"
    if v >= 1e3: return f"{v / 1e3:.1f}K"
    return f"{int(v)}"

def scene_D(lt, src=None):
    c = BG.copy()
    t = 21.80 + lt
    CX, CY, R = 540, 1060, 330
    fly0 = 23.85
    k3 = ease_io((t - 25.55) / 0.45)
    # Claude logo node
    kn = spring(t - 23.55, w=11, z=0.6)
    if kn > 0 and k3 < 1:
        g = glow(420, TERRA)
        absorbed = clamp((t - 24.55) / 0.4)
        gs = int(420 * kn * (1 + 0.06 * math.sin(t * 6)) * (1 + 0.3 * absorbed))
        if gs > 4:
            gg = g.resize((gs, gs)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * (1 - k3))))
            c.alpha_composite(gg, (int(CX - gs / 2), int(CY - gs / 2)))
        paste_logo(c, 190, CX, CY, kn * (1 + 0.12 * absorbed), rot=(1 - kn) * 90 + (t - 23.55) * 12, alpha=1 - k3)
        lab = text_layer("Claude agent", font("Light", 38), CREAM)
        paste_alpha(c, lab, CX - lab.width / 2, CY + 140, clamp(kn) * (1 - k3))
    # rotating carousel of the four SFX videos
    if t < fly0 + 0.9:
        k_in = spring(lt, w=10, z=0.75)
        base = 45 + lt * 52.0
        cards = []
        for i in range(4):
            th = math.radians(base + i * 90)
            z = math.cos(th)
            x = CX + R * math.sin(th)
            s = lerp(0.58, 1.0, (z + 1) / 2) * lerp(0.85, 1.0, k_in)
            cards.append((z, i, x, s))
        cards.sort()
        for z, i, x, s in cards:
            f = ease_io((t - fly0 - i * 0.08) / 0.6)
            if f >= 1: continue
            fr = sfx_card_frame(i, int(lt * 30) + i * 40)
            w_, h_ = int(360 * s * lerp(1, 0.15, f)), int(640 * s * lerp(1, 0.15, f))
            if w_ < 4: continue
            im = fr.resize((w_, h_), Image.BILINEAR)
            shade = (1 - (z + 1) / 2) * 0.55
            if shade > 0: im = Image.blend(im, Image.new("RGB", im.size, BG0), shade)
            cx_ = lerp(x, CX, f); cy_ = lerp(CY, CY, f)
            # shadow + rounded card
            sh = soft_shadow(w_, h_, 26)
            c.alpha_composite(sh, (int(cx_ - w_ / 2) - 90, int(cy_ - h_ / 2) - 90))
            m = card_mask(w_, h_, max(6, int(26 * s)))
            a = clamp(lt / 0.25) * (1 - f * 0.8)
            if a < 1: m = m.point(lambda v: int(v * a))
            c.paste(im, (int(cx_ - w_ / 2), int(cy_ - h_ / 2)), m)
    # phase 3: Reels-style growth of this very video
    if k3 > 0:
        lt3 = t - 25.55
        pw, ph_ = 500, 890
        px_, py_ = 290, int(lerp(1200, 600, ease_out(lt3 / 0.5)))
        sh = soft_shadow(pw, ph_, 40)
        c.alpha_composite(sh, (px_ - 90, py_ - 90))
        if src is not None:
            scw = SW; sch = min(SH, scw * ph_ / pw); scw = sch * pw / ph_
            fr = src.resize((pw, ph_), Image.BILINEAR, box=((SW - scw) / 2, (SH - sch) * 0.45, (SW + scw) / 2, (SH - sch) * 0.45 + sch)).convert("RGBA")
        else:
            fr = Image.new("RGBA", (pw, ph_), (40, 30, 26, 255))
        grad = Image.new("RGBA", (pw, 360), (0, 0, 0, 0))
        grad.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 360) ** 1.4 * 200)[:, None], pw, 1).astype(np.uint8)))
        fr.alpha_composite(grad, (0, ph_ - 360))
        d = ImageDraw.Draw(fr)
        d.text((28, 40), "Reels", font=font("SemiBold", 34), fill="white", anchor="lm")
        views = 2_400_000 * ease_out((lt3 - 0.2) / 1.5) ** 1.3
        likes = 186_000 * ease_out((lt3 - 0.3) / 1.5)
        coms = 3_912 * ease_out((lt3 - 0.4) / 1.5)
        icx = pw - 54
        for j, (val, kind) in enumerate(((likes, "heart"), (coms, "comment"), (None, "share"))):
            iy = ph_ - 430 + j * 120
            if kind == "heart":
                hs = 20
                d.ellipse((icx - hs - 1, iy - hs, icx + 1, iy), outline="white", width=4)
                d.ellipse((icx - 1, iy - hs, icx + hs + 1, iy), outline="white", width=4)
                d.line([(icx - hs, iy - 6), (icx, iy + hs), (icx + hs, iy - 6)], fill="white", width=4)
            elif kind == "comment":
                d.ellipse((icx - 22, iy - 22, icx + 22, iy + 18), outline="white", width=4)
                d.polygon([(icx + 8, iy + 12), (icx + 24, iy + 26), (icx + 18, iy + 6)], fill="white")
            else:
                d.polygon([(icx - 22, iy - 4), (icx + 22, iy - 22), (icx + 6, iy + 22)], outline="white", width=4)
            if val is not None:
                d.text((icx, iy + 44), fmt_count(val), font=font("Medium", 24), fill="white", anchor="mm")
        d.polygon([(30, ph_ - 70), (30, ph_ - 40), (56, ph_ - 55)], fill="white")
        d.text((70, ph_ - 55), fmt_count(views), font=font("SemiBold", 44), fill="white", anchor="lm")
        d.text((72 + font("SemiBold", 44).getlength(fmt_count(views)) + 12, ph_ - 52), "ko'rish", font=font("Light", 30), fill=(230, 230, 230), anchor="lm")
        m = card_mask(pw, ph_, 40)
        if k3 < 1: m = m.point(lambda v: int(v * k3))
        c.paste(fr.convert("RGB"), (px_, py_), m)
        o = Image.new("RGBA", (pw + 4, ph_ + 4), (0, 0, 0, 0))
        ImageDraw.Draw(o).rounded_rectangle((1, 1, pw + 2, ph_ + 2), 41, outline=(255, 236, 214, int(70 * k3)), width=2)
        c.alpha_composite(o, (px_ - 2, py_ - 2))
        # floating "+" view bursts beside the phone
        for j in range(5):
            tj = 0.45 + j * 0.28
            u = (lt3 - tj) / 1.0
            if 0 < u < 1:
                lab = text_layer("+" + ["120K", "340K", "75K", "510K", "260K"][j], font("SemiBold", 34), TERRA)
                xx = [820, 120, 860, 100, 840][j]
                paste_alpha(c, lab, xx, lerp(1200, 900, ease_out(u)), math.sin(math.pi * u))
    return c

SCENES = [(0.0, 4.40, "E"), (4.40, 9.40, "A"), (9.40, 11.30, "E"), (11.30, 14.50, "B"), (14.50, 16.10, "E"),
          (16.10, 19.60, "C"), (19.60, 21.80, "E"), (21.80, 27.60, "D"), (27.60, END + 1, "E")]
TRANS = {4.40: "slide", 9.40: "push", 11.30: "slide", 14.50: "push", 16.10: "slide", 19.60: "push", 21.80: "slide", 27.60: "push"}
TD = 0.38

def scene_img(kind, t, src):
    for a, b, k in SCENES:
        if k == kind and a - 0.5 <= t <= b + 0.5:
            lt = t - a; break
    else:
        lt = 0
    if kind == "E": return expert_frame(src, t)
    if kind == "A": return scene_A(lt, src)
    if kind == "B": return scene_B(lt)
    if kind == "C": return scene_C(lt, src)
    return scene_D(lt, src)

def scene_at(t):
    for i, (a, b, k) in enumerate(SCENES):
        if a <= t < b: return i
    return len(SCENES) - 1

def render(i, src):
    t = i / FPS
    si = scene_at(t)
    a, b, kind = SCENES[si]
    cur = scene_img(kind, t, src)
    lt = t - a
    if si > 0 and lt < TD:
        prev = scene_img(SCENES[si - 1][2], t, src)
        p = ease_io(lt / TD)
        typ = TRANS.get(a, "slide")
        out = BG.copy()
        if typ == "slide":   # new scene pushes up from below
            pv = prev.resize((int(W * lerp(1, 0.94, p)), int(H * lerp(1, 0.94, p))), Image.BILINEAR)
            out.alpha_composite(pv, ((W - pv.width) // 2, (H - pv.height) // 2 - int(160 * p)))
            dim = Image.new("RGBA", (W, H), rgba(BG0, 0.55 * p)); out.alpha_composite(dim)
            out.alpha_composite(cur, (0, int(H * (1 - p))))
        else:                # horizontal push: no double exposure
            pv = prev.resize((int(W * lerp(1, 0.96, p)), int(H * lerp(1, 0.96, p))), Image.BILINEAR)
            out.alpha_composite(pv, (int((W - pv.width) / 2 - W * 0.35 * p), (H - pv.height) // 2))
            out.alpha_composite(Image.new("RGBA", (W, H), rgba(BG0, 0.5 * p)))
            out.alpha_composite(cur, (int(W * (1 - p)), 0))
        cur = out
    draw_captions(cur, t)
    return cur.convert("RGB")

# ---------- run ----------
def decode(fi):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{fi / FPS:.4f}", "-i", SRC, "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

if sys.argv[3] == "preview":
    for tt in [float(x) for x in sys.argv[4].split(",")]:
        fi = int(tt * FPS)
        p = decode(fi); img = Image.frombytes("RGB", (SW, SH), p.stdout.read(SW * SH * 3)); p.kill()
        render(fi, img).save(f"{OUT}_{tt:05.2f}.png")
    sys.exit(0)

a, b = int(sys.argv[3]), min(int(sys.argv[4]), N)
dec = decode(a)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", OUT + ".mp4"], stdin=subprocess.PIPE)
last = None
for i in range(a, b):
    buf = dec.stdout.read(SW * SH * 3)
    if len(buf) == SW * SH * 3: last = Image.frombytes("RGB", (SW, SH), buf)
    enc.stdin.write(render(i, last).tobytes())
enc.stdin.close(); enc.wait(); dec.kill()
print("done", a, b)
