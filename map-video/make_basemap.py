"""Builds a crisp, high-res light basemap (Yandex-like style) from the reference screenshot.

City boundary is segmented from the reference; roads/labels are redrawn as vectors.
Map units = pixels of the 620x376 reference image. Output texture is SCALE x larger.
"""
import json, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REF = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else '.'
SCALE = 8
W0, H0 = 620, 376
W, H = W0 * SCALE, H0 * SCALE

im = cv2.imread(REF)
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(int)
h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
city = ((h <= 19) & (s >= 30) & (v > 150)).astype(np.uint8) * 255
city = cv2.morphologyEx(city, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
n, lab, st, _ = cv2.connectedComponentsWithStats(city)
city = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8) * 255
city = cv2.morphologyEx(city, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
city = cv2.morphologyEx(city, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))  # drop thin road spurs
cnts, _ = cv2.findContours(city, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(cnts, key=cv2.contourArea)
cmask = np.zeros((H0, W0), np.uint8); cv2.drawContours(cmask, [cnt], -1, 255, -1)

def smooth_poly(c, k=9):
    pts = c.reshape(-1, 2).astype(float)
    ker = np.ones(k) / k
    xs = np.convolve(np.r_[pts[-k:, 0], pts[:, 0], pts[:k, 0]], ker, 'same')[k:-k]
    ys = np.convolve(np.r_[pts[-k:, 1], pts[:, 1], pts[:k, 1]], ker, 'same')[k:-k]
    return np.stack([xs, ys], 1)

city_poly = smooth_poly(cnt)[::3]

def clip_to_city(poly, inside=True):
    m = np.zeros((H0 * 4, W0 * 4), np.uint8)
    cv2.fillPoly(m, [np.int32(np.array(poly) * 4)], 255)
    cm = cv2.resize(cmask, (W0 * 4, H0 * 4), interpolation=cv2.INTER_LINEAR) > 127
    m = (m > 0) & (cm if inside else ~cm)
    m = m.astype(np.uint8) * 255
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2) / 4.0
    return c.round(2).tolist()

# approximate districts (reference-image pixel coords), clipped to the city outline
UCHTEPA = [(118, 132), (200, 134), (207, 160), (204, 182), (190, 189), (165, 193), (118, 201)]
CHILONZOR = [(118, 201), (165, 193), (190, 189), (204, 182), (216, 186), (240, 192), (252, 212), (232, 226), (200, 236), (118, 242)]
ZANGIOTA = [(118, 200), (150, 210), (168, 236), (182, 268), (196, 300), (186, 338), (140, 344), (100, 326), (92, 284), (100, 240)]
districts = {
    'uchtepa': clip_to_city(UCHTEPA),
    'chilonzor': clip_to_city(CHILONZOR),
    'zangiota': clip_to_city(ZANGIOTA, inside=False),
}

# ---------- draw basemap ----------
img = Image.new('RGB', (W, H), (246, 243, 236))
d = ImageDraw.Draw(img, 'RGBA')
S = lambda pts: [(x * SCALE, y * SCALE) for x, y in pts]

rng = np.random.default_rng(3)
# soft vegetation / field patches
for _ in range(140):
    x, y = rng.uniform(0, W), rng.uniform(0, H)
    r = rng.uniform(40, 220)
    d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(222, 236, 205, 60))
img = img.filter(ImageFilter.GaussianBlur(25))
d = ImageDraw.Draw(img, 'RGBA')

# minor roads (outside + inside), light gray
def poly_line(pts, col, w):
    d.line(S(pts), fill=col, width=w, joint='curve')

for _ in range(90):
    x, y = rng.uniform(0, W0), rng.uniform(0, H0)
    a = rng.uniform(0, np.pi)
    L = rng.uniform(30, 120)
    pts = [(x + np.cos(a) * L * t + rng.normal(0, 3), y + np.sin(a) * L * t + rng.normal(0, 3)) for t in np.linspace(-.5, .5, 6)]
    poly_line(pts, (214, 210, 202, 255), 5)

# city fill & dense street texture
city_s = S(city_poly)
d.polygon(city_s, fill=(250, 221, 193))
street = Image.new('L', (W, H), 0)
ds = ImageDraw.Draw(street)
for ang in (0.35, 0.35 + np.pi / 2):
    ca, sa = np.cos(ang), np.sin(ang)
    for off in np.arange(-W, W, rng.uniform(30, 50)):
        off += rng.uniform(-10, 10)
        p0 = (W / 2 + ca * off - sa * 4000, H / 2 + sa * off + ca * 4000)
        p1 = (W / 2 + ca * off + sa * 4000, H / 2 + sa * off - ca * 4000)
        ds.line([p0, p1], fill=int(rng.uniform(25, 60)), width=3)
cm_big = Image.fromarray(cv2.resize(cmask, (W, H), interpolation=cv2.INTER_LINEAR)).filter(ImageFilter.GaussianBlur(2))
street = Image.fromarray((np.array(street).astype(float) * (np.array(cm_big) / 255.0)).astype(np.uint8))
img.paste(Image.new('RGB', (W, H), (236, 190, 150)), (0, 0), street)
d = ImageDraw.Draw(img, 'RGBA')

# water
WATER = [[(66, 205), (72, 230), (75, 262), (70, 300)], [(392, 214), (398, 228), (404, 240)], [(410, 255), (420, 270)]]
for w in WATER:
    poly_line(w, (160, 200, 235, 255), 14)
d.ellipse(S([(212, 312), (224, 320)]), fill=(160, 200, 235))

