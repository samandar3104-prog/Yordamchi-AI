#!/usr/bin/env python3
"""iPhone-style 9:16 motion edit renderer (PIL + ffmpeg)."""
import math
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = sys.argv[1]
AUDIO = sys.argv[2]       # processed speech wav (with tail)
OUT = sys.argv[3]
PREVIEW = len(sys.argv) > 4 and sys.argv[4] == "preview"

W, H, FPS = 1080, 1920, 30
SW, SH = 854, 480
SRC_FRAMES = 956
TAIL = 1.05
N = int(math.ceil((SRC_FRAMES / FPS + TAIL) * FPS))
DUR = N / FPS

FD = "/usr/share/fonts/opentype/inter/"
def font(w, s): return ImageFont.truetype(FD + f"Inter-{w}.otf", s)
def dfont(w, s): return ImageFont.truetype(FD + f"InterDisplay-{w}.otf", s)

TEAL = (38, 196, 182)
INK = (22, 24, 40)

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def spring(t, w=13.0, z=0.55):
    if t <= 0: return 0.0
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_io(t): t = clamp(t); return 3 * t * t - 2 * t * t * t
def lerp(a, b, t): return a + (b - a) * t

# ---------- audio envelope (for island waveform) ----------
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", AUDIO, "-ac", "1", "-ar", "12000", "-f", "s16le", "-"],
                     capture_output=True).stdout
aud = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
spf = 12000 // FPS
def band_levels(i):
    seg = aud[i * spf:(i + 1) * spf]
    if len(seg) < 16: return [0] * 5
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    edges = [2, 6, 12, 22, 40, 80]
    v = [sp[edges[k]:edges[k + 1]].mean() for k in range(5)]
    return [clamp(math.log10(1 + x * 4) / 1.2) for x in v]
levels = [band_levels(i) for i in range(N)]
sm = [0.0] * 5
for i in range(N):
    sm = [max(l, s * 0.78) for l, s in zip(levels[i], sm)]
    levels[i] = sm

# ---------- static assets ----------
def rounded_mask(w, h, r):
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), r * 2, fill=255)
    return m.resize((w, h), Image.LANCZOS)

def shadow(w, h, r, blur, alpha, pad):
    s = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=(30, 40, 70, alpha))
    return s.filter(ImageFilter.GaussianBlur(blur))

# background: soft iOS-like wallpaper with drifting blobs
BGW, BGH = W + 160, H + 160
bg = Image.new("RGB", (BGW, BGH))
gy = np.linspace(0, 1, BGH)[:, None]
top, bot = np.array([236, 249, 247]), np.array([242, 239, 255])
bg = Image.fromarray(np.uint8((top + (bot - top) * gy)[:, None, :].repeat(BGW, 1)))
blobs = Image.new("RGBA", (BGW, BGH), (0, 0, 0, 0))
bd = ImageDraw.Draw(blobs)
bd.ellipse((-200, -150, 700, 700), fill=(120, 225, 214, 150))
bd.ellipse((600, 300, 1400, 1100), fill=(196, 180, 255, 120))
bd.ellipse((-250, 1300, 650, 2200), fill=(255, 205, 190, 110))
bd.ellipse((650, 1500, 1350, 2200), fill=(120, 225, 214, 110))
blobs = blobs.filter(ImageFilter.GaussianBlur(140))
bg = Image.alpha_composite(bg.convert("RGBA"), blobs).convert("RGB")

# speaker card
CX, CY, CW, CH, CR = 60, 500, 960, 960, 64
card_mask = rounded_mask(CW, CH, CR)
card_shadow = shadow(CW, CH, CR, 34, 70, 80)
CROP = (0, 38, 373, 411)   # speaker region in source (square)

# name tag
NAME_W, NAME_H = 640, 132
name_mask = rounded_mask(NAME_W, NAME_H, 36)
name_txt = Image.new("RGBA", (NAME_W, NAME_H), (0, 0, 0, 0))
d = ImageDraw.Draw(name_txt)
d.ellipse((24, 30, 96, 102), fill=TEAL)
d.text((60, 66), "MU", font=font("Bold", 28), fill="white", anchor="mm")
d.text((116, 38), "Muslima Usmaan", font=font("Bold", 36), fill=INK)
d.text((116, 84), "Defektolog-Logoped, ABA-terapist", font=font("Medium", 25), fill=(80, 86, 104))

# notifications
BULLETS = ["Lug'at boyligi kam", "Grammatik muammolar", "Til tizimi buzilishi",
           "Ijtimoiy aloqa yaxshi", "O'yin faoliyati shakllangan", "Ko'z bilan aloqa mavjud"]
