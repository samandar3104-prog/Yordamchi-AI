# ================= v13: motion-first layout — full-height animation stage, expert full / glass card / hidden =================
PUNCH[:] = [(1.70, 1.05, 2.70), (41.20, 1.04, 42.40)]

@lru_cache(maxsize=1)
def _mesh_full_parts():
    base = np.zeros((H, W, 3), np.float32)
    yy = np.linspace(0, 1, H)[:, None]
    base[:] = (np.array((9, 10, 24)) * (1 - yy[..., None]) + np.array((16, 12, 34)) * yy[..., None])
    blobs = []
    for col, r in (((96, 70, 240), 640), ((40, 120, 255), 560), ((210, 70, 160), 480), ((20, 170, 160), 420), ((120, 80, 255), 520)):
        yy2, xx2 = np.mgrid[0:r * 2, 0:r * 2]
        d = np.clip(1 - np.hypot(xx2 - r, yy2 - r) / r, 0, 1) ** 2.2
        blobs.append(np.array(col, np.float32) * d[..., None])
    return base, blobs

def mesh_full(t):
    base, blobs = _mesh_full_parts()
    out = base.copy()
    paths = [(220, 700, 0.21, 0.0), (880, 520, 0.17, 1.7), (640, 1250, 0.23, 3.1), (120, 300, 0.19, 4.4), (900, 1600, 0.15, 2.2)]
    for g, (x0, y0, sp, ph) in zip(blobs, paths):
        r = g.shape[0] // 2
        cx = int(x0 + 140 * math.sin(t * sp + ph)); cy = int(y0 + 110 * math.cos(t * sp * 1.3 + ph))
        xa, ya = max(0, cx - r), max(0, cy - r); xb, yb = min(W, cx + r), min(H, cy + r)
        if xb <= xa or yb <= ya: continue
        out[ya:yb, xa:xb] += g[ya - (cy - r):yb - (cy - r), xa - (cx - r):xb - (cx - r)] * 0.5
    return Image.fromarray(np.uint8(np.clip(out, 0, 255))).convert("RGBA")

# ---------- layout states ----------
CARD = (330, 1236, 420, 540)        # x, y, w, h of the expert glass card (bottom centre, below all animation)
FULL_R = (0, 0, W, H)
STAGE = {"vo": (1050, 1.24), "card": (905, 1.16)}   # animation stage centre-y and scale per layout

def _layout_vec(seg):
    a, b, lay, kind, z = seg
    if lay == "full": return dict(ex=FULL_R, ea=1.0, full=1.0, sy=1000, ss=1.22, sa=0.0)
    if kind == "card": return dict(ex=CARD, ea=1.0, full=0.0, sy=STAGE["card"][0], ss=STAGE["card"][1], sa=1.0)
    cx, cy, cw, chh = CARD
    return dict(ex=(cx + cw * 0.2, cy + chh * 0.25, cw * 0.6, chh * 0.6), ea=0.0, full=0.0, sy=STAGE["vo"][0], ss=STAGE["vo"][1], sa=1.0)

def _mix(A, B, k):
    out = {}
    for key in A:
        if key == "ex": out[key] = tuple(lerp(p, q, k) for p, q in zip(A[key], B[key]))
        else: out[key] = lerp(A[key], B[key], k)
    return out

def layout_at(t):
    si = seg_at(t); cur = SEG[si]; L = _layout_vec(cur)
    if si > 0 and t - cur[0] < 0.9:
        k = spring(t - cur[0], w=10, z=0.75)
        return _mix(_layout_vec(SEG[si - 1]), L, clamp(k, 0, 1.05)), True
    return L, False

def scene_at(t):
    for a, b, name in story.SCENES:
        if a <= t < b: return name, a
    return None, 0

def _full_box(z):
    """Source box for full screen (chin-anchored zoom: face high, subtitles on the chest)."""
    im_h = float(SH) - 120.0
    ch = im_h / max(1.0, z); cw = ch * W / H
    top = clamp(546.0 - 0.585 * ch, 0, SH - ch)
    return (SW / 2 - cw / 2, top, cw, ch)

