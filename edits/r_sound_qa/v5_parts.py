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
    paste_alpha(c, fc, hx - fc.width / 2 + 10, hy - fc.height + 30, 1.0)
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
