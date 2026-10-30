# ================= v11: premium glass look — mesh background, frosted glass icons/logos, new captions, body framing =================
import cv2 as _cv
import cairosvg as _cairosvg
import io as _io
SVG = os.path.join(HERE, "av", "svg")
PUNCH[:] = []
TERRA = (150, 140, 255)          # seam accent now violet (render() reads it at call time)

# ---------- expert framing: show head + shoulders + chest (pad the narrow source with its own wall) ----------
_PAD_CACHE = {}
def _padded(src):
    key = id(src)
    if key in _PAD_CACHE: return _PAD_CACHE[key]
    a = np.asarray(src.convert("RGB")).astype(np.float32)
    P_ = 90
    edgeL = _cv.GaussianBlur(a[:, :6].mean(1, keepdims=True), (1, 41), 0)
    edgeR = _cv.GaussianBlur(a[:, -6:].mean(1, keepdims=True), (1, 41), 0)
    wall = np.median(a[40:260, :30].reshape(-1, 3), 0)
    f = np.linspace(0, 1, P_)[None, :, None] ** 1.4
    L = edgeL * (1 - f[:, ::-1]) + wall * f[:, ::-1]
    R = edgeR * (1 - f) + wall * f
    out = np.concatenate([L.repeat(1, 0), a, R], 1)
    im = Image.fromarray(np.uint8(np.clip(out, 0, 255)))
    _PAD_CACHE.clear(); _PAD_CACHE[key] = (im, P_)
    return im, P_

def expert_crop(src, w, h, z=1.0, face_at=0.40, dx=0.0):
    """50/50: head + shoulders + chest (source padded with its own wall); full screen: the whole frame. Continuous in between."""
    im, P_ = _padded(src)
    f = clamp((h - HALF) / (H - HALF))
    ch = lerp(520.0, float(SH), f)
    cw = ch * w / h
    top = lerp(96.0, 0.0, f)
    top = clamp(top, 0, SH - ch)
    cx = P_ + SW / 2
    return im.resize((int(w), int(h)), Image.BICUBIC, box=(cx - cw / 2, top, cx + cw / 2, top + ch)).convert("RGBA")

# ---------- background: deep navy mesh gradient with slowly drifting colour light ----------
@lru_cache(maxsize=1)
def _mesh_parts():
    base = np.zeros((HALF, W, 3), np.float32)
    yy = np.linspace(0, 1, HALF)[:, None]
    base[:] = (np.array((9, 10, 24)) * (1 - yy[..., None]) + np.array((14, 12, 30)) * yy[..., None])
    blobs = []
    for col, r in (((96, 70, 240), 520), ((40, 120, 255), 460), ((210, 70, 160), 380), ((20, 170, 160), 340)):
        g = np.zeros((r * 2, r * 2, 3), np.float32)
        yy2, xx2 = np.mgrid[0:r * 2, 0:r * 2]
        d = np.clip(1 - np.hypot(xx2 - r, yy2 - r) / r, 0, 1) ** 2.2
        g[:] = np.array(col, np.float32) * d[..., None]
        blobs.append(g)
    return base, blobs

def mesh_bg(t):
    base, blobs = _mesh_parts()
    out = base.copy()
    paths = [(220, 620, 0.21, 0.0), (860, 520, 0.17, 1.7), (620, 930, 0.23, 3.1), (120, 300, 0.19, 4.4)]
    for g, (x0, y0, sp, ph) in zip(blobs, paths):
        r = g.shape[0] // 2
        cx = int(x0 + 120 * math.sin(t * sp + ph)); cy = int(y0 + 80 * math.cos(t * sp * 1.3 + ph))
        xa, ya = max(0, cx - r), max(0, cy - r); xb, yb = min(W, cx + r), min(HALF, cy + r)
        if xb <= xa or yb <= ya: continue
        out[ya:yb, xa:xb] += g[ya - (cy - r):yb - (cy - r), xa - (cx - r):xb - (cx - r)] * 0.55
    im = Image.fromarray(np.uint8(np.clip(out, 0, 255))).convert("RGBA")
    return im

def scene(kind="room"):
    return mesh_bg(_T_NOW[0])
_T_NOW = [0.0]
_render_prev = render
def render(i, src):
    _T_NOW[0] = i / FPS
    return _render_prev(i, src)

# ---------- icons ----------
@lru_cache(maxsize=256)
def svg_icon(name, size, color="#ffffff", stroke=None, fill=None):
    path = os.path.join(SVG, name + ".svg")
    s = open(path).read()
    if fill: s = s.replace('fill="none"', f'fill="{fill}"')
    if name.startswith("brand_"):
        s = s.replace("<path ", f'<path fill="{color}" ', 1)
    else:
        s = s.replace("currentColor", color)
        if stroke: s = s.replace('stroke-width="2"', f'stroke-width="{stroke}"')
    png = _cairosvg.svg2png(bytestring=s.encode(), output_width=size, output_height=size)
    return Image.open(_io.BytesIO(png)).convert("RGBA")

def _rr_mask(w_, h_, r):
    m = Image.new("L", (w_, h_), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w_ - 1, h_ - 1), r, fill=255); return m

