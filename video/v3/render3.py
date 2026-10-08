# v3: dark-violet neon kinetic typography in the style of the reference reel.
# 1920x1080, beats synced to the voiceover phrase timings, writes silent video + SFX events.
import sys, os, json, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
OFF = 0.6                      # voice starts at this time in the video
FONTDIR = os.environ.get("FONTDIR", os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "v3.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]

VIO = (139, 61, 255); MAG = (200, 80, 255); LAV = (217, 194, 255); WHITE = (255, 255, 255)
BG0 = (6, 3, 12)

def F(w, s):
    return ImageFont.truetype(f"{FONTDIR}/M{w}.ttf", s)

# ---------------- easing ----------------
def cl(x): return max(0.0, min(1.0, x))
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def eo5(x): x = cl(x); return 1 - (1 - x) ** 5
def eio(x): x = cl(x); return x * x * (3 - 2 * x)
def back(x, c=1.9): x = cl(x); return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------------- voice timing ----------------
SEGS = [
 (0.10, 4.29, "Autizmni yuz foiz davolaydigan dori va nihoyat topildi."),
 (4.94, 7.10, "Deganlarga hozircha ishonmay turing."),
 (7.79, 9.60, "Chunki autizm kasallik emas."),
 (10.08, 12.30, "U gripp yoki shamollashga o'xshamaydi,"),
 (12.69, 15.15, "uni dori ichib o'tkazib yuborib bo'lmaydi."),
 (15.86, 18.44, "Autizm bu miyaning boshqacha ishlashi."),
 (19.21, 20.88, "Bola dunyoni boshqacha ko'radi,"),
 (21.27, 22.27, "boshqacha eshitadi,"),
 (22.67, 23.68, "boshqacha his qiladi."),
 (24.29, 26.51, "Va bu hamma bolada har xil bo'ladi."),
 (27.55, 29.30, "Bolani shu holatda qabul qilib,"),
 (29.69, 31.82, "unga gapirishni, muloqot qilishni,"),
 (32.17, 33.91, "o'zini boshqarishni o'rgatish kerak."),
 (34.66, 37.85, "Agar farzandingiz tashxisli bo'lsa, markazimizga keling."),
 (38.20, 41.09, "Biz sizga qo'ldan kelgancha yordam beramiz."),
]
def word_times(i):
    s, e, txt = SEGS[i]; ws = txt.split(); wts = [len(w) + 2 for w in ws]; tot = sum(wts)
    out = []; acc = s
    for w, k in zip(ws, wts):
        out.append(acc + OFF); acc += (e - s) * k / tot
    return out
WT = [word_times(i) for i in range(len(SEGS))]
def at(seg, word=0, lead=0.08): return WT[seg][word] - lead
DUR = SEGS[-1][1] + OFF + 1.6

# ---------------- background ----------------
def make_bg(bright=False):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W * 0.55)) ** 2 + ((y - H * 0.48) / (H * 0.62)) ** 2)
    if not bright:
        glow = np.clip(1 - r, 0, 1) ** 2
        img = np.zeros((H, W, 3), np.float32)
        for c in range(3):
            img[..., c] = BG0[c] + glow * [46, 14, 92][c]
        # perspective floor grid
        im = Image.fromarray(img.clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im, "RGBA")
        hz = int(H * 0.70)
        for k in range(-14, 15):
            d.line([(W / 2 + k * 40, hz), (W / 2 + k * 260, H)], fill=(120, 70, 220, 22), width=1)
        yy = hz; g = 6
        while yy < H:
            d.line([(0, yy), (W, yy)], fill=(120, 70, 220, 20), width=1); yy += g; g *= 1.35
        for gx in range(0, W, 120):
            d.line([(gx, 0), (gx, hz)], fill=(255, 255, 255, 6))
        for gy in range(0, hz, 120):
            d.line([(0, gy), (W, gy)], fill=(255, 255, 255, 6))
        vig = Image.fromarray((np.clip(1 - (r - 0.55) * 0.9, 0.25, 1) * 255).astype(np.uint8))
        black = Image.new("RGB", (W, H), BG0)
        return Image.composite(im, black, vig)
    # bright scene: white with lavender rays
    ang = np.arctan2(y - H / 2, x - W / 2)
    rays = (np.sin(ang * 18) * 0.5 + 0.5) ** 3
    base = np.clip(1 - r * 0.5, 0, 1)
    img = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        img[..., c] = 236 + 19 * base - rays * (1 - base * 0.6) * [30, 45, 8][c] * 0.6
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))
BG = make_bg(False); BGB = make_bg(True)
GRAIN = [Image.fromarray(np.random.default_rng(i).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)).resize((W, H)) for i in range(4)]

random.seed(11)
DUST = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.6, 2.6), random.uniform(4, 22), random.uniform(0, 6.28)) for _ in range(140)]

# ---------------- text helpers ----------------
_TC = {}
def grad_fill(size, top, bot):
    w, h = size; g = Image.new("RGB", (1, 256))
    for i in range(256): g.putpixel((0, i), tuple(int(top[c] + (bot[c] - top[c]) * i / 255) for c in range(3)))
    return g.resize((w, h))
def text_img(txt, size, weight=900, top=WHITE, bot=LAV, track=0):
    key = (txt, size, weight, top, bot, track)
    if key in _TC: return _TC[key]
    f = F(weight, size)
    widths = [f.getlength(ch) for ch in txt]
    tw = int(sum(widths) + track * max(0, len(txt) - 1)) + 40
    th = int(size * 1.35) + 20
    m = Image.new("L", (tw, th)); d = ImageDraw.Draw(m); x = 20
    for ch, wch in zip(txt, widths):
        d.text((x, 10), ch, font=f, fill=255); x += wch + track
    bb = m.getbbox() or (0, 0, 1, 1)
    m = m.crop((bb[0] - 4, bb[1] - 4, bb[2] + 4, bb[3] + 4))
    im = grad_fill(m.size, top, bot).convert("RGBA"); im.putalpha(m)
    _TC[key] = im
    return im
