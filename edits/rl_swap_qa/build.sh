#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p5/render.py').read()
assert "N = 1620" in s
s = s.replace("N = 1620", "N = 1468", 1)
a = s.rindex('def decode(')
open('render.py', 'w').write(s[:a] + open('v9_cast.py').read() + "\n" + s[a:])
P
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | tail -4
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=240:-1,tile=8x2" -frames:v 1 pg.png
