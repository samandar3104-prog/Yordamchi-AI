# ================= v17: story cartoon — reference-image puppets + Fluent 3D props on the brand's motion background =================
PUNCH[:] = [(52.70, 1.04, 54.30), (101.20, 1.04, 102.10), (117.50, 1.04, 119.40)]
LIMBS["boy"] = dict(arms=[((318, 470), (335, 770), 46, -1)], hand=(118, 470, 70), brows=[(150, 168), (210, 168)], brow_r=48)
MOUTH["boy"] = (176, 300, 54)
MOODS = [(10.2, 14.5, {"logo": "sad"}), (14.5, 26.5, {"logo": "calm"}), (35.5, 49.6, {"logo": "happy", "boy": "happy", "girl": "happy"}),
         (66.3, 96.0, {"logo": "happy", "boy": "happy", "girl": "happy"})]

# ---------- full-screen moving background (the client's brown/gold sample), ping-pong looped ----------
_FULLBG = []
def full_bg(t):
    if not _FULLBG:
        w_, h_ = 405, 720
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "in", "bg2.mp4"), "-vf", f"fps=12,scale={w_}:{h_}",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        while True:
            b = p.stdout.read(w_ * h_ * 3)
            if len(b) < w_ * h_ * 3: break
            _FULLBG.append(np.frombuffer(b, np.uint8).reshape(h_, w_, 3))
    n = len(_FULLBG); k = int(t * 12) % (2 * n - 2)
    i = k if k < n else 2 * n - 2 - k
    im = Image.fromarray(_FULLBG[i]).resize((W, H), Image.BICUBIC).convert("RGBA")
    im.alpha_composite(_vignette())
    return im

@lru_cache(maxsize=1)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
    a = np.clip((d - 0.55) * 1.3, 0, 1) ** 1.4 * 150
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 0] = 18; arr[..., 1] = 9; arr[..., 2] = 5; arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

@lru_cache(maxsize=1)
def floor_glow():
    im = Image.new("RGBA", (1000, 220), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 0, 999, 219), fill=(255, 214, 160, 46))
    return im.filter(ImageFilter.GaussianBlur(30))

FLOOR = 1335          # feet line; captions live below ~1390

def actor(c, who, t, s, cx, lt0, lt, enter="up", seed=0, **kw):
    """Puppet that springs in (from below / side) and stands with its feet on FLOOR."""
    if lt < lt0: return
    k = spring(lt - lt0, w=9, z=0.7)
    im = puppet(who, t, s, seed=seed, **kw)
    dx = (1 - k) * (260 if enter == "right" else (-260 if enter == "left" else 0))
    dy = (1 - k) * (220 if enter == "up" else 0)
    sh = Image.new("RGBA", (int(im.width * 0.9), 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, 59), fill=(0, 0, 0, 110))
    paste_alpha(c, sh.filter(ImageFilter.GaussianBlur(12)), cx + dx - sh.width / 2, FLOOR - 30, clamp(k * 2))
    paste_alpha(c, im, cx + dx - im.width / 2, FLOOR - im.height + dy, clamp(k * 2.5))

def prop(c, name, x, y, size, lt0, lt, t=0.0, bob=8, ph=0.0, rot=0.0, a=1.0, w=11, z=0.5):
    pop(c, fl(name, size), x, y, lt0, lt, rot=rot, bob=bob, t=t, ph=ph, w=w, z=z, a=a)

def fly(c, name, size, p0, p1, lt0, dur, lt, arc=-160, rot0=0.0, rot1=0.0, fade_end=True):
    """3D prop flying along an arc from p0 to p1."""
    u = (lt - lt0) / dur
    if u <= 0: return False
    f = ease_io(clamp(u))
    x = lerp(p0[0], p1[0], f); y = lerp(p0[1], p1[1], f) + arc * math.sin(math.pi * f)
    float_card(c, fl(name, size), x, y, 1.0, rot=lerp(rot0, rot1, f), a=clamp(u * 4) * (1 - (clamp((u - 1) / 0.3) if fade_end else 0)))
    return u >= 1