def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a))); return im
def put(layer, im, cx, cy):
    x = int(cx - im.width / 2); y = int(cy - im.height / 2)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, W - x), min(im.height, H - y)
    if ex <= sx or ey <= sy: return
    if sx or sy or ex < im.width or ey < im.height: im = im.crop((sx, sy, ex, ey))
    layer.alpha_composite(im, (x + sx, y + sy))
def scaled(im, s):
    if abs(s - 1) < 0.004: return im
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)

def kin(layer, txt, cx, cy, size, t0, t1, now, style="blur", top=WHITE, bot=LAV, weight=900, track=0, exit_=True, hold_scale=0.035):
    """Animated text: entrance by style, slow push while held, blur-out exit."""
    if now < t0 or now > t1 + 0.01: return
    u = now - t0; d = t1 - t0; ex = cl((now - (t1 - 0.22)) / 0.22) if exit_ else 0.0
    base = text_img(txt, size, weight, top, bot, track)
    push = 1 + hold_scale * cl(u / max(d, 0.01))
    if style == "letters":
        f = F(weight, size); n = len(txt)
        full_w = sum(f.getlength(c) for c in txt) + track * (n - 1)
        x = cx - full_w / 2 * push
        for i, ch in enumerate(txt):
            wch = f.getlength(ch)
            p = eo((u - i * 0.035) / 0.38)
            if ch != " " and p > 0:
                g = text_img(ch, size, weight, top, bot)
                g = with_alpha(scaled(g, push), p * (1 - ex))
                if ex > 0: g = g.filter(ImageFilter.GaussianBlur(ex * 10))
                put(layer, g, x + wch * push / 2, cy + (1 - p) * size * 0.6 - ex * 20)
            x += (wch + track) * push
        return
    if style == "blur":
        p = eo5(u / 0.42); s = (1.35 - 0.35 * p) * push; a = p; bl = (1 - p) * 14
    elif style == "pop":
        p = back(u / 0.38, 2.4); s = max(0.02, p) * push; a = cl(u / 0.12); bl = 0
    elif style == "drop":
        p = eo5(u / 0.35); s = (2.2 - 1.2 * p) * push; a = cl(u / 0.1); bl = (1 - p) * 8
    elif style == "wipe":
        p = eo(u / 0.5); s = push; a = 1; bl = 0
    else:
        p = 1; s = push; a = 1; bl = 0
    s *= 1 + 0.12 * ex; a *= 1 - ex; bl += ex * 16
    im = scaled(base, s)
    if style == "wipe" and p < 1:
        cw = int(im.width * p)
        if cw < 2: return
        m = Image.new("L", im.size); ImageDraw.Draw(m).rectangle([0, 0, cw, im.height], fill=255)
        im = im.copy(); im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size), m))
        # glowing edge line
        dd = ImageDraw.Draw(layer)
        lx = cx - im.width / 2 + cw
        dd.line([(lx, cy - im.height * 0.7), (lx, cy + im.height * 0.7)], fill=LAV + (255,), width=4)
    if bl > 0.3:
        pad = int(bl * 2)
        big = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2)); big.alpha_composite(im, (pad, pad))
        im = big.filter(ImageFilter.GaussianBlur(bl))
    put(layer, with_alpha(im, a), cx, cy)

def label(layer, txt, cx, cy, t0, t1, now, size=30, col=LAV, track=10):
    kin(layer, txt, cx, cy, size, t0, t1, now, "letters", col, col, 700, track, hold_scale=0)

# ---------------- shapes ----------------
def glass(layer, box, a=1.0, r=26, accent=VIO):
    x0, y0, x1, y1 = box
    g = Image.new("RGBA", (int(x1 - x0) + 2, int(y1 - y0) + 2)); d = ImageDraw.Draw(g)
    d.rounded_rectangle([0, 0, g.width - 2, g.height - 2], radius=r, fill=(40, 22, 70, int(150 * a)), outline=(170, 130, 255, int(140 * a)), width=2)
    d.rounded_rectangle([2, 2, g.width - 4, (g.height - 2) * 0.45], radius=r, fill=(255, 255, 255, int(10 * a)))
    put(layer, g, (x0 + x1) / 2, (y0 + y1) / 2)

def ring(d, cx, cy, r, w, frac, col, start=-90):
    if frac <= 0: return
    d.arc([cx - r, cy - r, cx + r, cy + r], start, start + 360 * frac, fill=col, width=w)

