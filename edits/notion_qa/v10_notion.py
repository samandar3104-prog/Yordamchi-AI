# ================= v10: Notion content-plan reel — 3D objects (Fluent 3D, MIT) + app/UI mocks =================
FACE_Y = 330
PUNCH[:] = [(12.32, 1.06, 14.40), (27.42, 1.06, 28.30), (42.50, 1.05, 99)]
FL = os.path.join(HERE, "av", "fl")

@lru_cache(maxsize=128)
def fl(name, size, shadow=True):
    im = Image.open(os.path.join(FL, name + "_3d.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    return with_shadow(im, max(6, size // 14), max(6, size // 14), 0.45) if shadow else im

def pop(c, img, x, y, lt0, lt, rot=0.0, bob=0.0, t=0.0, ph=0.0, w=11, z=0.5, a=1.0):
    """Spring scale-in + idle float for a 3D object centred at x,y."""
    if lt < lt0: return
    k = spring(lt - lt0, w=w, z=z)
    float_card(c, img, x, y + bob * math.sin(t * 1.6 + ph), k, rot=rot, a=a)

# ---------- app icons (drawn with depth: gradient body, gloss, soft shadow) ----------
def _squircle(size, r, stops, radial=False):
    S2 = size * 2
    yy, xx = np.mgrid[0:S2, 0:S2].astype(np.float32) / S2
    if radial:
        d = np.clip(np.hypot(xx - 0.25, yy - 1.05) / 1.25, 0, 1)
    else:
        d = yy
    cols = np.array([s[1] for s in stops], np.float32); pos = np.array([s[0] for s in stops], np.float32)
    rgb = np.stack([np.interp(d, pos, cols[:, j]) for j in range(3)], -1)
    im = Image.fromarray(np.uint8(rgb)).convert("RGBA")
    m = Image.new("L", (S2, S2), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, S2 - 1, S2 - 1), r * 2, fill=255)
    im.putalpha(m)
    g = Image.new("RGBA", (S2, S2), (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((S2 * 0.04, S2 * 0.03, S2 * 0.96, S2 * 0.5), r * 2, fill=(255, 255, 255, 46))
    g.putalpha(ImageChops.multiply(g.getchannel("A"), m)); im.alpha_composite(g)
    return im

@lru_cache(maxsize=16)
def app_icon(kind, size=170):
    S2 = size * 2
    if kind == "instagram":
        im = _squircle(size, int(size * 0.26), [(0, (254, 218, 117)), (0.3, (250, 126, 30)), (0.6, (214, 41, 118)), (0.85, (150, 47, 191)), (1, (79, 91, 213))], radial=True)
        d = ImageDraw.Draw(im); s = S2
        d.rounded_rectangle((s * 0.22, s * 0.22, s * 0.78, s * 0.78), int(s * 0.17), outline=WHITE, width=int(s * 0.065))
        d.ellipse((s * 0.36, s * 0.36, s * 0.64, s * 0.64), outline=WHITE, width=int(s * 0.065))
        d.ellipse((s * 0.645, s * 0.29, s * 0.71, s * 0.355), fill=WHITE)
    elif kind == "telegram":
        im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0))
        disc = _squircle(size, size // 2, [(0, (94, 192, 240)), (1, (34, 140, 210))])
        im.alpha_composite(disc)
        d = ImageDraw.Draw(im); s = S2
        d.polygon([(s * 0.22, s * 0.5), (s * 0.76, s * 0.28), (s * 0.66, s * 0.74), (s * 0.48, s * 0.6)], fill=WHITE)
        d.polygon([(s * 0.48, s * 0.6), (s * 0.66, s * 0.74), (s * 0.44, s * 0.72)], fill=(214, 232, 244))
        d.line([(s * 0.42, s * 0.56), (s * 0.7, s * 0.36)], fill=(200, 224, 240), width=int(s * 0.03))
    elif kind == "sheets":
        im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0))
        body = _squircle(int(size * 0.78), int(size * 0.08), [(0, (52, 196, 120)), (1, (16, 140, 80))])
        im.alpha_composite(body, (int(S2 * 0.11), int(S2 * 0.11)))
        d = ImageDraw.Draw(im); s = S2
        d.polygon([(s * 0.66, s * 0.11), (s * 0.89, s * 0.34), (s * 0.66, s * 0.34)], fill=(140, 230, 180))
        d.rounded_rectangle((s * 0.28, s * 0.44, s * 0.72, s * 0.78), int(s * 0.02), fill=WHITE)
        for j in range(1, 4): d.line([(s * 0.28, s * (0.44 + j * 0.085)), (s * 0.72, s * (0.44 + j * 0.085))], fill=(16, 140, 80), width=int(s * 0.022))
        d.line([(s * 0.43, s * 0.44), (s * 0.43, s * 0.78)], fill=(16, 140, 80), width=int(s * 0.022))
    elif kind == "notion":
        im = _squircle(size, int(size * 0.2), [(0, (255, 255, 255)), (1, (226, 226, 222))])
        d = ImageDraw.Draw(im); s = S2
        d.rounded_rectangle((s * 0.18, s * 0.16, s * 0.82, s * 0.84), int(s * 0.07), outline=(24, 24, 24), width=int(s * 0.055))
        d.text((s * 0.5, s * 0.52), "N", font=dfont("Black", int(s * 0.5)), fill=(20, 20, 20), anchor="mm")
    im = im.resize((size, size), Image.LANCZOS)
    return with_shadow(im, max(8, size // 12), max(8, size // 12), 0.5)

# ---------- UI mocks ----------
CREAM = (250, 246, 238)
INK = (40, 32, 28)
def pill(d, x, y, text, bg, fg=WHITE, size=26, pad=16):
    f = dfont("Black", size); w_ = f.getlength(text)
    d.rounded_rectangle((x, y, x + w_ + pad * 2, y + size + 18), (size + 18) // 2, fill=bg)
    d.text((x + pad, y + (size + 18) / 2), text, font=f, fill=fg, anchor="lm")
    return w_ + pad * 2

def notion_window(w_, h_, lt, rows_at=(0.0, 0.25, 0.5, 0.75), cols_at=0.0, sidebar_at=0.0, title="Kontent plan"):
    """A Notion-like page: sidebar of pages + content-plan database (Mavzu / Status / Rubrika)."""
    im = grad_card(w_, h_, 26, (255, 255, 255), (240, 238, 234), hl=False).copy()
    d = ImageDraw.Draw(im)
    # top bar dots
    for j, col in enumerate(((255, 96, 92), (255, 190, 46), (40, 200, 64))):
        d.ellipse((22 + j * 26, 18, 38 + j * 26, 34), fill=col)
    # sidebar
    sbw = int(w_ * 0.27)
    d.rounded_rectangle((0, 50, sbw, h_), 0, fill=(246, 245, 242))
    items = [("clipboard", "Kontent plan"), ("spiral_calendar", "Kalendar"), ("clapper_board", "Syomka"), ("card_index_dividers", "Rubrikalar")]
    for j, (ic, nm) in enumerate(items):
        a = clamp((lt - sidebar_at - j * 0.12) / 0.25)
        if a <= 0: continue
        y = 74 + j * 50
        icon = fl(ic, 30, False)
        tmp = Image.new("RGBA", im.size, (0, 0, 0, 0)); tmp.alpha_composite(icon, (16, y))
        ImageDraw.Draw(tmp).text((54, y + 15), nm, font=dfont("Medium", 22), fill=INK, anchor="lm")
        tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * a)))
        im.alpha_composite(tmp)
    # title
    x0 = sbw + 28
    d.text((x0, 86), title, font=dfont("Black", 38), fill=INK, anchor="lm")
    # columns
    cols = [("Mavzu", 0.0), ("Status", 0.5), ("Rubrika", 0.74)]
    tw = w_ - x0 - 24
    if lt > cols_at:
        a = clamp((lt - cols_at) / 0.3)
        yh = 130
        d.line([(x0, yh + 40), (x0 + tw * a, yh + 40)], fill=(220, 216, 210), width=2)
        for nm, fx in cols:
            if fx <= a: d.text((x0 + tw * fx, yh + 18), nm, font=dfont("Medium", 22), fill=(130, 124, 118), anchor="lm")
    data = [("Bola gapirmayapti...", ("Syomka", (232, 170, 60)), ("Savol-javob", (120, 160, 230))),
            ("R tovushi qachon?", ("Joylandi", (90, 180, 120)), ("Mif", (220, 120, 140))),
            ("Uyda mashqlar", ("G'oya", (170, 160, 150)), ("Maslahat", (150, 120, 210))),
            ("Logoped yoki...", ("Montaj", (230, 130, 80)), ("Savol-javob", (120, 160, 230)))]
    for j, ra in enumerate(rows_at):
        if lt < ra: continue
        a = ease_out(clamp((lt - ra) / 0.3))
        y = 186 + j * 54
        if y + 40 > h_: break
        row = Image.new("RGBA", im.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        mt, (st, sc), (rb, rc) = data[j % 4]
        rd.text((x0, y + 18), mt, font=dfont("Medium", 22), fill=INK, anchor="lm")
        pill(rd, int(x0 + tw * 0.5), y + 2, st, sc, size=18, pad=10)
        pill(rd, int(x0 + tw * 0.74), y + 2, rb, rc, size=18, pad=10)
        rd.line([(x0, y + 44), (x0 + tw, y + 44)], fill=(232, 228, 222), width=1)
        row.putalpha(row.getchannel("A").point(lambda v: int(v * a)))
        im.alpha_composite(row, (int((1 - a) * 30), 0))
    return with_shadow(im, 18, 18, 0.5)

def phone_frame(screen, w_=250):
    h_ = int(w_ * 2.05)
    im = grad_card(w_, h_, 40, (36, 32, 30), (16, 14, 13), hl=False).copy()
    sc = screen.resize((w_ - 20, h_ - 20), Image.LANCZOS)
    m = Image.new("L", sc.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sc.width - 1, sc.height - 1), 32, fill=255)
    sc.putalpha(m); im.alpha_composite(sc, (10, 10))
    ImageDraw.Draw(im).rounded_rectangle((w_ / 2 - 36, 18, w_ / 2 + 36, 34), 8, fill=(16, 14, 13))
    return with_shadow(im, 16, 16, 0.5)

