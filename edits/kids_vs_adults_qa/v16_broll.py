# ================= v16: B-roll first — expert full / round / rounded card / hidden (voice only); no 50/50 panels =================
CIRC = (690, 268, 330)            # top-right round frame (below the IG top bar, above the subtitles)
CARDR = (650, 262, 370, 480, 44)  # top-right rounded card
FACE_SRC = 282.0                  # face centre in the 480x854 source

def _geo(kind):
    if kind == "full": return dict(r=(0, 0, W, H), rad=0.0, cy=427.0, ch=854.0, a=1.0)
    if kind == "circle":
        x, y, d = CIRC; return dict(r=(x, y, d, d), rad=d / 2, cy=FACE_SRC + 10, ch=300.0, a=1.0)
    if kind in ("card", "follow"):
        x, y, w_, h_, rr = CARDR
        if kind == "follow": x, y, d = CIRC; return dict(r=(x, y, d, d), rad=d / 2, cy=FACE_SRC + 10, ch=300.0, a=1.0)
        return dict(r=(x, y, w_, h_), rad=rr, cy=FACE_SRC + 70, ch=430.0, a=1.0)
    x, y, d = CIRC
    return dict(r=(x + d * 0.3, y + d * 0.3, d * 0.4, d * 0.4), rad=d * 0.2, cy=FACE_SRC + 10, ch=300.0, a=0.0)

def _mixg(A, B, k):
    return {key: (tuple(lerp(p, q, k) for p, q in zip(A[key], B[key])) if key == "r" else lerp(A[key], B[key], k)) for key in A}

_BR = {"p": None, "next": -1}
def broll_frame(i):
    if _BR["p"] is None or _BR["next"] != i:
        if _BR["p"] is not None: _BR["p"].kill()
        _BR["p"] = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{i / FPS:.4f}", "-i", os.path.join(HERE, "broll_track.mp4"),
                                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    b = _BR["p"].stdout.read(W * H * 3)
    _BR["next"] = i + 1
    if len(b) < W * H * 3: return Image.new("RGBA", (W, H), (0, 0, 0, 255))
    return Image.frombytes("RGB", (W, H), b).convert("RGBA")

def expert_layer(c, src, G, z):
    x, y, w_, h_ = G["r"]
    if G["a"] <= 0.01 or w_ < 8 or h_ < 8: return
    W_, H_ = int(round(w_)), int(round(h_))
    ch = G["ch"] / max(1.0, z); cw = ch * W_ / H_
    if cw > SW: cw = SW; ch = cw * H_ / W_
    top = clamp(G["cy"] - ch / 2, 0, SH - ch)
    fr = src.resize((W_, H_), Image.BICUBIC, box=(SW / 2 - cw / 2, top, SW / 2 + cw / 2, top + ch)).convert("RGBA")
    rad = int(G["rad"])
    if rad > 2:
        pad = 50
        sh = Image.new("RGBA", (W_ + pad * 2, H_ + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 16, pad + W_, pad + H_ + 16), rad, fill=(0, 0, 0, 150))
        paste_alpha(c, sh.filter(ImageFilter.GaussianBlur(18)), x - pad, y - pad, G["a"])
        fr.putalpha(_rr_mask(W_, H_, rad))
    paste_alpha(c, fr, x, y, G["a"])
    if rad > 2:
        ring = Image.new("RGBA", (W_ + 14, H_ + 14), (0, 0, 0, 0))
        ImageDraw.Draw(ring).rounded_rectangle((2, 2, W_ + 11, H_ + 11), rad + 5, outline=(246, 198, 92, 235), width=5)
        paste_alpha(c, ring, x - 7, y - 7, G["a"])

@lru_cache(maxsize=1)
def profile_card():
    im = Image.open(os.path.join(HERE, "profile_ig.png")).convert("RGBA")
    w_ = 900; h_ = int(im.height * w_ / im.width)
    im = im.resize((w_, h_), Image.LANCZOS); im.putalpha(_rr_mask(w_, h_, 34))
    return with_shadow(im, 22, 20, 0.6)

@lru_cache(maxsize=1)
def cap_band():
    yy = np.arange(H, dtype=np.float32)
    a = np.clip(1 - np.abs(yy - 1480) / 330, 0, 1) ** 1.3 * 165
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 0] = 24; arr[..., 1] = 14; arr[..., 2] = 10; arr[..., 3] = a[:, None].astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

def render(i, src):
    t = i / FPS
    si = seg_at(t); a, b, lay, kind, zb = SEG[si]
    G = _geo(kind); since = t - a
    if si > 0 and since < 0.7:
        G = _mixg(_geo(SEG[si - 1][3]), G, clamp(spring(since, w=11, z=0.82), 0, 1.02))
    full_now = kind == "full"
    prev_full = si > 0 and SEG[si - 1][3] == "full"
    # base picture: B-roll everywhere except full-screen expert parts (cross-fade 0.35 s at the switches)
    if full_now and not (prev_full is False and since < 0.35):
        c = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        c = broll_frame(i)
        sc = 1.0 + 0.04 * clamp(since / max(0.1, b - a))      # slow push-in on every B-roll shot
        if sc > 1.001:
            c = c.resize((int(W * sc), int(H * sc)), Image.BILINEAR).crop((int((W * sc - W) / 2), int((H * sc - H) / 2), int((W * sc - W) / 2) + W, int((H * sc - H) / 2) + H))
    z = full_zoom(t, zb) if full_now else 1.0
    if full_now:
        k = clamp(since / 0.35) if not prev_full else 1.0
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); expert_layer(layer, src, _geo("full"), z)
        paste_alpha(c, layer, 0, 0, k)
    else:
        if prev_full and since < 0.35:     # the full-screen expert shrinks into her frame while the B-roll fades in
            pass
        expert_layer(c, src, G, 1.0)
    if kind == "follow":
        u = since
        pc = profile_card()
        kk = spring(u - 0.3, w=10, z=0.62) if u > 0.3 else 0
        if kk > 0: paste_alpha(c, pc, W / 2 - pc.width * kk / 2, 820 - pc.height * kk / 2, clamp(kk * 2), kk)
        tu = t - TAP_T
        if -0.3 < tu < 0.8:   # the "Follow" button gets tapped
            bx, by = W / 2 - 900 / 2 + 900 * 0.22, 820 - pc.height / 2 + 22 + (pc.height - 64) * 0.86
            g = glow(110, (255, 255, 255)); paste_alpha(c, g, bx - 55, by - 55, 0.6 * clamp((tu + 0.3) / 0.2) * (1 - clamp((tu - 0.5) / 0.3)))
    c.alpha_composite(SCRIM)
    if not full_now: c.alpha_composite(cap_band())     # B-roll is often pale: a soft dark band keeps white text readable
    draw_captions(c, t)
    return c.convert("RGB")
