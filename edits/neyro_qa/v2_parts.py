# ================= v2 overrides =================
import os
HERE = os.path.dirname(os.path.abspath(__file__))
WHITE = (255, 255, 255)
GREEN = (98, 168, 88)

# ---------- adults ----------
def adult(d, cx, cy, s, t, style, mood="neutral", point=None, blink_t=()):
    """style: mom (light scarf), teacher (bun hair, glasses), doc (navy hijab, white coat)."""
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    coat = {"mom": (196, 120, 150), "teacher": (70, 130, 110), "doc": (244, 244, 246)}[style]
    d.rounded_rectangle((X - S(130), Y + S(100), X + S(130), Y + S(420)), int(S(80)), fill=coat)
    if style == "doc":
        d.polygon([(X - S(40), Y + S(100)), (X + S(40), Y + S(100)), (X, Y + S(190))], fill=(40, 60, 110))
        d.line([(X, Y + S(190)), (X, Y + S(400))], fill=(210, 210, 216), width=int(S(4)))
        d.rounded_rectangle((X + S(40), Y + S(200), X + S(96), Y + S(232)), int(S(6)), fill=(80, 130, 200))
        d.arc((X - S(60), Y + S(110), X + S(20), Y + S(230)), 90, 250, fill=(60, 60, 70), width=int(S(6)))
    if style in ("mom", "doc"):
        sc = (232, 214, 196) if style == "mom" else (40, 60, 110)
        d.ellipse((X - S(110), Y - S(124), X + S(110), Y + S(136)), fill=sc)
        d.ellipse((X - S(76), Y - S(84), X + S(76), Y + S(92)), fill=SKIN)
    else:
        d.ellipse((X - S(40), Y - S(170), X + S(40), Y - S(96)), fill=HAIR)
        d.ellipse((X - S(88), Y - S(100), X + S(88), Y + S(96)), fill=SKIN)
        d.chord((X - S(92), Y - S(112), X + S(92), Y + S(30)), 180, 360, fill=HAIR)
    bl = 1.0
    for bt in blink_t:
        if bt <= t < bt + 0.16: bl = abs(math.cos((t - bt) / 0.16 * math.pi))
    for sx in (-1, 1):
        ex, ey = X + sx * S(30), Y + S(8)
        d.ellipse((ex - S(9), ey - max(S(2), S(12) * bl), ex + S(9), ey + max(S(2), S(12) * bl)), fill=HAIR)
        if style == "teacher":
            d.ellipse((ex - S(22), ey - S(18), ex + S(22), ey + S(18)), outline=(60, 50, 40), width=int(S(4)))
        tilt = {"angry": -12, "neutral": 0, "kind": 4}[mood]
        d.line([(ex - S(15), ey - S(26) + S(tilt * sx * 0.5)), (ex + S(15), ey - S(26) - S(tilt * sx * 0.5))], fill=HAIR, width=int(S(6)))
    if mood == "angry":
        op = 0.5 + 0.5 * abs(math.sin(t * 9))
        d.ellipse((X - S(18), Y + S(46), X + S(18), Y + S(46) + S(26) * op + S(4)), fill=(150, 60, 50))
    elif mood == "kind":
        d.arc((X - S(26), Y + S(36), X + S(26), Y + S(70)), 20, 160, fill=(170, 60, 60), width=int(S(6)))
    else:
        op = abs(math.sin(t * 10)) if style == "mom" else 0
        d.ellipse((X - S(16), Y + S(50), X + S(16), Y + S(56) + S(14) * op), fill=(150, 60, 50))
    if point is not None:
        px, py = point[0] * SS, point[1] * SS
        sx_ = X + (S(110) if px > X else -S(110))
        d.line([(sx_, Y + S(160)), (px, py)], fill=coat, width=int(S(40)))
        d.ellipse((px - S(22), py - S(22), px + S(22), py + S(22)), fill=SKIN)