def _card_box(w_, h_):
    ch = 560.0; cw = ch * w_ / h_
    return (SW / 2 - cw / 2, 92.0, cw, ch)

def draw_expert(c, src, rect, ea, fullness, z):
    x, y, w_, h_ = rect
    if ea <= 0.01 or w_ < 8: return
    fb = _full_box(z); cb = _card_box(CARD[2], CARD[3])
    bx = tuple(lerp(p, q, fullness) for p, q in zip(cb, fb))
    im, P_ = _padded(src)
    W_, H_ = int(w_), int(h_)
    sx, sy, sw, sh_ = bx
    # keep the aspect of the target rect
    sw = sh_ * W_ / H_
    sx = SW / 2 - sw / 2
    fr = im.resize((W_, H_), Image.BICUBIC, box=(P_ + sx, sy, P_ + sx + sw, sy + sh_)).convert("RGBA")
    r = int(lerp(48, 0, fullness))
    if fullness < 0.999:
        # shadow + glow + glass rim
        pad = 40
        sh = Image.new("RGBA", (W_ + pad * 2, H_ + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 18, pad + W_, pad + H_ + 18), r, fill=(0, 0, 0, 150))
        paste_alpha(c, sh.filter(ImageFilter.GaussianBlur(22)), x - pad, y - pad, ea * (1 - fullness))
        g = glow(int(max(W_, H_) * 1.2), (124, 92, 255)); paste_alpha(c, g, x + W_ / 2 - g.width / 2, y + H_ / 2 - g.height / 2, 0.45 * ea * (1 - fullness))
        m = _rr_mask(W_, H_, max(1, r)); fr.putalpha(m)
    paste_alpha(c, fr, x, y, ea)
    if fullness < 0.999:
        bl = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        ImageDraw.Draw(bl).rounded_rectangle((1, 1, W_ - 2, H_ - 2), max(1, r), outline=(255, 255, 255, 150), width=3)
        paste_alpha(c, bl, x, y, ea * (1 - fullness))

def draw_stage(c, t, cy, s, a):
    if a <= 0.01: return
    name, t0 = scene_at(t)
    if not name: return
    pim = PANELS[name](t - t0, t)
    reg = pim.crop((0, 500, W, HALF))                      # the animation area of the panel (captions live elsewhere)
    nw, nh = int(W * s), int(reg.height * s)
    reg = reg.resize((nw, nh), Image.BICUBIC).crop(((nw - W) // 2, 0, (nw - W) // 2 + W, nh))
    fm = np.ones((nh,), np.float32)
    fd = 110
    fm[:fd] = np.linspace(0, 1, fd) ** 1.5; fm[-fd:] = np.linspace(1, 0, fd) ** 1.5
    al = (np.asarray(reg.getchannel("A"), np.float32) * fm[:, None]).astype(np.uint8)
    reg.putalpha(Image.fromarray(al))
    paste_alpha(c, reg, 0, cy - nh / 2, a)

def render(i, src):
    t = i / FPS
    _T_NOW[0] = t
    c = mesh_full(t)
    Lv, moving = layout_at(t)
    si = seg_at(t); a, b, lay, kind, zb = SEG[si]
    draw_stage(c, t, Lv["sy"], Lv["ss"], Lv["sa"])
    z = full_zoom(t, zb) if lay == "full" else 1.0
    draw_expert(c, src, Lv["ex"], Lv["ea"], Lv["full"], z)
    if Lv["full"] > 0.02:
        s_ = SCRIM if Lv["full"] >= 0.999 else Image.fromarray(np.dstack([np.array(SCRIM)[..., :3], (np.array(SCRIM)[..., 3] * Lv["full"]).astype(np.uint8)]))
        c.alpha_composite(s_)
    if moving:   # quick light flash on layout change
        u = t - a
        if u < 0.25: c.alpha_composite(Image.new("RGBA", (W, H), (200, 190, 255, int(60 * (1 - u / 0.25)))))
    draw_captions(c, t)
    return c.convert("RGB")
