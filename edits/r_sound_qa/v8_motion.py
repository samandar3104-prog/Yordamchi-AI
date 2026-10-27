# ================= v8: no lip movement; emotions (happy / sad) + body motion (arms, hands, head, blinks) =================
# limb rigs in sprite px
LIMBS = {
    "boy":  dict(arm=((318, 470), (335, 770), 46), hand=(118, 470, 70), brows=[(150, 168), (210, 168)], brow_r=48),
    "mom":  dict(hand=(232, 680, 120), brows=[(205, 172), (262, 176)], brow_r=46),
    "logo": dict(arm=((324, 254), (461, 103), 70), hand=(110, 360, 80), brows=[(126, 90), (160, 86)], brow_r=24),
}
MOUTH = {"boy": (176, 300, 54), "mom": (220, 312, 46), "logo": (158, 150, 24)}

# who feels what, by story time
MOODS = [  # (t0, t1, {who: mood})
    (1.8, 4.5, {"mom": "sad"}),
    (4.5, 7.05, {"mom": "calm"}),
    (7.05, 11.5, {"mom": "sad", "boy": "calm"}),
    (14.3, 19.0, {"logo": "happy", "boy": "happy"}),
    (19.0, 24.4, {"boy": "sad"}),
    (27.3, 33.9, {"logo": "calm", "boy": "sad"}),
    (33.9, 37.4, {"logo": "calm"}),
    (39.8, 42.2, {"logo": "happy", "boy": "happy"}),
    (42.2, 46.4, {"mom": "happy", "boy": "happy"}),
]
def mood_at(who, t):
    for a, b, m in MOODS:
        if a <= t < b:
            md = m.get(who, "calm")
            k = clamp((t - a) / 0.5)           # ease into the emotion at scene start
            return md, k
    return "calm", 1.0

def _field_seg(xx, yy, p0, p1, wid, ang):
    """Sample-offset for rotating a limb segment around p0 by ang degrees, smooth falloff."""
    (ex, ey), (tx, ty) = p0, p1
    vx, vy = tx - ex, ty - ey; L2 = vx * vx + vy * vy
    u = np.clip(((xx - ex) * vx + (yy - ey) * vy) / L2, -0.3, 1.3)
    px, py = ex + u * vx, ey + u * vy
    dd = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
    aw = np.clip((wid - dd) / (wid * 0.45), 0, 1) * np.clip(u / 0.25, 0, 1)
    aw = aw * aw * (3 - 2 * aw)
    an = math.radians(ang)
    rx_ = ex + (xx - ex) * math.cos(an) + (yy - ey) * math.sin(an)
    ry_ = ey - (xx - ex) * math.sin(an) + (yy - ey) * math.cos(an)
    return aw * (rx_ - xx), aw * (ry_ - yy)

def _field_blob(xx, yy, cx, cy, r, dx, dy):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    w_ = np.clip((r - d) / (r * 0.6), 0, 1); w_ = w_ * w_ * (3 - 2 * w_)
    return -w_ * dx, -w_ * dy

@lru_cache(maxsize=96)
def _expr_sprite(who, s100, sad_q):
    """Sad expression baked by a local warp: mouth corners pulled down (smile flattens), inner brows raised."""
    base = scaled(who, s100)
    if sad_q == 0: return base
    s = s100 / 100.0; a = sad_q / 10.0
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ox = np.zeros_like(xx); oy = np.zeros_like(yy)
    mx, my, mw = [v * s for v in MOUTH[who]]
    nx = (xx - mx) / (mw * 1.7)
    reg = np.clip(1 - nx ** 2, 0, 1) ** 1.5 * np.clip(1 - ((yy - my) / (mw * 0.8)) ** 2, 0, 1)
    oy -= a * reg * ((nx * 1.7) ** 2) * mw * 0.32 - a * reg * mw * 0.10   # corners down, centre up: smile -> frown
    L = LIMBS[who]
    for (bx, by) in L["brows"]:
        bx, by, br = bx * s, by * s, L["brow_r"] * s
        d = np.sqrt((xx - bx) ** 2 + (yy - by) ** 2)
        wb = np.clip((br * 0.8 - d) / (br * 0.5), 0, 1); wb = wb * wb * (3 - 2 * wb)
        oy += a * wb * br * 0.38                                     # sample from below = move up
    out = _cv2.remap(base, xx + ox, yy + oy, _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_REPLICATE)
    return out

def _lids(img, rig, s, close):
    if close <= 0.02: return img
    pil = Image.fromarray(img, "RGBA"); d = ImageDraw.Draw(pil)
    for (ex, ey, rx, ry) in rig["eyes"]:
        ex, ey, rx, ry = ex * s, ey * s, rx * s * 1.12, ry * s * 1.25
        lid = Image.new("L", pil.size, 0); ImageDraw.Draw(lid).ellipse((ex - rx, ey - ry, ex + rx, ey + ry), fill=255)
        cut = Image.new("L", pil.size, 0)
        ImageDraw.Draw(cut).rectangle((ex - rx - 2, ey - ry - 2, ex + rx + 2, ey - ry + 2 * ry * close), fill=255)
        m = ImageChops.multiply(lid, cut).filter(ImageFilter.GaussianBlur(max(0.6, s * 1.2)))
        pil.paste(Image.new("RGBA", pil.size, rig["skin"] + (255,)), (0, 0), m)
        yl = ey - ry + 2 * ry * close
        d.arc((ex - rx * 0.95, yl - ry * 0.5, ex + rx * 0.95, yl + ry * 0.35), 15, 165, fill=(60, 36, 28), width=max(2, int(s * 4)))
    return np.array(pil)