def speech_bubble(c, x, y, w, h, k, tail, fill=(30, 16, 12, 235)):
    if k <= 0: return
    lay = Image.new("RGBA", (W, HALF), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, cy = x + w / 2, y + h / 2
    ww, hh = w * k, h * k
    d.rounded_rectangle((cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2), int(46 * k), fill=fill, outline=(255, 255, 255, 50), width=2)
    tx, ty = tail
    bx = lerp(cx, tx, 0.55)
    d.polygon([(bx - 30 * k, cy + hh / 2 - 2), (bx + 30 * k, cy + hh / 2 - 2), (lerp(bx, tx, k), lerp(cy + hh / 2, ty, k))], fill=fill)
    c.alpha_composite(lay)

def bubble_words(c, text_lines, x, y, t0, t):
    yy = y
    for li, (txt, style, tin) in enumerate(text_lines):
        f = STY[style][0](); lh = STY[style][1]
        cx = x
        for i, wd in enumerate(txt.split(" ")):
            tt = t - tin - i * 0.07
            if tt > 0:
                k = spring(tt, w=14, z=0.8)
                lay = text_layer(wd, f, WHITE, pad=6)
                paste_alpha(c, lay, cx, yy + (1 - k) * 22, clamp(tt / 0.15), lerp(0.9, 1, k))
            cx += f.getlength(wd + " ")
        yy += lh

def cart_ask(lt, t):
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    k = spring(lt, w=9, z=0.8)
    kid(d, 330 - (1 - k) * 200, 780, 0.62, t, mood="worried", look=1.0, blink_t=(t - lt + 1.5, t - lt + 3.6))
    adult(d, 760 + (1 - k) * 220, 650, 0.78, t if t > 4.44 else 0, "mom", mood="neutral", blink_t=(t - lt + 2.2,))
    c.alpha_composite(finish(L))
    bk = spring(t - 4.40, w=11, z=0.7) if t > 4.40 else 0
    speech_bubble(c, 60, 276, 900, 250, bk, (720, 540))
    if bk > 0.5:
        bubble_words(c, [("Assalomu alaykum,", "thin", 4.44), ("o'g'lim 7 yoshda...", "bold", 5.40)], 104, 316, 4.44, t)
    return c

def cart_race(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    for i in range(3):
        dd.line([(0, 720 + i * 90), (W, 720 + i * 90)], fill=(255, 236, 214, 30), width=3)
    # finish flag
    for r_ in range(6):
        for q in range(2):
            col = CREAM if (r_ + q) % 2 == 0 else BG0
            dd.rectangle((960 + q * 26, 600 + r_ * 26, 986 + q * 26, 626 + r_ * 26), fill=col)
    dd.line([(960, 600), (960, 900)], fill=CREAM, width=6)
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    u = clamp(lt / 2.3)
    ax = lerp(300, 860, ease_out(u)); hx = lerp(120, 380, u)
    bob = lambda ph: 12 * abs(math.sin(lt * 11 + ph))
    kid(d, ax, 650 - bob(0), 0.5, t, mood="happy", look=1.0, shirt=GREEN)
    kid(d, hx, 740 - bob(1.3) * 0.6, 0.5, t, mood="worried", look=1.0, blink_t=(t - lt + 1.0,))
    c.alpha_composite(finish(L))
    for j in range(4):  # dust puffs
        ph = (lt * 2 + j / 4) % 1
        for x0, y0 in ((ax - 70, 820), (hx - 70, 900)):
            r = 10 + 24 * ph
            ImageDraw.Draw(c).ellipse((x0 - ph * 80 - r, y0 - r, x0 - ph * 80 + r, y0 + r), fill=rgba(CREAM, 0.25 * (1 - ph)))
    for j in range(3):  # speed lines behind the leader
        yy = 610 + j * 30
        ImageDraw.Draw(c).line([(ax - 160 - j * 20, yy), (ax - 90, yy)], fill=rgba(CREAM, 0.4), width=4)
    # sweat drop on the hero
    ImageDraw.Draw(c).ellipse((hx + 50, 640 + 10 * math.sin(lt * 6), hx + 66, 662 + 10 * math.sin(lt * 6)), fill=(140, 190, 230))
    return c

def cart_teacher(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    dd.rounded_rectangle((60, 580, 470, 820), 18, fill=(36, 70, 56), outline=WOOD, width=12)
    for i, ch in enumerate("ABD"):
        k = ease_out((lt - 0.2 - i * 0.25) / 0.3)
        if k > 0:
            dd.text((140 + i * 110, 700), ch, font=dfont("SemiBold", 110), fill=rgba(CREAM, 0.9 * k), anchor="mm")
    sh = 6 * math.sin(lt * 40) * (1 if 0.6 < lt % 1.2 < 0.9 else 0)
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    adult(d, 610 + sh, 640, 0.72, t, "teacher", mood="angry", point=(430 + sh, 650))
    kid(d, 900, 790, 0.5, t, mood="worried", look=-1.0, blink_t=(t - lt + 0.8, t - lt + 1.9))
    c.alpha_composite(finish(L))
    pk = 1 + 0.12 * abs(math.sin(lt * 8))
    ex = shadowed(text_layer("!", dfont("Black", 90), GOLD), 5)
    paste_alpha(c, ex, 700 - ex.width * pk / 2, 520, 1.0, pk)
    for j in range(3):  # shake lines around the boy
        a = math.radians(200 + j * 25)
        dd2 = ImageDraw.Draw(c)
        dd2.line([(900 + 90 * math.cos(a), 760 + 90 * math.sin(a)), (900 + 120 * math.cos(a), 760 + 120 * math.sin(a))], fill=rgba(CREAM, 0.6), width=4)
    tear = (lt * 0.8) % 1
    ImageDraw.Draw(c).ellipse((924, 800 + tear * 40, 936, 816 + tear * 40), fill=rgba((140, 190, 230), 1 - tear))
    return c

def cart_inspect(lt, t):
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    kid(d, 540, 780, 0.6, t, mood="neutral", look=math.sin(lt * 2), blink_t=(t - lt + 1.2,))
    c.alpha_composite(finish(L))
    lx = 540 + 260 * math.sin(lt * 1.6); ly = 690 + 60 * math.sin(lt * 3.2)
    icons = [icon_brain(110), icon_bulb(110, t), icon_cloud(110, t)]
    idx = int(lt / 0.95) % 3
    g = glow(300, GOLD); gg = g.resize((260, 260)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5)))
    c.alpha_composite(gg, (int(lx - 130), int(ly - 130)))
    paste_alpha(c, icons[idx], lx - 55, ly - 55)
    dd = ImageDraw.Draw(c)
    dd.ellipse((lx - 100, ly - 100, lx + 100, ly + 100), outline=CREAM, width=12)
    dd.line([(lx + 70, ly + 70), (lx + 150, ly + 150)], fill=WOOD, width=26)
    return c

def card_img(sym, col, flip):
    w, h = 110, 140
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if flip < 0.5:
        d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=(70, 90, 150))
        d.rounded_rectangle((12, 12, w - 13, h - 13), 12, outline=(120, 140, 200), width=4)
    else:
        d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=PAPER)
        d.text((w / 2, h / 2), sym, font=dfont("Black", 70), fill=col, anchor="mm")
    sx = abs(math.cos(flip * math.pi))
    return im.resize((max(2, int(w * sx)), h), Image.BICUBIC)

