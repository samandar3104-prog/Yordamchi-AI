# ================= v7: reference-character puppets (cv2 mesh warp) + realistic brain + new scenario =================
import cv2 as _cv2
AV = os.path.join(HERE, "av")

def _load(name):
    return np.array(Image.open(os.path.join(AV, name + ".png")).convert("RGBA"))

# anchors in sprite px (measured on the cut sprites)
RIGS = {
    "boy":  dict(img="boy_cut", eyes=[(126, 242, 36, 31), (231, 239, 36, 31)], mouth=(182, 306, 52), head=(182, 215, 165), neck=(185, 380),
                 skin=(246, 196, 168), lips=(205, 110, 100)),
    "mom":  dict(img="mom_cut", eyes=[(176, 220, 31, 24), (281, 232, 31, 24)], mouth=(220, 311, 42), head=(225, 220, 160), neck=(228, 380),
                 skin=(246, 200, 170), lips=(214, 120, 110)),
    "logo": dict(img="logo_cut", eyes=[(114, 113, 17, 14), (171, 100, 17, 14)], mouth=(158, 150, 24), head=(140, 115, 105), neck=(150, 215),
                 skin=(246, 206, 180), lips=(205, 110, 110), arm=((324, 254), (461, 103))),
}
_SPR = {}
def sprite(who):
    if who not in _SPR: _SPR[who] = _load(RIGS[who]["img"])
    return _SPR[who]

@lru_cache(maxsize=32)
def scaled(who, s100):
    s = s100 / 100.0
    im = sprite(who)
    h, w = im.shape[:2]
    return _cv2.resize(im, (int(w * s), int(h * s)), interpolation=_cv2.INTER_AREA)

def _overlay_face(img, rig, s, blink, talk):
    """Eyelids and an opening mouth painted on the scaled sprite before warping, so they move with the head."""
    pil = Image.fromarray(img, "RGBA"); d = ImageDraw.Draw(pil)
    if blink < 0.98:
        close = 1 - blink
        for (ex, ey, rx, ry) in rig["eyes"]:
            ex, ey, rx, ry = ex * s, ey * s, rx * s * 1.12, ry * s * 1.25
            lid = Image.new("L", pil.size, 0); ld = ImageDraw.Draw(lid)
            ld.ellipse((ex - rx, ey - ry, ex + rx, ey + ry), fill=255)
            cut = Image.new("L", pil.size, 0)
            ImageDraw.Draw(cut).rectangle((ex - rx - 2, ey - ry - 2, ex + rx + 2, ey - ry + 2 * ry * close), fill=255)
            m = ImageChops.multiply(lid, cut).filter(ImageFilter.GaussianBlur(max(0.6, s * 1.2)))
            col = Image.new("RGBA", pil.size, rig["skin"] + (255,))
            pil.paste(col, (0, 0), m)
            yl = ey - ry + 2 * ry * close
            d.arc((ex - rx * 0.95, yl - ry * 0.5, ex + rx * 0.95, yl + ry * 0.35), 15, 165, fill=(60, 36, 28), width=max(2, int(s * 4)))
    if talk > 0.1:
        mx, my, mw = rig["mouth"]; mx, my, mw = mx * s, my * s, mw * s
        h = mw * (0.08 + 0.42 * clamp(talk)); w = mw * (0.55 - 0.12 * clamp(talk))
        d.ellipse((mx - w, my - h * 0.35, mx + w, my + h), fill=(110, 36, 40))
        d.chord((mx - w * 0.8, my - h * 0.35, mx + w * 0.8, my + h * 0.3), 180, 360, fill=(250, 244, 238))
        d.chord((mx - w * 0.6, my + h * 0.2, mx + w * 0.6, my + h * 1.0), 180, 360, fill=(200, 92, 100))
        d.arc((mx - w * 1.05, my - h * 0.45, mx + w * 1.05, my + h * 1.1), 0, 180, fill=rig["lips"], width=max(2, int(s * 5)))
    return np.array(pil)

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None):
    rig = RIGS[who]
    base = scaled(who, int(round(s * 100)))
    h, w = base.shape[:2]
    blink = blink_amt(t, seed)
    img = _overlay_face(base, rig, s, blink, talk) if (blink < 0.98 or talk > 0.1) else base
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    # global: breathing (vertical stretch from the feet) + slow sway around the feet
    b = 0.006 * math.sin(t * 1.5 + seed)
    th = math.radians(0.7 * math.sin(t * 0.55 + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    # head: rotation around the neck + nod, smooth falloff
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.25 - dist) / (hr * 0.45), 0, 1) * np.clip((ny + hr * 0.15 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = math.radians(2.4 * math.sin(t * 0.9 + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 + seed)) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    # optional forearm gesture (logoped's pointer taps)
    if "arm" in rig and arm:
        (ex, ey), (tx, ty) = [(a * s, b_ * s) for a, b_ in rig["arm"]]
        vx, vy = tx - ex, ty - ey; L2 = vx * vx + vy * vy
        u = np.clip(((xx - ex) * vx + (yy - ey) * vy) / L2, -0.2, 1.2)
        px, py = ex + u * vx, ey + u * vy
        dd = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
        aw = np.clip((70 * s - dd) / (30 * s), 0, 1) * np.clip(u / 0.15, 0, 1)
        an = math.radians(arm)
        rx_ = ex + (xx - ex) * math.cos(an) + (yy - ey) * math.sin(an)
        ry_ = ey - (xx - ex) * math.sin(an) + (yy - ey) * math.cos(an)
        sx = sx + aw * (rx_ - xx); sy = sy + aw * (ry_ - yy)
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

def place(c, im, cx, top, shadow=True):
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.35)))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (int(cx - im.width / 2) + 14, int(top) + 10))
    c.alpha_composite(im, (int(cx - im.width / 2), int(top)))

