#!/usr/bin/env python3
"""5s 9:16 "To'liq video YouTube'da" card, same look as the ZRR story edit.

usage: promo.py THUMB.jpg OUT.mp4 [preview T1,T2,...]
"""
import math
import subprocess
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

THUMB, OUT = sys.argv[1], sys.argv[2]
W, H, FPS, DUR = 1080, 1920, 30, 5.0
N = int(DUR * FPS)

BG0 = (16, 8, 6)
BG1 = (52, 22, 14)
AMBER = (232, 160, 58)
GOLD = (246, 198, 92)
CREAM = (247, 233, 210)
PLAY_RED = (232, 40, 30)

FD = "/usr/share/fonts/opentype/inter/"
@lru_cache(None)
def font(w, s): return ImageFont.truetype(FD + f"Inter-{w}.otf", s)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def spring(t, w=12.0, z=0.6):
    if t <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_io(t): t = clamp(t); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def with_alpha(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))

# ---------- background ----------
def radial_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d1 = np.sqrt(((xx - 540) / 900) ** 2 + ((yy - 900) / 900) ** 2)
    d2 = np.sqrt(((xx - 900) / 800) ** 2 + ((yy - 1700) / 800) ** 2)
    g = np.clip(1 - d1, 0, 1) ** 1.5 * 0.95 + np.clip(1 - d2, 0, 1) ** 1.8 * 0.4
    base = np.array(BG0, np.float32); top = np.array(BG1, np.float32) * 1.3
    img = base[None, None] + (top - base)[None, None] * g[..., None]
    return Image.fromarray(np.uint8(np.clip(img, 0, 255))).convert("RGBA")
BG = radial_bg()

# ---------- thumbnail card ----------
CW, CH, CR = 1000, 563, 36
CX, CY = 540, 950            # card centre: well inside Instagram safe zone
THUMB_IM = Image.open(THUMB).convert("RGB")

def rr_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m
CARD_MASK = rr_mask(CW, CH, CR)

def card_shadow():
    pad = 110
    sh = Image.new("RGBA", (CW + pad * 2, CH + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 30, pad + CW, pad + CH + 30), CR, fill=(4, 1, 0, 190))
    return sh.filter(ImageFilter.GaussianBlur(40))
SHADOW = card_shadow()

def card_frame(t):
    kb = 1.0 + 0.06 * ease_io(t / DUR)
    sw, sh = THUMB_IM.size
    cw = sw / kb; ch = cw * CH / CW
    if ch > sh: ch = sh; cw = ch * CW / CH
    box = ((sw - cw) / 2, (sh - ch) / 2, (sw + cw) / 2, (sh + ch) / 2)
    im = THUMB_IM.resize((CW, CH), Image.LANCZOS, box=box).convert("RGBA")
    d = ImageDraw.Draw(im)
    # light sweep across the card
    st = (t - 2.6) / 0.9
    if 0 < st < 1:
        sweep = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        x = lerp(-300, CW + 300, ease_io(st))
        ImageDraw.Draw(sweep).polygon([(x - 80, 0), (x + 40, 0), (x - 120, CH), (x - 240, CH)], fill=(255, 245, 225, 60))
        im.alpha_composite(sweep.filter(ImageFilter.GaussianBlur(18)))
    # player bar
    kb_ = ease_out((t - 1.9) / 0.4)
    if kb_ > 0:
        grad = Image.new("RGBA", (CW, 120), (0, 0, 0, 0))
        grad.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 120) ** 1.5 * 170 * kb_)[:, None], CW, 1).astype(np.uint8)))
        im.alpha_composite(grad, (0, CH - 120))
        y = CH - 34
        d.rounded_rectangle((32, y, CW - 32, y + 7), 4, fill=(255, 255, 255, int(70 * kb_)))
        p = ease_io((t - 2.0) / 2.6)
        xe = lerp(32, CW - 32, p)
        d.rounded_rectangle((32, y, max(40, xe), y + 7), 4, fill=with_alpha(PLAY_RED, kb_))
        d.ellipse((xe - 11, y - 7, xe + 11, y + 14), fill=with_alpha(PLAY_RED, kb_))
    # hairline border
    o = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ImageDraw.Draw(o).rounded_rectangle((1, 1, CW - 2, CH - 2), CR, outline=(255, 236, 214, 70), width=2)
    im.alpha_composite(o)
    return im

def play_button(scale):
    w, h = int(200 * scale), int(140 * scale)
    if w < 4: return None
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), int(42 * scale), fill=PLAY_RED)
    cx, cy, s = w / 2 + 6 * scale, h / 2, 34 * scale
    d.polygon([(cx - s * 0.75, cy - s), (cx - s * 0.75, cy + s), (cx + s, cy)], fill="white")
    return im

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