def big_number(c, text, x, y, lt0, lt, col=(246, 198, 92)):
    if lt < lt0: return
    lay = Image.new("RGBA", (300, 230), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((150, 122), text, font=dfont("Black", 170), fill=WHITE, anchor="mm")
    glass(c, x, y, 300, 230, tint=col, k=spring(lt - lt0, w=11, z=0.45), r=60, alpha=(0.6, 0.4), content=lay, glow_col=col, shine=(lt - lt0 - 0.3) / 0.6)

def check(c, x, y, lt0, lt, size=74):
    gicon(c, "circle-check", x, y, size, "green", lt0, lt, w=13, z=0.45, glyph_k=0.62, glow_on=False)

# ---------- scenes (lt = time since scene start, t = absolute time) ----------
def s_hook(c, lt, t):
    actor(c, "logo", t, 1.05, 380, 0.05, lt, enter="left", seed=5, arm=-4 * abs(math.sin(lt * 2.4)))
    lay = Image.new("RGBA", (280, 260), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((140, 136), "?", font=dfont("Black", 210), fill=WHITE, anchor="mm")
    if lt > 0.6:
        k = spring(lt - 0.6, w=10, z=0.45)
        for j, (dx, dy, r) in enumerate(((560, 520, 16), (610, 470, 24))):
            glass(c, dx, dy, r * 2, r * 2, tint=(255, 255, 255), k=k, r=r, alpha=(0.4, 0.25))
        glass(c, 780, 390, 280, 260, tint=(217, 119, 87), k=k, r=90, alpha=(0.55, 0.35), content=lay, glow_col=(246, 198, 92),
              rot=6 * math.sin(lt * 2), shine=(lt - 1.0) / 0.7)
    prop(c, "sparkles", 870, 620, 110, 1.2, lt, t)

def s_duty(c, lt, t):
    actor(c, "logo", t, 1.05, 330, 0.0, lt, enter="none", seed=5, nod=0.6 if lt > 4.2 else 0)
    if lt > 4.2:   # "mas'uliyat": a big glowing shield
        u = lt - 4.2
        g = glow(520, (246, 198, 92)); paste_alpha(c, g, 790 - 260, 760 - 260, 0.7 * clamp(u / 0.4))
        prop(c, "shield", 790, 760, 330, 4.2, lt, t, bob=6, w=10, z=0.45)
        for j in range(8):
            ang = j * 0.785; r = 60 + 230 * ease_out(clamp(u / 0.6))
            float_card(c, fl("sparkles", 56), 790 + math.cos(ang) * r, 760 + math.sin(ang) * r, 1.0, a=1 - clamp((u - 0.6) / 0.6))
    prop(c, "glowing_star", 820, 470, 170, 2.3, lt, t, ph=1)

def s_eldest(c, lt, t):
    # family weight lands on her shoulders, piece by piece
    actor(c, "logo", t, 1.05, 420, 0.0, lt, enter="none", seed=5, nod=0.4 * min(1.0, lt / 3))
    gpill(c, 780, 470, "Birinchi farzand", tint=(217, 119, 87), size=34, k=spring(lt - 0.15, w=12, z=0.55), center=True, alpha=(0.65, 0.45))
    stack = [("house", 0.9, 200), ("receipt", 1.7, 160), ("money_bag", 2.4, 160), ("ledger", 3.0, 150)]
    for j, (nm, st, sz) in enumerate(stack):
        tx, ty = 420 + (j % 2) * 50 - 25, 420 - j * 115
        if lt < st: continue
        u = clamp((lt - st) / 0.45)
        y = lerp(-150, ty, ease_in(u)) - (math.sin(min(1, (lt - st - 0.45) / 0.25) * math.pi) * 18 if lt - st > 0.45 else 0)
        float_card(c, fl(nm, sz), tx, y, 1.0, rot=8 * math.sin(j * 1.7 + lt * 1.5) * (1 - u * 0.5))

def s_bills(c, lt, t):
    actor(c, "logo", t, 0.95, 230, 0.0, lt, enter="none", seed=5)
    big_number(c, "16", 760, 450, 0.1, lt)
    gpill(c, 760, 610, "yoshimda", tint=(120, 70, 40), size=30, k=spring(lt - 0.3, w=12, z=0.55), center=True, alpha=(0.65, 0.45))
    items = [("light_bulb", "Svet", 1.6, 540), ("droplet", "Suv", 2.7, 760), ("fire", "Gaz", 4.0, 960)]
    for j, (nm, lab, st, x) in enumerate(items):
        prop(c, nm, x, 860, 230, st, lt, t, ph=j)
        if lt > st + 0.2: gpill(c, x, 1010, lab, tint=(120, 70, 40), size=28, k=spring(lt - st - 0.2, w=12, z=0.55), center=True, alpha=(0.65, 0.45))
        if lt > st + 0.7:
            fly(c, "receipt", 110, (x, 860), (x + 70, 750), st + 0.7, 0.5, lt, arc=-60, fade_end=False)
            check(c, x + 70, 750, st + 1.15, lt, size=92)

def s_chores(c, lt, t):
    actor(c, "logo", t, 0.95, 250, 0.0, lt, enter="none", seed=5, arm=-5 * abs(math.sin(lt * 3)) if lt > 3.9 else 0)
    if lt < 2.0:
        prop(c, "electric_plug", 700, 640, 190, 0.0, lt, t)
        prop(c, "receipt", 880, 780, 180, 0.25, lt, t, ph=1)
        prop(c, "money_bag", 700, 920, 170, 0.5, lt, t, ph=2)
    if lt > 2.1:   # little brother's homework
        actor(c, "boy", t, 0.58, 760, 2.1, lt, enter="right", seed=3)
        prop(c, "books", 960, 740, 200, 2.4, lt, t)
        prop(c, "pencil", 960, 560, 130, 2.7, lt, t, rot=20)
    if lt > 3.9:   # cleaning the house
        u = lt - 3.9
        prop(c, "broom", 470 + 30 * math.sin(u * 7), 1020, 270, 3.9, lt, t, bob=0, rot=18 * math.sin(u * 7))
        for j in range(6):
            q = (u * 1.4 + j / 6) % 1
            float_card(c, fl("bubbles", 70), 520 + j * 30, 1150 - 260 * q, 1.0, a=1 - q)

def s_travel(c, lt, t):
    # parents fly away; she stays at home with grandma and her brother
    if lt < 5.4:
        prop(c, "house", 540, 900, 380, 0.0, lt, t, bob=4)
        fly(c, "airplane", 230, (-150, 700), (1250, 330), 0.9, 2.6, lt, arc=-140, rot0=-8, rot1=-14)
        if 1.2 < lt < 4.0:
            gpill(c, 540, 470, "Ota-onam safarda", tint=(120, 70, 40), size=34, k=spring(lt - 1.2, w=12, z=0.55) * (1 - clamp((lt - 3.7) / 0.3)), center=True, alpha=(0.65, 0.45))
        if lt > 2.9:
            prop(c, "spiral_calendar", 860, 520, 180, 2.9, lt, t)
    else:
        u = lt - 5.4
        prop(c, "house", 540, 560, 260, 5.4, lt, t, bob=3)
        actor(c, "logo", t, 0.92, 250, 5.4, lt, enter="left", seed=5)
        g = fl("old_woman", 300)
        k = spring(u - 0.1, w=10, z=0.6) if u > 0.1 else 0
        float_card(c, g, 590, FLOOR - 200 + 4 * math.sin(t * 1.6), k)
        gpill(c, 590, FLOOR - 390, "Buvim", tint=(217, 119, 87), size=30, k=spring(u - 0.3, w=12, z=0.55) if u > 0.3 else 0, center=True, alpha=(0.65, 0.45))
        actor(c, "boy", t, 0.56, 880, 6.4, lt, enter="right", seed=3)
        gpill(c, 880, FLOOR - 650, "Ukam", tint=(217, 119, 87), size=30, k=spring(lt - 6.7, w=12, z=0.55) if lt > 6.7 else 0, center=True, alpha=(0.65, 0.45))
        prop(c, "teacup_without_handle", 750, 1180, 100, 6.0, lt, t, bob=3)

def s_climb(c, lt, t):
    # responsibility → climbing: mountain, footsteps, star on the top; brother and niece look up to her
    prop(c, "mountain", 760, 820, 560, 0.0, lt, t, bob=3)
    for j in range(5):
        st = 1.0 + j * 0.35
        if lt > st:
            x = lerp(560, 880, j / 4); y = lerp(1000, 640, j / 4)
            float_card(c, fl("footprints", 70), x, y, spring(lt - st, w=13, z=0.5), rot=-30)
    prop(c, "glowing_star", 820, 440, 150, 2.6, lt, t)
    actor(c, "logo", t, 0.95, 250, 0.0, lt, enter="left", seed=5, arm=-6 * abs(math.sin(lt * 2)))
    if lt > 4.9:   # "ukam, jiyanlarim uchun o'rnak"
        actor(c, "boy", t, 0.5, 600, 4.9, lt, enter="up", seed=3)
        actor(c, "girl", t, 0.42, 820, 5.2, lt, enter="up", seed=4)
    if lt > 8.1:   # "motivatsiya" → strength + rocket
        u = lt - 8.1
        prop(c, "flexed_biceps", 470, 470, 220, 8.1, lt, t)
        ry = 900 - 700 * ease_in(clamp((u - 1.2) / 1.6))
        if u > 0.3: float_card(c, fl("rocket", 250), 980, ry, spring(u - 0.3, w=11, z=0.5), rot=0)
        if u > 1.2:
            for j in range(6):
                q = (u * 2 + j / 6) % 1
                float_card(c, fl("sparkles", 50), 960 + 30 * math.sin(j), ry + 90 + 160 * q, 1.0, a=1 - q)
    if lt > 11.4:
        gpill(c, 540, 380, "Men ko'rsatishim kerak!", tint=(217, 119, 87), size=36, k=spring(lt - 11.4, w=12, z=0.5), center=True, alpha=(0.65, 0.45))

def s_society(c, lt, t):
    g = glow(560, (246, 198, 92)); paste_alpha(c, g, 540 - 280, 560 - 280, 0.55 * clamp(lt / 0.5))
    prop(c, "heart_hands", 540, 540, 300, 3.4, lt, t)
    actor(c, "logo", t, 0.98, 540, 0.0, lt, enter="up", seed=5, arm=-5 * abs(math.sin(lt * 2.2)))
    actor(c, "boy", t, 0.5, 230, 4.9, lt, enter="left", seed=3)
    actor(c, "girl", t, 0.42, 860, 5.3, lt, enter="right", seed=4)
    if lt > 6.6:   # "iz qoldirish" — footprints across the floor
        for j in range(6):
            st = 6.6 + j * 0.2
            if lt > st: float_card(c, fl("footprints", 64), 120 + j * 170, 1260 - (j % 2) * 30, spring(lt - st, w=13, z=0.5), rot=-90)
    if lt > 8.6:   # "o'sishimga sabab" — seedling grows
        u = lt - 8.6
        s_ = 0.3 + 0.7 * ease_out(clamp(u / 1.2))
        float_card(c, fl("seedling", 270), 860, 560, s_)
        for j in range(5):
            ang = j * 1.256; r = 70 + 120 * ease_out(clamp(u / 0.8))
            float_card(c, fl("sparkles", 50), 860 + math.cos(ang) * r, 560 + math.sin(ang) * r, 1.0, a=1 - clamp((u - 0.8) / 0.6))

@lru_cache(maxsize=1)
def ig_card():
    im = Image.open(os.path.join(HERE, "profile_ig.png")).convert("RGBA")
    w_ = 860; h_ = int(im.height * w_ / im.width)
    im = im.resize((w_, h_), Image.LANCZOS); im.putalpha(_rr_mask(w_, h_, 34))
    return with_shadow(im, 22, 20, 0.6)

def s_brand(c, lt, t):
    pc = ig_card()
    k = spring(lt - 0.25, w=10, z=0.62)
    if k > 0: paste_alpha(c, pc, W / 2 - pc.width * k / 2, 470 - pc.height * k / 2, clamp(k * 2), k)
    prop(c, "crown", 540, 470 - pc.height / 2 - 30, 110, 1.0, lt, t, rot=-8)
    actor(c, "logo", t, 0.9, 300, 0.4, lt, enter="left", seed=5)
    if lt > 10.3:   # shogirdlar
        prop(c, "graduation_cap", 780, 740, 230, 10.3, lt, t)
        prop(c, "woman_teacher", 900, 1000, 260, 10.6, lt, t, ph=1)
    if lt > 12.9:
        for j in range(5):
            q = ((lt - 12.9) * 0.6 + j / 5) % 1
            float_card(c, fl("red_heart", 95), 640 + j * 80, 1180 - 380 * q, 1.0, a=(1 - q) * clamp((lt - 12.9) / 0.4))
    if lt > 16.7:
        prop(c, "handshake", 640, 640, 220, 16.7, lt, t)

SCN = {"hook": s_hook, "duty": s_duty, "eldest": s_eldest, "bills": s_bills, "chores": s_chores, "travel": s_travel,
       "climb": s_climb, "society": s_society, "brand": s_brand}

def scene_at2(t):
    for a, b, nm in story.SCENES:
        if a <= t < b: return nm, a, b
    return None, 0, 0

def cartoon_frame(t):
    c = full_bg(t)
    nm, a, b = scene_at2(t)
    lt = t - a
    c.alpha_composite(floor_glow(), (40, FLOOR - 110))
    if nm: SCN[nm](c, lt, t)
    # camera: gentle push-in over each scene, quick scale-settle on scene start
    sc = 1.0 + 0.03 * clamp(lt / max(1.0, b - a))
    if lt < 0.35: sc *= lerp(1.06, 1.0, ease_out(lt / 0.35))
    if sc > 1.001:
        c = c.resize((int(W * sc), int(H * sc)), Image.BILINEAR).crop((int((W * sc - W) / 2), int((H * sc - H) * 0.4), int((W * sc - W) / 2) + W, int((H * sc - H) * 0.4) + H))
    if lt < 0.14: c.alpha_composite(Image.new("RGBA", (W, H), (255, 228, 190, int(110 * (1 - lt / 0.14)))))
    return c

def expert_full(src, t):
    z = full_zoom(t, 1.02)
    cw, ch = SW / z, SH / z
    top = (SH - ch) * 0.25
    return src.resize((W, H), Image.BICUBIC, box=((SW - cw) / 2, top, (SW + cw) / 2, top + ch)).convert("RGBA")

def render(i, src):
    t = i / FPS
    _T_NOW[0] = t
    si = seg_at(t); a, b, lay, kind, zb = SEG[si]
    since = t - a
    if kind == "expert":
        c = expert_full(src, t)
        if since < 0.45 and si > 0:   # cartoon shrinks away behind a light flash
            u = ease_in(since / 0.45)
            ct = cartoon_frame(a - 0.02)
            ct = ct.resize((int(W * (1 + 0.3 * u)), int(H * (1 + 0.3 * u))), Image.BILINEAR)
            paste_alpha(c, ct, (W - ct.width) / 2, (H - ct.height) / 2, 1 - u)
    else:
        c = cartoon_frame(t)
        if since < 0.45 and si > 0:
            u = ease_out(since / 0.45)
            ex = expert_full(src, a - 0.02)
            ex = ex.resize((int(W * (1 + 0.25 * u)), int(H * (1 + 0.25 * u))), Image.BILINEAR)
            paste_alpha(c, ex, (W - ex.width) / 2, (H - ex.height) / 2, 1 - u)
    c.alpha_composite(SCRIM)
    draw_captions(c, t)
    return c.convert("RGB")