# ---------- realistic brain (side view, gyri from warped noise, lit) ----------
@lru_cache(maxsize=4)
def real_brain(size=300):
    W_, H_ = size, int(size * 0.8)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    u, v = xx / W_, yy / H_
    m = Image.new("L", (W_, H_), 0); d = ImageDraw.Draw(m)
    d.ellipse((W_ * 0.04, H_ * 0.05, W_ * 0.96, H_ * 0.82), fill=255)          # cerebrum
    d.ellipse((W_ * 0.5, H_ * 0.55, W_ * 0.86, H_ * 0.9), fill=255)            # cerebellum
    d.polygon([(W_ * 0.5, H_ * 0.7), (W_ * 0.6, H_ * 0.7), (W_ * 0.6, H_ * 1.0), (W_ * 0.52, H_ * 1.0)], fill=255)   # stem
    m = m.filter(ImageFilter.GaussianBlur(2))
    rng = np.random.default_rng(3)
    n = np.zeros_like(u)
    for k in range(6):
        fq = 3 + k * 2.2; ph = rng.uniform(0, 6.28, 2); a = rng.uniform(0.6, 1.0) / (1 + k * 0.6)
        n += a * np.sin(fq * u * 6.28 + 2.0 * np.sin(fq * 0.7 * v * 6.28 + ph[0])) * np.cos(fq * v * 6.28 + 1.5 * np.sin(fq * 0.6 * u * 6.28 + ph[1]))
    f = n * 3.2
    sulci = np.abs(np.sin(f * math.pi))
    height = np.clip(sulci, 0, 1) ** 0.6
    gx = np.gradient(height, axis=1); gy = np.gradient(height, axis=0)
    light = np.clip(0.65 + (-gx * 0.6 - gy * 0.9) * 6, 0.35, 1.25)
    base = np.array((232, 170, 172), np.float32)
    rgb = base[None, None] * light[..., None]
    rgb *= (0.55 + 0.45 * height)[..., None]
    # global shading: top-left light, bottom-right falloff
    rgb *= (1.08 - 0.35 * np.clip((u + v - 0.6), 0, 1))[..., None]
    # lateral (Sylvian) fissure + cerebellum stripes + stem tone
    fis = np.exp(-((v - (0.52 - 0.18 * (u - 0.3))) / 0.012) ** 2) * ((u > 0.28) & (u < 0.72))
    rgb *= (1 - 0.6 * fis)[..., None]
    cb = ((u - 0.68) ** 2 / 0.033 + (v - 0.73) ** 2 / 0.03) < 1
    stripes = 0.75 + 0.25 * np.abs(np.sin(v * 90))
    rgb[cb] = (np.array((214, 150, 156), np.float32) * stripes[cb][:, None])
    stem = (u > 0.5) & (u < 0.6) & (v > 0.8)
    rgb[stem] = np.array((206, 150, 140), np.float32)
    im = Image.fromarray(np.uint8(np.clip(rgb, 0, 255))).convert("RGBA")
    im.putalpha(m)
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((W_ * 0.12, H_ * 0.08, W_ * 0.6, H_ * 0.4), fill=(255, 240, 240, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(18)); hl.putalpha(ImageChops.multiply(hl.getchannel("A"), m))
    im.alpha_composite(hl)
    return with_shadow(im, 14, 16, 0.5)

@lru_cache(maxsize=4)
def brain_card(size=210):
    card = grad_card(size, size, 40, (68, 40, 32), (40, 22, 18)).copy()
    b = real_brain(int(size * 0.92))
    b = b.resize((int(size * 0.92), int(b.height * size * 0.92 / b.width)))
    card.alpha_composite(b, ((size - b.width) // 2, (size - b.height) // 2 + 6))
    return with_shadow(card, 14, 16)

@lru_cache(maxsize=2)
def speech_card(size=210):
    card = grad_card(size, size, 40, (68, 40, 32), (40, 22, 18)).copy()
    d = ImageDraw.Draw(card); s = size
    d.rounded_rectangle((s * 0.18, s * 0.24, s * 0.82, s * 0.66), int(s * 0.12), fill=(250, 240, 222))
    d.polygon([(s * 0.3, s * 0.64), (s * 0.44, s * 0.64), (s * 0.28, s * 0.8)], fill=(250, 240, 222))
    for j in range(5):
        hh = [0.08, 0.16, 0.22, 0.14, 0.07][j] * s
        x = s * (0.32 + j * 0.09)
        d.rounded_rectangle((x - s * 0.025, s * 0.45 - hh / 2, x + s * 0.025, s * 0.45 + hh / 2), int(s * 0.02), fill=TERRA)
    return with_shadow(card, 14, 16)

@lru_cache(maxsize=2)
def clinic_door():
    im = Image.new("RGBA", (260, 420), (0, 0, 0, 0))
    im.alpha_composite(grad_card(240, 400, 18, (236, 236, 240), (196, 198, 206)), (10, 10))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 220, 200), 12, fill=(170, 200, 224))
    d.ellipse((190, 230, 210, 250), fill=(150, 150, 160))
    d.rounded_rectangle((70, 260, 190, 340), 14, fill=(60, 130, 200))
    d.rectangle((122, 272, 138, 328), fill=WHITE); d.rectangle((102, 292, 158, 308), fill=WHITE)
    return with_shadow(im, 14, 14)

def chat_bubble(w=220, h=96):
    im = grad_card(w, h, 40, (92, 84, 80), (70, 64, 62)).copy()
    d = ImageDraw.Draw(im)
    for j in range(3): d.ellipse((w / 2 - 40 + j * 40 - 9, h / 2 - 9, w / 2 - 40 + j * 40 + 9, h / 2 + 9), fill=(230, 226, 220))
    return with_shadow(im, 10, 10)
CHAT = None

# ---------- backgrounds (no plant) ----------
@lru_cache(maxsize=4)
def room_bg(kind):
    h = HALF
    yy = np.linspace(0, 1, h)[:, None, None]
    wall0, wall1 = np.array((62, 32, 22), np.float32), np.array((36, 19, 13), np.float32)
    arr = (wall0 + (wall1 - wall0) * yy).repeat(W, 1)
    im = Image.fromarray(np.uint8(arr)).convert("RGBA")
    d = ImageDraw.Draw(im)
    if kind == "home":
        d.polygon([(120, 0), (340, 0), (560, h), (180, h)], fill=(255, 220, 160, 16))
        d.rounded_rectangle((760, 520, 1000, 760), 16, fill=(44, 30, 26), outline=(110, 72, 50), width=10)
        d.ellipse((900, 560, 950, 610), fill=(240, 226, 200))
    g = glow(700, (130, 58, 32)); im.alpha_composite(g.resize((1200, 1200)), (-60, 160))
    return im

def board_img(t, green):
    im = grad_card(300, 230, 20, (40, 70, 58), (28, 52, 42)).copy()
    d = ImageDraw.Draw(im); d.rounded_rectangle((0, 0, 299, 229), 20, outline=(150, 100, 64), width=12)
    tile = r_tile(130, "green" if green else "warm")
    im.alpha_composite(tile, (150 - tile.width // 2, 115 - tile.height // 2))
    return with_shadow(im, 14, 14)

# ---------- new scenario ----------
def scene(kind="room"): return room_bg(kind).copy()

def cart_intro(lt, t):
    c = scene()
    k = ease_out(lt / 0.8)
    m = puppet("mom", t, 0.62, seed=1)
    place(c, m, lerp(1250, 720, k), 560)
    for j, (x, y, ph) in enumerate(((250, 700, 0), (420, 620, 1.3))):
        kk = spring(lt - 0.5 - j * 0.25, w=10, z=0.6)
        float_card(c, icon_card("q", 170 + 30 * j), x, y + 12 * math.sin(t * 1.4 + ph), kk, rot=6 * math.sin(t * 0.9 + ph))
    return c

def cart_choice(lt, t):
    c = scene()
    tl = -9 if lt < 1.1 else (9 if lt < 2.1 else 0)
    tilt = lerp(0, tl, ease_io(((lt % 1.1) if lt < 2.2 else 1) / 0.35))
    m = puppet("mom", t, 0.62, talk=voice(t), seed=1, tilt=tilt)
    place(c, m, 540, 560)
    for j, (img, x) in enumerate(((speech_card(), 160), (brain_card(), 920))):
        k = spring(lt - 0.25 - j * 0.3, w=11, z=0.6)
        hot = (lt < 1.1 and j == 0) or (1.1 <= lt < 2.2 and j == 1)
        if hot:
            g = glow(320, GOLD); gg = g.resize((300, 300)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.6)))
            c.alpha_composite(gg, (x - 150, 700 - 150))
        float_card(c, img, x, 700 + 8 * math.sin(t * 1.3 + j), k * (1.06 if hot else 1.0))
    return c

def cart_family(lt, t):
    global CHAT
    if CHAT is None: CHAT = chat_bubble()
    c = scene("home")
    b = puppet("boy", t, 0.66, talk=(abs(math.sin(t * 9)) * 0.8 if 0.3 < lt < 2.2 else 0), seed=3)
    place(c, b, 300, 600)
    m = puppet("mom", t, 0.58, talk=voice(t), seed=2, tilt=-6)
    place(c, m, 640, 570)
    k = spring(lt - 0.3, w=11, z=0.5)
    sh = 7 * math.sin(lt * 42) if 0.5 < lt < 2.2 else 0
    float_card(c, r_tile(140, "warm" if lt < 1.4 else "gray"), 470 + sh, 640, k * (1 - 0.15 * clamp((lt - 1.4) / 0.4)))
    for j in range(3):   # relatives' comments sliding in from the right edge
        tj = 2.0 + j * 0.45
        if lt < tj: continue
        kk = ease_out((lt - tj) / 0.4)
        paste_alpha(c, CHAT, lerp(1100, 860, kk), 600 + j * 110, clamp(kk * 1.5))
    return c

def cart_practice(lt, t):
    c = scene()
    tap = 6 * abs(math.sin(lt * 3.2)) if lt < 3.0 else 0
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5, arm=-tap)
    place(c, lg, 250, 560)
    green = lt > 1.7
    paste_alpha(c, board_img(t, green), 520, 580, clamp(lt / 0.3))
    if green and lt < 2.6:
        g = glow(360, (120, 220, 140)); c.alpha_composite(g, (520 + 150 - 180, 580 + 130 - 180))
    b = puppet("boy", t, 0.6, talk=max(0, voice(t - 0.25) * 0.8) if lt > 0.8 else 0, seed=6)
    place(c, b, 930, 640)
    tn = 17.26 - (t - lt)
    if lt > tn:
        k = spring(lt - tn, w=11, z=0.7); out = ease_in((lt - tn - 1.1) / 0.5)
        float_card(c, desat_img(brain_card(150), clamp((lt - tn - 0.6) / 0.4)), 980 + 300 * out, 600, k, a=1 - out)
    return c