@lru_cache(maxsize=64)
def _glass_static(w_, h_, r, tint, alpha_top, alpha_bot, border=True):
    """Tint, sheen, depth and gradient border of a glass slab (frost is added per frame from the canvas)."""
    yy = np.linspace(0, 1, h_)[:, None]; xx = np.linspace(0, 1, w_)[None, :]
    tc = np.array(tint, np.float32)
    rgb = np.empty((h_, w_, 3), np.float32); rgb[:] = tc
    rgb = rgb * (1.0 - 0.25 * yy[..., None])
    a = (alpha_top + (alpha_bot - alpha_top) * yy) * np.ones_like(xx)
    # diagonal sheen (top-left)
    sheen = np.clip(1.0 - (xx * 0.9 + yy * 1.1) / 0.75, 0, 1) ** 1.6
    rgb = rgb * (1 - sheen[..., None] * 0.55) + 255 * sheen[..., None] * 0.55
    a = np.clip(a + sheen * 0.22, 0, 1)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), "RGBA")
    m = _rr_mask(w_, h_, r)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
    # inner bottom depth
    dep = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    ImageDraw.Draw(dep).rounded_rectangle((0, int(h_ * 0.86), w_ - 1, h_ - 1), r, fill=(0, 0, 0, 40))
    dep = dep.filter(ImageFilter.GaussianBlur(max(2, h_ // 30))); dep.putalpha(ImageChops.multiply(dep.getchannel("A"), m))
    im.alpha_composite(dep)
    if border:
        bw = max(2, int(min(w_, h_) * 0.012))
        bl = Image.new("L", (w_, h_), 0); ImageDraw.Draw(bl).rounded_rectangle((0, 0, w_ - 1, h_ - 1), r, outline=255, width=bw)
        g = np.clip(1.0 - (xx + yy) * 0.6, 0.18, 1.0)
        bA = (np.asarray(bl, np.float32) * g * 0.85).astype(np.uint8)
        bimg = Image.new("RGBA", (w_, h_), (255, 255, 255, 0)); bimg.putalpha(Image.fromarray(bA))
        im.alpha_composite(bimg)
    return im, m

def glass(c, x, y, w_, h_, tint=(255, 255, 255), k=1.0, glyph=None, glyph_k=0.5, r=None, rot=0.0, a=1.0,
          alpha=(0.30, 0.14), glow_col=None, shine=None, content=None):
    """Composite a frosted-glass slab centred at (x, y). `glyph` = RGBA icon, `content` = RGBA drawn on the glass."""
    if k <= 0.02 or a <= 0.01: return
    W_, H_ = max(8, int(w_ * k)), max(8, int(h_ * k))
    rr = int((r if r is not None else min(w_, h_) * 0.26) * k)
    x0, y0 = int(x - W_ / 2), int(y - H_ / 2)
    # shadow + colour glow
    pad = int(40 * k) + 10
    sh = Image.new("RGBA", (W_ + pad * 2, H_ + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + int(16 * k), pad + W_, pad + H_ + int(16 * k)), rr, fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(max(4, int(22 * k))))
    paste_alpha(c, sh, x0 - pad, y0 - pad, a)
    if glow_col:
        g = glow(int(max(W_, H_) * 0.9) + 2, glow_col)
        paste_alpha(c, g, x - g.width / 2, y - g.height / 2 + 10 * k, a * 0.55)
    # frost: blur what is behind
    tile = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    bx0, by0 = max(0, x0), max(0, y0); bx1, by1 = min(c.width, x0 + W_), min(c.height, y0 + H_)
    if bx1 > bx0 and by1 > by0:
        behind = c.crop((bx0, by0, bx1, by1)).filter(ImageFilter.GaussianBlur(max(3, int(16 * k))))
        tile.paste(behind, (bx0 - x0, by0 - y0))
    st, m = _glass_static(W_, H_, rr, tint, alpha[0], alpha[1])
    tile.alpha_composite(st)
    tile.putalpha(ImageChops.multiply(Image.new("L", (W_, H_), 255), m))
    if content is not None:
        cc = content.resize((W_, H_), Image.LANCZOS) if content.size != (W_, H_) else content
        tile.alpha_composite(cc)
    if glyph is not None:
        gs = int(min(W_, H_) * glyph_k)
        gi = glyph.resize((gs, int(glyph.height * gs / glyph.width)), Image.LANCZOS)
        gsh = Image.new("RGBA", gi.size, (0, 0, 0, 0)); gsh.putalpha(gi.getchannel("A").point(lambda v: int(v * 0.35)))
        gsh = gsh.filter(ImageFilter.GaussianBlur(max(2, gs // 30)))
        tile.alpha_composite(gsh, ((W_ - gi.width) // 2 + max(1, gs // 40), (H_ - gi.height) // 2 + max(2, gs // 22)))
        tile.alpha_composite(gi, ((W_ - gi.width) // 2, (H_ - gi.height) // 2))
    if shine is not None and 0 < shine < 1:      # diagonal light sweep
        sw = Image.new("L", (W_, H_), 0)
        sx = int(-W_ * 0.6 + shine * W_ * 2.2)
        ImageDraw.Draw(sw).polygon([(sx, 0), (sx + W_ * 0.22, 0), (sx - H_ * 0.35 + W_ * 0.22, H_), (sx - H_ * 0.35, H_)], fill=110)
        sw = ImageChops.multiply(sw.filter(ImageFilter.GaussianBlur(6)), m)
        tile.alpha_composite(Image.merge("RGBA", (Image.new("L", (W_, H_), 255),) * 3 + (sw,)))
    tile.putalpha(ImageChops.multiply(tile.getchannel("A"), m))
    if rot:
        tile = tile.rotate(rot, Image.BICUBIC, expand=True)
        x0, y0 = int(x - tile.width / 2), int(y - tile.height / 2)
    paste_alpha(c, tile, x0, y0, a)

TINTS = {"violet": (124, 92, 255), "blue": (56, 132, 255), "pink": (236, 72, 153), "teal": (20, 184, 166), "amber": (245, 166, 35),
         "green": (34, 197, 94), "red": (239, 68, 68), "white": (255, 255, 255), "tg": (42, 171, 238), "sheets": (15, 157, 88),
         "gold": (250, 204, 21)}

def gicon(c, name, x, y, size, tint, lt0, lt, t=0.0, bob=0.0, ph=0.0, rot=0.0, a=1.0, glyph_k=0.5, w=11, z=0.5, shine=None, glow_on=True):
    if lt < lt0: return
    k = spring(lt - lt0, w=w, z=z)
    col = TINTS.get(tint, tint)
    glass(c, x, y + bob * math.sin(t * 1.6 + ph), size, size, tint=col, k=k, glyph=svg_icon(name, 256), glyph_k=glyph_k,
          rot=rot, a=a * clamp(k * 1.6), alpha=(0.42, 0.20), glow_col=col if glow_on else None, shine=shine)

@lru_cache(maxsize=8)
def ig_gradient(size):
    im = _squircle(size, int(size * 0.26), [(0, (254, 218, 117)), (0.3, (250, 126, 30)), (0.6, (214, 41, 118)), (0.85, (150, 47, 191)), (1, (79, 91, 213))], radial=True)
    return im.resize((size, size), Image.LANCZOS)

def brand(c, kind, x, y, size, lt0, lt, t=0.0, bob=0.0, ph=0.0, a=1.0, shine=None):
    """Premium glass brand tile: frosted slab in brand colour + crisp white brand mark."""
    if lt < lt0: return
    k = spring(lt - lt0, w=10, z=0.55)
    yy = y + bob * math.sin(t * 1.5 + ph)
    if kind == "instagram":
        S_ = max(8, int(size * k))
        base = ig_gradient(S_).copy(); base.putalpha(base.getchannel("A").point(lambda v: int(v * 0.78)))
        glass(c, x, yy, size, size, tint=(214, 41, 118), k=k, glyph=svg_icon("brand_instagram", 256), glyph_k=0.5, a=a * clamp(k * 1.6),
              alpha=(0.0, 0.0), glow_col=(214, 41, 118), shine=shine, content=base)
        return
    col = {"telegram": TINTS["tg"], "sheets": TINTS["sheets"], "notion": (245, 245, 245)}[kind]
    gl = {"telegram": "brand_telegram", "sheets": "brand_googlesheets", "notion": "brand_notion"}[kind]
    gcol = "#111111" if kind == "notion" else "#ffffff"
    alpha = (0.92, 0.80) if kind == "notion" else (0.62, 0.42)
    glass(c, x, yy, size, size, tint=col, k=k, glyph=svg_icon(gl, 256, gcol), glyph_k=0.52, a=a * clamp(k * 1.6),
          alpha=alpha, glow_col=(150, 140, 255) if kind == "notion" else col, shine=shine)

def gpill(c, x, y, text, tint=(255, 255, 255), size=30, a=1.0, k=1.0, fg=WHITE, alpha=(0.34, 0.2), center=False):
    f = dfont("Black", size); tw = f.getlength(text)
    w_, h_ = int(tw + size * 1.4), int(size * 1.7)
    cx = x if center else x + w_ / 2
    lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((w_ / 2, h_ / 2 + 1), text, font=f, fill=fg, anchor="mm")
    glass(c, cx, y, w_, h_, tint=tint, k=k, r=h_ // 2, a=a, alpha=alpha, content=lay, glow_col=None)
    return w_

# ---------- captions: medium-weight words rising one by one + frosted-glass keyword pill ----------
STY["thin"] = (lambda: dfont("Medium", 56), 80)
STY["bold"] = (lambda: dfont("Black", 72), 106)
@lru_cache(maxsize=512)
def _word_img(word, style):
    f = STY[style][0]()
    w_ = int(f.getlength(word)) + 24; h_ = int(f.size * 1.45)
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((12, h_ / 2), word, font=f, fill=WHITE, anchor="lm")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.55)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)), (0, 3)); out.alpha_composite(im)
    return out

def anim_line(canvas, text, style, x, y, t0, t, out, center=False):
    u = t - t0
    if u <= 0: return
    f = STY[style][0]()
    words = text.split(" ")
    sp = f.getlength(" ")
    total = sum(f.getlength(w) for w in words) + sp * (len(words) - 1)
    x0 = (W - total) / 2 if center else x
    yo = -24 * out
    if style == "bold":
        pk = spring(u, w=12, z=0.62)
        ph = int(f.size * 1.42); pw = total + 44
        glass(canvas, x0 + total / 2, y + ph / 2 - 2 + yo, pw, ph, tint=(255, 255, 255), k=max(0.02, 0.85 + 0.15 * pk) if pk > 0 else 0.02,
              r=ph // 2, a=clamp(u / 0.18) * (1 - out), alpha=(0.26, 0.12), glow_col=(150, 140, 255))
    cx = x0
    for j, wd in enumerate(words):
        wu = u - j * (0.07 if style == "bold" else 0.09)
        ww = f.getlength(wd)
        if wu > 0:
            kk = spring(wu, w=14, z=0.7)
            im = _word_img(wd, style)
            b = (1 - clamp(wu / 0.25)) * 6
            if b > 0.5: im = im.filter(ImageFilter.GaussianBlur(b))
            dy = (1 - clamp(kk)) * 30 + (2 if style == "bold" else 0)
            paste_alpha(canvas, im, cx - 12, y + dy - (f.size * 1.45 - f.size) / 2 + yo + (6 if style == "bold" else -6), clamp(wu / 0.2) * (1 - out))
        cx += ww + sp

# ---------- glass Notion window ----------
def notion_glass(c, x, y, w_, h_, lt, rows_at=(0, 0.2, 0.4), cols_at=0.0, sidebar_at=0.0, k=1.0, a=1.0, title="Kontent plan"):
    lay = Image.new("RGBA", (w_, h_), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for j, col in enumerate(((255, 96, 92), (255, 190, 46), (40, 200, 64))):
        d.ellipse((22 + j * 26, 18, 38 + j * 26, 34), fill=col)
    sbw = int(w_ * 0.27)
    d.rounded_rectangle((10, 50, sbw, h_ - 10), 18, fill=(255, 255, 255, 22))
    items = [("notebook-pen", "Kontent plan"), ("calendar", "Kalendar"), ("clapperboard", "Syomka"), ("layers", "Rubrikalar")]
    for j, (ic, nm) in enumerate(items):
        al = clamp((lt - sidebar_at - j * 0.12) / 0.25)
        if al <= 0: continue
        yy = 72 + j * 48
        row = Image.new("RGBA", lay.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        row.alpha_composite(svg_icon(ic, 28, "#d9d4ff", 2), (24, yy))
        rd.text((62, yy + 14), nm, font=dfont("Medium", 22), fill=(236, 234, 250), anchor="lm")
        row.putalpha(row.getchannel("A").point(lambda v: int(v * al))); lay.alpha_composite(row)
    x0 = sbw + 28
    d.text((x0, 84), title, font=dfont("Black", 36), fill=WHITE, anchor="lm")
    tw = w_ - x0 - 24
    if lt > cols_at:
        al = clamp((lt - cols_at) / 0.3)
        d.line([(x0, 168), (x0 + tw * al, 168)], fill=(255, 255, 255, 60), width=2)
        for nm, fx in (("Mavzu", 0.0), ("Status", 0.5), ("Rubrika", 0.75)):
            if fx <= al: d.text((x0 + tw * fx, 148), nm, font=dfont("Medium", 21), fill=(200, 196, 230), anchor="lm")
    data = [("Hook g'oyalari", ("Syomka", (245, 166, 35)), ("Savol-javob", (56, 132, 255))),
            ("Mijoz keysi", ("Joylandi", (34, 197, 94)), ("Keys", (236, 72, 153))),
            ("3 ta xato", ("G'oya", (148, 140, 170)), ("Maslahat", (124, 92, 255))),
            ("Behind the scenes", ("Montaj", (239, 120, 60)), ("Lifestyle", (20, 184, 166)))]
    for j, ra in enumerate(rows_at):
        if lt < ra: continue
        al = ease_out(clamp((lt - ra) / 0.3))
        yy = 184 + j * 52
        if yy + 40 > h_: break
        row = Image.new("RGBA", lay.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        mt, (st, sc), (rb, rc) = data[j % 4]
        rd.text((x0, yy + 18), mt, font=dfont("Medium", 22), fill=WHITE, anchor="lm")
        for (txt, col, fx) in ((st, sc, 0.5), (rb, rc, 0.75)):
            ff = dfont("Black", 17); pw = ff.getlength(txt) + 22
            rd.rounded_rectangle((x0 + tw * fx, yy + 4, x0 + tw * fx + pw, yy + 34), 15, fill=col + (220,))
            rd.text((x0 + tw * fx + 11, yy + 19), txt, font=ff, fill=WHITE, anchor="lm")
        rd.line([(x0, yy + 44), (x0 + tw, yy + 44)], fill=(255, 255, 255, 30), width=1)
        row.putalpha(row.getchannel("A").point(lambda v: int(v * al)))
        lay.alpha_composite(row, (int((1 - al) * 30), 0))
    glass(c, x, y, w_, h_, tint=(190, 185, 255), k=k, r=28, a=a, alpha=(0.20, 0.10), content=lay, glow_col=(124, 92, 255))

# ---------- content-maker character (thinking) ----------
def _poly_round(d, pts, fill): d.polygon(pts, fill=fill)
def _vgrad(w_, h_, c0, c1):
    yy = np.linspace(0, 1, h_)[:, None, None]
    return Image.fromarray(np.uint8(np.array(c0) * (1 - yy) + np.array(c1) * yy).repeat(w_, 1)).convert("RGBA")

def _shape(size, draw_fn, fill_img):
    m = Image.new("L", size, 0); draw_fn(ImageDraw.Draw(m)); out = fill_img.resize(size) if fill_img.size != size else fill_img.copy()
    out.putalpha(m); return out

def creator(t, lt, s=1.0):
    """Stylised content creator at a desk, hand on chin, thinking. Drawn at 2x with soft shading."""
    S = 2.0
    Wc, Hc = int(560 * S), int(440 * S)
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    def P(x, y): return (x * S, y * S)
    # torso: brown tee with shoulder shading
    tee = _shape((Wc, Hc), lambda d: d.rounded_rectangle((*P(150, 262), *P(410, 470)), int(110 * S), fill=255),
                 _vgrad(Wc, Hc, (150, 92, 58), (96, 58, 36)))
    im.alpha_composite(tee)
    d = ImageDraw.Draw(im)
    d.pieslice((*P(238, 236), *P(322, 290)), 0, 180, fill=(92, 54, 34))                      # collar shadow
    d.rounded_rectangle((*P(258, 214), *P(302, 262)), int(16 * S), fill=(206, 152, 112))     # neck
    # head layer (tilts)
    HW, HH = int(240 * S), int(260 * S)
    hd = Image.new("RGBA", (HW, HH), (0, 0, 0, 0))
    def Q(x, y): return (x * S, y * S)
    face = _shape((HW, HH), lambda dd: dd.ellipse((*Q(48, 60), *Q(192, 230)), fill=255), _vgrad(HW, HH, (246, 200, 160), (222, 168, 128)))
    hd.alpha_composite(face)
    hdd = ImageDraw.Draw(hd)
    for ex in (40, 180):
        hdd.ellipse((*Q(ex, 130), *Q(ex + 26, 176)), fill=(226, 172, 132))                  # ears
    hair = (34, 28, 30)
    hdd.ellipse((*Q(40, 28), *Q(200, 150)), fill=hair)                                     # hair volume
    hdd.polygon([Q(44, 108), Q(60, 70), Q(110, 64), Q(150, 78), Q(186, 74), Q(198, 108), Q(186, 96), Q(140, 92), Q(100, 104), Q(64, 100)], fill=hair)
    hdd.arc((*Q(70, 40), *Q(170, 110)), 200, 280, fill=(80, 74, 80), width=int(5 * S))      # hair sheen
    face2 = _shape((HW, HH), lambda dd: dd.ellipse((*Q(54, 92), *Q(186, 230)), fill=255), _vgrad(HW, HH, (246, 200, 160), (224, 170, 130)))
    hd.alpha_composite(face2)
    hdd = ImageDraw.Draw(hd)
    hdd.polygon([Q(54, 120), Q(80, 92), Q(130, 98), Q(170, 88), Q(188, 120), Q(176, 104), Q(132, 108), Q(90, 112)], fill=hair)  # fringe
    bl = blink_amt(t, 7)
    look = 3 * math.sin(t * 0.7)
    for j, ex in enumerate((96, 148)):
        hdd.line([Q(ex - 18, 128 - j * 8), Q(ex + 16, 124 - j * 12)], fill=(40, 30, 30), width=int(6 * S))   # brows (right one raised)
        eh = 10 * bl + 0.8
        hdd.ellipse((*Q(ex - 14, 150 - eh), *Q(ex + 14, 150 + eh)), fill=(252, 250, 248))
        if bl > 0.25:
            hdd.ellipse((*Q(ex - 7 + look, 150 - min(8, eh)), *Q(ex + 7 + look, 150 + min(8, eh))), fill=(52, 36, 30))
            hdd.ellipse((*Q(ex - 2 + look, 145), *Q(ex + 2 + look, 149)), fill=(255, 255, 255))
    hdd.line([Q(124, 156), Q(118, 182), Q(128, 184)], fill=(200, 140, 104), width=int(4 * S))   # nose
    hdd.line([Q(108, 204), Q(140, 200)], fill=(160, 96, 80), width=int(5 * S))                    # pursed, unsure mouth
    hd = hd.rotate(4 * math.sin(t * 0.9) - 4, Image.BICUBIC, center=(120 * S, 230 * S))
    im.alpha_composite(hd, (int(160 * S), int(4 * S)))
    d = ImageDraw.Draw(im)
    # thinking arm: elbow on desk, fist under chin
    sleeve = (124, 74, 46)
    d.line([P(372, 300), P(392, 372)], fill=sleeve, width=int(52 * S), joint="curve")
    d.line([P(392, 372), P(330, 236)], fill=(226, 172, 132), width=int(38 * S), joint="curve")
    d.ellipse((*P(300, 202), *P(356, 258)), fill=(232, 178, 138))
    d.ellipse((*P(298, 214), *P(318, 236)), fill=(218, 162, 124))
    # desk + laptop (lid faces us, screen light on the face)
    desk = _shape((Wc, Hc), lambda dd: dd.rounded_rectangle((*P(30, 388), *P(530, 428)), int(18 * S), fill=255), _vgrad(Wc, Hc, (70, 64, 110), (40, 36, 70)))
    im.alpha_composite(desk)
    lid = _shape((Wc, Hc), lambda dd: dd.rounded_rectangle((*P(60, 284), *P(250, 394)), int(14 * S), fill=255), _vgrad(Wc, Hc, (210, 214, 236), (150, 156, 190)))
    im.alpha_composite(lid)
    d = ImageDraw.Draw(im)
    d.ellipse((*P(140, 326), *P(170, 356)), fill=(255, 255, 255, 160))
    im = im.resize((int(560 * s), int(440 * s)), Image.LANCZOS)
    return im

# ---------- scenes ----------
ORBIT = [("lightbulb", "amber"), ("video", "pink"), ("notebook-pen", "blue"), ("pin", "red"), ("clapperboard", "violet"), ("sparkles", "teal")]

def cart_apps(lt, t):
    c = scene()
    out = ease_in(clamp((lt - 2.65) / 0.35))
    if out < 1:
        for j, (nm, col) in enumerate(ORBIT):
            st = 0.25 + j * 0.12
            if lt < st: continue
            ang = j / 6 * 2 * math.pi + lt * 0.45
            r = ease_out(clamp((lt - st) / 0.5))
            gicon(c, nm, 540 + math.cos(ang) * 330 * r, 760 + math.sin(ang) * 140 * r, 116, col, st, lt, a=1 - out)
        brand(c, "instagram", 540, 760, 300, 0.02, lt, t=t, bob=6, a=1 - out, shine=(lt - 0.6) / 0.9)
    # Telegram «Избранное» (left) and Google Sheets (right): big, ~60% of the panel width together
    if lt > 2.8:
        brand(c, "telegram", 300, 770, 350, 2.86, lt, t=t, bob=6, shine=(lt - 3.2) / 0.8)
        if lt > 3.05: gpill(c, 300, 585, "Избранное", tint=TINTS["tg"], size=30, k=spring(lt - 3.05, w=12, z=0.55), center=True)
    if lt > 3.8:
        brand(c, "sheets", 780, 770, 350, 3.84, lt, t=t, bob=6, ph=1.3, shine=(lt - 4.2) / 0.8)
    for j, (nm, col) in enumerate(ORBIT):   # ideas fall into both apps
        st = 3.0 + j * 0.26
        if lt < st or (j % 2 == 1 and lt < 3.9): continue
        f = ease_io(clamp((lt - st) / 0.5))
        if f >= 1: continue
        tx = 300 if j % 2 == 0 else 780
        gicon(c, nm, lerp(540, tx, f), lerp(640, 770, f) - 110 * math.sin(math.pi * f), 90 * (1 - 0.6 * f), col, 0, 1, a=1 - f * 0.8, glow_on=False)
    if lt > 4.86:    # "yozib boradi": too many notes pile up — red alert pulses
        u = lt - 4.86
        for x0 in (300, 780):
            gicon(c, "file-text", x0 + 135, 640, 92, "red", 0, u * 1.0 + 0.0, a=1.0, w=13, z=0.45)
    return c

def cart_reveal(lt, t):
    c = scene()
    move = ease_io(clamp((lt - 1.05) / 0.45))
    bx, by, bs = lerp(540, 200, move), lerp(760, 640, move), lerp(330, 170, move)
    if lt > 0.06:
        g = glow(500, (255, 210, 90)); gg = g.resize((int(560 * (1 - 0.5 * move)),) * 2)
        paste_alpha(c, gg, bx - gg.width / 2, by - gg.height / 2, 0.7 * clamp((lt - 0.06) / 0.3))
        gicon(c, "lightbulb", bx, by, bs, "amber", 0.06, lt, t=t, bob=5, glyph_k=0.56, shine=(lt - 0.35) / 0.7)
    if lt > 1.2:
        for j in range(3):     # light rings behind the Notion logo
            u = (lt - 1.2 - j * 0.35) % 1.4
            rr = int(220 + 260 * u)
            ring = Image.new("RGBA", (rr * 2, rr * 2), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((4, 4, rr * 2 - 4, rr * 2 - 4), outline=(170, 160, 255, int(120 * (1 - u / 1.4))), width=3)
            paste_alpha(c, ring, 620 - rr, 755 - rr, 1.0)
        brand(c, "notion", 620, 755, 420, 1.24, lt, t=t, bob=5, shine=(lt - 1.5) / 0.7)
    return c

def cart_arch(lt, t):
    c = scene()
    k = spring(lt - 0.05, w=10, z=0.65)
    notion_glass(c, 540, 745 + (1 - k) * 60, 900, 360, lt, rows_at=(2.66, 2.86, 3.06), cols_at=1.82, sidebar_at=0.6, k=k)
    gicon(c, "layers", 975, 585, 110, "violet", 1.0, lt, t=t, bob=6, rot=0)
    return c

def note_card(c, x, y, k, rot, seed, tint=(255, 255, 255)):
    rng = np.random.default_rng(seed)
    lay = Image.new("RGBA", (170, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for j in range(3):
        d.rounded_rectangle((20, 26 + j * 26, 20 + 130 * rng.uniform(0.45, 0.9), 36 + j * 26), 5, fill=(255, 255, 255, 190))
    glass(c, x, y, 170, 120, tint=tint, k=k, r=24, rot=rot, alpha=(0.30, 0.14), content=lay)

def cart_order(lt, t):
    c = scene()
    cols = [("G'oya", (148, 140, 170), 220), ("Syomka", (245, 166, 35), 540), ("Joylandi", (34, 197, 94), 860)]
    hk = clamp((lt - 0.25) / 0.35)
    for nm, col, x in cols:
        if hk > 0: gpill(c, x, 590, nm, tint=col, size=30, a=hk, k=0.85 + 0.15 * hk, center=True, alpha=(0.55, 0.35))
    rng = np.random.default_rng(9)
    for j in range(6):
        sx, sy, sr = rng.uniform(150, 930), rng.uniform(660, 900), rng.uniform(-35, 35)
        tx, ty = cols[j % 3][2], 700 + (j // 3) * 140
        f = ease_io(clamp((lt - 0.5 - j * 0.12) / 0.6))
        note_card(c, lerp(sx, tx, f), lerp(sy, ty, f) + 3 * math.sin(t * 2 + j), 1.0, sr * (1 - f), j, tint=cols[j % 3][1] if f > 0.95 else (255, 255, 255))
    for j in range(3):
        gicon(c, "check", cols[j][2] + 88, 650, 64, "green", 1.5 + j * 0.15, lt, w=13, z=0.45, glyph_k=0.6)
    if lt > 2.3:    # share it: link + send
        gicon(c, "link", 985, 905, 110, "blue", 2.35, lt, t=t, bob=4)
        if lt > 3.4:
            u = ease_in(clamp((lt - 3.6) / 0.8))
            gicon(c, "send", lerp(860, 1180, u), lerp(900, 560, u), 100, "violet", 3.4, lt, rot=-12 * u)
    return c

def beam(c, p0, p1, u, col=(170, 160, 255)):
    """Glowing particle trail travelling from p0 to p1 (u = 0..1)."""
    for j in range(16):
        q = u - j * 0.025
        if q <= 0 or q > 1: continue
        x = lerp(p0[0], p1[0], q); y = lerp(p0[1], p1[1], q) - 140 * math.sin(math.pi * q)
        r = int(16 * (1 - j / 16)) + 2
        g = glow(r * 6, col).resize((r * 6, r * 6))
        paste_alpha(c, g, x - r * 3, y - r * 3, (1 - j / 16))

def cart_pro(lt, t):
    """Sender's Notion page reaches a receiver — and makes a professional impression."""
    c = scene()
    k = spring(lt - 0.05, w=10, z=0.65)
    # sender phone (left) with the page
    ph_lay = Image.new("RGBA", (220, 400), (0, 0, 0, 0)); pd = ImageDraw.Draw(ph_lay)
    pd.rounded_rectangle((84, 16, 136, 26), 5, fill=(255, 255, 255, 120))
    ph_lay.alpha_composite(svg_icon("notebook-pen", 40, "#ffffff", 2), (22, 46))
    pd.text((22, 112), "Kontent plan", font=dfont("Black", 24), fill=WHITE, anchor="lm")
    for j, col in enumerate(((245, 166, 35), (34, 197, 94), (56, 132, 255), (236, 72, 153), (124, 92, 255))):
        yy = 140 + j * 50
        pd.rounded_rectangle((22, yy, 198, yy + 38), 10, fill=(255, 255, 255, 28))
        pd.rounded_rectangle((32, yy + 14, 110, yy + 22), 4, fill=(255, 255, 255, 150))
        pd.rounded_rectangle((140, yy + 9, 188, yy + 29), 10, fill=col + (230,))
    glass(c, 210, 760 + (1 - k) * 80, 220, 400, tint=(200, 196, 255), k=k, r=36, alpha=(0.22, 0.10), content=ph_lay, glow_col=(124, 92, 255),
          shine=(lt - 0.4) / 0.8)
    # beam to the receiver
    if lt > 0.8:
        beam(c, (300, 680), (720, 690), clamp((lt - 0.8) / 0.7))
    # receiver card: avatar with story-ring + name + "seen"
    if lt > 1.42:
        kr = spring(lt - 1.42, w=10, z=0.6)
        rc = Image.new("RGBA", (440, 210), (0, 0, 0, 0)); rd = ImageDraw.Draw(rc)
        ring = ig_gradient(128).copy(); m = Image.new("L", (128, 128), 0); ImageDraw.Draw(m).ellipse((0, 0, 127, 127), fill=255)
        ring.putalpha(m); rc.alpha_composite(ring, (24, 40))
        rd.ellipse((32, 48, 144, 160), fill=(40, 40, 70))
        rc.alpha_composite(svg_icon("user", 76, "#ffffff", 1.6), (50, 66))
        rd.text((170, 80), "Mijoz", font=dfont("Black", 34), fill=WHITE, anchor="lm")
        seen = clamp((lt - 2.0) / 0.3)
        if seen > 0:
            ic = svg_icon("eye", 30, "#a7f3d0", 2); rc.alpha_composite(ic, (170, 116))
            rd.text((208, 131), "Ko'rdi", font=dfont("Medium", 26), fill=(167, 243, 208, int(255 * seen)), anchor="lm")
        glass(c, 760, 668, 440, 210, tint=(255, 255, 255), k=kr, r=40, alpha=(0.20, 0.09), content=rc, glow_col=(236, 72, 153),
              shine=(lt - 1.7) / 0.8)
    # "professional" reaction: award badge + bubble + stars
    if lt > 2.84:
        u = lt - 2.84
        for j in range(3):
            q = (u - j * 0.18)
            if 0 < q < 1.2:
                rr = int(80 + 240 * q)
                ring = Image.new("RGBA", (rr * 2, rr * 2), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse((3, 3, rr * 2 - 3, rr * 2 - 3), outline=(250, 204, 21, int(150 * (1 - q / 1.2))), width=3)
                paste_alpha(c, ring, 920 - rr, 860 - rr, 1)
        gicon(c, "award", 925, 860, 150, "gold", 2.84, lt, t=t, bob=5, glyph_k=0.56, shine=(lt - 3.0) / 0.8)
        bub = Image.new("RGBA", (380, 92), (0, 0, 0, 0))
        ImageDraw.Draw(bub).text((190, 46), "Juda professional!", font=dfont("Black", 30), fill=WHITE, anchor="mm")
        glass(c, 640, 890, 380, 92, tint=(124, 92, 255), k=spring(u - 0.1, w=11, z=0.55) if u > 0.1 else 0, r=46, alpha=(0.5, 0.3), content=bub)
    for j in range(5):
        st = 3.25 + j * 0.12
        if lt > st:
            kk = spring(lt - st, w=13, z=0.45)
            glass(c, 600 + j * 64, 812, 56, 56, tint=TINTS["gold"], k=kk, glyph=svg_icon("star", 128, "#fde68a", 1.5, fill="#facc15"), glyph_k=0.7,
                  alpha=(0.45, 0.25), a=clamp(kk * 1.6))
    return c

def cart_confused(lt, t):
    c = scene()
    ring_a = clamp(lt / 0.4)
    g = glow(420, (124, 92, 255)); paste_alpha(c, g, 330 - 210, 760 - 210, 0.6 * ring_a)
    ring = Image.new("RGBA", (300, 300), (0, 0, 0, 0))            # ring light behind the creator
    ImageDraw.Draw(ring).ellipse((10, 10, 290, 290), outline=(255, 245, 230, 200), width=14)
    paste_alpha(c, ring.filter(ImageFilter.GaussianBlur(2)), 330 - 150 + 120, 560, 0.55 * ring_a)
    k = spring(lt - 0.05, w=10, z=0.65)
    cr = creator(t, lt, 0.92)
    paste_alpha(c, cr, 320 - cr.width / 2, 548 + (1 - k) * 60 + 2 * math.sin(t * 1.4), clamp(k * 2))
    # thought bubble with a question mark
    if lt > 0.5:
        for j, (dx, dy, rr) in enumerate(((470, 640, 12), (510, 610, 18))):
            if lt > 0.5 + j * 0.12:
                glass(c, dx, dy, rr * 2, rr * 2, tint=(255, 255, 255), k=1, r=rr, alpha=(0.4, 0.25))
        q = Image.new("RGBA", (200, 150), (0, 0, 0, 0))
        ImageDraw.Draw(q).text((100, 75), "?", font=dfont("Black", 96), fill=WHITE, anchor="mm")
        glass(c, 640, 600, 200, 130, tint=(124, 92, 255), k=spring(lt - 0.8, w=11, z=0.55) if lt > 0.8 else 0, r=60, alpha=(0.5, 0.3),
              content=q, glow_col=(124, 92, 255))
    # templates that don't fit together: misaligned glass blocks jittering
    for j, (nm, col, x, y) in enumerate((("layout-grid", "blue", 820, 680), ("calendar", "pink", 940, 800), ("file-text", "teal", 800, 880))):
        jit = 10 * math.sin(lt * 3.3 + j * 2)
        gicon(c, nm, x + jit, y - jit * 0.5, 110, col, 0.9 + j * 0.15, lt, rot=14 * math.sin(lt * 1.8 + j), t=t)
    gicon(c, "x", 880, 760, 120, "red", 3.26, lt, w=13, z=0.45, glyph_k=0.58)
    return c

def cart_gift(lt, t):
    c = scene()
    if lt < 2.6:
        sq = 1 + 0.05 * math.sin(lt * 12) * clamp((lt - 1.5) / 0.6)
        gicon(c, "gift", 540, 760, int(330 * sq), "pink", 0.05, lt, t=t, bob=6, glyph_k=0.56, shine=(lt - 0.4) / 0.8)
    else:
        u = lt - 2.6
        burst = clamp(u / 0.5)
        for j in range(10):
            ang = j * 0.628
            r = 60 + 380 * ease_out(burst)
            gicon(c, "sparkles", 470 + math.cos(ang) * r, 760 + math.sin(ang) * r * 0.5, 54, "gold", 0, 1, a=1 - clamp((u - 0.4) / 0.4), glow_on=False)
        kw = spring(u, w=10, z=0.6)
        notion_glass(c, 450, 760 + (1 - kw) * 100, 640, 330, lt, rows_at=(2.9, 3.05, 3.2), cols_at=2.75, sidebar_at=2.7, k=kw)
        gpill(c, 900, 600, "BEPUL", tint=TINTS["green"], size=40, k=spring(u - 0.15, w=12, z=0.5) if u > 0.15 else 0, center=True, alpha=(0.6, 0.4))
        if lt > 3.28:
            gicon(c, "layers", 900, 720, 120, "violet", 3.28, lt, t=t, bob=5)
            for j, (nm, col) in enumerate((("Savol-javob", "blue"), ("Keys", "pink"), ("Maslahat", "violet"))):
                st = 5.26 + j * 0.15
                if lt < st: continue
                gpill(c, 900, 820 + j * 54, nm, tint=TINTS[col], size=24, k=spring(lt - st, w=12, z=0.55), center=True, alpha=(0.55, 0.35))
    return c

def cart_comment(lt, t):
    c = scene()
    k = spring(lt - 0.05, w=11, z=0.6)
    bar = Image.new("RGBA", (840, 116), (0, 0, 0, 0)); d = ImageDraw.Draw(bar)
    d.ellipse((20, 20, 96, 96), fill=(255, 255, 255, 40)); bar.alpha_composite(svg_icon("user", 48, "#ffffff", 1.8), (34, 34))
    typed = lt > 0.45
    if typed:
        d.text((122, 58), "8", font=dfont("Black", 56), fill=WHITE, anchor="lm")
    elif int(lt * 3) % 2 == 0:
        d.line([(124, 34), (124, 82)], fill=WHITE, width=3)
    else:
        d.text((122, 58), "Izoh qoldiring...", font=dfont("Medium", 34), fill=(255, 255, 255, 120), anchor="lm")
    d.text((812, 58), "Yuborish", font=dfont("Black", 30), fill=(120, 190, 255) if typed else (255, 255, 255, 90), anchor="rm")
    sent = clamp((lt - 1.0) / 0.3)
    glass(c, 540, 640 - 30 * ease_out(sent) + (1 - k) * 60, 840, 116, tint=(255, 255, 255), k=k, r=58, alpha=(0.22, 0.12), content=bar,
          glow_col=(56, 132, 255), shine=(lt - 0.6) / 0.6)
    gicon(c, "message-circle", 930, 560, 96, "blue", 0.1, lt, w=12, z=0.5)
    if lt > 1.25:
        u = spring(lt - 1.25, w=11, z=0.6)
        card = Image.new("RGBA", (720, 140), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        card.alpha_composite(svg_icon("link", 64, "#ffffff", 2), (34, 38))
        cd.text((126, 50), "Yangi xabar", font=dfont("Black", 32), fill=WHITE, anchor="lm")
        cd.text((126, 96), "Shablon linki: notion.so/...", font=dfont("Medium", 26), fill=(220, 214, 255), anchor="lm")
        glass(c, 480 + (1 - u) * 300, 820, 720, 140, tint=(124, 92, 255), k=1, r=36, a=clamp(u * 2), alpha=(0.45, 0.28), content=card,
              glow_col=(124, 92, 255))
        gicon(c, "bell", 935, 820, 116, "amber", 1.35, lt, rot=14 * math.sin(lt * 14) * (1 - clamp((lt - 1.35) / 0.8)), w=12, z=0.45)
    return c

PANELS.update({"apps": cart_apps, "reveal": cart_reveal, "arch": cart_arch, "order": cart_order, "pro": cart_pro,
               "confused": cart_confused, "gift": cart_gift, "comment": cart_comment})