BT = [3.05, 8.70, 14.05, 18.80, 23.90, 28.90]
NW, NH, NR = 960, 176, 46
NX, NY = 60, 1502
notif_shadow = shadow(NW, NH, NR, 24, 55, 50)
def make_notif(i, text):
    im = Image.new("RGBA", (NW, NH), (0, 0, 0, 0))
    base = Image.new("RGBA", (NW, NH), (255, 255, 255, 252))
    im.paste(base, (0, 0), rounded_mask(NW, NH, NR))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((28, 38, 128, 138), 26, fill=TEAL)
    d.line([(55, 89), (72, 106), (103, 72)], fill="white", width=11, joint="curve")
    for p in [(55, 89), (72, 106), (103, 72)]:
        d.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), fill="white")
    d.text((154, 50), f"ZRR BELGISI  ·  {i + 1}/6", font=font("SemiBold", 25), fill=(120, 126, 142))
    d.text((NW - 34, 50), "hozir", font=font("Medium", 25), fill=(150, 154, 168), anchor="ra")
    d.text((154, 88), text, font=font("Bold", 42), fill=INK)
    return im
notifs = [make_notif(i, t) for i, t in enumerate(BULLETS)]

# dynamic island content
IW0, IH0, IR0 = 250, 72, 36
IW1, IH1, IR1 = 920, 164, 60
ITOP = 302
island_content = Image.new("RGBA", (IW1, IH1), (0, 0, 0, 0))
d = ImageDraw.Draw(island_content)
d.rounded_rectangle((26, 30, 130, 134), 30, fill=TEAL)
d.rounded_rectangle((46, 56, 110, 96), 12, fill="white")
d.polygon([(58, 94), (58, 112), (76, 94)], fill="white")
d.rounded_rectangle((56, 66, 100, 72), 3, fill=TEAL)
d.rounded_rectangle((56, 79, 86, 85), 3, fill=(255, 150, 160))
d.text((156, 30), "TASHXIS 2 / 5", font=font("SemiBold", 24), fill=TEAL)
d.text((154, 56), "ZRR", font=dfont("Bold", 54), fill="white")
d.text((156, 116), "nutq rivojlanishi kechikishi", font=font("Medium", 27), fill=(160, 162, 176))

# ---------- timeline ----------
T_CARD = 0.05
T_ISLAND = 0.45
T_NAME_IN, T_NAME_OUT = 1.1, 6.2
PUNCH = [(16.30, 1.10), (21.0, 1.10)]   # (time, zoom)
T_OUT = DUR - 1.0

def zoom_at(t):
    z = 1.0 + 0.05 * (t / DUR)  # slow ken burns
    for tp, amt in PUNCH:
        if t >= tp:
            k = spring(t - tp, w=11, z=0.7)
            hold = 1.0 - ease_io((t - tp - 2.4) / 0.9)
            z += (amt - 1.0) * k * hold
    return z

def frame_speaker(src, t):
    x0, y0, x1, y1 = CROP
    z = zoom_at(t)
    cw = (x1 - x0) / z
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 18 * (z - 1) * 4
    box = (cx - cw / 2, cy - cw / 2, cx + cw / 2, cy + cw / 2)
    im = src.resize((CW, CH), Image.LANCZOS, box=box)
    return im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=60, threshold=2))

def paste_scaled(canvas, im, cx, cy, s, alpha, mask=None):
    if s <= 0.01 or alpha <= 0.01: return
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    im2 = im.resize((w, h), Image.BILINEAR) if s != 1 else im
    if im2.mode != "RGBA": im2 = im2.convert("RGBA")
    if mask is not None:
        m = mask.resize((w, h), Image.BILINEAR) if s != 1 else mask
        a = np.array(m, np.float32)
        a *= np.array(im2.getchannel("A"), np.float32) / 255
        im2.putalpha(Image.fromarray(np.uint8(a)))
    if alpha < 1:
        a = np.array(im2.getchannel("A"), np.float32) * alpha
        im2.putalpha(Image.fromarray(np.uint8(a)))
    canvas.alpha_composite(im2, (int(cx - w / 2), int(cy - h / 2)))

def draw_island(canvas, t, i):
    if t < T_OUT:
        k = spring(t - T_ISLAND, w=12, z=0.62) if t > T_ISLAND else 0
    else:
        k = 1 - ease_io((t - T_OUT) / 0.45)
    w, h, r = lerp(IW0, IW1, k), lerp(IH0, IH1, k), lerp(IR0, IR1, k)
    x0 = W / 2 - w / 2
    isl = Image.new("RGBA", (int(w) + 1, int(h) + 1), (0, 0, 0, 0))
    ImageDraw.Draw(isl).rounded_rectangle((0, 0, w, h), r, fill=(0, 0, 0, 255))
    ca = clamp((k - 0.55) / 0.35)
    if ca > 0:
        c = island_content.copy()
        dd = ImageDraw.Draw(c)
        for b in range(5):  # live audio bars
            lv = levels[i][b] if i < len(levels) else 0
            bh = 14 + 58 * lv
            bx = IW1 - 150 + b * 24
            dd.rounded_rectangle((bx, IH1 / 2 - bh / 2, bx + 12, IH1 / 2 + bh / 2), 6, fill=TEAL)
        c.putalpha(Image.fromarray(np.uint8(np.array(c.getchannel("A"), np.float32) * ca)))
        cs = c.resize((max(1, int(w)), max(1, int(h))), Image.BILINEAR)
        isl.alpha_composite(cs, (0, 0))
        mask = Image.new("L", isl.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), r, fill=255)
        isl.putalpha(Image.fromarray(np.minimum(np.array(isl.getchannel("A")), np.array(mask))))
    canvas.alpha_composite(isl, (int(x0), ITOP))