def icon(d, kind, cx, cy, s, col=LAV, w=7, p=1.0):
    """Neon line icons. p = draw-on progress."""
    if p <= 0: return
    c = col + (int(255 * cl(p * 2)),)
    if kind == "eye":
        pts = [(cx - s + 2 * s * i / 40, cy - math.sin(math.pi * i / 40) * s * 0.55) for i in range(41)]
        pts2 = [(cx - s + 2 * s * i / 40, cy + math.sin(math.pi * i / 40) * s * 0.55) for i in range(41)]
        n = int(41 * cl(p))
        if n > 1: d.line(pts[:n], fill=c, width=w, joint="curve"); d.line(pts2[:n], fill=c, width=w, joint="curve")
        r = s * 0.28 * eo(p); d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
        r2 = s * 0.1 * eo(p); d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=c)
    elif kind == "ear":
        d.arc([cx - s * 0.6, cy - s, cx + s * 0.6, cy + s * 0.4], 160, 160 + 220 * cl(p), fill=c, width=w)
        if p > 0.5:
            d.line([(cx + s * 0.55, cy - s * 0.1), (cx + s * 0.1, cy + s * 0.6), (cx - s * 0.1, cy + s * 0.9)], fill=c, width=w, joint="curve")
            d.arc([cx - s * 0.25, cy - s * 0.55, cx + s * 0.25, cy - s * 0.05], 180, 360, fill=c, width=w)
        for k in range(3):
            if p > 0.6 + k * 0.1:
                rr = s * (1.0 + 0.3 * k); d.arc([cx + s * 0.2 - rr, cy - rr * 0.8, cx + s * 0.2 + rr, cy + rr * 0.8], -35, 35, fill=col + (int(200 - 60 * k),), width=4)
    elif kind == "heart":
        pts = []
        for i in range(81):
            a = 2 * math.pi * i / 80
            x = 16 * math.sin(a) ** 3; y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
            pts.append((cx + x * s / 17, cy - y * s / 17))
        n = int(81 * cl(p))
        if n > 1: d.line(pts[:n], fill=c, width=w, joint="curve")
    elif kind == "pill":
        a = math.radians(-35); L = s * 1.6; r = s * 0.36
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        for sgn in (-1, 1):
            d.ellipse([cx + sgn * dx - r, cy + sgn * dy - r, cx + sgn * dx + r, cy + sgn * dy + r], outline=c, width=w)
        nx, ny = -math.sin(a) * r, math.cos(a) * r
        d.line([(cx - dx + nx, cy - dy + ny), (cx + dx + nx, cy + dy + ny)], fill=c, width=w)
        d.line([(cx - dx - nx, cy - dy - ny), (cx + dx - nx, cy + dy - ny)], fill=c, width=w)
        d.line([(cx + nx, cy + ny), (cx - nx, cy - ny)], fill=c, width=w)
    elif kind == "virus":
        r = s * 0.5 * eo(p); d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
        for k in range(8):
            if p > k / 10:
                a = k * math.pi / 4
                x0, y0 = cx + math.cos(a) * r, cy + math.sin(a) * r; x1, y1 = cx + math.cos(a) * s * 0.85, cy + math.sin(a) * s * 0.85
                d.line([(x0, y0), (x1, y1)], fill=c, width=w - 2); d.ellipse([x1 - 9, y1 - 9, x1 + 9, y1 + 9], fill=c)
    elif kind == "thermo":
        d.rounded_rectangle([cx - s * 0.18, cy - s * 0.9, cx + s * 0.18, cy + s * 0.45], radius=int(s * 0.18), outline=c, width=w)
        d.ellipse([cx - s * 0.36, cy + s * 0.25, cx + s * 0.36, cy + s * 0.97], outline=c, width=w)
        lv = cy + s * 0.5 - s * 1.1 * eo(p)
        d.line([(cx, cy + s * 0.55), (cx, lv)], fill=(255, 120, 170, 255), width=w + 2)
        d.ellipse([cx - s * 0.2, cy + s * 0.41, cx + s * 0.2, cy + s * 0.81], fill=(255, 120, 170, 255))
    elif kind == "chat":
        d.rounded_rectangle([cx - s, cy - s * 0.7, cx + s, cy + s * 0.5], radius=int(s * 0.3), outline=c, width=w)
        d.polygon([(cx - s * 0.5, cy + s * 0.48), (cx - s * 0.6, cy + s * 0.95), (cx - s * 0.1, cy + s * 0.48)], fill=c)
        for k in range(3):
            if p > 0.4 + k * 0.15:
                x = cx - s * 0.45 + k * s * 0.45; d.ellipse([x - 9, cy - 19, x + 9, cy - 1], fill=c)
    elif kind == "mouth":
        d.arc([cx - s, cy - s * 0.9, cx + s, cy + s * 0.6], 20, 20 + 140 * cl(p), fill=c, width=w)
        for k in range(3):
            if p > 0.5 + k * 0.12:
                rr = s * (0.5 + 0.28 * k); d.arc([cx + s * 0.6 - rr, cy - s * 0.6 - rr, cx + s * 0.6 + rr, cy - s * 0.6 + rr], -60, 0, fill=col + (220,), width=5)
    elif kind == "balance":
        d.line([(cx, cy - s * 0.8), (cx, cy + s * 0.8)], fill=c, width=w)
        d.line([(cx - s * 0.5, cy + s * 0.8), (cx + s * 0.5, cy + s * 0.8)], fill=c, width=w)
        tilt = math.sin((1 - eo(p)) * 3) * 0.3
        lx, ly = cx - s * math.cos(tilt), cy - s * 0.6 - s * math.sin(tilt); rx, ry = cx + s * math.cos(tilt), cy - s * 0.6 + s * math.sin(tilt)
        d.line([(lx, ly), (rx, ry)], fill=c, width=w)
        for (px, py) in ((lx, ly), (rx, ry)):
            d.arc([px - s * 0.3, py, px + s * 0.3, py + s * 0.5], 0, 180, fill=c, width=w - 2)

def xmark(d, cx, cy, s, p, col=(255, 70, 120)):
    if p <= 0: return
    a = cl(p * 2); b = cl(p * 2 - 1)
    d.line([(cx - s, cy - s), (cx - s + 2 * s * a, cy - s + 2 * s * a)], fill=col + (255,), width=14)
    if b > 0: d.line([(cx + s, cy - s), (cx + s - 2 * s * b, cy - s + 2 * s * b)], fill=col + (255,), width=14)

# ---------------- timeline ----------------
EV = []          # (sfx, time, gain)
FLASH = []       # times of white flash
SHAKE = []       # impact times
PUNCH = []       # camera punch-in times
STREAK = []      # light streak sweeps
def ev(n, t, g=1.0): EV.append((n, round(max(0, t), 3), g))

