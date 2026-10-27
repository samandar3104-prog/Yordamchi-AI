# ================= stuttering reel overrides =================
import sys as _sys
_sys.path.insert(0, HERE)
import story
SEG[:] = story.SEG
TAP_T = story.TAP_T
PUNCH[:] = [(15.36, 1.06, 16.30), (40.12, 1.06, 41.20), (55.58, 1.05, 99)]
PINK = (226, 130, 160)

# ---------- new type system: serif italic typewriter + ExtraBold blur-in ----------
SERIF_I = "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf"
@lru_cache(None)
def serif(s): return ImageFont.truetype(SERIF_I, s)
STY = {"thin": (lambda: serif(70), 88), "bold": (lambda: dfont("ExtraBold", 84), 104)}

@lru_cache(maxsize=512)
def glyph(ch, style):
    return shadowed(text_layer(ch, STY[style][0](), WHITE, pad=6), 6)

@lru_cache(maxsize=256)
def word_img(wd, style):
    return shadowed(text_layer(wd, STY[style][0](), WHITE, pad=8))

def line_width(text, style): return STY[style][0]().getlength(text)

def anim_line(canvas, text, style, x, y, t0, t, out):
    f = STY[style][0]()
    if out > 0:   # exit: drift up + fade
        y -= 24 * out
    a_out = 1 - out
    if style == "thin":            # typewriter, letter by letter
        cps = 34.0
        for i, ch in enumerate(text):
            if ch == " ": continue
            u = (t - t0) * cps - i
            if u <= 0: break
            a = clamp(u / 2.5) * a_out
            g = glyph(ch, style)
            paste_alpha(canvas, g, x + f.getlength(text[:i]) - 12, y + (1 - clamp(u / 2.5)) * 8, a)
    else:                          # words blur-in and settle from a larger scale
        cx = x
        for i, wd in enumerate(text.split(" ")):
            tt = t - t0 - i * 0.09
            lay = word_img(wd, style)
            if tt > 0:
                k = spring(tt, w=13, z=0.78)
                sc = lerp(1.14, 1.0, k)
                im = lay
                if tt < 0.3: im = lay.filter(ImageFilter.GaussianBlur(9 * (1 - tt / 0.3)))
                paste_alpha(canvas, im, cx - 16 - lay.width * (sc - 1) / 2, y - 16 - lay.height * (sc - 1) / 2, clamp(tt / 0.18) * a_out, sc)
            cx += f.getlength(wd + " ")

def draw_captions(canvas, t):
    for lines, t_out, where in story.CAPTIONS:
        if where == "bubble": continue
        if t < lines[0][2] or t > t_out + 0.32: continue
        out = ease_in((t - t_out) / 0.3) if t > t_out else 0.0
        full = SEG[seg_at(lines[0][2])][2] == "full"
        total_h = sum(STY[s][1] for _, s, _ in lines)
        y = min(FULL_CAP_Y, 1580 - total_h) if full else CAP_Y
        for txt, style, t_in in lines:
            x = (W - line_width(txt, style)) / 2 if full else CAP_X
            anim_line(canvas, txt, style, x, y, t_in, t, out)
            y += STY[style][1]

def stopwatch(canvas, t): return

# ---------- girl ----------
def girl(d, cx, cy, s, t, mood="neutral", look=0.0, blink_t=(), mouth=None):
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    for sx in (-1, 1):   # pigtails behind the head
        d.ellipse((X + sx * S(118) - S(36), Y - S(10), X + sx * S(118) + S(36), Y + S(90)), fill=HAIR)
    kid(d, cx, cy, s, t, mood=mood, look=look, blink_t=blink_t, shirt=PINK)
    for sx in (-1, 1):
        bx, by = X + sx * S(96), Y - S(40)
        d.polygon([(bx, by), (bx + sx * S(30), by - S(20)), (bx + sx * S(30), by + S(20))], fill=TERRA)
    if mouth == "o":
        d.ellipse((X - S(14), Y + S(52), X + S(14), Y + S(80)), fill=(150, 60, 50))
    elif mouth == "talk":
        op = abs(math.sin(t * 14))
        d.ellipse((X - S(16), Y + S(54), X + S(16), Y + S(60) + S(18) * op), fill=(150, 60, 50))

