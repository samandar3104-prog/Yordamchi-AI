# Toshkent 3D xarita animatsiyasi

Vertikal (1080×1920) 10 soniyalik 3D xarita videosi: Uchtepa, Chilonzor, Farhod bozori, Vatan kinoteatri, Algoritm, Zangiota va "Bizning markaz".

Xarita foydalanuvchi bergan Toshkent xaritasi uslubida qayta chizilgan: shahar chegarasi o'sha rasmdan ajratib olingan (`make_basemap.py` -> `basemap.jpg`, `geo.json`). Koordinatalar shu rasm pikselida; joylarni `index.html` ichidagi `PLACES` obyektida o'zgartirish mumkin.

```bash
python3 make_basemap.py reference_map.png .   # opencv-python-headless, pillow kerak
```

```bash
npm i three@0.160.0 playwright
python3 -m http.server 8765 &      # shu papkada
node render.mjs frames             # 313 kadr
ffmpeg -framerate 30 -i frames/f%04d.jpg -i asl_video.mov -map 0:v -map 1:a \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest toshkent_xarita_3d.mp4
```

## Yandex uslubidagi versiya (haqiqiy ma'lumotlar)

`yandex.html` haqiqiy OSM/Overture Maps ma'lumotlaridan foydalanadi: ko'chalar (nomlari bilan), 3D binolar, kanallar, tumanlar chegarasi, metro, hokimiyat va boshqa mo'ljallar.

```bash
pip install pyarrow shapely mapbox_earcut pillow numpy
# ma'lumotlarni yuklash (osm/ papkaga)
python3 fetch_overture.py transportation segment id,names,subtype,class,geometry
python3 fetch_overture.py buildings building id,height,num_floors,class,geometry
python3 fetch_overture.py base water id,names,subtype,class,geometry
python3 fetch_overture.py base land_use id,names,subtype,class,geometry
python3 fetch_overture.py places place id,names,basic_category,taxonomy,geometry,addresses
python3 fetch_overture.py divisions division_area id,names,subtype,admin_level,class,geometry,country intersects
# wide_segment / wide_water: BB=68.98,41.10,69.48,41.45 bilan katta yo'llar va suv
python3 build_map.py osm y           # y/wide.jpg, y/detail.jpg, y/buildings.bin, y/scene.json
PAGE=yandex.html node render.mjs frames
```
