# ================= v14: Instagram music via VPN — expert in full / 50-50 / round frame, realistic phone UI scenes =================
PUNCH[:] = [(1.86, 1.04, 2.60), (47.02, 1.04, 48.0)]
CHIN_Y = 512.0                     # source px (480x854)
FULL_TOP = 1392                    # he leans in at the start: keep full-screen subtitles well under the chin
CIRCLE = (64, 1380, 350)           # x, y, diameter of the round expert frame (bottom-left, below every animation)
SPLIT_R = (0, HALF, W, HALF)

# ---------- expert geometry per layout: target rect, corner radius, source crop (centre-y, height) ----------
def _lay(kind):
    if kind == "full":
        ch = float(SH) - 120.0
        top = clamp(CHIN_Y - 0.585 * ch, 0, SH - ch)
        return dict(r=(0, 0, W, H), rad=0.0, cy=top + ch / 2, ch=ch, a=1.0, scr=0.0)
    if kind == "split":
        return dict(r=SPLIT_R, rad=0.0, cy=96 + 260.0, ch=520.0, a=1.0, scr=1.0)
    x, y, d = CIRCLE
    if kind == "circle":
        return dict(r=(x, y, d, d), rad=d / 2, cy=392.0, ch=380.0, a=1.0, scr=1.0)
    return dict(r=(x + d * 0.25, y + d * 0.25, d * 0.5, d * 0.5), rad=d / 4, cy=372.0, ch=320.0, a=0.0, scr=1.0)   # hidden

def _mixl(A, B, k):
    out = {}
    for key in A:
        out[key] = tuple(lerp(p, q, k) for p, q in zip(A[key], B[key])) if key == "r" else lerp(A[key], B[key], k)
    return out

def layout_now(t):
    si = seg_at(t); cur = SEG[si]; L = _lay(cur[3])
    if si > 0 and t - cur[0] < 0.8:
        k = clamp(spring(t - cur[0], w=11, z=0.8), 0, 1.03)
        return _mixl(_lay(SEG[si - 1][3]), L, k), t - cur[0]
    return L, 9.0

def draw_expert2(c, src, L, z):
    x, y, w_, h_ = L["r"]
    if L["a"] <= 0.01 or w_ < 8 or h_ < 8: return
    W_, H_ = int(round(w_)), int(round(h_))
    im, P_ = _padded(src)
    ch = L["ch"] / max(1.0, z); cw = ch * W_ / H_
    top = clamp(L["cy"] - ch / 2, 0, SH - ch)
    fr = im.resize((W_, H_), Image.BICUBIC, box=(P_ + SW / 2 - cw / 2, top, P_ + SW / 2 + cw / 2, top + ch)).convert("RGBA")
    rad = int(L["rad"])
    framed = rad > 2 or (W_ < W - 4 and H_ < H - 4 and y > 4)
    if rad > 2:
        pad = 50
        sh = Image.new("RGBA", (W_ + pad * 2, H_ + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 16, pad + W_, pad + H_ + 16), rad, fill=(0, 0, 0, 160))
        paste_alpha(c, sh.filter(ImageFilter.GaussianBlur(20)), x - pad, y - pad, L["a"])
        g = glow(int(W_ * 1.5), (124, 92, 255)); paste_alpha(c, g, x + W_ / 2 - g.width / 2, y + H_ / 2 - g.height / 2, 0.5 * L["a"])
        fr.putalpha(_rr_mask(W_, H_, rad))
    paste_alpha(c, fr, x, y, L["a"])
    if rad > 2:   # glass rim: gradient ring
        ring = Image.new("RGBA", (W_ + 16, H_ + 16), (0, 0, 0, 0))
        ImageDraw.Draw(ring).rounded_rectangle((3, 3, W_ + 12, H_ + 12), rad + 5, outline=(255, 255, 255, 190), width=5)
        ig = ig_gradient(max(W_, H_) + 16).resize(ring.size); ig.putalpha(ImageChops.multiply(ig.getchannel("A"), ring.getchannel("A")))
        paste_alpha(c, ig, x - 8, y - 8, L["a"])

