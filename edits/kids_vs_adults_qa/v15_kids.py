# ================= v15: logoped long-form — sample motion backgrounds, glass icons, 4 caption typefaces =================
# (v10/v11 were loaded only for their glass/icon helpers: put back the caption/frame behaviour of this client's style)
anim_line = _ORIG["anim_line"]; draw_captions = _ORIG["draw_captions"]; expert_crop = _ORIG["expert_crop"]
scene = _ORIG["scene"]; render = _ORIG["render"]; TERRA = _ORIG["TERRA"]; STY.clear(); STY.update(_ORIG["STY"])
FACE_Y = 292
PUNCH[:] = [(1.94, 1.04, 2.70), (9.60, 1.05, 11.10), (23.12, 1.05, 23.90), (59.60, 1.05, 60.40), (75.64, 1.04, 99)]
SVG = os.path.join(HERE, "av", "svg")

# ---------- the sample backgrounds (looped forward/backward so there is never a jump) ----------
_BGF = {}
def _load_bg(name):
    if name in _BGF: return _BGF[name]
    w_, h_ = 540, 480
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "in", name + ".mp4"), "-vf",
                          f"fps=15,scale={w_}:-2,crop={w_}:{h_}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fr = []
    while True:
        b = p.stdout.read(w_ * h_ * 3)
        if len(b) < w_ * h_ * 3: break
        a_ = np.frombuffer(b, np.uint8).reshape(h_, w_, 3)
        if name == "bg1":   # white sample → warm brown duotone (dust and the 3D crosses stay), so white text reads on it
            g = a_.astype(np.float32).mean(2, keepdims=True) / 255.0
            a_ = np.uint8(np.array((34, 18, 12), np.float32) + (np.array((150, 92, 58), np.float32) - np.array((34, 18, 12), np.float32)) * g)
        fr.append(a_)
    _BGF[name] = fr
    return fr

def panel_bg(name, t):
    fr = _load_bg(name)
    n = len(fr); k = int(t * 15) % (2 * n - 2)
    i = k if k < n else 2 * n - 2 - k
    return Image.fromarray(fr[i]).resize((W, HALF), Image.BICUBIC).convert("RGBA")

def dim(c, a=0.25):
    c.alpha_composite(Image.new("RGBA", c.size, (20, 10, 6, int(255 * a))))

WARM = {"gold": (246, 198, 92), "terra": (217, 119, 87), "cream": (255, 240, 214), "brown": (120, 70, 40), "red": (220, 80, 70), "green": (86, 190, 120)}

def chip(c, x, y, text, col, lt0, lt, size=30, center=True):
    if lt < lt0: return
    gpill(c, x, y, text, tint=col, size=size, k=spring(lt - lt0, w=12, z=0.55), center=center, alpha=(0.62, 0.42))

def card(c, name, x, y, size, col, lt0, lt, t, bob=6, ph=0.0, rot=0.0, a=1.0, glyph_k=0.52):
    gicon(c, name, x, y, size, col, lt0, lt, t=t, bob=bob, ph=ph, rot=rot, a=a, glyph_k=glyph_k, shine=(lt - lt0 - 0.3) / 0.7)

# ---------- panels ----------
def p_adults(lt, t):
    c = panel_bg("bg2", t); dim(c, 0.18)
    items = [("users", "Qariyalar", 1.06, 230), ("brain", "Afaziya", 2.20, 540), ("heart-pulse", "Insultdan keyin", 3.44, 850)]
    for j, (ic, lab, st, x) in enumerate(items):
        card(c, ic, x, 735, 190, WARM["terra"] if j != 1 else WARM["gold"], st, lt, t, ph=j)
        chip(c, x, 885, lab, WARM["brown"], st + 0.15, lt, size=26)
    if lt > 4.36:
        card(c, "message-circle-off", 540, 600, 110, WARM["red"], 4.36, lt, t, bob=4)
    return c

