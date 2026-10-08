# v4: USMAN logopedik markazi — vertical 9:16 neon kinetic typography in brand colours
# (navy + blue neon + orange), logo watermark, logo/phone outro. Writes silent video + SFX events.
import sys, os, json, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
OFF = 0.6                      # voice starts at this time in the video
HERE = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.environ.get("FONTDIR", HERE)
ASSETS = os.environ.get("ASSETS", HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else "v4.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
PHONE = "+998 99 720 92 00"

# brand palette: VIO = bright brand blue, MAG = brand orange, LAV = pale blue
VIO = (70, 125, 255); MAG = (255, 150, 45); ORG = (245, 140, 43); LAV = (200, 218, 255); WHITE = (255, 255, 255)
BRAND = (52, 82, 155); BG0 = (3, 7, 22)
MAXW = W - 170
CX, CY = W / 2, H / 2

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


# ---------------- background
def make_bg(bright=False):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H * 0.47) / (H * 0.5)) ** 2)
    if not bright:
        glow = np.clip(1 - r, 0, 1) ** 2
        img = np.zeros((H, W, 3), np.float32)
        for c in range(3):
            img[..., c] = BG0[c] + glow * [18, 42, 110][c]
        im = Image.fromarray(img.clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im, "RGBA")
        hz = int(H * 0.74)
        for k in range(-12, 13):
            d.line([(W / 2 + k * 30, hz), (W / 2 + k * 200, H)], fill=(90, 140, 255, 22), width=1)
        yy = hz; g = 6
        while yy < H:
            d.line([(0, yy), (W, yy)], fill=(90, 140, 255, 20), width=1); yy += g; g *= 1.35
        for gx in range(0, W, 90):
            d.line([(gx, 0), (gx, hz)], fill=(255, 255, 255, 6))
        for gy in range(0, hz, 90):
            d.line([(0, gy), (W, gy)], fill=(255, 255, 255, 6))
        vig = Image.fromarray((np.clip(1 - (r - 0.6) * 0.9, 0.25, 1) * 255).astype(np.uint8))
        return Image.composite(im, Image.new("RGB", (W, H), BG0), vig)
    ang = np.arctan2(y - H / 2, x - W / 2)
    rays = (np.sin(ang * 18) * 0.5 + 0.5) ** 3
    base = np.clip(1 - r * 0.5, 0, 1)
    img = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        img[..., c] = 238 + 17 * base - rays * (1 - base * 0.6) * [40, 28, 6][c] * 0.6
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))
BG = make_bg(False); BGB = make_bg(True)
GRAIN = [Image.fromarray(np.random.default_rng(i).integers(0, 255, (H // 2, W // 2), dtype=np.uint8)).resize((W, H)) for i in range(4)]
random.seed(11)
DUST = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.6, 2.6), random.uniform(4, 22), random.uniform(0, 6.28)) for _ in range(150)]

# logo assets (cut from the brand logo; dot is redrawn so it can animate)
LOGO = Image.open(f"{ASSETS}/logo_full.png")
BODY = Image.open(f"{ASSETS}/logo_body.png")
WORD = Image.open(f"{ASSETS}/logo_text.png")
DOT_C, DOT_R = (132, 36), 35          # in BODY pixel coords
WM = LOGO.resize((300, int(LOGO.height * 300 / LOGO.width)), Image.LANCZOS)


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
    tw0 = text_img(txt, size, weight, top, bot, track).width
    if tw0 > MAXW: size = max(10, int(size * MAXW / tw0))
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
        dd.line([(lx, cy - im.height * 0.7), (lx, cy + im.height * 0.7)], fill=ORG + (255,), width=5)
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
    d.rounded_rectangle([0, 0, g.width - 2, g.height - 2], radius=r, fill=(18, 30, 70, int(160 * a)), outline=(120, 160, 255, int(150 * a)), width=2)
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

def xmark(d, cx, cy, s, p, col=(255, 85, 80)):
    if p <= 0: return
    a = cl(p * 2); b = cl(p * 2 - 1)
    d.line([(cx - s, cy - s), (cx - s + 2 * s * a, cy - s + 2 * s * a)], fill=col + (255,), width=14)
    if b > 0: d.line([(cx + s, cy - s), (cx + s - 2 * s * b, cy - s + 2 * s * b)], fill=col + (255,), width=14)


# ---------------- timeline
DUR = SEGS[-1][1] + OFF + 5.0
EV = []; FLASH = []; SHAKE = []; PUNCH = []; STREAK = []
def ev(n, t, g=1.0): EV.append((n, round(max(0, t), 3), g))
T = {}
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
T["outro"] = SEGS[-1][1] + OFF + 0.35
T["phone"] = T["outro"] + 1.5
T["end"] = DUR

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
# outro
ev("whoosh", T["outro"] - 0.3, 0.8); STREAK.append(T["outro"] - 0.2); ev("boom", T["outro"] + 0.15, 0.9); PUNCH.append(T["outro"] + 0.15)
ev("pop", T["outro"] + 0.55, 0.7); ev("sparkle", T["outro"] + 0.75, 0.6)
ev("swish", T["phone"] - 0.05, 0.6)
for i, ch in enumerate(PHONE):
    if ch != " ": ev("click", T["phone"] + 0.25 + i * 0.045, 0.35)
ev("ding", T["phone"] + 1.1, 0.6)


# ---------------- scenes
def stack(L, lines, now, t_list, t1, style="blur", cols=None, y0=0, gap=1.18):
    """Draw a vertical stack of animated lines centred on CY+y0. lines=[(txt,size)]."""
    hs = [sz * gap for _, sz in lines]; y = CY + y0 - sum(hs) / 2
    for i, (txt, sz) in enumerate(lines):
        top, bot = (cols[i] if cols else (WHITE, LAV))
        kin(L, txt, CX, y + hs[i] / 2, sz, t_list[i], t1, now, style if isinstance(style, str) else style[i], top, bot)
        y += hs[i]

def scene(now, L, d):
    bright = False
    if now < T["hozircha"]:
        label(L, "DIQQAT", CX, CY - 200, T["autizmni"] - 0.2, T["yuzfoiz"], now, 36)
        kin(L, "AUTIZMNI", CX, CY - 40, 200, T["autizmni"], T["yuzfoiz"], now, "blur")
        if T["yuzfoiz"] <= now < T["dori0"]:
            u = now - T["yuzfoiz"]; p = eo(u / 1.15); ex = cl((now - (T["dori0"] - 0.2)) / 0.2); a = int(255 * (1 - ex))
            rx, ry, R = CX, CY - 200, 230
            ring(d, rx, ry, R, 4, 1, (255, 255, 255, int(40 * (1 - ex))))
            ring(d, rx, ry, R, 16, p, VIO + (a,))
            ring(d, rx, ry, R + 28, 3, eo(u / 0.6), ORG + (int(a * 0.8),), start=90)
            for k in range(60):
                ang = math.radians(k * 6 - 90 + u * 20); r0 = R + 48; r1 = r0 + (9 if k % 5 else 22)
                d.line([(rx + math.cos(ang) * r0, ry + math.sin(ang) * r0), (rx + math.cos(ang) * r1, ry + math.sin(ang) * r1)], fill=(170, 200, 255, int(a * 0.5)), width=2)
            put(L, with_alpha(text_img(f"{int(round(100 * p))}%", 140, 900), 1 - ex), rx, ry)
            label(L, "DAVOLAYDIGAN", CX, CY + 160, T["yuzfoiz"] + 0.25, T["dori0"], now, 40, LAV, 10)
            kin(L, "DAVO?", CX, CY + 290, 210, T["yuzfoiz"] + 0.4, T["dori0"], now, "blur", WHITE, MAG)
        if T["dori0"] <= now < T["nihoyat"]:
            u = now - T["dori0"]; p = back(u / 0.4); ex = cl((now - (T["nihoyat"] - 0.18)) / 0.18)
            if p > 0.05:
                s = p * (1 - ex * 0.3)
                glass(L, (CX - 330 * s, CY - 330 * s, CX + 330 * s, CY + 330 * s), 1 - ex)
                icon(d, "pill", CX, CY - 60, 180 * s, LAV, 12, cl(u / 0.4) * (1 - ex))
            kin(L, "DORI", CX, CY + 210, 100, T["dori0"] + 0.1, T["nihoyat"], now, "letters", MAG, MAG, 800, 22)
        stack(L, [("NIHOYAT", 150), ("TOPILDI?", 230)], now, [T["nihoyat"], T["nihoyat"] + 0.3], T["hozircha"], ["wipe", "blur"], [(LAV, LAV), (WHITE, MAG)])
    elif now < T["chunki"]:
        label(L, "DEGANLARGA", CX, CY - 330, T["hozircha"], T["chunki"], now, 38)
        kin(L, "HOZIRCHA", CX, CY - 190, 190, T["hozircha"] + 0.1, T["chunki"], now, "blur", LAV, LAV, 800)
        if now >= T["ishonmay"]:
            u = now - T["ishonmay"]; g = (int(u * 30) % 3 == 0 and u < 0.5)
            off = random.Random(int(now * 60)).uniform(-18, 18) if g else 0
            for txt, yy, sz in (("ISHONMAY", CY + 30, 200), ("TURING!", CY + 250, 230)):
                if g:
                    put(L, with_alpha(text_img(txt, sz, 900, (255, 90, 60), (255, 90, 60)), 0.6), CX + off - 8, yy)
                    put(L, with_alpha(text_img(txt, sz, 900, (80, 200, 255), (80, 200, 255)), 0.6), CX - off + 8, yy)
                kin(L, txt, CX + off * 0.5, yy, sz, T["ishonmay"] + (0 if yy < CY + 100 else 0.12), T["chunki"], now, "drop", WHITE, MAG)
    elif now < T["gripp"] - 0.15:
        t1 = T["gripp"] - 0.15
        label(L, "CHUNKI", CX, CY - 380, T["chunki"], t1, now, 38)
        kin(L, "AUTIZM", CX, CY - 220, 240, T["chunki"] + 0.05, t1, now, "blur")
        kin(L, "KASALLIK", CX, CY + 20, 170, T["kasallik"], t1, now, "letters", LAV, LAV, 800, 4, hold_scale=0)
        u = now - (T["kasallik"] + 0.35)
        if u > 0:
            ex = cl((now - (t1 - 0.22)) / 0.22)
            sz = 170; tw = text_img("KASALLIK", sz, 800, LAV, LAV, 4).width
            if tw > MAXW: tw = MAXW
            lx0 = CX - tw / 2 - 15
            d.line([(lx0, CY + 22), (lx0 + (tw + 30) * eo(u / 0.25), CY + 22)], fill=(255, 85, 80, int(255 * (1 - ex))), width=16)
        kin(L, "EMAS", CX, CY + 250, 230, T["kasallik"] + 0.35, t1, now, "pop", WHITE, MAG)
    elif now < T["dori1"]:
        t0 = T["gripp"] - 0.15; ex = cl((now - (T["dori1"] - 0.2)) / 0.2)
        label(L, "U GRIPP YOKI", CX, CY - 600, t0, T["dori1"], now, 36)
        label(L, "SHAMOLLASHGA", CX, CY - 545, t0 + 0.2, T["dori1"], now, 36)
        for i, (k, ic, nm) in enumerate([("gripp", "virus", "GRIPP"), ("shamol", "thermo", "SHAMOLLASH")]):
            u = now - T[k]
            if u < 0: continue
            p = eo5(u / 0.45)
            cy = CY - 250 + i * 390; cx = CX + (1 - p) * (-900 if i == 0 else 900)
            glass(L, (cx - 420, cy - 165, cx + 420, cy + 165), p * (1 - ex))
            icon(d, ic, cx - 240, cy, 110, LAV, 9, cl(u / 0.6) * (1 - ex))
            put(L, with_alpha(text_img(nm, 72 if i == 0 else 62, 900, WHITE, LAV), p * (1 - ex)), cx + 110, cy)
            if now >= T["oxsha"]:
                xmark(d, cx - 240, cy, 120, cl((now - T["oxsha"] - i * 0.12) / 0.3) * (1 - ex))
        kin(L, "O'XSHAMAYDI", CX, CY + 430, 130, T["oxsha"], T["dori1"], now, "drop", WHITE, MAG)
    elif now < T["miya"]:
        if now < T["bolmaydi"]:
            u = now - T["dori1"]; p = back(u / 0.45); ex = cl((now - (T["bolmaydi"] - 0.15)) / 0.15)
            icl = Image.new("RGBA", (560, 560)); di = ImageDraw.Draw(icl); icon(di, "pill", 280, 280, 170, LAV, 12, 1)
            icl = with_alpha(scaled(icl.rotate(u * 40, resample=Image.BICUBIC), max(0.02, p)), 1 - ex)
            put(L, icl, CX, CY - 330)
            kin(L, "DORI ICHIB", CX, CY + 20, 150, T["dori1"] + 0.1, T["bolmaydi"], now, "blur", LAV, LAV, 800)
            kin(L, "O'TKAZIB", CX, CY + 200, 130, T["otkazib"], T["bolmaydi"], now, "wipe", WHITE, LAV)
            kin(L, "YUBORIB", CX, CY + 345, 130, T["otkazib"] + 0.25, T["bolmaydi"], now, "wipe", WHITE, LAV)
        else:
            u = now - T["bolmaydi"]
            kin(L, "BO'LMAYDI", CX, CY, 260, T["bolmaydi"], T["miya"], now, "drop", WHITE, MAG)
            if u > 0.25:
                ex = cl((now - (T["miya"] - 0.22)) / 0.22); q = cl((u - 0.25) / 0.2)
                d.rounded_rectangle([40, CY - 150, W - 40, CY + 150], radius=30, outline=(255, 85, 80, int(255 * q * (1 - ex))), width=9)
    elif now < T["dunyo"] - 0.15:
        t0 = T["miya"]; u = now - t0; ex = cl((now - (T["dunyo"] - 0.37)) / 0.22)
        label(L, "AUTIZM BU", CX, CY - 640, t0, T["dunyo"] - 0.15, now, 38)
        rnd = random.Random(4); nodes = []
        for k in range(30):
            a = rnd.uniform(0, 6.28); r = rnd.uniform(40, 260)
            nodes.append((CX + math.cos(a) * r * 1.5, CY - 230 + math.sin(a) * r * 1.3, rnd.uniform(0, 1), rnd.choice([VIO, MAG, LAV, (120, 200, 255)])))
        for i, (x, y, dl, c) in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                x2, y2, dl2, _ = nodes[j]
                if (x - x2) ** 2 + (y - y2) ** 2 < 190 ** 2:
                    p = cl((u - 0.2 - max(dl, dl2) * 0.8) / 0.35)
                    if p > 0: d.line([(x, y), (x + (x2 - x) * p, y + (y2 - y) * p)], fill=(150, 185, 255, int(150 * (1 - ex))), width=2)
        for (x, y, dl, c) in nodes:
            p = back((u - dl * 0.8) / 0.3)
            if p > 0.02:
                r = 13 * p * (1 + 0.25 * math.sin(now * 5 + dl * 9))
                d.ellipse([x - r, y - r, x + r, y + r], fill=c + (int(255 * (1 - ex)),))
        for k in range(4):
            q = (now * 0.7 + k * 0.25) % 1; a = q * 6.28
            x, y = CX + math.cos(a) * 420, CY - 230 + math.sin(a) * 360
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=ORG + (int(220 * (1 - ex)),))
        kin(L, "MIYANING", CX, CY + 300, 170, t0 + 0.6, T["boshqa"], now, "blur", WHITE, LAV)
        kin(L, "BOSHQACHA", CX, CY + 260, 150, T["boshqa"], T["dunyo"] - 0.15, now, "blur", LAV, LAV)
        kin(L, "ISHLASHI", CX, CY + 420, 170, T["boshqa"] + 0.2, T["dunyo"] - 0.15, now, "blur", WHITE, MAG)
    elif now < T["hamma"] - 0.1:
        t0 = T["dunyo"] - 0.15; ex = cl((now - (T["hamma"] - 0.32)) / 0.22)
        label(L, "BOLA DUNYONI", CX, CY - 640, t0, T["hamma"] - 0.1, now, 38)
        label(L, "BOSHQACHA", CX, CY - 585, t0 + 0.2, T["hamma"] - 0.1, now, 38)
        ys = [CY - 330, CY + 20, CY + 370]
        for i, (k, ic, nm) in enumerate([("koradi", "eye", "KO'RADI"), ("eshit", "ear", "ESHITADI"), ("his", "heart", "HIS QILADI")]):
            u = now - T[k]; cy = ys[i]
            if u < 0:
                q = cl((now - t0) / 0.4) * (1 - ex)
                d.rounded_rectangle([CX - 420, cy - 140, CX + 420, cy + 140], radius=26, outline=(100, 140, 230, int(70 * q)), width=2)
                continue
            p = back(u / 0.4, 1.6); a = 1 - ex; s = max(0.05, p)
            glass(L, (CX - 420 * s, cy - 140 * s, CX + 420 * s, cy + 140 * s), a)
            icon(d, ic, CX - 250, cy, 85, LAV if i != 2 else (255, 140, 120), 7, cl(u / 0.5) * a)
            put(L, with_alpha(text_img(nm, 66 if i < 2 else 58, 900, WHITE, LAV), cl(u / 0.25) * a), CX + 90, cy)
            put(L, with_alpha(text_img(f"0{i+1}", 28, 700, ORG, ORG), cl(u / 0.25) * a), CX + 370, cy - 105)
            if i > 0:
                pl = cl(u / 0.3); y0, y1 = ys[i - 1] + 145, cy - 145
                for dy in range(int(y0), int(y0 + (y1 - y0) * pl), 16):
                    d.line([(CX, dy), (CX, min(dy + 8, y1))], fill=LAV + (int(200 * a),), width=3)
                q = (now * 1.2) % 1
                if pl >= 1: d.ellipse([CX - 8, y0 + (y1 - y0) * q - 8, CX + 8, y0 + (y1 - y0) * q + 8], fill=ORG + (int(255 * a),))
    elif now < T["qabul"]:
        t0 = T["hamma"] - 0.1
        label(L, "VA BU", CX, CY - 470, t0, T["qabul"], now, 38)
        kin(L, "HAMMA", CX, CY - 340, 160, t0, T["qabul"], now, "blur", LAV, LAV, 800)
        kin(L, "BOLADA", CX, CY - 160, 160, t0 + 0.15, T["qabul"], now, "blur", LAV, LAV, 800)
        kin(L, "HAR XIL", CX, CY + 110, 240, T["harxil"], T["qabul"], now, "pop", WHITE, MAG)
        ub = now - T["harxil"]
        if ub > 0:
            rnd = random.Random(9); ex = cl((now - (T["qabul"] - 0.3)) / 0.3)
            for k in range(80):
                a = rnd.uniform(0, 6.28); v = rnd.uniform(300, 1000); c = rnd.choice([VIO, MAG, LAV, (120, 200, 255), (255, 200, 120), (255, 120, 120)])
                dist = v * eo(ub / 1.4); x = CX + math.cos(a) * dist * 0.8; y = CY + 110 + math.sin(a) * dist * 1.2
                s = rnd.uniform(9, 22); kind = k % 4; al = int(255 * (1 - ex))
                if kind == 0: d.ellipse([x - s, y - s, x + s, y + s], fill=c + (al,))
                elif kind == 1: d.rectangle([x - s, y - s, x + s, y + s], outline=c + (al,), width=4)
                elif kind == 2: d.polygon([(x, y - s), (x + s, y + s), (x - s, y + s)], outline=c + (al,), width=4)
                else: d.ellipse([x - s, y - s, x + s, y + s], outline=c + (al,), width=4)
    elif now < T["gap"] - 0.05:
        bright = True; t0 = T["qabul"]; t1 = T["gap"] - 0.05
        label(L, "BOLANI SHU", CX, CY - 380, t0 + 0.05, t1, now, 38, BRAND, 10)
        label(L, "HOLATDA", CX, CY - 320, t0 + 0.2, t1, now, 38, BRAND, 10)
        kin(L, "QABUL", CX, CY - 80, 300, t0, t1, now, "blur", (70, 115, 230), BRAND)
        kin(L, "QILIB", CX, CY + 170, 200, T["qabul2"], t1, now, "wipe", ORG, (230, 120, 30), 900)
    elif now < T["farz"] - 0.1:
        t0 = T["gap"] - 0.05; ex = cl((now - (T["farz"] - 0.32)) / 0.22)
        label(L, "UNGA O'RGATISH", CX, CY - 640, t0, T["farz"] - 0.1, now, 38)
        ys = [CY - 330, CY + 20, CY + 370]; lx = 95
        prog = 0
        for i, k in enumerate(["gap", "mul", "ozini"]):
            if now >= T[k]: prog = i + cl((now - T[k]) / 0.5)
        d.line([(lx, ys[0]), (lx, ys[2])], fill=(255, 255, 255, int(40 * (1 - ex))), width=4)
        d.line([(lx, ys[0]), (lx, ys[0] + (ys[2] - ys[0]) * cl(prog / 3))], fill=ORG + (int(255 * (1 - ex)),), width=6)
        for i, (k, ic, nm) in enumerate([("gap", "mouth", "GAPIRISH"), ("mul", "chat", "MULOQOT"), ("ozini", "balance", "O'ZINI")]):
            u = now - T[k]
            if u < 0: continue
            p = eo5(u / 0.4); a = 1 - ex; cy = ys[i]; cx = CX + 45 + (1 - p) * 300
            glass(L, (cx - 390, cy - 140, cx + 390, cy + 140), p * a)
            icon(d, ic, cx - 230, cy, 75, LAV, 7, cl(u / 0.6) * a)
            put(L, with_alpha(text_img(nm, 66, 900, WHITE, LAV), p * a), cx + 90, cy - (22 if i == 2 else 0))
            if i == 2: put(L, with_alpha(text_img("BOSHQARISH", 46, 800, LAV, LAV), p * a), cx + 90, cy + 45)
            put(L, with_alpha(text_img(f"0{i+1}", 28, 700, ORG, ORG), p * a), cx + 340, cy - 105)
            d.ellipse([lx - 14, cy - 14, lx + 14, cy + 14], fill=ORG + (int(255 * p * a),))
        if now >= T["orgat"]:
            u = now - T["orgat"]
            L.alpha_composite(Image.new("RGBA", (W, H), (3, 7, 22, int(185 * cl(u / 0.2) * (1 - ex)))))
            kin(L, "O'RGATISH", CX, CY - 90, 170, T["orgat"], T["farz"] - 0.1, now, "drop", WHITE, LAV)
            kin(L, "KERAK", CX, CY + 110, 230, T["orgat"] + 0.15, T["farz"] - 0.1, now, "drop", WHITE, MAG)
    elif now < T["biz"] - 0.1:
        t0 = T["farz"] - 0.1; u = now - t0; ex = cl((now - (T["biz"] - 0.32)) / 0.22)
        cone = Image.new("L", (W // 4, H // 4)); dc = ImageDraw.Draw(cone); sp = eo(u / 0.6)
        dc.polygon([(W / 8 - 14, 0), (W / 8 + 14, 0), (W / 8 + 125 * sp, H / 4), (W / 8 - 125 * sp, H / 4)], fill=int(110 * (1 - ex)))
        cone = cone.filter(ImageFilter.GaussianBlur(10)).resize((W, H))
        lay = Image.new("RGBA", (W, H), (170, 200, 255, 0)); lay.putalpha(cone); L.alpha_composite(lay)
        d.ellipse([CX - 480 * sp, H - 330, CX + 480 * sp, H - 270], fill=(150, 180, 255, int(60 * (1 - ex))))
        if now < T["markaz"]:
            kin(L, "FARZANDINGIZ", CX, CY - 180, 160, t0 + 0.05, T["markaz"], now, "blur", WHITE, LAV)
            kin(L, "TASHXISLI", CX, CY + 10, 150, T["tash"], T["markaz"], now, "wipe", LAV, LAV, 800)
            kin(L, "BO'LSA", CX, CY + 170, 150, T["tash"] + 0.2, T["markaz"], now, "wipe", LAV, LAV, 800)
        else:
            label(L, "BIZNING", CX, CY - 300, T["markaz"], T["biz"] - 0.1, now, 40)
            kin(L, "MARKAZIMIZGA", CX, CY - 150, 160, T["markaz"], T["biz"] - 0.1, now, "blur", WHITE, LAV)
            kin(L, "KELING", CX, CY + 60, 240, T["markaz"] + 0.45, T["biz"] - 0.1, now, "pop", WHITE, MAG)
    elif now < T["outro"]:
        t0 = T["biz"] - 0.1; u = now - t0; ex = cl((now - (T["outro"] - 0.25)) / 0.25)
        beat = 1 + 0.07 * max(0, math.sin((now - T["biz"]) * 2 * math.pi * 0.9)) ** 12
        icon(d, "heart", CX, CY - 260, 230 * back(u / 0.6) * beat, (255, 120, 90), 13, cl(u / 0.9) * (1 - ex))
        for k in range(3):
            rr = 250 + k * 50; ang = now * (30 + 15 * k)
            box = [CX - rr * 1.5, CY - 260 - rr * 0.45, CX + rr * 1.5, CY - 260 + rr * 0.45]
            d.arc(box, ang, ang + 220, fill=LAV + (int(110 * (1 - ex) * cl(u / 0.8)),), width=2)
            q = math.radians(ang + 220); px, py = CX + math.cos(q) * rr * 1.5, CY - 260 + math.sin(q) * rr * 0.45
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=ORG + (int(230 * (1 - ex) * cl(u / 0.8)),))
        label(L, "QO'LDAN KELGANCHA", CX, CY + 110, T["biz"] + 0.6, T["outro"], now, 38)
        kin(L, "YORDAM", CX, CY + 260, 200, T["yordam"], T["outro"], now, "blur", WHITE, LAV)
        kin(L, "BERAMIZ", CX, CY + 450, 200, T["yordam"] + 0.25, T["outro"], now, "blur", WHITE, MAG)
    else:
        outro(now, L, d)
    return bright

def outro(now, L, d):
    u = now - T["outro"]
    # emblem body: scale-in with overshoot
    p = back((u - 0.1) / 0.5, 2.0); es = 2.0
    if p > 0.02:
        b = scaled(BODY, es * p)
        put(L, b, CX, CY - 380 + (1 - cl(p)) * 40)
        # orange dot drops in with bounce
        q = (u - 0.4) / 0.55
        if q > 0:
            fall = 1 - eo5(q); bounce = abs(math.sin(cl(q) * math.pi * 2.2)) * (1 - cl(q)) * 60
            dx = CX + (DOT_C[0] - BODY.width / 2) * es; dy = CY - 380 + (DOT_C[1] - BODY.height / 2) * es - fall * 500 - bounce
            r = DOT_R * es
            d.ellipse([dx - r, dy - r, dx + r, dy + r], fill=ORG + (255,))
    # wordmark wipe
    q = eo((u - 0.75) / 0.6)
    if q > 0:
        wm = scaled(WORD, 0.62)
        cw = int(wm.width * q)
        if cw > 2:
            m = Image.new("L", wm.size); ImageDraw.Draw(m).rectangle([0, 0, cw, wm.height], fill=255)
            wm = wm.copy(); wm.putalpha(Image.composite(wm.getchannel("A"), Image.new("L", wm.size), m))
            put(L, wm, CX, CY - 40)
    label(L, "LOGOPEDIK MARKAZ", CX, CY + 85, T["outro"] + 1.0, DUR + 1, now, 36, LAV, 12)
    # phone pill
    v = now - T["phone"]
    if v > 0:
        label(L, "MUROJAAT UCHUN", CX, CY + 300, T["phone"], DUR + 1, now, 38, ORG, 12)
        pw = 470 * eo5(v / 0.45); ph = 82; py = CY + 440
        if pw > 10:
            pulse = 0.5 + 0.5 * math.sin(v * 4)
            d.rounded_rectangle([CX - pw - 12, py - ph - 12, CX + pw + 12, py + ph + 12], radius=ph + 12, outline=ORG + (int(90 + 80 * pulse),), width=3)
            d.rounded_rectangle([CX - pw, py - ph, CX + pw, py + ph], radius=ph, fill=(245, 140, 43, 255))
        if v > 0.3:
            # phone glyph
            hx, hy = CX - 370, py
            d.ellipse([hx - 46, hy - 46, hx + 46, hy + 46], fill=(255, 255, 255, 255))
            d.rounded_rectangle([hx - 16, hy - 28, hx + 16, hy + 28], radius=7, outline=(245, 140, 43, 255), width=6)
            d.line([(hx - 5, hy + 19), (hx + 5, hy + 19)], fill=(245, 140, 43, 255), width=4)
            n = int(cl((v - 0.25) / (len(PHONE) * 0.045)) * len(PHONE))
            shown = PHONE[:n]
            if shown:
                im = text_img(shown, 66, 800, WHITE, WHITE)
                full = text_img(PHONE, 66, 800, WHITE, WHITE)
                put(L, im, CX + 45 - full.width / 2 + im.width / 2, py + 2)
            if n < len(PHONE) and int(v * 6) % 2 == 0:
                full = text_img(PHONE, 66, 800, WHITE, WHITE); cur = text_img(shown or " ", 66, 800).width if shown else 0
                x = CX + 45 - full.width / 2 + cur + 8; d.line([(x, py - 34), (x, py + 34)], fill=(255, 255, 255, 255), width=4)


# ---------------- frame compose
def frame(now):
    L = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(L)
    bright = scene(now, L, d)
    base = (BGB if bright else BG).copy()
    bd = ImageDraw.Draw(base, "RGBA")
    if not bright:
        for (x, y, s, sp, ph) in DUST:
            yy = (y - now * sp) % H; xx = x + math.sin(now * 0.5 + ph) * 12
            a = int(90 + 90 * math.sin(now * 2 + ph))
            bd.ellipse([xx - s, yy - s, xx + s, yy + s], fill=(170, 200, 255, max(0, a)))
    for st in STREAK:
        u = now - st
        if 0 <= u < 0.9:
            q = eo(u / 0.6); a = int(255 * (1 - cl((u - 0.4) / 0.5))); w = W * 0.5 * q
            bd.line([(CX - w, CY), (CX + w, CY)], fill=(160, 195, 255, a), width=4)
            bd.line([(CX - w * 0.6, CY), (CX + w * 0.6, CY)], fill=(255, 255, 255, a), width=2)
    a = L.getchannel("A").resize((W // 4, H // 4), Image.BILINEAR)
    g1 = a.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    g2 = a.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    gc = (80, 140, 255) if not bright else (150, 180, 255)
    base = base.convert("RGBA")
    gl = Image.new("RGBA", (W, H), gc + (0,)); gl.putalpha(g1.point(lambda v: int(v * (0.55 if not bright else 0.3)))); base.alpha_composite(gl)
    gl2 = Image.new("RGBA", (W, H), gc + (0,)); gl2.putalpha(g2.point(lambda v: int(v * (0.45 if not bright else 0.2)))); base.alpha_composite(gl2)
    base.alpha_composite(L)
    img = base.convert("RGB")
    z = 1.02 + 0.012 * math.sin(now * 0.4)
    for p in PUNCH:
        u = now - p
        if 0 <= u < 0.6: z += 0.035 * (1 - eo(u / 0.6))
    sx = sy = 0.0
    for s in SHAKE:
        u = now - s
        if 0 <= u < 0.35:
            k = (1 - u / 0.35) * 14; r = random.Random(int(now * 1000)); sx += r.uniform(-k, k); sy += r.uniform(-k, k)
    cw, ch = W / z, H / z; ox = max(0, min(W - cw, (W - cw) / 2 + sx)); oy = max(0, min(H - ch, (H - ch) / 2 + sy))
    img = img.resize((W, H), Image.BICUBIC, box=(ox, oy, ox + cw, oy + ch))
    img = Image.blend(img, Image.merge("RGB", [GRAIN[int(now * FPS) % 4]] * 3), 0.035)
    # logo watermark (top, outside camera motion); hidden on the white scene and in the outro
    if not bright and 0.8 < now < T["outro"] - 0.1:
        wa = cl((now - 0.8) / 0.5) * (1 - cl((now - (T["outro"] - 0.4)) / 0.3))
        im = img.convert("RGBA"); im.alpha_composite(with_alpha(WM, 0.92 * wa), (int(CX - WM.width / 2), 120)); img = im.convert("RGB")
    for f in FLASH:
        u = now - f
        if -0.05 <= u < 0.35:
            a = (1 - cl(u / 0.35)) if u >= 0 else 1
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 0.85 * a)
    if now < 0.3: img = Image.blend(Image.new("RGB", (W, H)), img, now / 0.3)
    if now > DUR - 0.4: img = Image.blend(img, Image.new("RGB", (W, H)), cl((now - (DUR - 0.4)) / 0.4) * 0.6)
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
    json.dump({"events": EV, "dur": DUR, "off": OFF}, open("events4.json", "w"))
    print("frames", len(times), "dur", DUR)
