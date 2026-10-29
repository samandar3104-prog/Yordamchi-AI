# ================= v9: new cast (girl, mom in blue) + "R/L at 2 y.o." scenario =================
RIGS.update({
    "girl": dict(img="girl_cut", eyes=[(255, 275, 48, 42), (452, 275, 48, 42)], mouth=(350, 380, 70), head=(350, 250, 230), neck=(350, 445),
                 skin=(246, 202, 180), lips=(205, 110, 100)),
    "mom3": dict(img="mom3_cut", eyes=[(140, 192, 30, 22), (238, 192, 30, 22)], mouth=(190, 262, 38), head=(190, 190, 125), neck=(195, 320),
                 skin=(240, 192, 162), lips=(200, 110, 100)),
    "mom2": dict(img="mom2_cut", eyes=[(152, 212, 26, 24), (277, 212, 26, 24)], mouth=(217, 285, 40), head=(215, 215, 150), neck=(215, 345),
                 skin=(240, 194, 166), lips=(205, 120, 110)),
})
LIMBS = {
    "girl": dict(arms=[((205, 455), (55, 300), 72, 1), ((495, 455), (650, 300), 72, -1)], brows=[(270, 182), (430, 182)], brow_r=55),
    "mom3": dict(arms=[((95, 400), (78, 555), 46, 1)], hand=(255, 565, 70), brows=[(170, 146), (218, 146)], brow_r=30),
    "mom2": dict(arms=[((105, 450), (62, 690), 48, 1), ((322, 450), (337, 700), 48, -1)], brows=[(187, 158), (247, 155)], brow_r=32),
    "logo": dict(arms=[((324, 254), (461, 103), 70, 0)], hand=(110, 360, 80), brows=[(126, 90), (160, 86)], brow_r=24),
}
MOUTH = {"mom3": (190, 262, 38), "girl": (350, 380, 70), "mom2": (217, 285, 40), "logo": (158, 150, 24)}
MOODS = [
    (2.2, 6.9, {"mom3": "sad", "girl": "calm"}),
    (6.9, 12.2, {"logo": "happy"}),
    (14.8, 17.0, {"logo": "happy"}),
    (17.0, 21.3, {"girl": "happy"}),
    (21.3, 25.4, {"mom3": "sad", "girl": "calm"}),
    (25.4, 28.2, {"mom3": "happy", "girl": "happy"}),
    (28.2, 32.4, {"mom3": "happy", "girl": "happy"}),
    (32.4, 36.6, {"girl": "happy"}),
    (39.0, 40.3, {"mom3": "calm", "girl": "calm"}),
    (40.3, 42.0, {"mom3": "happy", "girl": "happy"}),
]

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None, wave=0.0):
    """Body-only acting (mouth never moves): breathing, sway, head, arms, lids; sad face baked by warp."""
    rig = RIGS[who]; L = LIMBS[who]
    mood, mk = mood_at(who, t)
    sad = mk if mood == "sad" else 0.0
    happy = mk if mood == "happy" else 0.0
    s100 = int(round(s * 100))
    base = _expr_sprite(who, s100, int(round(sad * 10)))
    h, w = base.shape[:2]
    blink = blink_amt(t, seed)
    img = _lids(base, rig, s, max(1 - blink, 0.14 * sad))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    sp = 1.0 + 0.6 * happy - 0.35 * sad
    b = (0.006 + 0.004 * happy) * math.sin(t * 1.5 * sp + seed) - 0.012 * sad
    th = math.radians((0.8 + 0.8 * happy) * math.sin(t * 0.55 * sp + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.15 - dist) / (hr * 0.4), 0, 1) * np.clip((ny + hr * 0.12 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = (2.4 * math.sin(t * 0.9 * sp + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt
          + happy * 3.5 * math.sin(t * 3.1 + seed) + sad * (5.0 + 1.0 * math.sin(t * 0.7)))
    ht = math.radians(ht)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 * sp + seed) + happy * 5 * abs(math.sin(t * 3.1 + seed)) - sad * 10) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    for j, (p0, p1, wid, side) in enumerate(L.get("arms", [])):
        p0 = (p0[0] * s, p0[1] * s); p1 = (p1[0] * s, p1[1] * s)
        if who == "logo":
            ang = arm + 3.0 * math.sin(t * 1.7 + seed) + happy * 7 * math.sin(t * 4.2)
        else:
            ph = seed + j * 1.9
            ang = (3.0 * math.sin(t * 1.3 + ph)) * (1 - 0.7 * sad)
            ang += side * (happy * 7 * math.sin(t * 4.5 + j * math.pi) + wave * 12 * math.sin(t * 7.0 + j * math.pi))
            ang -= side * sad * 4
        ox, oy = _field_seg(xx, yy, p0, p1, wid * s, ang)
        sx += ox; sy += oy
    if "hand" in L:
        hx_, hy_, hr_ = L["hand"]
        ox, oy = _field_blob(xx, yy, hx_ * s, hy_ * s, hr_ * s, 4 * math.sin(t * 1.1 + seed) * s,
                             (5 * math.sin(t * 1.6 + seed * 1.3) + happy * 9 * abs(math.sin(t * 5.0))) * s)
        sx += ox; sy += oy
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR,
                     borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

# ---------- objects ----------
@lru_cache(maxsize=32)
def letter_tile(ch, size=150, mode="warm"):
    c0, c1 = {"warm": ((246, 186, 96), (214, 104, 70)), "green": ((140, 214, 140), (60, 150, 90)),
              "gray": ((150, 144, 140), (96, 92, 90)), "blue": ((150, 196, 236), (78, 124, 196)),
              "cream": ((252, 244, 228), (226, 210, 186))}[mode]
    im = grad_card(size, size, int(size * 0.24), c0, c1).copy()
    col = (90, 52, 38) if mode == "cream" else WHITE
    ImageDraw.Draw(im).text((size / 2, size / 2 + 4), ch, font=dfont("Black", int(size * (0.6 if len(ch) == 1 else 0.46))), fill=col, anchor="mm")
    return with_shadow(im, 12, 12)

@lru_cache(maxsize=4)
def check_badge(size=120):
    S2 = size * 3
    im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, S2 - 1, S2 - 1), fill=(84, 186, 116))
    d.ellipse((S2 * 0.06, S2 * 0.04, S2 * 0.94, S2 * 0.6), fill=(255, 255, 255, 30))
    d.line([(S2 * 0.27, S2 * 0.52), (S2 * 0.44, S2 * 0.68), (S2 * 0.74, S2 * 0.34)], fill=WHITE, width=int(S2 * 0.11), joint="curve")
    return with_shadow(im.resize((size, size), Image.LANCZOS), 10, 10)