# main roads (orange)
CX, CY = 282, 168
ring = [(CX + 80 * np.cos(t), CY + 68 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 200)]
ROADS = [
    [(287, 140), (296, 100), (305, 55), (315, 20)],
    [(287, 140), (250, 95), (228, 60), (210, 28)],
    [(287, 140), (240, 150), (200, 150), (160, 146), (120, 140), (60, 132)],
    [(287, 140), (255, 185), (225, 225), (180, 262), (130, 300), (88, 328)],
    [(287, 140), (295, 200), (292, 250), (270, 330), (262, 376)],
    [(287, 140), (330, 175), (370, 215), (400, 260), (420, 320), (430, 376)],
    [(287, 140), (340, 128), (380, 135), (430, 150), (520, 160), (620, 165)],
    [(287, 140), (330, 105), (370, 80), (420, 60), (500, 40), (560, 20)],
    [(225, 245), (300, 244), (330, 252), (360, 250)],
    [(150, 70), (190, 55), (230, 42), (275, 38)],
]
for r in ROADS:
    poly_line(r, (240, 170, 100, 255), 18)
poly_line(ring, (240, 170, 100, 255), 18)
for r in ROADS:
    poly_line(r, (255, 214, 140, 255), 8)
poly_line(ring, (255, 214, 140, 255), 8)

# city boundary
d.line(city_s + city_s[:1], fill=(226, 118, 92, 255), width=12, joint='curve')

# labels
F = lambda w, sz: ImageFont.truetype(f'/usr/share/fonts/opentype/inter/Inter-{w}.otf', sz)
def label(x, y, ru, uz, big=False, dot=True):
    X, Y = x * SCALE, y * SCALE
    f1 = F('SemiBold', 120 if big else 64)
    f2 = F('Regular', 50)
    if dot:
        d.ellipse([X - 12, Y - 12, X + 12, Y + 12], fill=(120, 120, 120))
        X += 26
    d.text((X, Y), ru, font=f1, fill=(60, 60, 60), anchor='lm', stroke_width=6, stroke_fill=(255, 255, 255))
    if uz:
        d.text((X, Y + (100 if big else 60)), uz, font=f2, fill=(120, 120, 120), anchor='lm', stroke_width=5, stroke_fill=(255, 255, 255))

TOWNS = [
    ('Келес', 'Keles', 200, 26), ('Сагбан', "Sag'bon", 165, 32), ('Хасанбай', 'Hasanboy', 245, 20), ('Шуро', 'Shuro', 318, 12),
    ('Гулистан', 'Guliston', 315, 36), ('Янгиюль', "Yangiyo'l", 372, 26), ('Салар', 'Salor', 358, 60), ('Дурмон', "Do'rmon", 398, 74),
    ('Каттасув', 'Kattasuv', 412, 106), ('Кибрай', "Qibray", 448, 46), ('Гульзар', 'Gulzor', 355, 133), ('Чинар', 'Chinor', 375, 162),
    ('Аргын', 'Argin', 378, 185), ('Шахризар', '', 372, 226), ('Иик-Ота', 'Yik Ota', 382, 248), ('Кипчак', 'Qipchoq', 320, 262),
    ('Закиров', 'Zokirov', 260, 275), ('Бабур', 'Bobur', 202, 262), ('Эркин', 'Erkin', 160, 255), ('Эшангузар', "Eshong'uzor", 128, 222),
    ('Назарбек', 'Nazarbek', 116, 150), ('Дамарык', '', 130, 66), ('Рамадан', 'Ramazon', 96, 110), ('Тарнау', 'Tarnov', 96, 180),
    ('Хасково', 'Xaskovo', 72, 208), ('Гулистан', 'Guliston', 24, 252), ('Далигузар', "Dalig'uzor", 100, 252),
    ('Зангиата', 'Zangiota', 142, 288), ('Багзар', "Bog'zor", 148, 322), ('Чартак', 'Chortoq', 212, 322), ('Шоликор', 'Sholikor', 312, 308),
    ('Кумарык', 'Qumariq', 240, 240), ('Казахаул', 'Qozoqovul', 296, 236), ('Шамсиабад', 'Shamsiobod', 60, 78), ('Дустлик', "Do'stlik", 210, 350),
    ('Янгитурмуш', '', 300, 345), ('Ченгтепа', '', 92, 325), ('Хитай-Тепа', '', 436, 142), ('Балта', 'Balta', 434, 182),
]
for ru, uz, x, y in TOWNS:
    label(x, y, ru, uz)

def dlabel(x, y, t, sz=52):
    d.text((x * SCALE, y * SCALE), t, font=F('Medium', sz), fill=(140, 110, 100), anchor='mm', stroke_width=4, stroke_fill=(250, 225, 200))
dlabel(262, 92, 'Юнусабадский р-н'); dlabel(290, 182, 'Мирабадский р-н'); dlabel(318, 198, 'Яшнабадский р-н')
dlabel(266, 120, 'Шайхантахурский р-н', 44); dlabel(250, 160, 'Алмазарский р-н', 44)
d.text((262 * SCALE, 140 * SCALE), 'ТАШКЕНТ', font=F('Bold', 170), fill=(50, 45, 45), anchor='mm', stroke_width=10, stroke_fill=(250, 225, 200))
d.text((262 * SCALE, 154 * SCALE), 'Toshkent', font=F('Medium', 80), fill=(90, 80, 80), anchor='mm', stroke_width=6, stroke_fill=(250, 225, 200))
dlabel(176, 176, 'Учтепинский р-н', 48); dlabel(214, 197, 'Чиланзарский р-н', 48)

img.save(f'{OUT}/basemap.jpg', quality=92)
json.dump({'w': W0, 'h': H0, 'city': city_poly.round(2).tolist(), 'districts': districts}, open(f'{OUT}/geo.json', 'w'))
print('ok', W, H)