def cart_age(lt, t):
    c = scene("home")
    speak = lt > 2.24
    b = puppet("boy", t, 0.66, talk=(voice(t) if speak else 0), seed=7, nod=1.0 if lt < 1.5 else 0)
    place(c, b, 800, 590)
    k = spring(lt - 0.2, w=10, z=0.7)
    cb = cake_base()
    paste_alpha(c, with_shadow(cb, 14, 14), 320 - cb.width / 2 - 28, 900 - cb.height - 28 + (1 - k) * 60, clamp(k * 2))
    lit = 20.56
    d = ImageDraw.Draw(c)
    for j in range(5):
        x = 210 + j * 55; y0 = 680 + (1 - k) * 60
        d.rounded_rectangle((x - 8, y0 - 70, x + 8, y0), 6, fill=[GOLD, TERRA, (120, 180, 230), (140, 210, 140), (230, 140, 200)][j])
        if t > lit + j * 0.12:
            fl = 1 + 0.15 * math.sin(t * 20 + j)
            g = glow(120, GOLD); c.alpha_composite(g, (int(x - 60), int(y0 - 130)))
            d.ellipse((x - 9 * fl, y0 - 104 * fl, x + 9 * fl, y0 - 76), fill=(255, 214, 120))
    if speak:
        u = lt - 2.24
        pts = [(lerp(450, 650, q / 50), 640 + (26 * math.sin(q * 0.9 + t * 8) + 18 * math.sin(q * 2.7)) * clamp(u / 0.4)) for q in range(51)]
        d.line(pts, fill=WARN, width=6, joint="curve")
    return c

