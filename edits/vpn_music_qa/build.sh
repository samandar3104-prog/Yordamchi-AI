#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p6/render.py').read()
assert "N = 1468" in s
s = s.replace("N = 1468", "N = 1518", 1)
s = s.replace("if 0.84 <= t < 1.04:", "if False:", 1)
a = s.rindex('def decode(')
new = '\n'.join(open(f).read() for f in ('../p7/v10_notion.py', '../p7/v11_glass.py', '../p7m/v13_motion.py', 'v14_vpn.py'))
open('render.py', 'w').write(s[:a] + new + "\n" + s[a:])
P
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | tail -4
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=240:-1,tile=8x2" -frames:v 1 pg.png
