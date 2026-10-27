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