def adult2(d, cx, cy, s, t, style, **kw):
    if style != "doctor": return adult(d, cx, cy, s, t, style, **kw)
    def S(v): return v * s * SS
    X, Y = cx * SS, cy * SS
    d.rounded_rectangle((X - S(130), Y + S(100), X + S(130), Y + S(420)), int(S(80)), fill=(244, 244, 246))
    d.polygon([(X - S(40), Y + S(100)), (X + S(40), Y + S(100)), (X, Y + S(190))], fill=(90, 130, 190))
    d.arc((X - S(60), Y + S(110), X + S(30), Y + S(240)), 80, 260, fill=(60, 60, 70), width=int(S(7)))
    d.ellipse((X - S(86), Y - S(98), X + S(86), Y + S(96)), fill=SKIN)
    d.chord((X - S(90), Y - S(110), X + S(90), Y + S(20)), 180, 360, fill=(70, 60, 56))
    for sx in (-1, 1):
        ex, ey = X + sx * S(30), Y + S(8)
        d.ellipse((ex - S(9), ey - S(11), ex + S(9), ey + S(11)), fill=HAIR)
        d.line([(ex - S(15), ey - S(26)), (ex + S(15), ey - S(26))], fill=(70, 60, 56), width=int(S(6)))
    d.arc((X - S(24), Y + S(38), X + S(24), Y + S(70)), 20, 160, fill=(150, 60, 50), width=int(S(6)))

def panel_layer(): return Image.new("RGBA", (W * SS, HALF * SS), (0, 0, 0, 0))

def bubble_small(c, x, y, w, h, k, tail):
    speech_bubble(c, x, y, w, h, k, tail, fill=(250, 240, 222, 245))

