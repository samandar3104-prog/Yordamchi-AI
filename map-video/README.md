# Toshkent 3D xarita animatsiyasi

Vertikal (1080×1920) 10 soniyalik 3D xarita videosi: Uchtepa, Chilonzor, Farhod bozori, Vatan kinoteatri, Algoritm, Zangiota va "Bizning markaz".

Koordinatalar taxminiy (stilize qilingan xarita). Joylarni `index.html` ichidagi `PLACES` obyektida o'zgartirish mumkin.

```bash
npm i three@0.160.0 playwright
python3 -m http.server 8765 &      # shu papkada
node render.mjs frames             # 313 kadr
ffmpeg -framerate 30 -i frames/f%04d.jpg -i asl_video.mov -map 0:v -map 1:a \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest toshkent_xarita_3d.mp4
```
