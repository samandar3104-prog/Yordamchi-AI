"""Builds a Yandex-style 3D map of west Tashkent from Overture Maps (OSM-based) data.

Inputs (from fetch.py): segment, building, water, land_use, division_area, place, wide_segment, wide_water parquet.
Outputs: wide.jpg, detail.jpg (ground textures), buildings.bin (3D mesh), scene.json (bounds, districts, POIs).
World units: 1 unit = 10 m, origin at LON0/LAT0, +x east, +z south.
"""
import json, math, struct, sys
import numpy as np, shapely, pyarrow.parquet as pq
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import transform
from PIL import Image, ImageDraw, ImageFont
import mapbox_earcut as earcut

DATA, OUT = sys.argv[1], sys.argv[2]
LON0, LAT0 = 69.19, 41.28
KX, KZ = 111320 * math.cos(math.radians(LAT0)), 110574
def W(lon, lat): return ((lon - LON0) * KX / 10, -(lat - LAT0) * KZ / 10)

def read(name, cols=None):
    t = pq.read_table(f'{DATA}/{name}.parquet', columns=cols).to_pylist()
    for r in t:
        r['g'] = shapely.from_wkb(r['geometry'])
        r['name'] = ((r.get('names') or {}) or {}).get('primary') or ''
    return t

FONT = lambda w, s: ImageFont.truetype(f'/usr/share/fonts/opentype/inter/Inter-{w}.otf', s)

class Canvas:
    def __init__(self, lon0, lat0, lon1, lat1, width):
        self.lon0, self.lat0, self.lon1, self.lat1 = lon0, lat0, lon1, lat1
        self.wm = (lon1 - lon0) * KX; self.hm = (lat1 - lat0) * KZ
        self.W = width; self.H = int(round(width * self.hm / self.wm))
        self.mpp = self.wm / self.W
        self.img = Image.new('RGB', (self.W, self.H), (245, 243, 239))
        self.d = ImageDraw.Draw(self.img, 'RGBA')
    def px(self, lon, lat): return ((lon - self.lon0) * KX / self.mpp, (self.lat1 - lat) * KZ / self.mpp)
    def coords(self, g): return [self.px(x, y) for x, y in g.coords]
    def poly(self, g, fill, outline=None, w=1):
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.geom_type != 'Polygon': continue
            self.d.polygon(self.coords(p.exterior), fill=fill, outline=outline, width=w)
            for i in p.interiors: self.d.polygon(self.coords(i), fill=(245, 243, 239))
    def line(self, g, col, w):
        for l in (g.geoms if hasattr(g, 'geoms') else [g]):
            if l.geom_type not in ('LineString', 'LinearRing'): continue
            c = self.coords(l)
            if len(c) > 1: self.d.line(c, fill=col, width=max(1, int(round(w))), joint='curve')
    def world_bounds(self):
        x0, z0 = W(self.lon0, self.lat1); x1, z1 = W(self.lon1, self.lat0)
        return [x0, z0, x1, z1]

LAND = {('park', 'park'): (205, 233, 190), ('managed', 'grass'): (214, 237, 200), ('recreation', 'pitch'): (200, 232, 190),
        ('cemetery', 'cemetery'): (220, 230, 212), ('agriculture', 'farmland'): (238, 240, 222), ('horticulture', 'orchard'): (220, 236, 205),
        ('developed', 'industrial'): (235, 230, 236), ('residential', 'residential'): (240, 237, 232), ('education', 'school'): (246, 238, 218),
        ('education', 'university'): (246, 238, 218), ('medical', 'hospital'): (248, 230, 230)}
WATER_COL = (170, 212, 245)
# (casing, fill, width meters)
ROAD = {'motorway': ((228, 160, 60), (255, 209, 110), 26), 'trunk': ((228, 160, 60), (255, 209, 110), 24),
        'primary': ((226, 186, 110), (255, 233, 160), 19), 'secondary': ((214, 206, 194), (255, 255, 255), 15),
        'tertiary': ((214, 206, 194), (255, 255, 255), 12), 'residential': ((222, 216, 206), (255, 255, 255), 8),
        'unclassified': ((222, 216, 206), (255, 255, 255), 8), 'living_street': ((226, 221, 212), (253, 253, 251), 5.5),
        'service': ((226, 221, 212), (253, 253, 251), 4.5), 'pedestrian': ((226, 221, 212), (250, 248, 244), 4)}