@lru_cache(maxsize=2)
def mini_page():
    im = Image.new("RGBA", (460, 940), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    im.alpha_composite(fl("clipboard", 90, False), (34, 70))
    d.text((34, 200), "Kontent plan", font=dfont("Black", 46), fill=INK, anchor="lm")
    for j, (col, w_) in enumerate((((232, 170, 60), 0.8), ((90, 180, 120), 0.6), ((120, 160, 230), 0.72), ((220, 120, 140), 0.5), ((150, 120, 210), 0.66), ((232, 170, 60), 0.58))):
        y = 270 + j * 96
        d.rounded_rectangle((34, y, 426, y + 76), 16, fill=(246, 245, 242))
        d.rounded_rectangle((52, y + 22, 52 + 220 * w_, y + 36), 7, fill=(205, 200, 194))
        d.rounded_rectangle((300, y + 20, 404, y + 52), 16, fill=col)
    return im

def messy_note(seed, size=150):
    rng = np.random.default_rng(seed)
    im = grad_card(size, int(size * 0.8), 14, (255, 246, 196), (246, 226, 150)).copy()
    d = ImageDraw.Draw(im)
    for j in range(4):
        y = 26 + j * 22; w_ = rng.uniform(0.4, 0.85)
        d.line([(16, y), (16 + (size - 32) * w_, y + rng.uniform(-3, 3))], fill=(150, 120, 80), width=4)
    return with_shadow(im, 10, 10, 0.4)
NOTES_M = None

# ---------- scenes ----------
IDEAS = ["memo", "light_bulb", "clapper_board", "spiral_notepad", "video_camera", "pushpin"]

def cart_apps(lt, t):
    c = scene()
    # 0–2.8: Instagram with content ideas bursting around it
    out = ease_in(clamp((lt - 2.7) / 0.4))
    if out < 1:
        k = spring(lt - 0.05, w=10, z=0.55)
        float_card(c, app_icon("instagram", 190), 540, 730 + 8 * math.sin(t * 1.8), k * (1 - 0.6 * out), a=1 - out)
        for j, nm in enumerate(IDEAS):
            ang = j / len(IDEAS) * 2 * math.pi + lt * 0.5
            st = 0.25 + j * 0.13
            if lt < st: continue
            r = 210 * ease_out(clamp((lt - st) / 0.5))
            pop(c, fl(nm, 104), 540 + math.cos(ang) * r * 1.6, 735 + math.sin(ang) * r * 0.62, st, lt, rot=10 * math.sin(t + j), a=1 - out)
    # 2.88: Telegram "saved" (left), 3.86: Google Sheets (right) — notes pile into both
    if lt > 2.8:
        pop(c, app_icon("telegram", 170), 290, 760, 2.86, lt, bob=8, t=t)
    if lt > 3.8:
        pop(c, app_icon("sheets", 170), 790, 760, 3.84, lt, bob=8, t=t, ph=1)
    for j, nm in enumerate(IDEAS):
        st = 3.0 + j * 0.28
        if lt < st: continue
        f = ease_io(clamp((lt - st) / 0.55))
        tx = 290 if j % 2 == 0 else 790
        if j % 2 == 1 and lt < 3.9: continue
        x = lerp(540, tx, f); y = lerp(700, 640 - (j // 2) * 26, f) - 120 * math.sin(math.pi * f)
        float_card(c, fl(nm, 70), x, y, 1.0, rot=lerp(0, 25 * (1 if j % 2 else -1), f))
    if lt > 4.86:   # "yozib boradi" — the pile gets messy (jitter)
        jt = clamp((lt - 4.86) / 0.2) * (1 - clamp((lt - 5.4) / 0.2))
        for x0 in (290, 790):
            g = glow(260, (200, 80, 60)); gg = g.resize((220, 220)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5 * jt)))
            c.alpha_composite(gg, (x0 - 110, 650))
    return c

def cart_reveal(lt, t):
    c = scene()
    pop(c, fl("light_bulb", 150), 250, 720, 0.06, lt, bob=10, t=t)
    if lt > 1.15:
        k = spring(lt - 1.24, w=9, z=0.5)
        g = glow(420, GOLD); gg = g.resize((max(1, int(460 * k)),) * 2)
        c.alpha_composite(gg, (int(640 - gg.width / 2), int(740 - gg.height / 2)))
        float_card(c, app_icon("notion", 230), 640, 740 + 6 * math.sin(t * 2), k, rot=8 * (1 - clamp(k)))
        for j in range(6):
            u = lt - 1.3 - j * 0.07
            if u <= 0: continue
            ang = j * 1.047 + 0.4
            r = 170 + 120 * ease_out(clamp(u / 0.6))
            pop(c, fl("sparkles", 60), 640 + math.cos(ang) * r, 740 + math.sin(ang) * r * 0.7, 0, u, a=1 - clamp((u - 0.6) / 0.4))
    return c

def cart_arch(lt, t):
    c = scene()
    k = spring(lt - 0.05, w=10, z=0.65)
    win = notion_window(880, 350, lt, rows_at=(2.66, 2.86, 3.06), cols_at=1.82, sidebar_at=0.6)
    paste_alpha(c, win, 540 - win.width / 2, 560 + (1 - k) * 80, clamp(k * 2))
    pop(c, fl("puzzle_piece", 110), 960, 600, 1.0, lt, rot=12 * math.sin(t * 1.4), bob=8, t=t)
    return c

def cart_order(lt, t):
    global NOTES_M
    if NOTES_M is None: NOTES_M = [messy_note(s) for s in range(6)]
    c = scene()
    cols = [("G'oya", (170, 160, 150), 230), ("Syomka", (232, 170, 60), 540), ("Joylandi", (90, 180, 120), 850)]
    d = ImageDraw.Draw(c)
    hk = clamp((lt - 0.3) / 0.4)
    for nm, col, x in cols:
        if hk > 0:
            tmp = Image.new("RGBA", c.size, (0, 0, 0, 0))
            pill(ImageDraw.Draw(tmp), int(x - 80), 590, nm, col, size=28)
            tmp.putalpha(tmp.getchannel("A").point(lambda v: int(v * hk)))
            c.alpha_composite(tmp)
    rng = np.random.default_rng(9)
    for j in range(6):
        sx, sy, sr = rng.uniform(150, 930), rng.uniform(640, 900), rng.uniform(-35, 35)
        col_i = j % 3; row_i = j // 3
        tx, ty = cols[col_i][2], 700 + row_i * 120
        f = ease_io(clamp((lt - 0.5 - j * 0.12) / 0.6))
        float_card(c, NOTES_M[j], lerp(sx, tx, f), lerp(sy, ty, f) + 3 * math.sin(t * 2 + j), 1.0, rot=sr * (1 - f))
    for j in range(3):
        pop(c, fl("check_mark_button", 54), cols[j][2] + 70, 666, 1.5 + j * 0.15, lt, w=13, z=0.45)
    if lt > 2.3:    # share: link + envelope flying out
        pop(c, fl("link", 120), 930, 900, 2.35, lt, rot=10 * math.sin(t * 2), w=12, z=0.5)
        u = ease_in(clamp((lt - 3.6) / 0.9))
        if lt > 3.4:
            float_card(c, fl("envelope_with_arrow", 120), lerp(780, 1150, u), lerp(860, 560, u), spring(lt - 3.4, w=12, z=0.5), rot=-15 * u)
    return c

def cart_pro(lt, t):
    c = scene()
    k = spring(lt - 0.05, w=10, z=0.65)
    ph = phone_frame(mini_page(), 200)
    paste_alpha(c, ph, 330 - ph.width / 2, 570 + (1 - k) * 120, clamp(k * 2))
    pop(c, fl("crown", 120), 330, 570, 0.4, lt, rot=-12, w=12, z=0.45)
    for j in range(5):    # 5-star rating fills in
        x = 560 + j * 92
        pop(c, fl("star", 80), x, 720, 1.5 + j * 0.16, lt, w=13, z=0.45)
    pop(c, fl("hundred_points", 140), 750, 860, 2.86, lt, rot=-8, bob=6, t=t, w=12, z=0.45)
    if lt > 2.86:
        u = lt - 2.86
        for j in range(5):
            ang = j * 1.256
            pop(c, fl("sparkles", 50), 750 + math.cos(ang) * 130 * ease_out(clamp(u / 0.5)), 860 + math.sin(ang) * 80, 0, u, a=1 - clamp((u - 0.7) / 0.4))
    return c

def cart_confused(lt, t):
    c = scene()
    pop(c, fl("thinking_face", 200), 270, 760, 0.05, lt, bob=8, t=t)
    gear = fl("gear", 130)
    if lt > 0.3:
        float_card(c, gear, 640, 690, spring(lt - 0.3, w=10, z=0.6), rot=-lt * 60)
        float_card(c, gear.resize((90, 90)), 735, 790, spring(lt - 0.45, w=10, z=0.6), rot=lt * 85)
    # two puzzle pieces trying (and failing) to fit
    for j, (x0, y0) in enumerate(((820, 640), (900, 870))):
        if lt < 0.6 + j * 0.2: continue
        tr = 30 * math.sin(lt * 3.2 + j * math.pi)
        pop(c, fl("puzzle_piece", 110), x0 + tr * (1 if j else -1), y0, 0.6 + j * 0.2, lt, rot=20 * math.sin(lt * 2 + j))
    pop(c, fl("cross_mark", 120), 860, 760, 3.26, lt, w=13, z=0.45)
    return c

def cart_gift(lt, t):
    c = scene()
    opened = lt > 2.6
    if not opened:
        sq = 1 + 0.05 * math.sin(lt * 10) * clamp((lt - 1.6) / 0.6)
        pop(c, fl("wrapped_gift", int(220 * sq)), 540, 760, 0.05, lt, bob=6, t=t)
        if lt > 1.18: pop(c, fl("sparkles", 70), 680, 640, 1.2, lt, bob=6, t=t)
    else:
        u = lt - 2.6
        g = glow(460, GOLD); gg = g.resize((max(1, int(520 * clamp(u / 0.4))),) * 2)
        c.alpha_composite(gg, (int(540 - gg.width / 2), int(760 - gg.height / 2)))
        win = notion_window(620, 330, lt, rows_at=(2.9, 3.05, 3.2), cols_at=2.75, sidebar_at=2.7)
        kw = spring(u, w=10, z=0.6)
        paste_alpha(c, win, 470 - win.width / 2 * kw, 575 + (1 - kw) * 160, clamp(u / 0.2), scale=kw)
        tmp = Image.new("RGBA", c.size, (0, 0, 0, 0))
        pill(ImageDraw.Draw(tmp), 800, 600, "BEPUL", (90, 180, 120), size=34, pad=20)
        paste_alpha(c, tmp, 0, 0, clamp((u - 0.15) / 0.25))
        if lt > 3.28:   # rubrikalar
            pop(c, fl("card_index_dividers", 130), 880, 760, 3.28, lt, bob=6, t=t)
            for j, (nm, col) in enumerate((("Savol-javob", (120, 160, 230)), ("Mif", (220, 120, 140)), ("Maslahat", (150, 120, 210)))):
                st = 5.26 + j * 0.15
                if lt < st: continue
                a = ease_out(clamp((lt - st) / 0.3))
                tmp = Image.new("RGBA", c.size, (0, 0, 0, 0))
                xx = [800, 800, 800][j]; yy = 830 + j * 44
                pill(ImageDraw.Draw(tmp), xx, yy, nm, col, size=22, pad=12)
                paste_alpha(c, tmp, (1 - a) * 40, 0, a)
    return c

def cart_comment(lt, t):
    c = scene()
    k = spring(lt - 0.05, w=11, z=0.6)
    bar = grad_card(820, 110, 55, (255, 255, 255), (238, 236, 232), hl=False).copy()
    d = ImageDraw.Draw(bar)
    d.ellipse((18, 18, 92, 92), fill=(220, 210, 200))
    d.ellipse((40, 30, 70, 60), fill=(170, 150, 136)); d.chord((28, 58, 82, 104), 180, 360, fill=(170, 150, 136))
    txt = "Shablon kerak"
    n = int(clamp((lt - 0.3) / 0.9) * len(txt))
    d.text((112, 55), txt[:n] + ("|" if int(lt * 3) % 2 == 0 and n < len(txt) else ""), font=dfont("Medium", 38), fill=INK, anchor="lm")
    sent = lt > 1.35
    d.text((800 - 24, 55), "Yuborish", font=dfont("Black", 30), fill=(0, 149, 246) if n == len(txt) else (170, 200, 230), anchor="rm")
    bar = with_shadow(bar, 14, 14, 0.5)
    paste_alpha(c, bar, 540 - bar.width / 2, (600 if not sent else lerp(600, 560, ease_out(clamp((lt - 1.35) / 0.3)))) + (1 - k) * 60, clamp(k * 2))
    pop(c, fl("speech_balloon", 110), 900, 590, 0.1, lt, w=12, z=0.5)
    if lt > 1.5:   # DM notification with the link
        u = spring(lt - 1.5, w=11, z=0.6)
        card = grad_card(700, 130, 30, (60, 44, 36), (40, 28, 22)).copy()
        cd = ImageDraw.Draw(card)
        card.alpha_composite(fl("link", 80, False), (24, 25))
        cd.text((124, 46), "Yangi xabar", font=dfont("Black", 32), fill=WHITE, anchor="lm")
        cd.text((124, 90), "Shablon linki: notion.so/...", font=dfont("Light", 28), fill=(230, 214, 200), anchor="lm")
        card = with_shadow(card, 14, 14, 0.5)
        paste_alpha(c, card, 500 - card.width / 2 + (1 - u) * 300, 760, clamp(u * 2))
        pop(c, fl("bell", 110), 900, 800, 1.6, lt, rot=14 * math.sin(lt * 14) * (1 - clamp((lt - 1.6) / 0.8)), w=12, z=0.45)
    return c

PANELS.update({"apps": cart_apps, "reveal": cart_reveal, "arch": cart_arch, "order": cart_order, "pro": cart_pro,
               "confused": cart_confused, "gift": cart_gift, "comment": cart_comment})