def note_img(size, col, double=False):
    S2 = size * 3
    im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((S2 * 0.08, S2 * 0.66, S2 * 0.42, S2 * 0.92), fill=col)
    d.rectangle((S2 * 0.36, S2 * 0.12, S2 * 0.43, S2 * 0.8), fill=col)
    if double:
        d.ellipse((S2 * 0.56, S2 * 0.56, S2 * 0.9, S2 * 0.82), fill=col)
        d.rectangle((S2 * 0.84, S2 * 0.04, S2 * 0.91, S2 * 0.7), fill=col)
        d.polygon([(S2 * 0.36, S2 * 0.12), (S2 * 0.91, S2 * 0.02), (S2 * 0.91, S2 * 0.16), (S2 * 0.36, S2 * 0.26)], fill=col)
    else:
        d.polygon([(S2 * 0.43, S2 * 0.12), (S2 * 0.7, S2 * 0.3), (S2 * 0.66, S2 * 0.4), (S2 * 0.43, S2 * 0.28)], fill=col)
    return im.resize((size, size), Image.LANCZOS)
NOTES = None

@lru_cache(maxsize=8)
def bubble_img(ch, mode, flip=False):
    w_, h_ = 230, 190
    im = Image.new("RGBA", (w_, h_ + 40), (0, 0, 0, 0))
    im.alpha_composite(grad_card(w_, h_, 46, (252, 246, 236), (232, 220, 204)), (0, 0))
    d = ImageDraw.Draw(im)
    tx = 50 if not flip else w_ - 50
    d.polygon([(tx - 22, h_ - 4), (tx + 22, h_ - 4), (tx - 30 if not flip else tx + 30, h_ + 36)], fill=(232, 220, 204))
    t_ = letter_tile(ch, 120, mode)
    im.alpha_composite(t_, ((w_ - t_.width) // 2, (h_ - t_.height) // 2 + 4))
    return with_shadow(im, 12, 12)

def age_ruler(c, x0, x1, y, p):
    """Rounded track 2→5 years, progress p 0..1."""
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((x0, y - 10, x1, y + 10), 10, fill=(80, 50, 40))
    xp = lerp(x0, x1, clamp(p))
    if xp > x0 + 20: d.rounded_rectangle((x0, y - 10, xp, y + 10), 10, fill=(130, 208, 140))
    f = dfont("Black", 38)
    for j, yr in enumerate((2, 3, 4, 5)):
        x = lerp(x0, x1, j / 3)
        on = p >= j / 3 - 0.01
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(130, 208, 140) if on else (110, 74, 60))
        d.text((x, y + 52), str(yr), font=f, fill=WHITE if on else (170, 140, 126), anchor="mm")
    d.text((x1 + 18, y + 52), "yosh", font=dfont("Light", 34), fill=(220, 200, 186), anchor="lm") if x1 + 120 < W else None

# ---------- scenes ----------
def cart_question(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=1)
    place(c, m, 235, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 840, 620)
    # R and L swap places (she mixes them), then L gets "eaten"
    k = spring(lt - 0.3, w=10, z=0.6)
    sw = ease_io(((lt - 0.9) % 1.4) / 0.7) if lt > 0.9 else 0
    flip = int(max(0, lt - 0.9) // 1.4) % 2 == 1
    u = 1 - sw if flip else sw
    pr = (lerp(470, 640, u), 700 - 60 * math.sin(math.pi * u))
    pl = (lerp(640, 470, u), 700 + 60 * math.sin(math.pi * u))
    eat = clamp((lt - 1.95) / 0.6)
    float_card(c, letter_tile("R", 140, "warm"), pr[0], pr[1], k)
    float_card(c, letter_tile("L", 140, "gray" if eat > 0.3 else "blue"), pl[0], pl[1], k * (1 - 0.45 * eat), a=1 - 0.6 * eat)
    if lt > 3.3:
        kk = spring(lt - 3.3, w=11, z=0.55)
        float_card(c, icon_card("q", 130), 430, 610 + 8 * math.sin(t * 2), kk, rot=8 * math.sin(t * 1.3))
    return c

def cart_normal(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, seed=5, arm=-5 * abs(math.sin(lt * 2.5)) if lt < 2.5 else 0)
    place(c, lg, 230, 560)
    k = spring(lt - 0.35, w=10, z=0.6)
    float_card(c, letter_tile("L", 170, "blue"), 680, 690 + 8 * math.sin(t * 1.6), k)
    if lt > 1.9:
        kb = spring(lt - 1.9, w=12, z=0.45)
        float_card(c, check_badge(96), 770, 610, kb)
    if lt > 2.9:
        a = clamp((lt - 2.9) / 0.4)
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0)); age_ruler(lay, 470, 880, 850, ease_io((lt - 3.3) / 1.6))
        paste_alpha(c, lay, 0, (1 - a) * 30, a)
    return c

