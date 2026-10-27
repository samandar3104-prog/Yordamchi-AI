#!/usr/bin/env python3
"""Cut the reference characters out of their backgrounds (GrabCut + white-key), write RGBA sprites."""
import sys
import cv2
import numpy as np
from PIL import Image

D = sys.argv[1]

def grabcut(img, rect, fg_hint=None, bg_hint=None, iters=6):
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
    if fg_hint is not None or bg_hint is not None:
        if fg_hint is not None: mask[fg_hint] = cv2.GC_FGD
        if bg_hint is not None: mask[bg_hint] = cv2.GC_BGD
        cv2.grabCut(img, mask, None, bgd, fgd, 4, cv2.GC_INIT_WITH_MASK)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

def white_bg(img, thr=238):
    """Background = near-white region connected to the border."""
    near = (img.min(axis=2) >= thr).astype(np.uint8)
    h, w = near.shape
    ff = near.copy(); m = np.zeros((h + 2, w + 2), np.uint8)
    for (x, y) in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2)):
        if ff[y, x] == 1: cv2.floodFill(ff, m, (x, y), 2)
    return ff == 2

def finish(img_bgr, alpha, name, crop_bottom=None):
    k = np.ones((3, 3), np.uint8)
    a = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, k, iterations=1)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((a > 0).astype(np.uint8))
    if n > 1:
        big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]); a = np.where(lab == big, 255, 0).astype(np.uint8)
    a = cv2.GaussianBlur(a, (5, 5), 0)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    out = np.dstack([rgb, a])
    if crop_bottom: out = out[:crop_bottom]
    ys, xs = np.where(out[..., 3] > 10)
    out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    Image.fromarray(out, "RGBA").save(f"{D}/{name}.png")
    print(name, out.shape)

# boy on a street: GrabCut seeded by a rectangle, sky/road corners forced to background
boy = cv2.cvtColor(np.array(Image.open(f"{D}/boy.webp").convert("RGB")), cv2.COLOR_RGB2BGR)
h, w = boy.shape[:2]
bg = np.zeros((h, w), bool); bg[:, :150] = True; bg[:, 600:] = True; bg[:80, :] = True
fg = np.zeros((h, w), bool); fg[300:450, 300:440] = True; fg[480:760, 280:450] = True; fg[200:290, 260:470] = True
a = grabcut(boy, (160, 80, 420, 1120), fg, bg)
finish(boy, a, "boy_cut")

# mom on white: white key, then GrabCut to clean edges; the artist credit at bottom-right is outside the figure
mom = cv2.cvtColor(np.array(Image.open(f"{D}/mom.webp").convert("RGB")), cv2.COLOR_RGB2BGR)
wb = white_bg(cv2.cvtColor(mom, cv2.COLOR_BGR2RGB))
a = np.where(wb, 0, 255).astype(np.uint8)
a[1000:, 700:] = 0
finish(mom, a, "mom_cut")

logo = cv2.cvtColor(np.array(Image.open(f"{D}/logo.png").convert("RGB")), cv2.COLOR_RGB2BGR)
wb = white_bg(cv2.cvtColor(logo, cv2.COLOR_BGR2RGB), thr=240)
a = np.where(wb, 0, 255).astype(np.uint8)
finish(logo, a, "logo_cut")

# preview on the reel's dark background
prev = Image.new("RGB", (1500, 700), (40, 20, 14))
x = 10
for n in ("boy_cut", "mom_cut", "logo_cut"):
    im = Image.open(f"{D}/{n}.png"); s = 680 / im.height
    im = im.resize((int(im.width * s), 680))
    prev.paste(im, (x, 10), im); x += im.width + 20
prev.save(f"{D}/cut_preview.png")