def p_hard(lt, t):
    c = panel_bg("bg2", t); dim(c, 0.25)
    # battery drains as she lists what was hard
    lvl = 1 - ease_io(clamp((lt - 0.6) / 4.5))
    bx, by, bw, bh = 300, 650, 300, 160
    lay = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((6, 6, bw - 34, bh - 6), 30, outline=(255, 240, 214, 255), width=8)
    d.rounded_rectangle((bw - 30, bh / 2 - 26, bw - 10, bh / 2 + 26), 8, fill=(255, 240, 214, 255))
    col = (86, 190, 120) if lvl > 0.5 else ((246, 198, 92) if lvl > 0.22 else (220, 80, 70))
    fw = (bw - 66) * max(0.04, lvl)
    d.rounded_rectangle((22, 22, 22 + fw, bh - 22), 18, fill=col + (255,))
    glass(c, bx + bw / 2 - 20, by + bh / 2, bw + 60, bh + 60, tint=(255, 220, 180), k=spring(lt - 0.1, w=10, z=0.6), r=50, alpha=(0.18, 0.08), content=None)
    paste_alpha(c, lay, bx - 20, by, clamp((lt - 0.1) / 0.3))
    chip(c, 780, 640, "Stress", WARM["red"], 1.08, lt)
    chip(c, 780, 730, "Qiyin", WARM["terra"], 0.4, lt)
    chip(c, 780, 820, "Kapriz", WARM["brown"], 7.62, lt)
    if lt > 7.62:
        card(c, "zap", 930, 900, 100, WARM["gold"], 7.62, lt, t, bob=4)
    return c

def p_kids(lt, t):
    c = panel_bg("bg1", t)
    card(c, "baby", 210, 720, 200, WARM["terra"], 0.1, lt, t)
    chip(c, 210, 880, "3–14 yosh", WARM["brown"], 0.56, lt, size=30)
    tags = [("Nutq muammosi", 2.2, 640), ("Autizm", 3.5, 735), ("Xulq", 4.5, 830)]
    for j, (lab, st, y) in enumerate(tags):
        chip(c, 640, y, lab, WARM["terra"] if j % 2 == 0 else WARM["brown"], st, lt, size=30)
    if lt > 6.64:
        card(c, "sprout", 900, 690, 150, WARM["green"], 6.64, lt, t)
        chip(c, 900, 820, "O'smirlar", WARM["green"], 6.8, lt, size=28)
    if lt > 9.5:   # "mazza": trophy with a burst
        u = lt - 9.5
        for j in range(10):
            ang = j * 0.628; r = 60 + 230 * ease_out(clamp(u / 0.5))
            card(c, "sparkles", 540 + math.cos(ang) * r, 740 + math.sin(ang) * r * 0.55, 54, WARM["gold"], 0, 1, t, bob=0,
                 a=1 - clamp((u - 0.5) / 0.4))
        card(c, "trophy", 540, 740, 210, WARM["gold"], 9.5, lt, t)
    return c

def p_path(lt, t):
    c = panel_bg("bg2", t); dim(c, 0.2)
    rot = 40 * math.sin(lt * 2.2) * (1 - clamp((lt - 1.1) / 0.6))
    card(c, "compass", 380, 745, 230, WARM["gold"], 0.1, lt, t, rot=rot)
    if lt > 1.1:
        u = ease_out(clamp((lt - 1.1) / 0.6))
        card(c, "arrow-right", lerp(560, 760, u), 745, 120, WARM["terra"], 1.1, lt, t, bob=0)
        chip(c, 830, 880, "O'z yo'nalishingiz", WARM["brown"], 1.5, lt, size=28)
    return c

def p_scatter(lt, t):
    """Universal: energy split into many directions — each little and weak."""
    c = panel_bg("bg2", t); dim(c, 0.3)
    cx, cy = 540, 760
    card(c, "user-check", cx, cy, 170, WARM["gold"], 0.1, lt, t, bob=3)
    dirs = [("Autizm", 1.5), ("Katta yoshlilar", 3.86), ("Kichiklar", 4.48), ("Duduqlanish", 5.4), ("Afaziya", 6.2), ("Kapriz", 6.8)]
    for j, (lab, st) in enumerate(dirs):
        if lt < st: continue
        ang = -math.pi / 2 + (j - 2.5) * 0.62
        u = ease_out(clamp((lt - st) / 0.5))
        x, y = cx + math.cos(ang) * 360 * u, cy + math.sin(ang) * 175 * u + 60
        d = ImageDraw.Draw(c)
        weak = clamp((lt - 8.1) / 1.0)
        d.line([(cx, cy), (x, y)], fill=(255, 220, 160, int(200 * (1 - 0.6 * weak))), width=max(2, int(8 * (1 - 0.7 * weak))))
        chip(c, x, y, lab, WARM["brown"], st, lt, size=24)
    if lt > 8.2:   # "100 tarafga": battery icon empties
        card(c, "battery-low", 900, 900, 110, WARM["red"], 8.2, lt, t, bob=4)
    return c