def cart_same(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, seed=5)
    place(c, lg, 230, 560)
    k = spring(lt - 0.2, w=10, z=0.6)
    u = ease_io(clamp((lt - 0.4) / 0.8))
    float_card(c, letter_tile("R", 140, "warm"), lerp(560, 840, u), 720 - 70 * math.sin(math.pi * u), k)
    float_card(c, letter_tile("L", 140, "blue"), lerp(840, 560, u), 720 + 70 * math.sin(math.pi * u), k)
    if lt > 0.66:
        kb = spring(lt - 0.66, w=12, z=0.45)
        g = glow(320, (120, 220, 140)); gg = g.resize((max(1, int(260 * kb)),) * 2)
        c.alpha_composite(gg, (int(700 - gg.width / 2), int(620 - gg.height / 2)))
        float_card(c, check_badge(110), 700, 620, kb)
    return c

def cart_sounds(lt, t):
    c = scene("home")
    g = puppet("girl", t, 0.5, seed=3)
    place(c, g, 830, 600)
    letters = "ABLRS"
    rng = np.random.default_rng(4)
    placed = lt > 3.1
    for j, ch in enumerate(letters):
        sx_, sy_ = 90 + j * 118, 760
        d = ImageDraw.Draw(c); d.rounded_rectangle((sx_ - 52, sy_ - 52, sx_ + 52, sy_ + 52), 22, outline=(120, 80, 62), width=4)
        st = 0.3 + j * 0.42
        if lt < st: continue
        f = ease_out(clamp((lt - st) / 0.7))
        x0, y0 = rng.uniform(60, 640), rng.uniform(600, 920)
        r0 = rng.uniform(-40, 40)
        x = lerp(x0, sx_, f); y = lerp(y0, sy_, f) - 50 * math.sin(math.pi * f)
        float_card(c, letter_tile(ch, 104, "green" if placed else "cream"), x, y, clamp((lt - st) / 0.2), rot=r0 * (1 - f))
    if placed:
        kb = spring(lt - 3.1, w=12, z=0.45)
        float_card(c, check_badge(90), 330, 640, kb)
    return c