def wipe_in(canvas, lay, x, y, t0, t):
    """Thin caption revealed from the left with a soft edge (same as story captions)."""
    k = ease_out((t - t0) / 0.7)
    if k <= 0.002: return
    wv = max(1, int(lay.width * k))
    piece = lay.crop((0, 0, wv, lay.height))
    edge = min(60, wv)
    if edge > 1:
        a = np.array(piece.getchannel("A"), np.float32)
        a[:, wv - edge:] *= np.linspace(1, 0, edge)[None, :]
        piece.putalpha(Image.fromarray(np.uint8(a)))
    paste_alpha(canvas, piece, x - 36 * (1 - k), y)

T1 = text_layer("To'liq video", font("Light", 84), CREAM)
@lru_cache(None)
def dfont(w, s): return ImageFont.truetype(FD + f"InterDisplay-{w}.otf", s)
T2_TEXT, T2_FONT = "YouTube'da", dfont("SemiBold", 124)

def letters_rise(canvas, txt, f, cx, y, t0, t, fill, stagger=0.035):
    """Letters rise one by one out of a clip line (no underline, no bounce)."""
    total = f.getlength(txt)
    x0 = cx - total / 2
    asc, desc = f.getmetrics()
    lh = asc + desc + 16
    for i, ch in enumerate(txt):
        k = ease_out((t - t0 - i * stagger) / 0.45)
        if k <= 0: continue
        lay = Image.new("RGBA", (int(f.getlength(ch)) + 24, lh), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((12, 8 + (1 - k) * lh), ch, font=f, fill=fill)
        paste_alpha(canvas, lay, x0 + f.getlength(txt[:i]) - 12, y, clamp(k * 1.4))

def render(i):
    t = i / FPS
    canvas = BG.copy()
    # card rise
    k = spring(t - 0.05, w=10, z=0.72)
    s = lerp(0.86, 1.0, k)
    a = clamp((t - 0.05) / 0.3)
    fy = 6 * math.sin(t * 2 * math.pi / 3.2)
    cy = CY + (1 - k) * 120 + fy
    paste_alpha(canvas, SHADOW, CX - SHADOW.width * s / 2, cy - SHADOW.height * s / 2 + 10, a, s)
    card = card_frame(t)
    card.putalpha(Image.fromarray(np.minimum(np.array(card.getchannel("A")), np.array(CARD_MASK))))
    paste_alpha(canvas, card, CX - CW * s / 2, cy - CH * s / 2, a, s)
    # play button pop + pulse rings
    kp = spring(t - 1.35, w=14, z=0.45)
    if kp > 0:
        for r0 in (1.9, 2.7, 3.5, 4.3):
            u = (t - r0) / 0.9
            if 0 < u < 1:
                ring = Image.new("RGBA", (420, 420), (0, 0, 0, 0))
                rr = lerp(70, 170, ease_out(u))
                ImageDraw.Draw(ring).ellipse((210 - rr, 210 - rr * 0.72, 210 + rr, 210 + rr * 0.72),
                                             outline=with_alpha(CREAM, 0.5 * (1 - u)), width=3)
                canvas.alpha_composite(ring, (int(CX - CW * s * 0.06 - 210), int(cy - 210)))
        pulse = 1 + 0.04 * math.sin(max(0, t - 2.0) * 5)
        pb = play_button(0.8 * kp * pulse * s)
        px = CX - CW * s * 0.06   # sits in the gap between the expert and the list
        if pb: paste_alpha(canvas, pb, px - pb.width / 2, cy - pb.height / 2, clamp(kp * 2))
    # texts (all inside the safe zone)
    wipe_in(canvas, T1, 540 - T1.width / 2, 520, 0.85, t)
    letters_rise(canvas, T2_TEXT, T2_FONT, 540, 1280, 1.8, t, CREAM)
    # fade from / to black edges
    if t < 0.25:
        canvas.alpha_composite(Image.new("RGBA", (W, H), with_alpha(BG0, 1 - t / 0.25)))
    return canvas.convert("RGB")

if len(sys.argv) > 3 and sys.argv[3] == "preview":
    for tt in [float(x) for x in sys.argv[4].split(",")]:
        render(int(tt * FPS)).save(OUT.replace(".mp4", f"_{tt:04.2f}.png"))
    sys.exit(0)

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
for i in range(N):
    enc.stdin.write(render(i).tobytes())
enc.stdin.close(); enc.wait()
print("done")
