# ================= v12: full-screen version — zoom jump-cuts, keyword push-ins, glass icons beside the head =================
PUNCH[:] = [(1.70, 1.05, 2.70), (6.94, 1.06, 7.80), (12.32, 1.05, 13.40), (22.66, 1.05, 23.80), (31.66, 1.06, 32.30),
            (35.00, 1.05, 35.60), (41.20, 1.04, 42.40)]

def expert_crop(src, w, h, z=1.0, face_at=0.40, dx=0.0):
    """Full frame with a little top wall trimmed; zoom keeps the face high so subtitles stay on the chest."""
    im, P_ = _padded(src)
    z = max(1.0, z)
    ch = (float(SH) - 120.0) / z
    cw = ch * w / h
    top = clamp(546.0 - 0.585 * ch, 0, SH - ch)   # zoom pivots on the chin: it stays ~y1125, subtitles stay below
    cx = P_ + SW / 2
    return im.resize((int(w), int(h)), Image.BICUBIC, box=(cx - cw / 2, top, cx + cw / 2, top + ch)).convert("RGBA")

# (t_in, t_out, side, kind, name, tint) — side icons, never over the face
SIDE = [
    (0.05, 2.80, "L", "brand", "instagram", None),
    (2.88, 5.60, "L", "brand", "telegram", None), (3.86, 5.60, "R", "brand", "sheets", None),
    (5.76, 7.86, "L", "icon", "lightbulb", "amber"), (6.94, 7.86, "R", "brand", "notion", None),
    (8.90, 11.30, "L", "icon", "layers", "violet"), (10.56, 11.30, "R", "icon", "notebook-pen", "blue"),
    (12.32, 14.62, "R", "icon", "list-checks", "green"),
    (17.40, 19.70, "L", "icon", "link", "blue"), (18.64, 19.70, "R", "icon", "send", "violet"),
    (21.28, 25.20, "L", "icon", "user", "pink"), (22.66, 25.20, "R", "icon", "award", "gold"),
    (27.42, 28.10, "R", "icon", "puzzle", "teal"),
    (28.56, 32.30, "L", "icon", "puzzle", "teal"), (31.66, 32.30, "R", "icon", "x", "red"),
    (33.58, 35.62, "L", "icon", "notebook-pen", "blue"), (35.00, 35.62, "R", "icon", "gift", "pink"),
    (35.68, 39.10, "L", "icon", "gift", "pink"), (37.66, 39.10, "R", "icon", "layers", "violet"),
    (40.42, 42.30, "L", "icon", "message-circle", "blue"),
    (42.50, 43.60, "R", "icon", "link", "violet"),
]

def side_icons(c, t):
    for t0, t1, side, kind, name, tint in SIDE:
        if t < t0 or t > t1 + 0.3: continue
        out = ease_in(clamp((t - t1) / 0.3))
        x = 128 if side == "L" else W - 128
        y = 1030 + 10 * math.sin(t * 1.7 + (0 if side == "L" else 1.5))
        a = 1 - out
        if kind == "brand":
            brand(c, name, x, y, 190, t0, t, a=a, shine=(t - t0 - 0.3) / 0.7)
        else:
            gicon(c, name, x, y, 170, tint, t0, t, a=a, glyph_k=0.55, shine=(t - t0 - 0.3) / 0.7)

_render_full_prev = render
def render(i, src):
    t = i / FPS
    img = _render_full_prev(i, src).convert("RGBA")
    side_icons(img, t)
    return img.convert("RGB")