def cart_ok(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=1, tilt=-3)
    place(c, m, 235, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    wob = clamp((lt - 3.3) / 0.3) * (1 - clamp((lt - 4.3) / 0.3))
    tiles = (("Sh", "warm", 0.56, 480, 680), ("J", "warm", 0.86, 585, 680), ("Ch", "warm", 1.16, 690, 680),
             ("R", "warm", 1.46, 530, 795), ("L", "blue", 2.54, 640, 795))
    for j, (ch, mode, st, x, y) in enumerate(tiles):
        if lt < st: continue
        k = spring(lt - st, w=12, z=0.55)
        sh = wob * 8 * math.sin(lt * 38 + j)
        rot = wob * 10 * math.sin(lt * 21 + j * 2)
        float_card(c, letter_tile(ch, 100, mode), x + sh, y + 5 * math.sin(t * 1.5 + j), k, rot=rot)
    if lt > 4.3:
        kb = spring(lt - 4.3, w=12, z=0.45)
        g2 = glow(320, (120, 220, 140)); gg = g2.resize((max(1, int(280 * kb)),) * 2)
        c.alpha_composite(gg, (int(745 - gg.width / 2), int(770 - gg.height / 2)))
        float_card(c, check_badge(90), 745, 770, kb)
    return c

def cart_tongue(lt, t):
    global MIRROR
    if MIRROR is None: MIRROR = mirror_img()
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=2)
    place(c, m, 220, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    k = spring(lt - 0.2, w=10, z=0.65)
    mi = MIRROR.resize((int(MIRROR.width * 1.25), int(MIRROR.height * 1.25)))
    paste_alpha(c, mi, 545 - mi.width / 2, 610 + (1 - k) * 60, clamp(k * 2))
    if lt > 2.2:
        kk = spring(lt - 2.2, w=11, z=0.55)
        float_card(c, icon_card("mouth", 120), 545, 735 + 6 * math.sin(t * 3), kk)
    return c

def cart_music(lt, t):
    global NOTES
    if NOTES is None: NOTES = [note_img(90, col, j % 2 == 1) for j, col in enumerate((GOLD, (150, 196, 236), (240, 150, 170), (140, 214, 140)))]
    c = scene("home")
    beat = (lt * 2.0) % 1.0
    pulse = math.exp(-beat * 5)
    for r_, a_ in ((260, 0.35), (380, 0.2)):
        rr = int(r_ * (1 + 0.15 * pulse))
        gg = glow(rr, (220, 140, 90)).resize((rr * 2, rr * 2))
        gg.putalpha(gg.getchannel("A").point(lambda v: int(v * (a_ + 0.4 * pulse))))
        c.alpha_composite(gg, (540 - rr, 760 - rr))
    g = puppet("girl", t, 0.52, seed=3, wave=1.0, jump=-14 * pulse)
    place(c, g, 540, 590)
    for j in range(8):
        st = 0.2 + j * 0.45
        u = lt - st
        if u <= 0 or u > 2.6: continue
        side = -1 if j % 2 == 0 else 1
        x = 540 + side * (170 + 110 * u) + 20 * math.sin(u * 5 + j)
        y = 860 - 150 * u
        if y < 560: continue
        paste_alpha(c, NOTES[j % 4].rotate(10 * math.sin(u * 4 + j), Image.BICUBIC, expand=True), x - 45, y - 45,
                    clamp(u / 0.2) * (1 - clamp((u - 2.0) / 0.6)))
    return c

def cart_correct(lt, t):
    c = scene("home")
    m = puppet("mom3", t, 0.8, seed=2, tilt=-4)
    place(c, m, 220, 565)
    g = puppet("girl", t, 0.48, seed=3)
    place(c, g, 860, 620)
    k1 = spring(lt - 0.2, w=11, z=0.6)
    wrong = lt < 1.38
    sh = 6 * math.sin(lt * 40) if 0.4 < lt < 1.2 else 0
    float_card(c, bubble_img("L", "gray" if wrong else "blue", True), 660 + sh, 640, k1 * (1 - 0.25 * clamp((lt - 1.38) / 0.3)))
    if lt > 1.38:
        k2 = spring(lt - 1.38, w=11, z=0.55)
        float_card(c, bubble_img("L", "green"), 450, 700, k2)
    if lt > 1.9:
        kb = spring(lt - 1.9, w=12, z=0.45)
        float_card(c, check_badge(84), 545, 620, kb)
    return c

PANELS.update({"question": cart_question, "normal": cart_normal, "same": cart_same, "sounds": cart_sounds, "ok": cart_ok,
               "tongue": cart_tongue, "music": cart_music, "correct": cart_correct})