def cart_exam(lt, t):
    c = scene()
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5, tilt=4 if lt > 1.8 else 0)
    place(c, lg, 230, 560)
    b = puppet("boy", t, 0.6, seed=6)
    place(c, b, 900, 640)
    if lt > 1.8:
        k = spring(lt - 1.8, w=10, z=0.6)
        pulse = 0.6 + 0.4 * abs(math.sin(t * 4))
        g = glow(340, AMBER); gg = g.resize((max(1, int(320 * k * pulse)), max(1, int(320 * k * pulse))))
        c.alpha_composite(gg, (int(600 - gg.width / 2), int(700 - gg.height / 2)))
        br = real_brain(360)
        float_card(c, br, 600, 730 + 8 * math.sin(t * 2), k)
    tp = 32.94 - (t - lt)
    if lt > tp:
        k = spring(lt - tp, w=12, z=0.5)
        float_card(c, icon_card("pill", 130), 650, 880, k, rot=8 * math.sin(t * 2))
    return c

def cart_refer(lt, t):
    global ENV_IMG
    if ENV_IMG is None: ENV_IMG = envelope_img()
    c = scene()
    lg = puppet("logo", t, 0.98, talk=voice(t), seed=5)
    place(c, lg, 230, 560)
    door = clinic_door()
    k = spring(lt - 0.2, w=10, z=0.7)
    paste_alpha(c, door, 860 - door.width / 2, 560 + (1 - k) * 80, clamp(k * 2))
    f = ease_io((lt - 0.8) / 0.9)
    x = lerp(420, 800, f); y = lerp(720, 690, f) - 90 * math.sin(math.pi * f)
    if lt < 1.9:
        paste_alpha(c, ENV_IMG.rotate(-12 * math.sin(math.pi * f), Image.BICUBIC, expand=True), x - 100, y - 80, clamp((lt - 0.4) / 0.3) * (1 - clamp((lt - 1.7) / 0.2)))
    if lt > 1.7:
        u = clamp((lt - 1.7) / 0.6)
        g = glow(360, (90, 150, 220)); gg = g.resize((max(1, int(380 * (0.6 + 0.4 * u))),) * 2)
        gg.putalpha(gg.getchannel("A").point(lambda v: int(v * (1 - 0.5 * u))))
        c.alpha_composite(gg, (int(860 - gg.width / 2), int(860 - 80 - gg.height / 2)))
    return c