def puppet(who, t, s, talk=0.0, seed=0, nod=0.0, tilt=0.0, arm=0.0, jump=0.0, look=None):
    """Body-only acting: mouth never moves. Emotion from MOODS drives posture, head, arms, lids and a baked sad face."""
    rig = RIGS[who]; L = LIMBS[who]
    mood, mk = mood_at(who, t)
    sad = mk if mood == "sad" else 0.0
    happy = mk if mood == "happy" else 0.0
    s100 = int(round(s * 100))
    base = _expr_sprite(who, s100, int(round(sad * 10)))
    h, w = base.shape[:2]
    # lids: normal blinks, heavier when sad
    blink = blink_amt(t, seed)
    close = max(1 - blink, 0.14 * sad)
    img = _lids(base, rig, s, close)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fx, fy = w / 2, h * 1.02
    # whole body: breathing + weight shift; happy = bouncier, sad = slumped & slow
    sp = 1.0 + 0.6 * happy - 0.35 * sad
    b = (0.006 + 0.004 * happy) * math.sin(t * 1.5 * sp + seed) - 0.012 * sad
    th = math.radians((0.8 + 0.8 * happy) * math.sin(t * 0.55 * sp + seed) + tilt * 0.15)
    dx, dy = xx - fx, yy - fy
    sx = fx + dx * math.cos(th) + dy * math.sin(th)
    sy = fy + (-dx * math.sin(th) + dy * math.cos(th)) / (1 + b)
    # head around the neck
    hx, hy, hr = [v * s for v in rig["head"]]; nx, ny = [v * s for v in rig["neck"]]
    dist = np.sqrt((xx - hx) ** 2 + (yy - hy) ** 2)
    wgt = np.clip((hr * 1.25 - dist) / (hr * 0.45), 0, 1) * np.clip((ny + hr * 0.15 - yy) / (hr * 0.3), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    ht = (2.4 * math.sin(t * 0.9 * sp + seed) + 1.1 * math.sin(t * 2.3 + seed * 2) + tilt
          + happy * 3.5 * math.sin(t * 3.1 + seed) + sad * (5.0 + 1.0 * math.sin(t * 0.7)))
    ht = math.radians(ht)
    hdy = (nod * 6 + 2.0 * math.sin(t * 1.9 * sp + seed) + happy * 5 * abs(math.sin(t * 3.1 + seed)) - sad * 10) * s
    ddx, ddy = xx - nx, yy - ny
    hsx = nx + ddx * math.cos(ht) + ddy * math.sin(ht)
    hsy = ny - ddx * math.sin(ht) + ddy * math.cos(ht) - hdy
    sx = sx + wgt * (hsx - xx); sy = sy + wgt * (hsy - yy)
    # arms / hands
    if "arm" in L:
        p0, p1, wid = L["arm"]
        p0 = (p0[0] * s, p0[1] * s); p1 = (p1[0] * s, p1[1] * s)
        if who == "logo":
            ang = arm + 3.0 * math.sin(t * 1.7 + seed) + happy * 7 * math.sin(t * 4.2)
        else:   # boy's free arm swings; happy = little waves, sad = hangs still
            ang = (3.5 * math.sin(t * 1.3 + seed)) * (1 - 0.7 * sad) + happy * 8 * math.sin(t * 4.5)
        ox, oy = _field_seg(xx, yy, p0, p1, wid * s, ang)
        sx += ox; sy += oy
    if "hand" in L:
        hx_, hy_, hr_ = L["hand"]
        hdx = 4 * math.sin(t * 1.1 + seed) * s
        hdy2 = (5 * math.sin(t * 1.6 + seed * 1.3) + happy * 9 * abs(math.sin(t * 5.0)) + sad * 8) * s
        ox, oy = _field_blob(xx, yy, hx_ * s, hy_ * s, hr_ * s, hdx, hdy2)
        sx += ox; sy += oy
    out = _cv2.remap(img, sx.astype(np.float32), (sy + jump).astype(np.float32), _cv2.INTER_LINEAR,
                     borderMode=_cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out, "RGBA")

# backgrounds: no wall board/frame
@lru_cache(maxsize=4)
def room_bg(kind):
    h = HALF
    yy = np.linspace(0, 1, h)[:, None, None]
    wall0, wall1 = np.array((62, 32, 22), np.float32), np.array((36, 19, 13), np.float32)
    arr = (wall0 + (wall1 - wall0) * yy).repeat(W, 1)
    im = Image.fromarray(np.uint8(arr)).convert("RGBA")
    if kind == "home":
        ImageDraw.Draw(im).polygon([(120, 0), (340, 0), (560, h), (180, h)], fill=(255, 220, 160, 16))
    g = glow(700, (130, 58, 32)); im.alpha_composite(g.resize((1200, 1200)), (-60, 160))
    return im

def cart_home(lt, t):
    """Mom and boy at home together, both happy — no flashcards."""
    c = scene("home")
    ImageDraw.Draw(c).rounded_rectangle((60, 840, 1020, 960), 40, fill=(110, 56, 46))
    m = puppet("mom", t, 0.62, seed=2, tilt=-4)
    place(c, m, 400, 555)
    b = puppet("boy", t, 0.62, seed=3)
    place(c, b, 730, 630)
    return c

PANELS.update({"home": cart_home})
