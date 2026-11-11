#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p6/render.py').read()
s = s.replace("N = 1468", "N = 972", 1)
s = s.replace("if 0.84 <= t < 1.04:", "if False:", 1)
a = s.rindex('def decode(')
extra = "PUNCH[:] = [(1.16, 1.04, 2.10), (4.50, 1.04, 5.30), (12.02, 1.04, 13.20), (25.58, 1.04, 26.50), (30.58, 1.04, 99)]\nFACE_Y = 372\n"
open('render.py', 'w').write(s[:a] + extra + "\n" + s[a:])
P
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | tail -4
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=240:-1,tile=8x1" -frames:v 1 pg.png