def cart_success(lt, t):
    c = scene()
    jump = -abs(math.sin(lt * 5)) * 36 * clamp((lt - 0.6) / 0.3) * (1 - clamp((lt - 2.0) / 0.3))
    b = puppet("boy", t, 0.64, talk=0.25 if lt > 0.3 else 0, seed=6)
    place(c, b, 300, 600 + jump)
    lg = puppet("logo", t, 0.94, seed=5, arm=-6 * abs(math.sin(lt * 4)))
    place(c, lg, 820, 570)
    k = spring(lt - 0.2, w=10, z=0.5)
    g = glow(360, (120, 220, 140)); gg = g.resize((max(1, int(340 * k)),) * 2); c.alpha_composite(gg, (int(560 - gg.width / 2), int(660 - gg.height / 2)))
    float_card(c, r_tile(170, "green"), 560, 660, k)
    d = ImageDraw.Draw(c)
    rk = ease_out((lt - 0.4) / 1.2)
    d.arc((440, 540, 680, 780), -90, -90 + 360 * rk, fill=(140, 220, 150), width=10)
    rng = np.random.default_rng(5)
    for j in range(26):
        u = lt - 0.5 - rng.uniform(0, 0.4)
        if u <= 0: continue
        ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(240, 520)
        x = 560 + math.cos(ang) * sp * u; y = 660 + math.sin(ang) * sp * u + 380 * u * u
        if y > 950 or y < 560: continue
        col = [GOLD, TERRA, (120, 180, 230), (140, 210, 140)][j % 4]
        d.rectangle((x - 9, y - 4.5, x + 9, y + 4.5), fill=rgba(col, 1 - clamp(u / 1.6)))
    return c

def cart_home(lt, t):
    c = scene("home")
    d0 = ImageDraw.Draw(c)
    d0.rounded_rectangle((60, 840, 1020, 960), 40, fill=(110, 56, 46))
    m = puppet("mom", t, 0.6, talk=voice(t), seed=2, tilt=-4)
    place(c, m, 330, 560)
    b = puppet("boy", t, 0.6, talk=max(0, voice(t - 0.3) * 0.7), seed=3, nod=0.6)
    place(c, b, 800, 640)
    which = "rocket" if lt < 2.1 else "rainbow"
    fl = clamp((lt - 0.4) / 0.35) if lt < 2.1 else clamp((lt - 2.3) / 0.35)
    fc = flash_card(which, 0.5 + 0.5 * fl)
    paste_alpha(c, fc, 560 - fc.width / 2, 600 + 10 * math.sin(t * 1.5), 1.0)
    return c

PANELS.update({"intro": cart_intro, "choice": cart_choice, "family": cart_family, "practice": cart_practice, "age": cart_age,
               "exam": cart_exam, "refer": cart_refer, "success": cart_success, "home": cart_home})