# beat start times
T = {}
T["intro"] = 0.0
T["autizmni"] = at(0, 0); T["yuzfoiz"] = at(0, 1); T["dori0"] = at(0, 4); T["nihoyat"] = at(0, 5)
T["hozircha"] = at(1, 0); T["ishonmay"] = at(1, 2)
T["chunki"] = at(2, 0); T["kasallik"] = at(2, 2)
T["gripp"] = at(3, 1); T["shamol"] = at(3, 3); T["oxsha"] = at(3, 4)
T["dori1"] = at(4, 1); T["otkazib"] = at(4, 3); T["bolmaydi"] = at(4, 5)
T["miya"] = at(5, 0); T["boshqa"] = at(5, 3)
T["dunyo"] = at(6, 0); T["koradi"] = at(6, 3); T["eshit"] = at(7, 1); T["his"] = at(8, 1)
T["hamma"] = at(9, 2); T["harxil"] = at(9, 4)
T["qabul"] = at(10, 0); T["qabul2"] = at(10, 3)
T["gap"] = at(11, 1); T["mul"] = at(11, 2); T["ozini"] = at(12, 0); T["orgat"] = at(12, 2)
T["farz"] = at(13, 0); T["tash"] = at(13, 2); T["markaz"] = at(13, 4)
T["biz"] = at(14, 0); T["yordam"] = at(14, 4)
T["end"] = DUR

# sfx & camera cues
ev("boom", 0.05, 0.8); STREAK.append(0.0)
for k in ["autizmni", "nihoyat", "hozircha", "chunki", "gripp", "shamol", "dori1", "otkazib", "dunyo", "hamma", "gap", "mul", "ozini", "farz", "tash", "biz"]:
    ev("swish", T[k] - 0.06, 0.7); PUNCH.append(T[k])
ev("ticks", T["yuzfoiz"] + 0.05, 0.6); ev("click", T["dori0"], 0.8)
ev("glitch", T["ishonmay"], 0.7); SHAKE.append(T["ishonmay"])
ev("swell", T["chunki"] - 0.9, 0.7); FLASH.append(T["chunki"]); ev("boom", T["chunki"], 0.9)
ev("boom", T["kasallik"] + 0.35, 0.8); SHAKE.append(T["kasallik"] + 0.35); ev("glitch", T["kasallik"] + 0.3, 0.5)
ev("click", T["gripp"] + 0.05, 0.8); ev("click", T["shamol"] + 0.05, 0.8); ev("glitch", T["oxsha"], 0.6); SHAKE.append(T["oxsha"])
ev("boom", T["bolmaydi"], 0.9); SHAKE.append(T["bolmaydi"])
ev("whoosh", T["miya"] - 0.35, 0.8); STREAK.append(T["miya"] - 0.25); ev("sparkle", T["miya"] + 0.3, 0.5)
for k in ["koradi", "eshit", "his"]: ev("pop", T[k], 0.6); ev("click", T[k] + 0.05, 0.5); PUNCH.append(T[k])
ev("sparkle", T["harxil"], 0.6); ev("boom", T["harxil"], 0.5)
ev("swell", T["qabul"] - 0.9, 0.8); FLASH.append(T["qabul"]); ev("boom", T["qabul"], 0.9); ev("sparkle", T["qabul"] + 0.2, 0.5)
ev("whoosh", T["gap"] - 0.3, 0.6); FLASH.append(T["gap"] - 0.05)
ev("boom", T["orgat"], 0.7); SHAKE.append(T["orgat"])
ev("riser", T["farz"] - 1.4, 0.5); ev("boom", T["farz"], 0.8); STREAK.append(T["farz"] - 0.2)
ev("sparkle", T["markaz"], 0.6); ev("boom", T["markaz"], 0.6)
ev("heart", T["biz"] + 0.2, 0.9); ev("heart", T["biz"] + 1.3, 0.8); ev("sparkle", T["yordam"], 0.7); ev("boom", T["yordam"], 0.7)
ev("ding", DUR - 1.3, 0.5)