def p_focus(lt, t):
    """Focus: the same energy in one beam → bullseye → best in that field."""
    c = panel_bg("bg2", t); dim(c, 0.2)
    tx, ty = 820, 740
    card(c, "target", tx, ty, 220, WARM["terra"], 0.2, lt, t, bob=3)
    if lt > 2.1:
        u = ease_in(clamp((lt - 2.1) / 0.7))
        d = ImageDraw.Draw(c)
        for j in range(5):
            y0 = 620 + j * 60
            x1 = lerp(120, tx - 120, u); y1 = lerp(y0, ty, u)
            d.line([(120, y0), (x1, y1)], fill=(255, 220, 160, 170), width=6)
        if u >= 1:
            g = glow(360, WARM["gold"]); paste_alpha(c, g, tx - 180, ty - 180, 0.7 * clamp((lt - 2.8) / 0.3))
    if lt > 5.6:
        card(c, "medal", 300, 760, 220, WARM["gold"], 5.6, lt, t)
        chip(c, 300, 905, "Eng zo'r mutaxassis", WARM["brown"], 5.8, lt, size=26)
    return c

def p_advice(lt, t):
    c = panel_bg("bg1", t)
    rows = [("x", "Universal bo'lishga urinmang", WARM["red"], 0.9), ("heart", "Yoqqan yo'nalishni tanlang", WARM["terra"], 3.6),
            ("sprout", "O'sha yo'nalishda rivojlaning", WARM["green"], 6.1)]
    for j, (ic, lab, col, st) in enumerate(rows):
        y = 625 + j * 112
        card(c, ic, 190, y, 92, col, st, lt, t, bob=0, glyph_k=0.56)
        if lt > st:
            gpill(c, 260, y, lab, tint=WARM["brown"], size=32, k=spring(lt - st - 0.1, w=12, z=0.6), alpha=(0.7, 0.5))
    return c

PANELS.update({"adults": p_adults, "hard": p_hard, "kids": p_kids, "path": p_path, "scatter": p_scatter,
               "focus": p_focus, "advice": p_advice})

# ---------- two extra caption typefaces: a gold serif italic and spaced caps ----------
SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf"
@lru_cache(None)
def _serif(s): return ImageFont.truetype(SERIF, s)
STY["serif"] = (lambda: _serif(76), 98)
STY["caps"] = (lambda: dfont("Bold", 60), 88)
_anim_base = anim_line

def anim_line(canvas, text, style, x, y, t0, t, out, center=False):
    if style not in ("serif", "caps"):
        return _anim_base(canvas, text, style, x, y, t0, t, out, center)
    u = t - t0
    if u <= 0: return
    if style == "serif":       # letters wipe in left to right, gold, with a soft glow
        f = _serif(76); tw = f.getlength(text)
        lay = Image.new("RGBA", (int(tw) + 40, 110), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((20, 55), text, font=f, fill=(246, 198, 92), anchor="lm")
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.6)))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        comp = Image.new("RGBA", lay.size, (0, 0, 0, 0)); comp.alpha_composite(sh, (0, 4)); comp.alpha_composite(lay)
        rev = ease_out(clamp(u / 0.6))
        m = Image.new("L", comp.size, 0); ImageDraw.Draw(m).rectangle((0, 0, int(comp.width * rev) + 20, comp.height), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(10))
        comp.putalpha(ImageChops.multiply(comp.getchannel("A"), m))
        x0 = (W - tw) / 2 if center else x
        paste_alpha(canvas, comp, x0 - 20, y - 18 - 24 * out, 1 - out)
    else:                       # spaced capitals drop in one by one
        f = dfont("Bold", 60); track = 8
        x0 = x
        widths = [f.getlength(ch) for ch in text]
        total = sum(widths) + track * (len(text) - 1)
        if center: x0 = (W - total) / 2
        cx = x0
        for j, ch in enumerate(text):
            lu = u - j * 0.035
            if lu > 0 and ch != " ":
                kk = spring(lu, w=15, z=0.6)
                g = glyph_caps(ch)
                paste_alpha(canvas, g, cx - 8, y - 10 - (1 - clamp(kk)) * 40 - 24 * out, clamp(lu / 0.12) * (1 - out))
            cx += widths[j] + track

@lru_cache(maxsize=128)
def glyph_caps(ch):
    f = dfont("Bold", 60)
    im = Image.new("RGBA", (int(f.getlength(ch)) + 20, 90), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, 45), ch, font=f, fill=(255, 240, 214), anchor="lm")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.6)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)), (0, 3)); out.alpha_composite(im)
    return out