def cart_session(lt, t):
    """New neuropsychologist (navy hijab, white coat) playing a memory-pairs game with the boy."""
    c = PANEL_BG.copy()
    L = Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    happy = lt > 3.4
    kid(d, 190, 720, 0.62, t, mood="happy" if happy else "think", look=1.0, blink_t=(t - lt + 1.1, t - lt + 4.0))
    adult(d, 890, 640, 0.7, t, "doc", mood="kind", blink_t=(t - lt + 2.0,))
    d.rounded_rectangle((P(60), P(860), P(1020), P(910)), P(14), fill=WOOD)
    d.rectangle((P(60), P(900), P(1020), P(960)), fill=WOOD_D)
    c.alpha_composite(finish(L))
    syms = [("A", TERRA), ("B", GOLD), ("A", TERRA), ("D", GREEN), ("B", GOLD), ("D", GREEN)]
    order = [(0, 2, 0.4), (1, 4, 1.4), (3, 5, 2.4)]   # pairs and when they are flipped
    for i, (sym, col) in enumerate(syms):
        x = 330 + (i % 3) * 140; y = 640 + (i // 3) * 160
        flip = 0.0; matched = 0.0
        for a, b, tf in order:
            if i in (a, b):
                flip = clamp((lt - tf - (0.25 if i == b else 0)) / 0.3)
                matched = ease_out((lt - tf - 0.6) / 0.3)
        ci = card_img(sym, col, flip)
        lift = 14 * matched
        if matched > 0:
            g = glow(220, col); gg = g.resize((200, 200)); gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.45 * matched)))
            c.alpha_composite(gg, (int(x - 100), int(y - 100 - lift)))
        paste_alpha(c, ci, x - ci.width / 2, y - 70 - lift)
    if lt > 3.4:  # rising stars on "ijobiy natija"
        for j in range(8):
            u = (lt - 3.4 - j * 0.12) / 1.0
            if 0 < u < 1:
                x = 330 + j * 40; y = lerp(760, 560, ease_out(u))
                r = 10 * (1 - u) + 4
                pts = [(x + (r if q % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + q * 36)),
                        y + (r if q % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + q * 36))) for q in range(10)]
                ImageDraw.Draw(c).polygon(pts, fill=rgba(GOLD, 1 - u))
    return c

