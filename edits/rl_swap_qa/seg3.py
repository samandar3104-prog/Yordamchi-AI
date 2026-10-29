import sys, cv2, numpy as np
from PIL import Image
D = sys.argv[1]
def cut(src, name, tol=26):
    rgb = np.array(Image.open(f"{D}/{src}").convert("RGB")).astype(np.int16)
    if src == 'mom3.png': rgb[660:, 520:] = rgb[5, 5]   # paint out the artist credit
    h, w = rgb.shape[:2]
    bgc = np.median(np.concatenate([rgb[:20].reshape(-1, 3), rgb[:, :20].reshape(-1, 3), rgb[:, -20:].reshape(-1, 3)]), 0)
    near = (np.abs(rgb - bgc).max(2) < tol).astype(np.uint8)
    ff = near.copy(); m = np.zeros((h + 2, w + 2), np.uint8)
    for (x, y) in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2)):
        if ff[y, x] == 1: cv2.floodFill(ff, m, (x, y), 2)
    a = np.where(ff == 2, 0, 255).astype(np.uint8)
    # grabcut refine
    bgr = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    gm = np.where(a > 0, cv2.GC_PR_FGD, cv2.GC_BGD).astype(np.uint8)
    er = cv2.erode(a, np.ones((15, 15), np.uint8)); gm[er > 0] = cv2.GC_FGD
    bg_, fg_ = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(bgr, gm, None, bg_, fg_, 4, cv2.GC_INIT_WITH_MASK)
    a = np.where((gm == 1) | (gm == 3), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0).astype(np.uint8))
    big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); a = np.where(lab == big, 255, 0).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    # holes between legs + floor shadow: anything bg-like or light-grey in the lower part goes
    y0 = int(h * 0.72)
    low = rgb[y0:].astype(np.int16)
    nr = (np.abs(low - bgc).max(2) < 48).astype(np.uint8)
    hh = nr.shape[0]; mm = np.zeros((hh + 2, w + 2), np.uint8)
    for x in range(0, w, 7):
        if nr[hh - 1, x] == 1: cv2.floodFill(nr, mm, (x, hh - 1), 2)
    a[y0:][nr == 2] = 0
    a = cv2.morphologyEx(a, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats((a > 0).astype(np.uint8))
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 1500]
    a = np.where(np.isin(lab, keep), 255, 0).astype(np.uint8)
    a = cv2.erode(a, np.ones((3, 3), np.uint8))
    a = cv2.GaussianBlur(a, (5, 5), 0)
    out = np.dstack([rgb.astype(np.uint8), a])
    ys, xs = np.where(a > 10); out = out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    Image.fromarray(out, "RGBA").save(f"{D}/{name}.png"); print(name, out.shape, bgc)

import sys as _s
cut(_s.argv[2], _s.argv[3], tol=int(_s.argv[4]))