# ---------- small UI helpers ----------
def F(w, s): return dfont(w, s)
def note_glyph(size, col=(255, 255, 255)):
    S2 = size * 3
    im = Image.new("RGBA", (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((S2 * 0.10, S2 * 0.62, S2 * 0.42, S2 * 0.88), fill=col); d.ellipse((S2 * 0.56, S2 * 0.52, S2 * 0.88, S2 * 0.78), fill=col)
    d.rectangle((S2 * 0.35, S2 * 0.14, S2 * 0.42, S2 * 0.76), fill=col); d.rectangle((S2 * 0.81, S2 * 0.06, S2 * 0.88, S2 * 0.66), fill=col)
    d.polygon([(S2 * 0.35, S2 * 0.14), (S2 * 0.88, S2 * 0.04), (S2 * 0.88, S2 * 0.20), (S2 * 0.35, S2 * 0.30)], fill=col)
    return im.resize((size, size), Image.LANCZOS)

def ripple(c, x, y, u, col=(255, 255, 255)):
    if not (0 <= u < 0.6): return
    r = int(18 + 70 * ease_out(u / 0.6))
    rg = Image.new("RGBA", (r * 2 + 4, r * 2 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(rg).ellipse((2, 2, r * 2 + 2, r * 2 + 2), fill=col + (int(90 * (1 - u / 0.6)),), outline=col + (int(220 * (1 - u / 0.6)),), width=4)
    paste_alpha(c, rg, x - r - 2, y - r - 2, 1)

def finger(c, x, y, a=1.0):
    """A soft fingertip dot that 'taps' the UI."""
    g = glow(90, (255, 255, 255)); paste_alpha(c, g, x - 45, y - 45, 0.55 * a)
    dot = Image.new("RGBA", (44, 44), (0, 0, 0, 0)); ImageDraw.Draw(dot).ellipse((2, 2, 42, 42), fill=(255, 255, 255, 200), outline=(255, 255, 255, 255), width=3)
    paste_alpha(c, dot, x - 22, y - 22, a)

@lru_cache(maxsize=8)
def cover(seed, size):
    rng = np.random.default_rng(seed)
    c0 = tuple(int(v) for v in rng.integers(60, 255, 3)); c1 = tuple(int(v) for v in rng.integers(20, 200, 3))
    im = _vgrad(size, size, c0, c1)
    d = ImageDraw.Draw(im)
    for j in range(3):
        r = rng.integers(size // 6, size // 2); cx, cy = rng.integers(0, size, 2)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(v) for v in rng.integers(80, 255, 3)) + (90,))
    m = _rr_mask(size, size, size // 7); im.putalpha(m)
    return im

PHONE_W, PHONE_H = 400, 820
def phone(c, cx, top, screen, k=1.0, a=1.0):
    """iPhone-style body with glass rim; `screen` is an RGBA (PHONE_W-24) x (PHONE_H-24) image."""
    if k <= 0.02: return
    body = Image.new("RGBA", (PHONE_W, PHONE_H), (0, 0, 0, 0)); d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, PHONE_W - 1, PHONE_H - 1), 64, fill=(24, 24, 30, 255))
    d.rounded_rectangle((2, 2, PHONE_W - 3, PHONE_H - 3), 62, outline=(150, 150, 170, 255), width=3)
    sc = screen.copy(); sc.putalpha(ImageChops.multiply(sc.getchannel("A"), _rr_mask(sc.width, sc.height, 52)))
    body.alpha_composite(sc, (12, 12))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((PHONE_W / 2 - 60, 26, PHONE_W / 2 + 60, 58), 16, fill=(10, 10, 12, 255))       # dynamic island
    sh = Image.new("RGBA", (PHONE_W + 120, PHONE_H + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((60, 80, 60 + PHONE_W, 80 + PHONE_H), 64, fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(26))
    W2, H2 = int(PHONE_W * k), int(PHONE_H * k)
    paste_alpha(c, sh.resize((int(sh.width * k), int(sh.height * k))), cx - sh.width * k / 2, top - 60 * k, a)
    g = glow(int(PHONE_W * 1.6), (124, 92, 255)); paste_alpha(c, g, cx - g.width / 2, top + H2 / 2 - g.height / 2, 0.45 * a)
    paste_alpha(c, body.resize((W2, H2), Image.LANCZOS), cx - W2 / 2, top, a)

SW_, SH_ = PHONE_W - 24, PHONE_H - 24
def status_bar(d, dark=False):
    col = WHITE if dark else (20, 20, 24)
    d.text((40, 40), "9:41", font=F("Black", 22), fill=col, anchor="lm")
    d.rounded_rectangle((SW_ - 70, 32, SW_ - 34, 48), 5, outline=col, width=2); d.rectangle((SW_ - 68, 34, SW_ - 44, 46), fill=col)

def ig_header(d, title):
    d.text((SW_ / 2, 92), title, font=F("Black", 26), fill=(20, 20, 24), anchor="mm")
    d.line([(26, 92), (40, 80)], fill=(20, 20, 24), width=3); d.line([(26, 92), (40, 104)], fill=(20, 20, 24), width=3)

# ---------- scenes (draw straight onto the 1080x1920 canvas) ----------
def sc_nomusic(c, lt, t):
    """Split: a post editor where 'Add music' is locked — then a free fix is promised."""
    k = spring(lt - 0.05, w=10, z=0.65)
    card = Image.new("RGBA", (880, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    card.alpha_composite(cover(3, 230), (30, 50))
    d.text((290, 70), "Yangi post", font=F("Black", 34), fill=WHITE, anchor="lm")
    rows = [("Odamlarni belgilash", 140), ("Joylashuv qo'shish", 200), ("Musiqa qo'shish", 260)]
    for txt, y in rows:
        d.text((290, y), txt, font=F("Medium", 28), fill=(235, 232, 250), anchor="lm")
        d.line([(290, y + 26), (850, y + 26)], fill=(255, 255, 255, 40), width=1)
    card.alpha_composite(note_glyph(34, (235, 232, 250)), (560, 243))
    locked = lt < 0.96
    if locked:
        card.alpha_composite(svg_icon("lock", 36, "#fca5a5", 2.2), (800, 242))
    else:
        card.alpha_composite(svg_icon("circle-check", 38, "#86efac", 2.2), (798, 241))
    sh = 8 * math.sin(lt * 40) * (1 - clamp((lt - 0.25) / 0.4)) if 0.15 < lt < 0.7 else 0
    glass(c, 540 + sh, 755 + (1 - k) * 60, 880, 330, tint=(190, 185, 255), k=k, r=36, alpha=(0.20, 0.10), content=card, glow_col=(124, 92, 255))
    if 0.18 < lt < 1.0:
        gpill(c, 780, 545, "Mavjud emas", tint=TINTS["red"], size=28, k=spring(lt - 0.18, w=12, z=0.5), center=True, alpha=(0.6, 0.4))
    if lt > 0.96:
        gpill(c, 780, 545, "Tekin yechim bor", tint=TINTS["green"], size=28, k=spring(lt - 0.96, w=12, z=0.5), center=True, alpha=(0.6, 0.4))

@lru_cache(maxsize=4)
def app_shot(w_):
    im = Image.open(os.path.join(HERE, "av", "app.jpg")).convert("RGBA")
    h_ = int(im.height * w_ / im.width)
    im = im.resize((w_, h_), Image.LANCZOS); im.putalpha(_rr_mask(w_, h_, 34))
    return im

def sc_store(c, lt, t):
    """Split: Play Market / App Store, then the real App Store page of JumpJump VPN (the user's screenshot)."""
    move = ease_io(clamp((lt - 1.9) / 0.5))
    if move < 1:
        for j, (kind, x) in enumerate((("googleplay", 360), ("appstore", 720))):
            st = 0.1 + j * 0.55
            if lt < st: continue
            k = spring(lt - st, w=10, z=0.55)
            col = (52, 168, 83) if kind == "googleplay" else (10, 132, 255)
            glass(c, x, 760 - 200 * move, 260, 260, tint=col, k=k * (1 - 0.5 * move), glyph=svg_icon("brand_" + kind, 256), glyph_k=0.5,
                  alpha=(0.62, 0.42), a=clamp(k * 1.6) * (1 - move), glow_col=col, shine=(lt - st - 0.3) / 0.7)
            nm = "Play Market" if kind == "googleplay" else "App Store"
            if move < 0.5: gpill(c, x, 925, nm, size=26, k=k, center=True, a=1 - move * 2)
    if lt > 2.0:
        k = spring(lt - 2.08, w=10, z=0.62)
        shot = app_shot(580)
        pulse = 1 + 0.03 * math.sin((lt - 4.5) * 8) if lt > 4.5 else 1
        kk = k * pulse
        sh = Image.new("RGBA", (shot.width + 100, shot.height + 100), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((50, 66, 50 + shot.width, 66 + shot.height), 34, fill=(0, 0, 0, 170))
        paste_alpha(c, sh.filter(ImageFilter.GaussianBlur(24)), 540 - sh.width * kk / 2, 752 - sh.height * kk / 2, clamp(k * 2), kk)
        g = glow(760, (56, 132, 255)); paste_alpha(c, g, 540 - 380, 752 - 380, 0.55 * clamp(k * 2))
        paste_alpha(c, shot, 540 - shot.width * kk / 2, 752 - shot.height * kk / 2, clamp(k * 2), kk)
        # "Download" button press (the blue button sits at ~(36%, 58%) of the shot)
        bx, by = 540 - shot.width / 2 + shot.width * 0.452, 752 - shot.height / 2 + shot.height * 0.58
        if lt > 3.6:
            u = lt - 3.74
            if u < 0.9: finger(c, bx, by, clamp(u / 0.15) * (1 - clamp((u - 0.6) / 0.3)))
            ripple(c, bx, by, u, (120, 190, 255))
        if lt > 4.5:   # "the picture is at the top" — arrow bouncing up at the card
            gicon(c, "arrow-up", 905, 640 - 14 * abs(math.sin(lt * 5)), 110, "blue", 4.5, lt, glyph_k=0.55)

def vpn_screen(lt):
    sc = _vgrad(SW_, SH_, (18, 26, 64), (8, 12, 30)); d = ImageDraw.Draw(sc)
    status_bar(d, dark=True)
    # brand mark: the J from the icon, as a gradient capsule
    jm = Image.new("RGBA", (60, 60), (0, 0, 0, 0)); ImageDraw.Draw(jm).rounded_rectangle((18, 4, 40, 50), 11, fill=255)
    jg = _vgrad(60, 60, (88, 101, 242), (94, 234, 212)); jg.putalpha(jm.getchannel("A")); sc.alpha_composite(jg, (32, 76))
    d.text((104, 106), "JumpJump VPN", font=F("Black", 26), fill=WHITE, anchor="lm")
    if lt < 2.1:     # terms dialog
        d.rounded_rectangle((26, 200, SW_ - 26, 600), 30, fill=(255, 255, 255, 236))
        d.text((SW_ / 2, 246), "Foydalanish shartlari", font=F("Black", 26), fill=(20, 22, 40), anchor="mm")
        for j in range(6):
            d.rounded_rectangle((56, 290 + j * 30, SW_ - 56 - (60 if j % 2 else 0), 302 + j * 30), 6, fill=(200, 204, 220))
        pressed = 1.45 < lt < 1.75
        d.rounded_rectangle((56, 500, SW_ - 56, 566), 33, fill=(64, 100, 255) if not pressed else (40, 70, 210))
        d.text((SW_ / 2, 533), "Qabul qilaman", font=F("Black", 25), fill=WHITE, anchor="mm")
        return sc, (12 + SW_ / 2, 12 + 533)
    connected = lt > 5.9
    # big connect button
    cx, cy, r = SW_ / 2, 330, 110
    col = (52, 211, 153) if connected else (88, 101, 242)
    for j in range(3):
        rr = r + 22 + j * 18 + (6 * math.sin(lt * 4 + j) if connected else 0)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=col + (60 - j * 18,), width=3)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    sc.alpha_composite(svg_icon("power", 96, "#ffffff", 2.4), (int(cx - 48), int(cy - 48)))
    d.text((cx, cy + r + 50), "Ulandi" if connected else "Ulanmagan", font=F("Black", 28), fill=(167, 243, 208) if connected else (200, 205, 240), anchor="mm")
    # server row
    d.rounded_rectangle((26, 560, SW_ - 26, 640), 22, fill=(255, 255, 255, 26))
    sc.alpha_composite(svg_icon("globe", 34, "#c7d2fe", 2), (46, 583))
    srv = "New York · Free" if lt > 4.95 else "Server tanlang"
    d.text((96, 600), srv, font=F("Black", 24), fill=WHITE, anchor="lm")
    # server sheet
    if 3.0 < lt < 5.8:
        u = ease_out(clamp((lt - 3.08) / 0.35)) * (1 - ease_in(clamp((lt - 5.45) / 0.3)))
        y0 = SH_ - 520 * u
        d.rounded_rectangle((0, y0, SW_, SH_ + 40), 34, fill=(250, 250, 255, 250))
        d.text((SW_ / 2, y0 + 44), "Server", font=F("Black", 26), fill=(20, 22, 40), anchor="mm")
        rows = [("Avtomatik", "Free"), ("New York", "Free"), ("London", "Premium"), ("Tokyo", "Premium"), ("Frankfurt", "Premium")]
        for j, (nm, tier) in enumerate(rows):
            yy = y0 + 90 + j * 76
            sel = nm == "New York" and lt > 4.95
            d.rounded_rectangle((20, yy, SW_ - 20, yy + 64), 18, fill=(225, 232, 255) if sel else (242, 243, 248))
            d.text((44, yy + 32), nm, font=F("Black", 23), fill=(20, 22, 40), anchor="lm")
            tc = (34, 160, 90) if tier == "Free" else (150, 150, 170)
            d.text((SW_ - 44, yy + 32), tier, font=F("Medium", 20), fill=tc, anchor="rm")
            if sel: sc.alpha_composite(svg_icon("circle-check", 26, "#4f46e5", 2.4), (int(SW_ - 160), int(yy + 19)))
        return sc, (12 + SW_ / 2, 12 + y0 + 90 + 76 + 32)
    return sc, (12 + cx, 12 + cy)

def sc_vpn(c, lt, t):
    """Round-frame layout: the VPN app — accept terms, pick New York (free), connect."""
    k = spring(lt - 0.05, w=10, z=0.65)
    scr, tap = vpn_screen(lt)
    cx, top = 640, 600
    phone(c, cx, top + (1 - k) * 80, scr, k=1.0, a=clamp(k * 2))
    ox, oy = cx - PHONE_W / 2, top
    for t0 in (1.45, 4.92, 5.6):
        u = lt - t0
        if -0.25 < u < 0.7:
            fx, fy = (ox + tap[0], oy + tap[1]) if t0 != 5.6 else (ox + 12 + SW_ / 2, oy + 12 + 330)
            finger(c, fx, fy, clamp((u + 0.25) / 0.2) * (1 - clamp((u - 0.4) / 0.3)))
            ripple(c, fx, fy, u)
    if lt > 1.6:
        gicon(c, "shield-check", 200, 760, 140, "green", 1.6, lt, t=t, bob=5)
    if lt > 4.95:
        gpill(c, 230, 940, "New York · Free", tint=TINTS["blue"], size=28, k=spring(lt - 4.95, w=12, z=0.5), center=True, alpha=(0.55, 0.35))

def sc_timer(c, lt, t):
    """Split: about 2 hours — a glass clock — then straight into Instagram."""
    k = spring(lt - 0.05, w=10, z=0.6)
    cx, cy, R = 360, 755, 165
    lay = Image.new("RGBA", (R * 2, R * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    prog = ease_io(clamp((lt - 1.5) / 3.0))
    d.arc((14, 14, R * 2 - 14, R * 2 - 14), -90, -90 + 360 * prog, fill=(250, 204, 21), width=14)
    d.text((R, R - 16), "≈ 2", font=F("Black", 92), fill=WHITE, anchor="mm")
    d.text((R, R + 62), "soat", font=F("Medium", 36), fill=(230, 226, 250), anchor="mm")
    glass(c, cx, cy, R * 2, R * 2, tint=(250, 204, 21), k=k, r=R, alpha=(0.30, 0.16), content=lay, glow_col=(250, 204, 21), shine=(lt - 0.4) / 0.8)
    if lt > 2.9:
        u = clamp((lt - 2.9) / 0.6)
        for j in range(4):
            q = u - j * 0.15
            if 0 < q < 1:
                g = glow(60, (214, 41, 118)).resize((40, 40)); paste_alpha(c, g, lerp(560, 690, q) - 20, 755 - 20, 1 - j * 0.2)
        brand(c, "instagram", 820, 755, 290, 3.6, lt, t=t, bob=5, shine=(lt - 3.9) / 0.7)

def music_screen(lt):
    sc = Image.new("RGBA", (SW_, SH_), (255, 255, 255, 255)); d = ImageDraw.Draw(sc)
    status_bar(d); ig_header(d, "Musiqa")
    d.rounded_rectangle((22, 130, SW_ - 22, 180), 16, fill=(239, 239, 242))
    sc.alpha_composite(svg_icon("search", 26, "#8e8e93", 2.2), (38, 142))
    q = "Sevimli qo'shig'im"
    n = int(clamp((lt - 0.5) / 1.1) * len(q))
    if n > 0: d.text((76, 155), q[:n], font=F("Medium", 22), fill=(20, 20, 24), anchor="lm")
    else: d.text((76, 155), "Musiqa qidirish", font=F("Medium", 22), fill=(142, 142, 147), anchor="lm")
    tab = 1 if lt > 2.3 else 0
    for j, nm in enumerate(("Qidiruv", "Siz uchun", "Trend")):
        x = 40 + j * 118
        d.text((x, 216), nm, font=F("Black", 21), fill=(20, 20, 24) if j == tab else (150, 150, 156), anchor="lm")
        if j == tab: d.rounded_rectangle((x, 232, x + F("Black", 21).getlength(nm), 236), 2, fill=(20, 20, 24))
    songs = [("Yulduzlar", "Sevara", "2:48"), ("Bahor", "Shahzoda", "3:12"), ("Orzular", "Ozodbek", "2:31"),
             ("Tun", "Lola", "3:05"), ("Yo'l", "Jasur", "2:56"), ("Shamol", "Rayhon", "3:20")]
    if tab == 0: songs = songs[:2]
    sel = 2 if lt > 4.9 else -1
    for j, (ti, ar, du) in enumerate(songs):
        y = 262 + j * 84
        if j == sel: d.rounded_rectangle((12, y - 8, SW_ - 12, y + 72), 16, fill=(237, 233, 255))
        sc.alpha_composite(cover(10 + j, 64), (24, y))
        d.text((104, y + 20), ti, font=F("Black", 22), fill=(20, 20, 24), anchor="lm")
        d.text((104, y + 46), ar + " · " + du, font=F("Medium", 18), fill=(130, 130, 136), anchor="lm")
        if j == sel: sc.alpha_composite(svg_icon("circle-check", 30, "#6d28d9", 2.4), (SW_ - 64, y + 17))
        else: sc.alpha_composite(svg_icon("play", 24, "#3a3a3c", 2.2), (SW_ - 60, y + 20))
    return sc, (12 + SW_ / 2, 12 + 262 + 2 * 84 + 32)

def sc_music(c, lt, t):
    """Round-frame layout: Instagram's music picker — search your own track or pick a recommended one."""
    k = spring(lt - 0.05, w=10, z=0.65)
    scr, tap = music_screen(lt)
    cx, top = 640, 600
    phone(c, cx, top + (1 - k) * 80, scr, a=clamp(k * 2))
    u = lt - 4.9
    if -0.25 < u < 0.7:
        fx, fy = cx - PHONE_W / 2 + tap[0], top + tap[1]
        finger(c, fx, fy, clamp((u + 0.25) / 0.2) * (1 - clamp((u - 0.4) / 0.3))); ripple(c, fx, fy, u)
    gicon(c, "search", 205, 700, 120, "blue", 0.5, lt, t=t, bob=5)
    if lt > 2.3:
        gicon(c, "sparkles", 205, 860, 120, "pink", 2.3, lt, t=t, bob=5, ph=1)
    if lt > 4.9:
        glass(c, 220, 1010, 150, 150, tint=TINTS["violet"], k=spring(lt - 4.9, w=12, z=0.5), glyph=note_glyph(256), glyph_k=0.5, alpha=(0.5, 0.3),
              glow_col=TINTS["violet"])

def post_card(lay, x, y, w_, song=True, seed=5):
    d = ImageDraw.Draw(lay)
    d.ellipse((x, y, x + 54, y + 54), fill=(200, 200, 210)); lay.alpha_composite(svg_icon("user", 34, "#ffffff", 2), (x + 10, y + 10))
    d.text((x + 70, y + 16), "sizning_sahifa", font=F("Black", 22), fill=WHITE, anchor="lm")
    if song:
        lay.alpha_composite(note_glyph(22, (230, 226, 250)), (x + 70, y + 32))
        d.text((x + 98, y + 43), "Orzular · Ozodbek", font=F("Medium", 19), fill=(230, 226, 250), anchor="lm")
    img = cover(seed, w_); lay.alpha_composite(img, (x, y + 70))

def sc_publish(c, lt, t):
    """Split: preview with the music sticker, tap Share, 'posted' toast."""
    k = spring(lt - 0.05, w=10, z=0.62)
    lay = Image.new("RGBA", (860, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    lay.alpha_composite(cover(21, 270), (30, 36))
    st = Image.new("RGBA", (220, 56), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle((0, 0, 219, 55), 16, fill=(255, 255, 255, 235)); st.alpha_composite(note_glyph(30, (109, 40, 217)), (12, 13))
    sd.text((52, 28), "Orzular", font=F("Black", 22), fill=(30, 20, 60), anchor="lm")
    lay.alpha_composite(st, (55, 230))
    d.text((340, 70), "Post tayyor", font=F("Black", 34), fill=WHITE, anchor="lm")
    d.text((340, 120), "Musiqa: Orzular · Ozodbek", font=F("Medium", 26), fill=(225, 220, 250), anchor="lm")
    pressed = 1.9 < lt < 2.2
    d.rounded_rectangle((340, 210, 820, 286), 38, fill=(0, 149, 246) if not pressed else (0, 110, 200))
    d.text((580, 248), "Ulashish", font=F("Black", 30), fill=WHITE, anchor="mm")
    glass(c, 540, 755 + (1 - k) * 60, 860, 340, tint=(190, 185, 255), k=k, r=36, alpha=(0.20, 0.10), content=lay, glow_col=(124, 92, 255))
    bx, by = 540 - 430 + 580, 755 - 170 + 248
    u = lt - 1.94
    if -0.25 < u < 0.7: finger(c, bx, by, clamp((u + 0.25) / 0.2) * (1 - clamp((u - 0.4) / 0.3))); ripple(c, bx, by, u)
    if lt > 2.4:
        gpill(c, 540, 575, "Post joylandi", tint=TINTS["green"], size=30, k=spring(lt - 2.4, w=12, z=0.5), center=True, alpha=(0.62, 0.42))

def feed_screen(lt):
    sc = Image.new("RGBA", (SW_, SH_), (0, 0, 0, 255)); d = ImageDraw.Draw(sc)
    status_bar(d, dark=True)
    d.text((28, 100), "Instagram", font=F("Black", 34), fill=WHITE, anchor="lm")
    post_card(sc, 18, 150, SW_ - 36, song=True, seed=21)
    y = 150 + 70 + SW_ - 36 + 20
    for j, ic in enumerate(("heart", "message-circle", "send")):
        sc.alpha_composite(svg_icon(ic, 34, "#ffffff", 2), (22 + j * 56, int(y)))
    d.text((24, y + 64), "1 284 ta yoqtirish", font=F("Black", 21), fill=WHITE, anchor="lm")
    if lt > 4.6:   # glow on the music line
        a = clamp((lt - 4.6) / 0.3)
        d.rounded_rectangle((80, 180, 330, 208), 12, outline=(196, 181, 253, int(255 * a)), width=3)
    return sc

def sc_persist(c, lt, t):
    """Round-frame layout: the feed later, VPN off — the music line is still on the post."""
    k = spring(lt - 0.05, w=10, z=0.65)
    cx, top = 640, 600
    phone(c, cx, top + (1 - k) * 80, feed_screen(lt), a=clamp(k * 2))
    if lt > 1.2:
        lay = Image.new("RGBA", (260, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        lay.alpha_composite(svg_icon("power", 40, "#fecaca", 2.2), (24, 20))
        d.text((80, 40), "VPN o'chiq", font=F("Black", 28), fill=WHITE, anchor="lm")
        glass(c, 215, 720, 260, 80, tint=TINTS["red"], k=spring(lt - 1.2, w=12, z=0.5), r=40, alpha=(0.55, 0.35), content=lay)
    if lt > 4.6:
        glass(c, 215, 880, 170, 170, tint=TINTS["violet"], k=spring(lt - 4.6, w=12, z=0.45), glyph=note_glyph(256), glyph_k=0.5,
              alpha=(0.5, 0.3), glow_col=TINTS["violet"], shine=(lt - 4.9) / 0.6)
        gicon(c, "circle-check", 285, 815, 70, "green", 4.75, lt, w=13, z=0.45, glyph_k=0.62, glow_on=False)

def sc_edit(c, lt, t):
    """Split: old posts → '...' → Edit → Add music → done; every old post gets a note badge."""
    k = spring(lt - 0.05, w=10, z=0.62)
    xs = (230, 540, 850)
    for j, x in enumerate(xs):
        kk = spring(lt - 0.05 - j * 0.12, w=11, z=0.6)
        img = cover(30 + j, 250)
        paste_alpha(c, with_shadow(img, 14, 14), x - 125 - 28, 640 - 28 + (1 - kk) * 60, clamp(kk * 2))
        if lt > 5.9 + j * 0.15:
            glass(c, x + 92, 666, 66, 66, tint=TINTS["violet"], k=spring(lt - 5.9 - j * 0.15, w=13, z=0.45), glyph=note_glyph(128), glyph_k=0.6,
                  alpha=(0.62, 0.42))
    # tap the middle post, menu appears
    u = lt - 1.25
    if -0.25 < u < 0.7: finger(c, 540, 760, clamp((u + 0.25) / 0.2) * (1 - clamp((u - 0.4) / 0.3))); ripple(c, 540, 760, u)
    if 1.5 < lt < 5.9:
        mk = spring(lt - 1.5, w=12, z=0.6) * (1 - ease_in(clamp((lt - 5.6) / 0.3)))
        lay = Image.new("RGBA", (420, 250), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        items = [("pencil", "Tahrirlash"), ("music", "Musiqa qo'shish"), ("circle-check", "Saqlash")]
        for j, (ic, nm) in enumerate(items):
            y = 22 + j * 76
            on = (j == 0 and 3.3 < lt < 4.6) or (j == 1 and 4.6 < lt < 5.4) or (j == 2 and lt > 5.4)
            if on: d.rounded_rectangle((12, y - 6, 408, y + 62), 18, fill=(255, 255, 255, 40))
            if ic == "music": lay.alpha_composite(note_glyph(36), (30, y + 10))
            else: lay.alpha_composite(svg_icon(ic, 36, "#ffffff", 2), (30, y + 10))
            d.text((86, y + 28), nm, font=F("Black", 28), fill=WHITE, anchor="lm")
        glass(c, 700, 810, 420, 250, tint=(124, 92, 255), k=mk, r=30, alpha=(0.55, 0.35), content=lay, glow_col=(124, 92, 255))
    if lt > 5.9:
        gpill(c, 540, 905, "Musiqa qo'shildi", tint=TINTS["green"], size=30, k=spring(lt - 5.9, w=12, z=0.5), center=True, alpha=(0.62, 0.42))

SCN = {"nomusic": sc_nomusic, "store": sc_store, "vpn": sc_vpn, "timer": sc_timer, "music": sc_music,
       "publish": sc_publish, "persist": sc_persist, "edit": sc_edit}

def scene_now(t):
    for a, b, name in story.SCENES:
        if a <= t < b: return name, a, b
    return None, 0, 0

END_ICONS = [(47.02, "heart", "pink", "L"), (49.04, "send", "blue", "R")]

def render(i, src):
    t = i / FPS
    _T_NOW[0] = t
    c = mesh_full(t)
    L, since = layout_now(t)
    name, a, b = scene_now(t)
    if name:
        lay = c.copy()                      # glass frosts what is behind it, so draw on a real copy
        SCN[name](lay, t - a, t)
        fade = clamp((t - a) / 0.25) * (1 - clamp((t - (b - 0.2)) / 0.2))
        c = lay if fade >= 0.999 else Image.blend(c, lay, fade)
    si = seg_at(t)
    z = full_zoom(t, 1.0) if SEG[si][3] == "full" else 1.0
    draw_expert2(c, src, L, z)
    if SEG[si][3] == "split" or (since < 0.8 and SEG[si - 1][3] == "split"):
        y = int(L["r"][1]) if SEG[si][3] == "split" else HALF
        sh = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        sh.putalpha(Image.fromarray(np.repeat((np.linspace(0, 1, 40) ** 2 * 110)[:, None], W, 1).astype(np.uint8)))
        c.alpha_composite(sh, (0, max(0, y - 40)))
        ImageDraw.Draw(c).line((0, y, W, y), fill=(200, 190, 255, 90), width=2)
    if SEG[si][3] == "full":
        full = clamp(since / 0.6) if since < 0.8 else 1.0
        s_ = SCRIM if full >= 0.999 else Image.fromarray(np.dstack([np.array(SCRIM)[..., :3], (np.array(SCRIM)[..., 3] * full).astype(np.uint8)]))
        c.alpha_composite(s_)
        for t0, ic, tint, side in END_ICONS:
            if t >= t0:
                gicon(c, ic, 120 if side == "L" else W - 120, 1180 + 8 * math.sin(t * 1.7), 170, tint, t0, t, glyph_k=0.55, shine=(t - t0 - 0.3) / 0.7)
    draw_captions(c, t)
    return c.convert("RGB")
