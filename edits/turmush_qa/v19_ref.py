# ================= v19: reference-reel style =================
import story_ref as R
@lru_cache(None)
def mf(w, s): return ImageFont.truetype(os.path.join(HERE, f"Montserrat-{w}.ttf"), s)
KIND = {"n": (("Medium", 44), ("ExtraBold", 44), False), "cap": (("ExtraBold", 52), ("ExtraBold", 52), False),
        "it": (("ExtraBoldItalic", 54), ("ExtraBoldItalic", 54), False)}
CAP_Y = 1185; LINE_H = 66; MAXW = 940

@lru_cache(maxsize=2048)
def word_img(word, wt, size):
    f = mf(wt, size); tw = int(f.getlength(word)) + 24
    lay = Image.new("RGBA", (tw, size + 40), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((12, (size + 40) // 2), word, font=f, fill=(255, 255, 255), anchor="lm")
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.75)))
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (0, 2)); out.alpha_composite(lay)
    return out

def parse(text):
    out, bold = [], False
    for w in text.split(" "):
        b = bold or w.startswith("*")
        if w.startswith("*"): bold = True
        end = w.endswith("*") or w.endswith("*?") or w.endswith("*,")
        clean = w.replace("*", "")
        out.append((clean, b))
        if end: bold = False
    return out

@lru_cache(maxsize=256)
def layout_group(gi):
    lines, t_out = R.CAPTIONS[gi]
    rows = []   # each row: list of (word, wt, size, t)
    for li, (text, kind, t_in) in enumerate(lines):
        nxt = lines[li + 1][2] if li + 1 < len(lines) else min(t_out, t_in + 3)
        (rw, rs), (bw, bs), _ = KIND[kind]
        words = parse(text); n = len(words)
        per = 0.10 if kind != "n" else min(0.42, max(0.12, (nxt - t_in) / max(1, n) * 0.85))
        items = [(w, bw if b else rw, bs if b else rs, t_in + j * per) for j, (w, b) in enumerate(words)]
        row = []; width = 0
        for it in items:   # wrap long lines
            ww = mf(it[1], it[2]).getlength(it[0] + " ")
            if row and width + ww > MAXW: rows.append(row); row = []; width = 0
            row.append(it); width += ww
        rows.append(row)
    return rows

def draw_captions(c, t):
    for gi, (lines, t_out) in enumerate(R.CAPTIONS):
        if not (lines[0][2] - 0.05 <= t < t_out + 0.18): continue
        out = clamp((t - t_out) / 0.18)
        rows = layout_group(gi)
        y = (1470 if lines[0][2] < R.HOOK[3] else CAP_Y) - (len(rows) - 1) * LINE_H / 2
        for row in rows:
            widths = [mf(w, s).getlength(wd) for wd, w, s, _ in row]
            sp = 13
            total = sum(widths) + sp * (len(row) - 1)
            x = (W - total) / 2
            for (wd, wt, sz, tw), ww in zip(row, widths):
                u = t - tw
                if u > 0:
                    k = ease_out(clamp(u / 0.18))
                    im = word_img(wd, wt, sz)
                    paste_alpha(c, im, x - 12, y - im.height / 2 + (1 - k) * 16 - out * 10, k * (1 - out))
                x += ww + sp
            y += LINE_H

# ---- expert: full frame with hard jump-cut zooms (wide / close alternate per caption group) ----
FACE_X, FACE_Y = 262.0, 300.0
def zoom_at(t):
    starts = [0.0] + [g[0][0][2] for g in R.CAPTIONS] + [R.FOLLOW_T - 0.6]
    k = sum(1 for s in starts if s <= t + 1e-6)
    return 1.24 if k % 2 == 0 else 1.0

def expert_full(src, z):
    cw, ch = SW / z, SH / z
    x0 = clamp(FACE_X - cw / 2, 0, SW - cw); y0 = clamp(FACE_Y - FACE_Y / z, 0, SH - ch)
    return src.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

def in_broll(t):
    for b in R.BROLL:
        if b[0] <= t < b[1]: return b
    return None

@lru_cache(maxsize=1)
def band():
    yy = np.arange(H, dtype=np.float32)
    a = np.clip(1 - np.abs(yy - CAP_Y) / 260, 0, 1) ** 1.4 * 120
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = a[:, None].astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

