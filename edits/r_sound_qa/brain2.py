
def _chaikin(pts, it=4):
    for _ in range(it):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts

def _curve(pts, it=4):
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(pts[-1]); pts = q
    return pts

import cv2
@lru_cache(maxsize=4)
def real_brain(size=300):
    """Anatomical lateral view of a human brain (frontal lobe left): Turing-pattern gyri on a lit dome,
    Sylvian fissure, central sulcus, temporal lobe, cerebellum folia and brainstem."""
    S = 2
    W_, H_ = size * S, int(size * 0.80) * S
    def P(pts): return [(x * W_, y * H_) for x, y in pts]
    def mask_poly(pts):
        m = Image.new("L", (W_, H_), 0); ImageDraw.Draw(m).polygon(P(_chaikin(pts)), fill=255)
        return np.asarray(m, np.float32) / 255
    cer = mask_poly([(0.03, 0.47), (0.06, 0.26), (0.18, 0.09), (0.38, 0.02), (0.60, 0.03), (0.79, 0.11), (0.93, 0.26),
                     (0.98, 0.44), (0.94, 0.58), (0.84, 0.64), (0.70, 0.64), (0.60, 0.72), (0.44, 0.77), (0.31, 0.74),
                     (0.24, 0.64), (0.19, 0.60), (0.10, 0.62), (0.04, 0.57)])
    cbm = mask_poly([(0.62, 0.66), (0.76, 0.60), (0.90, 0.62), (0.93, 0.72), (0.84, 0.82), (0.70, 0.84), (0.60, 0.77)])
    stm = mask_poly([(0.55, 0.70), (0.64, 0.70), (0.66, 0.86), (0.64, 0.99), (0.57, 0.99), (0.56, 0.84)])
    cbm = cbm * (1 - cer); stm = stm * (1 - cer) * (1 - cbm)

    # dome height from distance to silhouette
    def dome(m, r):
        d = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / (r * W_)
        return np.sqrt(np.clip(1 - (1 - np.clip(d, 0, 1)) ** 2, 0, 1))
    hc, hb, hs = dome(cer, 0.16), dome(cbm, 0.07), dome(stm, 0.03)

    # gyri: labyrinth via difference-of-Gaussians iteration, biased so crests are wide and sulci narrow
    rng = np.random.default_rng(11)
    x = rng.standard_normal((H_, W_)).astype(np.float32)
    s1 = W_ * 0.0068; s2 = s1 * 2.0
    for _ in range(16):
        x = cv2.GaussianBlur(x, (0, 0), s1) - cv2.GaussianBlur(x, (0, 0), s2)
        x = np.tanh(x / (np.abs(x).mean() + 1e-6) * 2.0)
    g = cv2.GaussianBlur((x + 1) * 0.5, (0, 0), s1 * 0.35)
    g = np.clip((g - 0.0) / 0.5, 0, 1) ** 0.55

    # deep fissures drawn as soft grooves
    fis = Image.new("L", (W_, H_), 0); fd = ImageDraw.Draw(fis)
    fd.line(P(_curve([(0.22, 0.62), (0.34, 0.56), (0.48, 0.50), (0.60, 0.44), (0.66, 0.36)])), fill=255, width=int(W_ * 0.016))
    fd.line(P(_curve([(0.55, 0.03), (0.52, 0.14), (0.54, 0.22), (0.49, 0.32), (0.47, 0.42), (0.44, 0.50)])), fill=230, width=int(W_ * 0.010))
    fd.line(P(_curve([(0.30, 0.66), (0.42, 0.66), (0.55, 0.62)])), fill=170, width=int(W_ * 0.008))
    fis = cv2.GaussianBlur(np.asarray(fis, np.float32) / 255, (0, 0), W_ * 0.004)

    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32); u, v = xx / W_, yy / H_
    folia = 0.5 + 0.5 * np.cos((np.hypot(u - 0.66, (v - 0.40) * 0.8)) * 2 * math.pi * 55)
    folia = folia ** 0.6

    relief = np.where(cbm > 0.5, folia * 0.7, g * (1 - fis * 0.95))
    H = hc * 0.55 * cer + hb * 0.45 * cbm + hs * 0.35 * stm + relief * 0.10 * np.clip(cer + cbm, 0, 1)
    gx = cv2.Sobel(H, cv2.CV_32F, 1, 0, ksize=3) * (W_ / 60)
    gy = cv2.Sobel(H, cv2.CV_32F, 0, 1, ksize=3) * (W_ / 60)
    n = np.dstack([-gx, -gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array((-0.5, -0.65, 0.58)); L /= np.linalg.norm(L)
    diff = np.clip((n * L).sum(2), 0, 1)
    hv = L + np.array((0, 0, 1.0)); hv /= np.linalg.norm(hv)
    spec = np.clip((n * hv).sum(2), 0, 1) ** 40 * 0.45
    ao = np.where(stm > 0.5, 1.0, 0.6 + 0.4 * np.clip(relief, 0, 1))

    crest = np.array((232, 186, 182), np.float32)
    deep = np.array((150, 88, 94), np.float32)
    t = np.clip(relief, 0, 1)[..., None]
    rgb = deep + (crest - deep) * t
    rgb = np.where((cbm > 0.5)[..., None], rgb * np.array((0.93, 0.86, 0.88)), rgb)
    rgb = np.where((stm > 0.5)[..., None], np.array((210, 166, 156), np.float32), rgb)
    rgb = rgb * (0.30 + 0.85 * diff)[..., None] * ao[..., None] + spec[..., None] * 255 * ao[..., None]
    rgb += np.array((40, 8, 14)) * (1 - diff)[..., None] * 0.4       # warm subsurface in shadow

    a = np.clip(cer + cbm + stm, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.8 * S)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA").resize((size, int(size * 0.80)), Image.LANCZOS)
    return with_shadow(im, 14, 16, 0.5)