# ---------- Instagram profile (real account) ----------
PROFILE_SRC = Image.open(os.path.join(HERE, "profile_ig.png")).convert("RGB")
def ig_avatar(size):
    av = PROFILE_SRC.resize((size, size), Image.LANCZOS, box=(112, 190, 412, 490))
    m = Image.new("L", (size, size), 0); ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0)); out.paste(av, (0, 0), m)
    return out
AVATAR = ig_avatar(170)

def verified(d, x, y, r=16):
    pts = [(x + (r if i % 2 == 0 else r * 0.82) * math.cos(math.radians(i * 22.5)), y + (r if i % 2 == 0 else r * 0.82) * math.sin(math.radians(i * 22.5))) for i in range(16)]
    d.polygon(pts, fill=(0, 149, 246))
    d.line([(x - 7, y), (x - 2, y + 6), (x + 8, y - 6)], fill=WHITE, width=4, joint="curve")

def cart_follow(lt, t, src):
    c = PANEL_BG.copy()
    k = spring(lt, w=10, z=0.78)
    cw_, ch_ = 960, 360
    x0, y0 = (W - cw_) // 2, int(575 + (1 - k) * 80)
    lay = Image.new("RGBA", (cw_, ch_), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, cw_ - 1, ch_ - 1), 36, fill=(12, 16, 20, 248), outline=(255, 255, 255, 40), width=2)
    ring = Image.new("RGBA", (186, 186), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse((0, 0, 185, 185), outline=(80, 80, 80), width=5)
    lay.alpha_composite(ring, (28, 28)); lay.alpha_composite(AVATAR, (36, 36))
    nf = font("SemiBold", 36)
    d.text((240, 52), "logoped_muslimausman", font=nf, fill=WHITE, anchor="lm")
    verified(d, 240 + nf.getlength("logoped_muslimausman") + 26, 52)
    d.text((240, 96), "DEFEKTOLOG | LOGOPED | ABA - TERAPIST", font=font("Regular", 24), fill=(220, 220, 220), anchor="lm")
    tap = 36.42 - (t - lt)
    fol = 40.2 + (0.1 if lt > tap + 0.2 else 0)
    stats = [("393", "nashr"), (f"{fol:.1f}K".replace(".", ","), "obunachi"), ("293", "obuna")]
    sx = 240
    for val, lab in stats:
        d.text((sx, 146), val, font=font("SemiBold", 28), fill=WHITE, anchor="lm")
        sx += font("SemiBold", 28).getlength(val) + 8
        d.text((sx, 147), lab, font=font("Regular", 26), fill=(200, 200, 200), anchor="lm")
        sx += font("Regular", 26).getlength(lab) + 34
    d.text((36, 250), "ZPR, ZRR, Autizm tashxisli bolalarga yordam", font=font("Regular", 25), fill=(225, 225, 225), anchor="lm")
    pressed = lt >= tap
    bk = ease_out((lt - tap) / 0.25) if pressed else 0
    bx0, by0, bx1, by1 = 36, 286, 470, 340
    col = tuple(int(lerp(a_, b_, bk)) for a_, b_ in zip((0, 149, 246), (54, 54, 58)))
    sq = 1 - 0.05 * math.sin(math.pi * clamp((lt - tap) / 0.2)) if pressed else 1
    cxb, cyb = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw, hh = (bx1 - bx0) / 2 * sq, (by1 - by0) / 2 * sq
    d.rounded_rectangle((cxb - hw, cyb - hh, cxb + hw, cyb + hh), 14, fill=col)
    d.text((cxb, cyb), "Obuna bo'lish" if bk < 0.5 else "Obuna bo'lingan  ✓", font=font("SemiBold", 26), fill=WHITE, anchor="mm")
    d.rounded_rectangle((486, 286, 920, 340), 14, fill=(54, 54, 58))
    d.text((703, 313), "Xabar yozish", font=font("SemiBold", 26), fill=WHITE, anchor="mm")
    c.alpha_composite(lay, (x0, y0))
    fx, fy = x0 + cxb + 60, y0 + cyb + 20
    appear = ease_out((lt - (tap - 0.7)) / 0.5)
    if appear > 0 and lt < tap + 0.6:
        fx2 = lerp(fx + 140, fx, appear); fy2 = lerp(fy + 180, fy, appear)
        ImageDraw.Draw(c).ellipse((fx2 - 32, fy2 - 32, fx2 + 32, fy2 + 32), fill=rgba(WHITE, 0.8 * (1 - clamp((lt - tap - 0.3) / 0.3))))
    if pressed:
        u = clamp((lt - tap) / 0.6); r = lerp(20, 150, ease_out(u))
        ImageDraw.Draw(c).ellipse((x0 + cxb - r, y0 + cyb - r, x0 + cxb + r, y0 + cyb + r), outline=rgba(WHITE, 0.6 * (1 - u)), width=4)
    return c

PANELS.update({"ask": cart_ask, "race": cart_race, "teacher": cart_teacher, "inspect": cart_inspect,
               "session": cart_session, "follow": cart_follow})

SEG[:] = [
    (0.00, 2.00, "full", None, 1.10),
    (2.00, 7.05, "split", "ask", 1.00),
    (7.05, 9.38, "split", "race", 1.12),
    (9.38, 11.80, "split", "teacher", 1.00),
    (11.80, 14.75, "full", None, 1.00),
    (14.75, 17.35, "split", "inspect", 1.15),
    (17.35, 20.30, "full", None, 1.04),
    (20.30, 23.90, "split", "areas", 1.18),
    (23.90, 28.15, "split", "memory", 1.00),
    (28.15, 33.90, "split", "session", 1.12),
    (33.90, 38.80, "split", "follow", 1.00),
    (38.80, 99.0, "full", None, 1.12),
]
PUNCH[:] = [(12.22, 1.06, 14.75), (39.46, 1.06, 99)]

CAPTIONS[:] = [
    ([("1 daqiqada", "thin", 0.05), ("1 savolga javob", "bold", 0.64)], 1.90),
    ([("Savollarga oldindan", "thin", 2.02), ("tayyorlanmaganman", "bold", 2.68)], 4.25),
    ([("Tengdoshlaridan", "thin", 7.10), ("orqada qolyapti", "bold", 8.18)], 9.30),
    ([("Harflarni", "thin", 9.42), ("eslab qololmayapti", "bold", 10.44)], 11.72),
    ([("Bola harflarni", "thin", 12.22), ("eslab qololmasa", "bold", 13.30)], 14.68),
    ([("faqat «orqada qolyapti»", "thin", 15.06), ("deb xulosa qilmang", "bold", 15.40)], 17.28),
    ([("Boshqa rivojlanish", "thin", 17.42), ("sohalarini tekshiring", "bold", 18.66)], 20.22),
    ([("Intellekt, tafakkur,", "thin", 20.72), ("tasavvur", "bold", 22.48)], 23.85),
    ([("Harflarni eslab qololmasa —", "thin", 23.98), ("xotirasi sust", "bold", 26.68), ("bo'lishi mumkin", "thin", 27.40)], 28.05),
    ([("Buning uchun", "thin", 28.18), ("neyropsixolog", "bold", 29.30), ("mashg'ulotlariga boring", "thin", 30.06)], 31.40),
    ([("Natija —", "thin", 31.52), ("yaxshi va ijobiy", "bold", 31.96)], 33.85),
    ([("Sahifamga hali", "thin", 34.02), ("obuna bo'lmagan bo'lsangiz,", "thin", 35.26), ("tezroq obuna bo'ling", "bold", 36.42)], 37.30),
    ([("chunki ota-onalar", "thin", 37.40), ("uchun", "thin", 37.90)], 38.72),
    ([("foydali tavsiyalar", "bold", 39.46), ("berib boraman", "thin", 40.72)], 99),
]

@lru_cache(maxsize=96)
def cap_layer(txt, style):
    return shadowed(text_layer(txt, STY[style][0](), WHITE, pad=8))

FULL_CAP_Y = 1200
def rise_words_c(canvas, text, style, y, t0, t, out):
    f = STY[style][0](); lh = STY[style][1]
    total = f.getlength(text)
    cx = (W - total) / 2 - 16
    for i, wd in enumerate(text.split(" ")):
        lay = cap_layer(wd, style)
        tt = t - t0 - i * 0.06
        if tt > 0:
            k = spring(tt, w=14, z=0.82)
            off = (1 - k) * lh * 0.85 + out * 26
            clip = Image.new("RGBA", (lay.width, lay.height + 4), (0, 0, 0, 0))
            clip.alpha_composite(lay, (0, int(max(-lay.height, min(lay.height, off)))))
            paste_alpha(canvas, clip, cx, y, clamp(tt / 0.14) * (1 - out))
        cx += f.getlength(wd + " ")

def draw_captions(canvas, t):
    for lines, t_out in CAPTIONS:
        if t < lines[0][2] or t > t_out + 0.35: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        full = SEG[seg_at(lines[0][2])][2] == "full"
        y = FULL_CAP_Y if full else CAP_Y
        for txt, style, t_in in lines:
            if full: rise_words_c(canvas, txt, style, y, t_in, t, out)
            else: rise_words(canvas, txt, style, CAP_X, y, t_in, t, out)
            y += STY[style][1]
    stopwatch(canvas, t)

def stopwatch(canvas, t):
    if t > 2.2: return
    out = ease_in((t - 1.9) / 0.3) if t > 1.9 else 0.0
    k = spring(t - 0.02, w=11, z=0.55) * (1 - out)
    if k <= 0.01: return
    s = 160
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; r = 52
    d.rounded_rectangle((c - 10, c - r - 22, c + 10, c - r - 8), 4, fill=WHITE)
    d.ellipse((c - r, c - r, c + r, c + r), outline=WHITE, width=7)
    sweep = (t * 160) % 360
    d.pieslice((c - r + 12, c - r + 12, c + r - 12, c + r - 12), -90, -90 + sweep, fill=TERRA)
    ang = math.radians(-90 + sweep)
    d.line([(c, c), (c + (r - 14) * math.cos(ang), c + (r - 14) * math.sin(ang))], fill=WHITE, width=5)
    im = im.rotate((1 - k) * 90, Image.BICUBIC)
    paste_alpha(canvas, shadowed(im, 6), W / 2 - s * k / 2 - 12, FULL_CAP_Y - 150, clamp(k * 1.5), k)

def bottom_scrim():
    al = np.clip((np.arange(H) - 1000) / 600, 0, 1) ** 1.4 * 0.55 * 255
    v = np.zeros((H, W, 4), np.uint8); v[..., :3] = BG0; v[..., 3] = al[:, None].astype(np.uint8)
    return Image.fromarray(v)
SCRIM = bottom_scrim()