# ---- hook: green rounded title box ----
@lru_cache(maxsize=1)
def hook_box():
    l1, l2 = R.HOOK[0], R.HOOK[1]
    f1, f2 = mf("ExtraBold", 54), mf("Bold", 34)
    w1, w2 = f1.getlength(l1), f2.getlength(l2)
    bw = int(max(w1, w2) + 64); bh = 150
    im = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + bw, 40 + bh), 26, fill=(0, 0, 0, 140))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((30, 30, 30 + bw, 30 + bh), 26, fill=(22, 104, 52, 255), outline=(255, 255, 255, 235), width=4)
    d.text((30 + bw / 2, 30 + 56), l1, font=f1, fill="white", anchor="mm")
    d.text((30 + bw / 2, 30 + 112), l2, font=f2, fill="white", anchor="mm")
    return im

# ---- follow pill (avatar from her own frame) ----
@lru_cache(maxsize=1)
def avatar():
    im = Image.open(os.path.join(HERE, "profile_shot.png")).convert("RGB").crop((196, 146, 464, 414)).resize((120, 120), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (480, 480), 0); ImageDraw.Draw(m).ellipse((0, 0, 479, 479), fill=255)
    im.putalpha(m.resize((120, 120), Image.LANCZOS))
    out = Image.new("RGBA", (136, 136), (0, 0, 0, 0)); ImageDraw.Draw(out).ellipse((0, 0, 135, 135), fill=(255, 255, 255, 255))
    out.alpha_composite(im, (8, 8)); return out

def badge(d, x, y, r=15):
    pts = [(x + (r if k % 2 == 0 else r * 0.8) * math.cos(math.pi * k / 8), y + (r if k % 2 == 0 else r * 0.8) * math.sin(math.pi * k / 8)) for k in range(16)]
    d.polygon(pts, fill=(0, 149, 246))
    d.line([(x - 6, y), (x - 1.5, y + 5), (x + 7, y - 5)], fill="white", width=4)

def pill(on):
    w_, h_ = 690, 136
    im = Image.new("RGBA", (w_ + 40, h_ + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((20, 28, 20 + w_, 28 + h_), h_ // 2, fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + w_, 20 + h_), h_ // 2, fill=(255, 255, 255, 250))
    f_ = mf("Bold", 32); d.text((180, 56), "logoped_muslimausman", font=f_, fill=(18, 18, 22), anchor="lm")
    badge(d, 180 + f_.getlength("logoped_muslimausman") + 24, 57)
    d.text((180, 93), "DEFEKTOLOG | LOGOPED | ABA - TERAPIST", font=mf("Medium", 19), fill=(110, 110, 118), anchor="lm")
    # toggle
    tx, ty = 180, 122
    d.rounded_rectangle((tx, ty, tx + 64, ty + 26), 13, fill=(0, 149, 246) if on > 0.5 else (205, 205, 210))
    kx = tx + 13 + 38 * on
    d.ellipse((kx - 10, ty + 3, kx + 10, ty + 23), fill="white")
    d.text((tx + 78, ty + 13), "FOLLOWING" if on > 0.5 else "FOLLOW", font=mf("Bold", 18), fill=(0, 149, 246) if on > 0.5 else (90, 90, 98), anchor="lm")
    return im

def render(i, src):
    t = i / FPS
    b = in_broll(t)
    if b:
        c = broll_frame(i)
        u = (t - b[0]) / max(0.1, b[1] - b[0]); sc = 1.0 + 0.05 * u
        c = c.resize((int(W * sc), int(H * sc)), Image.BILINEAR).crop((int((W * sc - W) / 2), int((H * sc - H) / 2), int((W * sc - W) / 2) + W, int((H * sc - H) / 2) + H))
    else:
        c = expert_full(src, zoom_at(t))
    c.alpha_composite(band())
    h0, h1 = R.HOOK[2], R.HOOK[3]
    if h0 <= t < h1 + 0.25:
        hb = hook_box(); k = spring(t - h0, w=12, z=0.6); out = clamp((t - h1) / 0.25)
        paste_alpha(c, hb, W / 2 - hb.width * k / 2, 1270 - hb.height * k / 2, clamp(k * 2) * (1 - out), max(0.01, k))
    draw_captions(c, t)
    u = t - R.FOLLOW_T
    if u > 0:
        av = avatar(); ka = spring(u, w=12, z=0.6)
        on = ease_out(clamp((u - 1.3) / 0.25))
        if u < 0.45:
            paste_alpha(c, av, 250 - av.width * ka / 2, 1430 - av.height * ka / 2, clamp(ka * 2), max(0.01, ka))
        else:
            p = pill(on).rotate(6, resample=Image.BICUBIC, expand=True)
            ke = ease_out(clamp((u - 0.45) / 0.35))
            vis = p.crop((0, 0, max(1, int(p.width * (0.28 + 0.72 * ke))), p.height))
            paste_alpha(c, vis, 250 - 92, 1430 - p.height / 2)
            paste_alpha(c, av, 250 - av.width / 2 + 2, 1430 - av.height / 2 + 26)
    return c.convert("RGB")