# ---------- scenes ----------
def cart_ask(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    k = spring(lt, w=9, z=0.8)
    girl(d, 320 - (1 - k) * 200, 800, 0.6, t, mood="worried", look=1.0, blink_t=(t - lt + 1.3, t - lt + 3.4))
    adult(d, 770 + (1 - k) * 220, 700, 0.74, t if t > 3.78 else 0, "mom", mood="neutral", blink_t=(t - lt + 2.0,))
    c.alpha_composite(finish(L))
    bk = spring(t - 3.72, w=11, z=0.7) if t > 3.72 else 0
    speech_bubble(c, 60, 250, 900, 320, bk, (740, 590))
    if bk > 0.5:
        lines = story.CAPTIONS[2][0]
        y = 282
        for txt, style, tin in lines:
            anim_line(c, txt, style, 104, y, tin, t, 0.0)
            y += STY[style][1]
    return c

def stutter_tiles(c, lt, x0, y0, n=3, size=78):
    for j in range(n):
        u = (lt * 1.6 - j * 0.3) % 1.6
        if u > 1.2: continue
        k = spring(u, w=16, z=0.4)
        jit = 6 * math.sin(lt * 40 + j) * (1 - clamp(u / 0.4))
        tile = letter_tile("M", [GOLD, TERRA, AMBER][j % 3], size)
        paste_alpha(c, tile, x0 + j * (size + 18) + jit, y0, clamp(k * 2) * (1 - clamp((u - 0.9) / 0.3)), lerp(0.5, 1, k))

def cart_stutter(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 300, 780, 0.66, t, mood="worried", look=0.8, blink_t=(t - lt + 1.0, t - lt + 2.6), mouth="talk")
    c.alpha_composite(finish(L))
    k = spring(lt - 0.2, w=11, z=0.7)
    bubble_small(c, 500, 600, 500, 190, k, (390, 760))
    if k > 0.6:
        stutter_tiles(c, lt, 560, 650)
    if lt > 2.3:   # question on mom's mind: "will it pass?" — dots pulse
        for j in range(3):
            a = 0.4 + 0.6 * abs(math.sin(t * 5 + j))
            ImageDraw.Draw(c).ellipse((640 + j * 50, 840, 664 + j * 50, 864), fill=rgba(CREAM, a))
    return c

def syrup_bottle(gray=0.0):
    im = Image.new("RGBA", (120 * SS, 200 * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = tuple(int(lerp(a, b, gray)) for a, b in zip((196, 110, 50), (110, 100, 96)))
    d.rounded_rectangle((P(20), P(50), P(100), P(196)), P(22), fill=col)
    d.rectangle((P(42), P(16), P(78), P(54)), fill=(240, 240, 240))
    d.rounded_rectangle((P(36), P(0), P(84), P(22)), P(6), fill=(230, 80, 70) if gray < 0.5 else (140, 140, 140))
    d.rounded_rectangle((P(30), P(100), P(90), P(150)), P(8), fill=PAPER)
    d.line([(P(42), P(118)), (P(78), P(118))], fill=col, width=P(5)); d.line([(P(42), P(132)), (P(70), P(132))], fill=col, width=P(5))
    return finish(im)

def cart_syrup(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 280, 790, 0.6, t, mood="worried" if lt > 2.8 else "neutral", look=1.0, blink_t=(t - lt + 0.8, t - lt + 3.1), mouth="talk" if lt > 3.0 else None)
    adult2(d, 830, 690, 0.72, t, "doctor")
    c.alpha_composite(finish(L))
    k = ease_out((lt - 1.4) / 0.6)
    gray = ease_io((lt - 2.8) / 0.6)
    bx = lerp(760, 520, k); by = lerp(740, 700, k) - 60 * math.sin(math.pi * k)
    b = syrup_bottle(gray)
    if gray > 0: b = b.rotate(8 * math.sin(lt * 18) * (1 - clamp((lt - 3.4) / 0.4)), Image.BICUBIC, expand=True)
    paste_alpha(c, b, bx - b.width / 2, by - b.height / 2, clamp((lt - 1.2) / 0.3))
    if lt > 3.0:
        kk = spring(lt - 3.0, w=11, z=0.7)
        bubble_small(c, 60, 600, 300, 150, kk, (240, 740))
        if kk > 0.6: stutter_tiles(c, lt, 92, 636, n=2, size=70)
    return c

def storm_cloud(t, size=220):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for (x, y, r) in ((0.3, 0.45, 0.18), (0.52, 0.36, 0.24), (0.72, 0.47, 0.17)):
        d.ellipse((S * (x - r), S * (y - r), S * (x + r), S * (y + r)), fill=(96, 92, 110))
    d.rectangle((S * 0.16, S * 0.45, S * 0.86, S * 0.62), fill=(96, 92, 110))
    if int(t * 6) % 3 != 0:
        d.polygon([(S * 0.52, S * 0.6), (S * 0.42, S * 0.8), (S * 0.52, S * 0.8), (S * 0.44, S * 0.98), (S * 0.66, S * 0.72), (S * 0.55, S * 0.72), (S * 0.62, S * 0.6)], fill=GOLD)
    return finish(im)

def cart_causes(lt, t):
    c = PANEL_BG.copy()
    tf, tn = 19.04 - (t - lt), 20.86 - (t - lt)
    scared = lt > tf
    shake = 5 * math.sin(lt * 50) if tf < lt < tf + 1.5 else 0
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 540 + shake, 790, 0.62, t, mood="worried" if scared else "think", look=-1 if scared and lt < tn else (1 if lt > tn else 0), blink_t=(t - lt + 0.8,))
    c.alpha_composite(finish(L))
    dd = ImageDraw.Draw(c)
    for x in (230, 850):   # placeholders that wait for the causes
        k = ease_out((lt - 0.8) / 0.4)
        if k > 0:
            for a in range(0, 360, 20):
                if (a // 20) % 2: continue
                r = 110
                dd.arc((x - r, 690 - r, x + r, 690 + r), a + lt * 30, a + 10 + lt * 30, fill=rgba(CREAM, 0.35 * k), width=4)
    if lt > tf:
        k = spring(lt - tf, w=11, z=0.5)
        if scared and int(lt * 6) % 3 != 0 and lt < tf + 1.5:
            g = glow(360, GOLD); c.alpha_composite(g.resize((300, 300)), (80, 540))
        paste_alpha(c, storm_cloud(t), 230 - 110 * k, 690 - 110 * k, clamp(k * 2), k)
    if lt > tn:
        k = spring(lt - tn, w=11, z=0.5)
        br = icon_brain(170)
        g = glow(300, TERRA); gg = g.resize((max(1, int(280 * k)), max(1, int(280 * k)))); c.alpha_composite(gg, (int(850 - gg.width / 2), int(690 - gg.height / 2)))
        paste_alpha(c, br, 850 - 85 * k, 690 - 85 * k, clamp(k * 2), k)
        if int(lt * 8) % 2 == 0:
            dd.line([(800, 640), (830, 680), (812, 690), (850, 740)], fill=rgba(GOLD, 0.9), width=6)
    return c

def cart_home(lt, t):
    c = PANEL_BG.copy()
    dd = ImageDraw.Draw(c)
    dd.rounded_rectangle((90, 590, 330, 800), 16, fill=(30, 40, 70), outline=WOOD, width=10)
    dd.line([(210, 590), (210, 800)], fill=WOOD, width=8); dd.line([(90, 695), (330, 695)], fill=WOOD, width=8)
    dd.ellipse((240, 616, 290, 666), fill=CREAM); dd.ellipse((256, 608, 302, 654), fill=(30, 40, 70))
    pulse = 0.85 + 0.15 * math.sin(lt * 2.2)
    g = glow(520, GOLD); gg = g.resize((int(520 * pulse), int(520 * pulse)))
    c.alpha_composite(gg, (int(900 - gg.width / 2), int(640 - gg.height / 2)))
    dd.polygon([(860, 600), (940, 600), (960, 650), (840, 650)], fill=GOLD)
    dd.line([(900, 650), (900, 900)], fill=WOOD_D, width=8)
    dd.rounded_rectangle((300, 800, 820, 930), 40, fill=(120, 60, 50))
    dd.rounded_rectangle((280, 760, 340, 930), 26, fill=(140, 72, 60)); dd.rounded_rectangle((780, 760, 840, 930), 26, fill=(140, 72, 60))
    L = panel_layer(); d = ImageDraw.Draw(L)
    adult(d, 640, 690, 0.62, t, "mom", mood="kind", blink_t=(t - lt + 1.8, t - lt + 3.9))
    girl(d, 450, 760, 0.52, t, mood="happy", look=1.0, blink_t=(t - lt + 1.0, t - lt + 3.2))
    c.alpha_composite(finish(L))
    for j in range(10):   # calm floating motes
        u = (lt * 0.18 + j / 10) % 1
        x = 120 + j * 90 + 20 * math.sin(lt + j); y = lerp(930, 580, u)
        ImageDraw.Draw(c).ellipse((x - 4, y - 4, x + 4, y + 4), fill=rgba(GOLD, 0.5 * math.sin(math.pi * u)))
    return c

def item_icon(kind, t):
    S = 150 * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if kind == "wand":
        d.line([(S * 0.25, S * 0.8), (S * 0.68, S * 0.37)], fill=(60, 50, 60), width=int(S * 0.08))
        d.line([(S * 0.62, S * 0.43), (S * 0.68, S * 0.37)], fill=CREAM, width=int(S * 0.08))
        cx, cy, r = S * 0.74, S * 0.28, S * 0.14
        pts = [(cx + (r if q % 2 == 0 else r * 0.45) * math.cos(math.radians(-90 + q * 36 + t * 60)),
                cy + (r if q % 2 == 0 else r * 0.45) * math.sin(math.radians(-90 + q * 36 + t * 60))) for q in range(10)]
        d.polygon(pts, fill=GOLD)
    elif kind == "pills":
        d.rounded_rectangle((S * 0.15, S * 0.4, S * 0.65, S * 0.62), int(S * 0.11), fill=CREAM)
        d.rounded_rectangle((S * 0.4, S * 0.4, S * 0.65, S * 0.62), int(S * 0.11), fill=TERRA)
        d.ellipse((S * 0.55, S * 0.6, S * 0.85, S * 0.9), fill=(230, 230, 236))
        d.line([(S * 0.58, S * 0.75), (S * 0.82, S * 0.75)], fill=(190, 190, 196), width=int(S * 0.03))
    elif kind == "bolt":
        d.polygon([(S * 0.56, S * 0.08), (S * 0.24, S * 0.56), (S * 0.48, S * 0.56), (S * 0.4, S * 0.92), (S * 0.78, S * 0.4), (S * 0.54, S * 0.4)], fill=GOLD)
    elif kind == "scissors":
        for sx in (-1, 1):
            d.ellipse((S * (0.5 + sx * 0.18) - S * 0.12, S * 0.62, S * (0.5 + sx * 0.18) + S * 0.12, S * 0.86), outline=TERRA, width=int(S * 0.06))
        ang = 0.25 + 0.15 * abs(math.sin(t * 6))
        for sx in (-1, 1):
            d.line([(S * 0.5, S * 0.56), (S * 0.5 + sx * S * 0.4 * math.sin(ang), S * 0.56 - S * 0.46 * math.cos(ang))], fill=(210, 210, 220), width=int(S * 0.06))
            d.line([(S * 0.5, S * 0.56), (S * (0.5 + sx * 0.18), S * 0.66)], fill=(210, 210, 220), width=int(S * 0.06))
    return finish(im)

def desat(im, amt):
    if amt <= 0: return im
    g = im.convert("LA").convert("RGBA")
    g.putalpha(im.getchannel("A"))
    return Image.blend(im, g, amt)

def cart_nomagic(lt, t):
    c = PANEL_BG.copy()
    base = t - lt
    items = [("wand", 30.36), ("syrup", 31.22), ("pills", 31.90), ("bolt", 32.84), ("scissors", 34.58)]
    xs = [150, 345, 540, 735, 930]
    fall = ease_in((t - 36.94) / 0.9) if t > 36.94 else 0
    for (kind, ti), x in zip(items, xs):
        u = t - ti
        if u <= 0: continue
        k = spring(u, w=12, z=0.5)
        dead = ease_io((u - 0.9) / 0.5)
        im = syrup_bottle(dead) if kind == "syrup" else item_icon(kind, t)
        if kind == "syrup": im = im.resize((int(im.width * 0.75), int(im.height * 0.75)))
        im = desat(im, dead * 0.9)
        sh = 6 * math.sin(u * 30) * (1 - clamp((u - 0.9) / 0.5)) if 0.9 < u < 1.4 else 0
        y = 700 + 40 * (1 - k) + fall * 300
        if dead < 1:
            g = glow(260, GOLD); gg = g.resize((max(1, int(220 * k)), max(1, int(220 * k))))
            gg.putalpha(gg.getchannel("A").point(lambda v: int(v * 0.5 * (1 - dead))))
            c.alpha_composite(gg, (int(x - gg.width / 2), int(y - gg.height / 2)))
        paste_alpha(c, im, x - im.width * k / 2 + sh, y - im.height * k / 2, clamp(k * 2) * (1 - 0.45 * dead) * (1 - fall), k)
    return c

def pinwheel(t, spin, size=200):
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = cy = S / 2
    cols = [TERRA, GOLD, AMBER, CREAM]
    for i in range(4):
        a = math.radians(spin + i * 90)
        p1 = (cx + S * 0.45 * math.cos(a), cy + S * 0.45 * math.sin(a))
        p2 = (cx + S * 0.3 * math.cos(a + 1.2), cy + S * 0.3 * math.sin(a + 1.2))
        d.polygon([(cx, cy), p1, p2], fill=cols[i])
    d.ellipse((cx - S * 0.05, cy - S * 0.05, cx + S * 0.05, cy + S * 0.05), fill=WOOD_D)
    return finish(im)

def cart_exercise(lt, t):
    c = PANEL_BG.copy()
    base = t - lt
    speech = t > 44.48
    L = panel_layer(); d = ImageDraw.Draw(L)
    blow = 42.0 <= t < 44.2 and (t * 0.9) % 1 < 0.6
    girl(d, 290, 790, 0.62, t, mood="happy" if speech else "neutral", look=1.0, blink_t=(base + 1.0,), mouth="o" if blow else ("talk" if speech else None))
    if speech:
        adult(d, 860, 700, 0.66, t, "doc", mood="kind", blink_t=(base + 4.0,))
    c.alpha_composite(finish(L))
    if not speech or t < 44.9:
        fade = 1 - ease_io((t - 44.48) / 0.4)
        spin = (t * 40) + (t - 42.0) * 420 * (1 if t > 42 else 0)
        paste_alpha(c, pinwheel(t, spin), 620, 600, fade)
        ImageDraw.Draw(c).line([(720, 800), (720, 940)], fill=rgba(WOOD, fade), width=10)
        if blow:
            for j in range(5):
                u = ((t * 1.6) + j / 5) % 1
                x = lerp(380, 640, u); y = 770 - 40 * u + 10 * math.sin(u * 9 + j)
                ImageDraw.Draw(c).arc((x - 20, y - 10, x + 20, y + 10), 300, 60, fill=rgba(CREAM, 0.7 * (1 - u)), width=4)
    if speech:
        u = t - 44.48
        for j, syl in enumerate(("MA", "MA")):
            k = spring(u - 0.3 - j * 0.45, w=13, z=0.55) if u > 0.3 + j * 0.45 else 0
            tile = Image.new("RGBA", (130, 110), (0, 0, 0, 0)); td = ImageDraw.Draw(tile)
            td.rounded_rectangle((0, 0, 129, 109), 22, fill=[GOLD, TERRA][j])
            td.text((65, 57), syl, font=dfont("Black", 54), fill=BG0, anchor="mm")
            paste_alpha(c, tile, 470 + j * 160, 620, clamp(k * 2), lerp(0.4, 1, k))
        wk = ease_out((u - 1.4) / 0.8)
        if wk > 0:   # smooth (fluent) speech wave
            pts = [(lerp(450, 780, q / 60), 790 + 22 * math.sin(q / 60 * 12 + t * 4)) for q in range(int(60 * wk) + 1)]
            if len(pts) > 1: ImageDraw.Draw(c).line(pts, fill=GOLD, width=6, joint="curve")
    return c

def cart_logoped(lt, t):
    c = PANEL_BG.copy()
    L = panel_layer(); d = ImageDraw.Draw(L)
    girl(d, 300, 790, 0.6, t, mood="happy", look=1.0, blink_t=(t - lt + 1.2, t - lt + 3.4), mouth="talk")
    adult(d, 820, 690, 0.7, t, "doc", mood="kind", blink_t=(t - lt + 2.2,))
    c.alpha_composite(finish(L))
    # clipboard with a ticking plan
    k = spring(lt - 0.2, w=11, z=0.7)
    cb = Image.new("RGBA", (220, 280), (0, 0, 0, 0)); cd = ImageDraw.Draw(cb)
    cd.rounded_rectangle((0, 10, 219, 279), 18, fill=(150, 100, 70)); cd.rounded_rectangle((16, 30, 203, 263), 10, fill=PAPER)
    cd.rounded_rectangle((70, 0, 150, 30), 8, fill=(90, 90, 96))
    for j in range(3):
        yy = 70 + j * 62
        tk = ease_out((lt - 0.8 - j * 0.6) / 0.3)
        cd.rounded_rectangle((34, yy - 16, 66, yy + 16), 6, outline=(120, 110, 100), width=3)
        if tk > 0: cd.line([(40, yy), (48, yy + 9), (62, yy - 10)], fill=rgba(GREEN, tk), width=5)
        cd.rounded_rectangle((80, yy - 6, 80 + 100 * (0.6 + 0.4 * (j % 2)), yy + 6), 6, fill=(200, 186, 170))
    paste_alpha(c, cb, 540 - 110 * k, 640 - 140 * k + (1 - k) * 60, clamp(k * 2), k)
    # fluent speech wave from the girl
    pts = [(lerp(380, 520, q / 40), 720 + 16 * math.sin(q / 40 * 10 + t * 5)) for q in range(41)]
    ImageDraw.Draw(c).line(pts, fill=rgba(GOLD, clamp((lt - 1.2) / 0.4)), width=5, joint="curve")
    return c

PANELS.update({"ask": cart_ask, "stutter": cart_stutter, "syrup": cart_syrup, "causes": cart_causes, "home": cart_home,
               "nomagic": cart_nomagic, "exercise": cart_exercise, "logoped": cart_logoped})