def draw_roads(cv, segs, scale=1.0, minw=1.0):
    order = ['pedestrian', 'service', 'living_street', 'unclassified', 'residential', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway']
    rails = [r for r in segs if r['subtype'] == 'rail' and r['class'] in ('standard_gauge', 'narrow_gauge')]
    for r in rails: cv.line(r['g'], (175, 170, 165), max(minw, 3 * scale / cv.mpp))
    for phase in (0, 1):
        for cls in order:
            if cls not in ROAD: continue
            cas, fill, wm = ROAD[cls]
            w = max(minw, wm * scale / cv.mpp)
            for r in segs:
                if r['subtype'] == 'road' and r['class'] == cls:
                    cv.line(r['g'], cas if phase == 0 else fill, w + (max(2, w * 0.28) if phase == 0 else 0))

def street_labels(cv, segs, classes, size, every_m):
    from collections import defaultdict
    groups = defaultdict(list)
    for r in segs:
        if r['subtype'] == 'road' and r['class'] in classes and r['name']:
            groups[r['name']].append(r['g'])
    f = FONT('Medium', size)
    placed = []
    for name, gs in groups.items():
        merged = shapely.line_merge(shapely.union_all(gs))
        lines = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
        for l in lines:
            pts = np.array(cv.coords(l))
            if len(pts) < 2: continue
            seglen = np.hypot(*np.diff(pts, axis=0).T); L = seglen.sum()
            tw = f.getlength(name)
            if L < tw * 1.6: continue
            n = max(1, int(L * cv.mpp / every_m))
            for k in range(n):
                s = L * (k + 0.5) / n
                i = np.searchsorted(np.cumsum(seglen), s)
                i = min(i, len(seglen) - 1)
                a, b = pts[i], pts[i + 1]
                cx, cy = (a + b) / 2
                if any(math.hypot(cx - px, cy - py) < tw * 1.2 for px, py in placed): continue
                ang = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
                if ang > 90: ang -= 180
                if ang < -90: ang += 180
                pad = 8
                tile = Image.new('RGBA', (int(tw) + pad * 2, size * 2), (0, 0, 0, 0))
                td = ImageDraw.Draw(tile)
                td.text((pad, size), name, font=f, fill=(85, 80, 75, 255), anchor='lm', stroke_width=max(2, size // 7), stroke_fill=(255, 255, 255, 235))
                tile = tile.rotate(ang, expand=True, resample=Image.BICUBIC)
                cv.img.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)
                placed.append((cx, cy))

def largest(g):
    if isinstance(g, MultiPolygon): return max(g.geoms, key=lambda p: p.area)
    return g

# ---------------- load ----------------
segs = read('segment', ['names', 'subtype', 'class', 'geometry'])
wsegs = read('wide_segment', ['names', 'subtype', 'class', 'geometry'])
water = read('water', ['names', 'subtype', 'class', 'geometry'])
wwater = read('wide_water', ['names', 'subtype', 'class', 'geometry'])
land = read('land_use', ['names', 'subtype', 'class', 'geometry'])
divs = read('division_area', ['names', 'subtype', 'admin_level', 'class', 'geometry'])
DIV = {r['name']: largest(r['g']) for r in divs if r['subtype'] in ('county', 'region')}
city = DIV['Toshkent']
districts = {'uchtepa': DIV['Uchtepa Tumani'], 'chilonzor': DIV['Chilonzor Tumani'], 'zangiota': DIV['Zangiota Tumani']}

# ---------------- wide texture ----------------
wide = Canvas(68.98, 41.10, 69.48, 41.45, 4096)
for r in wwater:
    g = r['g']
    if g.geom_type in ('Polygon', 'MultiPolygon'): wide.poly(g, WATER_COL)
    elif r['class'] in ('canal', 'river'): wide.line(g, WATER_COL, 3)
wide.poly(city, (241, 237, 229))
for r in wwater:
    if r['g'].geom_type in ('Polygon', 'MultiPolygon'): wide.poly(r['g'], WATER_COL)
    elif r['class'] in ('canal', 'river'): wide.line(r['g'], WATER_COL, 3)
for name, g in DIV.items():
    if name.endswith('Tumani') or name.endswith('tumani'):
        wide.line(g.exterior, (190, 165, 215, 160), 2)
wide.line(city.exterior, (165, 120, 210), 5)
draw_roads(wide, wsegs, scale=2.2, minw=1.5)
# locality labels
for r in divs:
    if r['subtype'] == 'locality' and r['name']:
        c = r['g'].representative_point(); x, y = wide.px(c.x, c.y)
        wide.d.text((x, y), r['name'].replace(' MFY', ''), font=FONT('Medium', 26), fill=(110, 105, 100), anchor='mm', stroke_width=3, stroke_fill=(255, 255, 255))
RU = {'Uchtepa Tumani': 'Учтепинский р-н', 'Chilonzor Tumani': 'Чиланзарский р-н', 'Zangiota Tumani': 'Зангиатинский р-н',
      'Yunusobod Tumani': 'Юнусабадский р-н', 'Olmazor Tumani': 'Алмазарский р-н', 'Shayhontohur Tumani': 'Шайхантахурский р-н',
      'Mirzo Ulug‘bek Tumani': 'Мирзо-Улугбекский р-н', 'Yakkasaroy Tumani': 'Яккасарайский р-н', 'Mirobod Tumani': 'Мирабадский р-н',
      'Yashnobod Tumani': 'Яшнабадский р-н', 'Sergeli tumani': 'Сергелийский р-н', 'Bektemir Tumani': 'Бектемирский р-н',
      'Yangi hayot Tumani': 'Янгихаётский р-н', 'Yangi Toshkent Tumani': 'Янги Ташкент', 'Qibray Tumani': 'Кибрайский р-н',
      'Toshkent Tumani': 'Ташкентский р-н', "Yangiyo'l Tumani": 'Янгиюльский р-н'}
for name, ru in RU.items():
    if name in DIV:
        c = DIV[name].representative_point(); x, y = wide.px(c.x, c.y)
        wide.d.text((x, y), ru, font=FONT('SemiBold', 34), fill=(150, 110, 185), anchor='mm', stroke_width=4, stroke_fill=(255, 255, 255))
x, y = wide.px(69.27, 41.315)
wide.d.text((x, y), 'Ташкент', font=FONT('Bold', 64), fill=(60, 55, 55), anchor='mm', stroke_width=6, stroke_fill=(255, 255, 255))
wide.img.save(f'{OUT}/wide.jpg', quality=90)

# ---------------- detail texture ----------------
det = Canvas(69.13, 41.235, 69.25, 41.31, 8192)
det.poly(city, (241, 237, 229))
for r in land:
    key = (r['subtype'], r['class'])
    if key in LAND and r['g'].geom_type in ('Polygon', 'MultiPolygon'): det.poly(r['g'], LAND[key])
for r in water:
    g = r['g']
    if g.geom_type in ('Polygon', 'MultiPolygon'): det.poly(g, WATER_COL)
    elif r['class'] in ('canal', 'river', 'stream'): det.line(g, WATER_COL, max(2, 8 / det.mpp))
    elif r['class'] in ('ditch', 'drain'): det.line(g, WATER_COL, max(1.5, 3 / det.mpp))
# flat building footprints (3D ones are drawn on top in the focus zone)
blds = read('building', ['height', 'num_floors', 'class', 'geometry'])
for r in blds:
    g = r['g']
    if g.geom_type in ('Polygon', 'MultiPolygon'): det.poly(g, (226, 221, 213), (214, 208, 199), 1)
draw_roads(det, segs)
for name, g in DIV.items():
    if name.endswith('Tumani') or name.endswith('tumani'):
        det.line(g.exterior, (180, 140, 215, 200), 5)
street_labels(det, segs, ('trunk', 'primary', 'secondary', 'tertiary'), 30, 700)
street_labels(det, segs, ('residential', 'unclassified'), 22, 450)
det.img.save(f'{OUT}/detail.jpg', quality=90)

# ---------------- 3D buildings ----------------
FOCUS = box(69.145, 41.245, 69.225, 41.305)
rng = np.random.default_rng(7)
dprep = {k: shapely.prepared.prep(v) for k, v in districts.items()}
pos, col, zone = [], [], []
ROOF = np.array([238, 234, 227]); WALL = np.array([222, 215, 205])
def add_tri(a, b, c, colr, z):
    pos.extend([*a, *b, *c]); col.extend([*colr] * 3); zone.extend([z] * 3)
count = 0
for r in blds:
    g = r['g']
    if g.geom_type == 'MultiPolygon': g = largest(g)
    if g.geom_type != 'Polygon' or not FOCUS.contains(g.centroid): continue
    area_m2 = g.area * KX * KZ
    if area_m2 < 25: continue
    if r['height']: h = r['height']
    elif r['num_floors']: h = r['num_floors'] * 3.2
    else: h = (4 if area_m2 > 400 else 2) * 3.2 * rng.uniform(0.8, 1.25) if area_m2 > 150 else rng.uniform(3.5, 6)
    h = min(h, 120) / 10
    c = g.centroid
    z = 1 if dprep['uchtepa'].contains(c) else 2 if dprep['chilonzor'].contains(c) else 3 if dprep['zangiota'].contains(c) else 0
    ring = np.array([W(x, y) for x, y in g.exterior.coords[:-1]])
    if len(ring) < 3: continue
    tris = earcut.triangulate_float64(ring, np.array([len(ring)], dtype=np.uint32))
    shade = rng.uniform(0.96, 1.03)
    for i in range(0, len(tris), 3):
        a, b, cc = ring[tris[i]], ring[tris[i + 1]], ring[tris[i + 2]]
        add_tri((a[0], h, a[1]), (cc[0], h, cc[1]), (b[0], h, b[1]), ROOF * shade, z)
    # ensure CCW (in x,z with z south) for outward normals
    area2 = np.sum(ring[:, 0] * np.roll(ring[:, 1], -1) - np.roll(ring[:, 0], -1) * ring[:, 1])
    rr = ring if area2 < 0 else ring[::-1]
    for i in range(len(rr)):
        p, q = rr[i], rr[(i + 1) % len(rr)]
        add_tri((p[0], 0, p[1]), (q[0], 0, q[1]), (q[0], h, q[1]), WALL * shade, z)
        add_tri((p[0], 0, p[1]), (q[0], h, q[1]), (p[0], h, p[1]), WALL * shade, z)
    count += 1
pos = np.array(pos, np.float32); col = np.clip(np.array(col), 0, 255).astype(np.uint8); zone = np.array(zone, np.uint8)
with open(f'{OUT}/buildings.bin', 'wb') as fh:
    fh.write(struct.pack('<I', len(pos) // 3)); fh.write(pos.tobytes()); fh.write(col.tobytes()); fh.write(zone.tobytes())
print('buildings', count, 'verts', len(pos) // 3)

# ---------------- scene json ----------------
def wpoly(p, tol=0.0004):
    p = p.simplify(tol)
    return [list(map(lambda v: round(v, 2), W(x, y))) for x, y in p.exterior.coords]
P = lambda lat, lon: [round(v, 2) for v in W(lon, lat)]
scene = {
    'wide': wide.world_bounds(), 'detail': det.world_bounds(),
    'districts': {k: wpoly(v) for k, v in districts.items()},
    'districtCenter': {k: [round(v, 2) for v in W(*v.representative_point().coords[0])] for k, v in districts.items()},
    'city': wpoly(city, 0.001),
    'places': {
        'farhad': P(41.28525, 69.18975), 'metro': P(41.27455, 69.20474), 'vatan': P(41.28184, 69.17663),
        'algoritm': P(41.26200, 69.16400), 'center': P(41.27898, 69.18425),
    },
    'pois': [
        ['gov', 'Хокимият Учтепинского района', P(41.29520, 69.17633)],
        ['gov', 'Суд Учтепинского района', P(41.29117, 69.16901)],
        ['metro', 'Мирзо Улугбек', P(41.28208, 69.21245)],
        ['metro', 'Олмазор', P(41.25655, 69.19597)],
        ['metro', 'Новза', P(41.29263, 69.22296)],
        ['mall', 'Globus Mall', P(41.27225, 69.17576)],
        ['mall', 'Депо Молл', P(41.27335, 69.16952)],
        ['mall', 'Scopus Mall', P(41.28309, 69.19392)],
        ['mall', 'Mediapark Чиланзар', P(41.28165, 69.20212)],
        ['sport', 'Стадион «Бунёдкор»', P(41.27975, 69.21259)],
        ['park', 'Парк Гафура Гуляма', P(41.28131, 69.21697)],
        ['sport', 'Стадион «Октепа»', P(41.29914, 69.20927)],
        ['mosque', 'Мечеть Хазрат Али', P(41.30338, 69.17048)],
        ['med', 'Kimyo University Hospital', P(41.27207, 69.16530)],
        ['bus', 'Автостанция 20-й квартал', P(41.26619, 69.17736)],
    ],
}
json.dump(scene, open(f'{OUT}/scene.json', 'w'), ensure_ascii=False)
print('ok', wide.W, wide.H, det.W, det.H)
