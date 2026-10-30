#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p6/render.py').read()
s = s.replace("N = 1468", "N = 1319", 1)
s = s.replace("if 0.84 <= t < 1.04:", "if False:", 1)
a = s.rindex('def decode(')
open('render.py', 'w').write(s[:a] + open('v10_notion.py').read() + '\n' + open('v11_glass.py').read() + "\n" + s[a:])
P
grep -c "N = 1319" render.py >/dev/null || echo "N not set"
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | tail -4
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=240:-1,tile=8x2" -frames:v 1 pg.png