# ---------------- scenes ----------------
CX, CY = W / 2, H / 2
def scene(now, L, d):
    """Draw foreground elements for time `now` onto layer L. Returns (bright, glowcol)."""
    bright = False
    # ---- intro streak + hook
    if now < T["hozircha"]:
        label(L, "DIQQAT", CX, CY - 190, T["autizmni"] - 0.2, T["yuzfoiz"], now, 34)
        kin(L, "AUTIZMNI", CX, CY - 20, 230, T["autizmni"], T["yuzfoiz"], now, "blur")
        # 100% counter ring
        if T["yuzfoiz"] <= now < T["dori0"]:
            u = now - T["yuzfoiz"]; p = eo(u / 1.15); ex = cl((now - (T["dori0"] - 0.2)) / 0.2)
            a = int(255 * (1 - ex))
            ring(d, CX - 380, CY, 190, 4, 1, (255, 255, 255, int(40 * (1 - ex))))
            ring(d, CX - 380, CY, 190, 14, p, VIO + (a,))
            ring(d, CX - 380, CY, 216, 2, eo(u / 0.6), LAV + (int(a * 0.6),), start=90)
            for k in range(60):
                ang = math.radians(k * 6 - 90 + u * 20); r0 = 238; r1 = 247 if k % 5 else 262
                d.line([(CX - 380 + math.cos(ang) * r0, CY + math.sin(ang) * r0), (CX - 380 + math.cos(ang) * r1, CY + math.sin(ang) * r1)], fill=(200, 170, 255, int(a * 0.5)), width=2)
            num = f"{int(round(100 * p))}%"
            put(L, with_alpha(text_img(num, 120, 900), 1 - ex), CX - 380, CY)
            label(L, "DAVOLAYDIGAN", CX + 300, CY - 90, T["yuzfoiz"] + 0.25, T["dori0"], now, 34, LAV, 8)
            kin(L, "DAVO?", CX + 300, CY + 30, 200, T["yuzfoiz"] + 0.4, T["dori0"], now, "blur", LAV, MAG)
        if T["dori0"] <= now < T["nihoyat"]:
            u = now - T["dori0"]; p = back(u / 0.4); ex = cl((now - (T["nihoyat"] - 0.18)) / 0.18)
            if p > 0.05:
                s = p * (1 - ex * 0.3)
                glass(L, (CX - 280 * s, CY - 280 * s, CX + 280 * s, CY + 280 * s), 1 - ex)
                icon(d, "pill", CX, CY - 50, 150 * s, LAV, 10, cl(u / 0.4) * (1 - ex))
            kin(L, "DORI", CX, CY + 175, 80, T["dori0"] + 0.1, T["nihoyat"], now, "letters", LAV, LAV, 800, 18)
        kin(L, "NIHOYAT", CX, CY - 100, 150, T["nihoyat"], T["hozircha"], now, "wipe", LAV, LAV, 800)
        kin(L, "TOPILDI?", CX, CY + 80, 240, T["nihoyat"] + 0.3, T["hozircha"], now, "blur", WHITE, MAG)
    # ---- don't believe
    elif now < T["chunki"]:
        label(L, "DEGANLARGA", CX, CY - 220, T["hozircha"], T["chunki"], now, 36)
        kin(L, "HOZIRCHA", CX, CY - 80, 190, T["hozircha"] + 0.1, T["chunki"], now, "blur", LAV, LAV, 800)
        if now >= T["ishonmay"]:
            u = now - T["ishonmay"]
            g = (int(u * 30) % 3 == 0 and u < 0.5)
            off = random.Random(int(now * 60)).uniform(-18, 18) if g else 0
            if g:
                put(L, with_alpha(text_img("ISHONMAY TURING!", 170, 900, (255, 60, 140), (255, 60, 140)), 0.6), CX + off - 8, CY + 110)
                put(L, with_alpha(text_img("ISHONMAY TURING!", 170, 900, (80, 200, 255), (80, 200, 255)), 0.6), CX - off + 8, CY + 110)
            kin(L, "ISHONMAY TURING!", CX + off * 0.5, CY + 110, 170, T["ishonmay"], T["chunki"], now, "drop", WHITE, MAG)
    # ---- not a disease
    elif now < T["gripp"] - 0.15:
        label(L, "CHUNKI", CX, CY - 250, T["chunki"], T["gripp"] - 0.15, now, 32)
        kin(L, "AUTIZM", CX, CY - 100, 250, T["chunki"] + 0.05, T["gripp"] - 0.15, now, "blur")
        wk = text_img("KASALLIK", 130, 800, LAV, LAV, 4).width; we = text_img("EMAS", 150, 900, WHITE, MAG).width
        tot = wk + 60 + we; kx = CX - tot / 2 + wk / 2; exx = CX + tot / 2 - we / 2
        kin(L, "KASALLIK", kx, CY + 130, 130, T["kasallik"], T["gripp"] - 0.15, now, "letters", LAV, LAV, 800, 4, hold_scale=0)
        u = now - (T["kasallik"] + 0.35)
        if u > 0:
            ex = cl((now - (T["gripp"] - 0.37)) / 0.22)
            w = wk
            lx0 = kx - w / 2 - 10
            d.line([(lx0, CY + 132), (lx0 + (w + 20) * eo(u / 0.25), CY + 132)], fill=(255, 70, 120, int(255 * (1 - ex))), width=12)
        kin(L, "EMAS", exx, CY + 130, 150, T["kasallik"] + 0.35, T["gripp"] - 0.15, now, "pop", WHITE, MAG)
    # ---- flu / cold cards
    elif now < T["dori1"]:
        t0 = T["gripp"] - 0.15
        label(L, "U GRIPP YOKI SHAMOLLASHGA", CX, 170, t0, T["dori1"], now, 30)
        for i, (k, ic, nm) in enumerate([("gripp", "virus", "GRIPP"), ("shamol", "thermo", "SHAMOLLASH")]):
            u = now - T[k]
            if u < 0: continue
            ex = cl((now - (T["dori1"] - 0.2)) / 0.2); p = eo5(u / 0.45)
            cx = CX + (-300 if i == 0 else 300) + (1 - p) * (-500 if i == 0 else 500); cy = CY - 10
            glass(L, (cx - 230, cy - 220, cx + 230, cy + 220), p * (1 - ex))
            icon(d, ic, cx, cy - 50, 110, LAV, 8, cl(u / 0.6) * (1 - ex))
            put(L, with_alpha(text_img(nm, 54, 800, WHITE, LAV), p * (1 - ex)), cx, cy + 130)
            if now >= T["oxsha"]:
                xmark(d, cx, cy - 50, 120, cl((now - T["oxsha"] - i * 0.12) / 0.3) * (1 - ex))
        kin(L, "O'XSHAMAYDI", CX, CY + 330, 90, T["oxsha"], T["dori1"], now, "drop", WHITE, MAG)
    # ---- can't cure with pills
    elif now < T["miya"]:
        if now < T["bolmaydi"]:
            u = now - T["dori1"]; p = back(u / 0.45); ex = cl((now - (T["bolmaydi"] - 0.15)) / 0.15)
            ang = u * 40
            icl = Image.new("RGBA", (420, 420)); di = ImageDraw.Draw(icl); icon(di, "pill", 210, 210, 120, LAV, 9, 1)
            icl = with_alpha(scaled(icl.rotate(ang, resample=Image.BICUBIC), max(0.02, p)), 1 - ex)
            put(L, icl, CX - 380, CY)
            kin(L, "DORI ICHIB", CX + 230, CY - 70, 110, T["dori1"] + 0.1, T["bolmaydi"], now, "blur", LAV, LAV, 800)
            kin(L, "O'TKAZIB YUBORIB", CX + 230, CY + 60, 84, T["otkazib"], T["bolmaydi"], now, "wipe", WHITE, LAV, 900)
        else:
            u = now - T["bolmaydi"]
            kin(L, "BO'LMAYDI", CX, CY, 230, T["bolmaydi"], T["miya"], now, "drop", WHITE, MAG)
            if u > 0.25:
                ex = cl((now - (T["miya"] - 0.22)) / 0.22)
                q = cl((u - 0.25) / 0.2)
                bw = text_img("BO'LMAYDI", 230, 900, WHITE, MAG).width / 2 * 1.06 + 50
                d.rounded_rectangle([CX - bw, CY - 175, CX + bw, CY + 175], radius=30, outline=(255, 70, 120, int(255 * q * (1 - ex))), width=8)
    # ---- brain network
    elif now < T["dunyo"] - 0.15:
        t0 = T["miya"]; u = now - t0; ex = cl((now - (T["dunyo"] - 0.37)) / 0.22)
        label(L, "AUTIZM BU", CX, 150, t0, T["dunyo"] - 0.15, now, 32)
        rnd = random.Random(4); nodes = []
        for k in range(26):
            a = rnd.uniform(0, 6.28); r = rnd.uniform(40, 230)
            nodes.append((CX + math.cos(a) * r * 1.9, CY - 90 + math.sin(a) * r * 1.05, rnd.uniform(0, 1), rnd.choice([VIO, MAG, LAV, (120, 200, 255)])))
        for i, (x, y, dl, c) in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                x2, y2, dl2, _ = nodes[j]
                if (x - x2) ** 2 + (y - y2) ** 2 < 200 ** 2:
                    p = cl((u - 0.2 - max(dl, dl2) * 0.8) / 0.35)
                    if p > 0: d.line([(x, y), (x + (x2 - x) * p, y + (y2 - y) * p)], fill=(190, 150, 255, int(150 * (1 - ex))), width=2)
        for (x, y, dl, c) in nodes:
            p = back((u - dl * 0.8) / 0.3)
            if p > 0.02:
                pul = 1 + 0.25 * math.sin(now * 5 + dl * 9); r = 11 * p * pul
                d.ellipse([x - r, y - r, x + r, y + r], fill=c + (int(255 * (1 - ex)),))
        # travelling signal
        for k in range(4):
            q = (now * 0.7 + k * 0.25) % 1; a = q * 6.28
            x, y = CX + math.cos(a) * 470, CY - 90 + math.sin(a) * 250
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=WHITE + (int(200 * (1 - ex)),))
        kin(L, "MIYANING", CX, CY + 300, 140, t0 + 0.6, T["boshqa"], now, "blur", WHITE, LAV)
        kin(L, "BOSHQACHA ISHLASHI", CX, CY + 300, 130, T["boshqa"], T["dunyo"] - 0.15, now, "blur", LAV, MAG)
    # ---- see / hear / feel flow
    elif now < T["hamma"] - 0.1:
        t0 = T["dunyo"] - 0.15; ex = cl((now - (T["hamma"] - 0.32)) / 0.22)
        label(L, "BOLA DUNYONI BOSHQACHA", CX, 170, t0, T["hamma"] - 0.1, now, 34)
        xs = [CX - 520, CX, CX + 520]
        for i, (k, ic, nm) in enumerate([("koradi", "eye", "KO'RADI"), ("eshit", "ear", "ESHITADI"), ("his", "heart", "HIS QILADI")]):
            u = now - T[k]
            if u < 0:
                # empty placeholder slot
                q = cl((now - t0) / 0.4) * (1 - ex)
                d.rounded_rectangle([xs[i] - 220, CY - 240, xs[i] + 220, CY + 240], radius=26, outline=(140, 100, 220, int(70 * q)), width=2)
                continue
            p = back(u / 0.4, 1.6); a = (1 - ex)
            s = max(0.05, p)
            glass(L, (xs[i] - 220 * s, CY - 240 * s, xs[i] + 220 * s, CY + 240 * s), a, accent=MAG)
            icon(d, ic, xs[i], CY - 60, 115, LAV if i != 2 else (255, 130, 190), 7, cl(u / 0.5) * a)
            put(L, with_alpha(text_img(nm, 60, 900, WHITE, LAV), cl(u / 0.25) * a), xs[i], CY + 150)
            put(L, with_alpha(text_img(f"0{i+1}", 26, 700, LAV, LAV), cl(u / 0.25) * a * 0.7), xs[i], CY - 205)
            if i > 0:
                pl = cl(u / 0.3)
                x0, x1 = xs[i - 1] + 225, xs[i] - 225
                for dx in range(int(x0), int(x0 + (x1 - x0) * pl), 18):
                    d.line([(dx, CY), (min(dx + 9, x1), CY)], fill=LAV + (int(200 * a),), width=3)
                q = (now * 1.2) % 1
                if pl >= 1: d.ellipse([x0 + (x1 - x0) * q - 7, CY - 7, x0 + (x1 - x0) * q + 7, CY + 7], fill=MAG + (int(255 * a),))
    # ---- every child different
    elif now < T["qabul"]:
        t0 = T["hamma"] - 0.1; u = now - t0
        label(L, "VA BU", CX, CY - 240, t0, T["qabul"], now, 32)
        kin(L, "HAMMA BOLADA", CX, CY - 110, 150, t0, T["qabul"], now, "blur", LAV, LAV, 800)
        kin(L, "HAR XIL", CX, CY + 90, 280, T["harxil"], T["qabul"], now, "pop", WHITE, MAG)
        ub = now - T["harxil"]
        if ub > 0:
            rnd = random.Random(9); ex = cl((now - (T["qabul"] - 0.3)) / 0.3)
            for k in range(70):
                a = rnd.uniform(0, 6.28); v = rnd.uniform(300, 900); c = rnd.choice([VIO, MAG, LAV, (120, 200, 255), (255, 200, 120), (255, 120, 170)])
                dist = v * eo(ub / 1.4); x = CX + math.cos(a) * dist * 1.4; y = CY + 90 + math.sin(a) * dist * 0.8
                s = rnd.uniform(8, 20); kind = k % 4; al = int(255 * (1 - ex))
                if kind == 0: d.ellipse([x - s, y - s, x + s, y + s], fill=c + (al,))
                elif kind == 1: d.rectangle([x - s, y - s, x + s, y + s], outline=c + (al,), width=4)
                elif kind == 2: d.polygon([(x, y - s), (x + s, y + s), (x - s, y + s)], outline=c + (al,), width=4)
                else: d.ellipse([x - s, y - s, x + s, y + s], outline=c + (al,), width=4)
    # ---- bright: accept
    elif now < T["gap"] - 0.05:
        bright = True; t0 = T["qabul"]
        label(L, "BOLANI SHU HOLATDA", CX, CY - 250, t0 + 0.05, T["gap"] - 0.05, now, 34, (110, 60, 200), 10)
        kin(L, "QABUL", CX, CY - 40, 330, t0, T["gap"] - 0.05, now, "blur", (150, 70, 255), (100, 40, 220))
        kin(L, "QILIB", CX, CY + 210, 160, T["qabul2"], T["gap"] - 0.05, now, "wipe", (120, 60, 230), (90, 40, 200), 800)
    # ---- teach steps
    elif now < T["farz"] - 0.1:
        t0 = T["gap"] - 0.05
        label(L, "UNGA O'RGATISH KERAK", CX, 160, t0, T["farz"] - 0.1, now, 32)
        ys = CY - 30; xs = [CX - 560, CX, CX + 560]
        ex = cl((now - (T["farz"] - 0.32)) / 0.22)
        # progress line
        prog = 0
        for i, k in enumerate(["gap", "mul", "ozini"]):
            if now >= T[k]: prog = i + cl((now - T[k]) / 0.5)
        d.line([(xs[0], ys + 230), (xs[2], ys + 230)], fill=(255, 255, 255, int(40 * (1 - ex))), width=4)
        d.line([(xs[0], ys + 230), (xs[0] + (xs[2] - xs[0]) * cl(prog / 3 * 1.0 + 0.0) , ys + 230)], fill=VIO + (int(255 * (1 - ex)),), width=6)
        for i, (k, ic, nm) in enumerate([("gap", "mouth", "GAPIRISH"), ("mul", "chat", "MULOQOT"), ("ozini", "balance", "O'ZINI BOSHQARISH")]):
            u = now - T[k]
            if u < 0: continue
            p = eo5(u / 0.4); a = 1 - ex
            cy = ys + (1 - p) * 120
            glass(L, (xs[i] - 230, cy - 170, xs[i] + 230, cy + 170), p * a)
            icon(d, ic, xs[i], cy - 40, 80, LAV, 7, cl(u / 0.6) * a)
            fs = 44 if len(nm) < 12 else 34
            put(L, with_alpha(text_img(nm, fs, 900, WHITE, LAV), p * a), xs[i], cy + 105)
            put(L, with_alpha(text_img(f"0{i+1}", 24, 700, LAV, LAV), p * a * 0.7), xs[i] - 180, cy - 140)
            d.ellipse([xs[i] - 12, ys + 218, xs[i] + 12, ys + 242], fill=MAG + (int(255 * p * a),))
        if now >= T["orgat"]:
            u = now - T["orgat"]
            dim = Image.new("RGBA", (W, H), (6, 3, 12, int(170 * cl(u / 0.2) * (1 - ex))))
            L.alpha_composite(dim)
            kin(L, "O'RGATISH KERAK", CX, CY, 200, T["orgat"], T["farz"] - 0.1, now, "drop", WHITE, MAG)
    # ---- spotlight: come to us
    elif now < T["biz"] - 0.1:
        t0 = T["farz"] - 0.1; u = now - t0; ex = cl((now - (T["biz"] - 0.32)) / 0.22)
        cone = Image.new("L", (W // 4, H // 4)); dc = ImageDraw.Draw(cone)
        sp = eo(u / 0.6)
        dc.polygon([(W / 8 - 18, 0), (W / 8 + 18, 0), (W / 8 + 150 * sp, H / 4), (W / 8 - 150 * sp, H / 4)], fill=int(120 * (1 - ex)))
        cone = cone.filter(ImageFilter.GaussianBlur(10)).resize((W, H))
        lay = Image.new("RGBA", (W, H), (200, 170, 255, 0)); lay.putalpha(cone); L.alpha_composite(lay)
        d.ellipse([CX - 600 * sp, H - 190, CX + 600 * sp, H - 130], fill=(180, 140, 255, int(60 * (1 - ex))))
        if now < T["markaz"]:
            kin(L, "FARZANDINGIZ", CX, CY - 70, 170, t0 + 0.05, T["markaz"], now, "blur", WHITE, LAV)
            kin(L, "TASHXISLI BO'LSA", CX, CY + 100, 110, T["tash"], T["markaz"], now, "wipe", LAV, LAV, 800)
        else:
            label(L, "BIZNING", CX, CY - 190, T["markaz"], T["biz"] - 0.1, now, 34)
            kin(L, "MARKAZIMIZGA", CX, CY - 40, 190, T["markaz"], T["biz"] - 0.1, now, "blur", WHITE, LAV)
            kin(L, "KELING", CX, CY + 150, 200, T["markaz"] + 0.45, T["biz"] - 0.1, now, "pop", LAV, MAG)
    # ---- neon heart finale
    else:
        t0 = T["biz"] - 0.1; u = now - t0; endf = cl((now - (DUR - 0.8)) / 0.8)
        beat = 1 + 0.07 * max(0, math.sin((now - T["biz"]) * 2 * math.pi * 0.9)) ** 12
        hs = 210 * back(u / 0.6) * beat
        icon(d, "heart", CX, CY - 130, hs, (255, 110, 180), 12, cl(u / 0.9) * (1 - endf))
        for k in range(3):
            rr = 290 + k * 55; ang = now * (30 + 15 * k)
            d.arc([CX - rr * 1.6, CY - 120 - rr * 0.45, CX + rr * 1.6, CY - 120 + rr * 0.45], ang, ang + 220, fill=LAV + (int(110 * (1 - endf) * cl(u / 0.8)),), width=2)
            q = math.radians(ang + 220); px, py = CX + math.cos(q) * rr * 1.6, CY - 120 + math.sin(q) * rr * 0.45
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=WHITE + (int(220 * (1 - endf) * cl(u / 0.8)),))
        label(L, "QO'LDAN KELGANCHA", CX, CY + 175, T["biz"] + 0.6, DUR, now, 34)
        kin(L, "YORDAM BERAMIZ", CX, CY + 290, 170, T["yordam"], DUR + 1, now, "blur", WHITE, MAG, exit_=False)
    return bright

# ---------------- frame compose ----------------
def frame(now):
    L = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(L)
    bright = scene(now, L, d)
    base = (BGB if bright else BG).copy()
    bd = ImageDraw.Draw(base, "RGBA")
    if not bright:
        for (x, y, s, sp, ph) in DUST:
            yy = (y - now * sp) % H; xx = x + math.sin(now * 0.5 + ph) * 12
            a = int(90 + 90 * math.sin(now * 2 + ph))
            bd.ellipse([xx - s, yy - s, xx + s, yy + s], fill=(200, 170, 255, max(0, a)))
    # light streak sweeps
    for st in STREAK:
        u = now - st
        if 0 <= u < 0.9:
            q = eo(u / 0.6); a = int(255 * (1 - cl((u - 0.4) / 0.5)))
            w = 900 * q
            bd.line([(CX - w, CY), (CX + w, CY)], fill=(220, 180, 255, a), width=4)
            bd.line([(CX - w * 0.6, CY), (CX + w * 0.6, CY)], fill=(255, 255, 255, a), width=2)
    # glow from foreground alpha
    a = L.getchannel("A").resize((W // 4, H // 4), Image.BILINEAR)
    g1 = a.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    g2 = a.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    gc = (170, 110, 255) if not bright else (190, 150, 255)
    base = base.convert("RGBA")
    gl = Image.new("RGBA", (W, H), gc + (0,)); gl.putalpha(g1.point(lambda v: int(v * (0.55 if not bright else 0.35)))); base.alpha_composite(gl)
    gl2 = Image.new("RGBA", (W, H), gc + (0,)); gl2.putalpha(g2.point(lambda v: int(v * (0.45 if not bright else 0.25)))); base.alpha_composite(gl2)
    base.alpha_composite(L)
    img = base.convert("RGB")
    # camera: drift zoom + punch + shake
    z = 1.02 + 0.012 * math.sin(now * 0.4)
    for p in PUNCH:
        u = now - p
        if 0 <= u < 0.6: z += 0.035 * (1 - eo(u / 0.6))
    sx = sy = 0.0
    for s in SHAKE:
        u = now - s
        if 0 <= u < 0.35:
            k = (1 - u / 0.35) * 14; r = random.Random(int(now * 1000)); sx += r.uniform(-k, k); sy += r.uniform(-k, k)
    cw, ch = W / z, H / z; ox = (W - cw) / 2 + sx; oy = (H - ch) / 2 + sy
    ox = max(0, min(W - cw, ox)); oy = max(0, min(H - ch, oy))
    img = img.resize((W, H), Image.BICUBIC, box=(ox, oy, ox + cw, oy + ch))
    # grain
    img = Image.blend(img, Image.merge("RGB", [GRAIN[int(now * FPS) % 4]] * 3), 0.035)
    # white flash
    for f in FLASH:
        u = now - f
        if -0.05 <= u < 0.35:
            a = (1 - cl(u / 0.35)) if u >= 0 else 1
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 0.85 * a)
    # fade in/out
    if now < 0.3: img = Image.blend(Image.new("RGB", (W, H)), img, now / 0.3)
    if now > DUR - 0.5: img = Image.blend(img, Image.new("RGB", (W, H)), cl((now - (DUR - 0.5)) / 0.5))
    return img

if __name__ == "__main__":
    times = PREVIEW if PREVIEW else [i / FPS for i in range(int(DUR * FPS))]
    if os.environ.get("PART"):
        k, n = map(int, os.environ["PART"].split("/")); m = len(times); times = times[m * k // n: m * (k + 1) // n]
    if PREVIEW:
        for t in times: frame(t).save(f"pv_{t:05.2f}.png")
        print("preview", len(times)); sys.exit()
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    for t in times: proc.stdin.write(frame(t).tobytes())
    proc.stdin.close(); proc.wait()
    json.dump({"events": EV, "dur": DUR, "off": OFF}, open("events3.json", "w"))
    print("frames", len(times), "dur", DUR)