def render(i, src):
    t = i / FPS
    dx = 40 * math.sin(t * 0.25); dy = 50 * math.cos(t * 0.2)
    canvas = bg.crop((80 + dx, 80 + dy, 80 + dx + W, 80 + dy + H)).convert("RGBA")

    # global outro factor (card collapses into the island)
    o = ease_io((t - T_OUT) / 0.55) if t > T_OUT else 0.0

    # speaker card
    k = spring(t - T_CARD, w=10, z=0.62)
    s = lerp(0.86, 1.0, k) * lerp(1, 0.08, o)
    alpha = clamp((t - T_CARD) / 0.25) * (1 - clamp((o - 0.6) / 0.4))
    ccx = CX + CW / 2
    ccy = lerp(CY + CH / 2 + 60 * (1 - k), ITOP + IH1 / 2, o)
    card = frame_speaker(src, t).convert("RGBA")
    # name tag (frosted glass)
    if T_NAME_IN < t < T_NAME_OUT + 0.6:
        kin = spring(t - T_NAME_IN, w=12, z=0.65)
        kout = ease_io((t - T_NAME_OUT) / 0.5)
        nx, ny = 34, int(CH - NAME_H - 34 + (1 - kin) * 60 + kout * 40)
        na = clamp((t - T_NAME_IN) / 0.2) * (1 - kout)
        if na > 0:
            region = card.crop((nx, ny, nx + NAME_W, ny + NAME_H)).filter(ImageFilter.GaussianBlur(22))
            glass = Image.alpha_composite(region, Image.new("RGBA", region.size, (255, 255, 255, 175)))
            glass = Image.alpha_composite(glass, name_txt)
            a = np.array(name_mask, np.float32) * na
            glass.putalpha(Image.fromarray(np.uint8(a)))
            card.alpha_composite(glass, (nx, max(0, ny)))
    if alpha > 0:
        sh_a = alpha * (1 - o)
        paste_scaled(canvas, card_shadow, ccx, ccy + 22 * s, s, sh_a)
        paste_scaled(canvas, card, ccx, ccy, s, alpha, card_mask)

    # notification stack
    shown = [j for j, bt in enumerate(BT) if t >= bt]
    na_out = 1 - ease_io((t - T_OUT) / 0.35)
    for j in shown[-3:]:
        depth_t = 0.0
        for later in shown:
            if later > j:
                depth_t += spring(t - BT[later], w=12, z=0.7)
        kin = spring(t - BT[j], w=13, z=0.58)
        sc = lerp(0.9, 1.0, kin) * (1 - 0.06 * depth_t)
        yy = NY + NH / 2 + (1 - kin) * 110 - 26 * depth_t
        aa = clamp((t - BT[j]) / 0.15) * clamp(1 - 0.38 * depth_t) * na_out
        if depth_t > 2.6: continue
        paste_scaled(canvas, notif_shadow, NX + NW / 2, yy + 14, sc, aa * clamp(1 - depth_t))
        paste_scaled(canvas, notifs[j], NX + NW / 2, yy, sc, aa)

    draw_island(canvas, t, i)
    return canvas.convert("RGB")

# ---------- run ----------
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = None if PREVIEW else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", AUDIO, "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                       stdin=subprocess.PIPE)
frames = range(N)
if PREVIEW:
    frames = [int(x * FPS) for x in [0.1, 0.3, 0.6, 1.0, 1.5, 3.2, 9.0, 16.5, 17.5, 29.3, 31.95, 32.3, 32.6]]
last = None
fi = 0
for i in range(N):
    if fi < SRC_FRAMES:
        buf = dec.stdout.read(SW * SH * 3)
        if len(buf) == SW * SH * 3:
            last = Image.frombytes("RGB", (SW, SH), buf)
        fi += 1
    if PREVIEW:
        if i in frames:
            render(i, last).save(OUT.replace(".mp4", f"_{i:04d}.png"))
        continue
    enc.stdin.write(render(i, last).tobytes())
    if i % 100 == 0: print(f"{i}/{N}", flush=True)
dec.stdout.close()
if enc: enc.stdin.close(); enc.wait()
print("done")
