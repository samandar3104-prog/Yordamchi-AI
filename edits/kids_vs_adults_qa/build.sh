#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p6/render.py').read()
s = s.replace("N = 1468", "N = 2316", 1)
s = s.replace("if 0.84 <= t < 1.04:", "if False:", 1)
a = s.rindex('def decode(')
keep = '\n_ORIG = dict(anim_line=anim_line, draw_captions=draw_captions, expert_crop=expert_crop, scene=scene, render=render, TERRA=TERRA, STY=dict(STY))\n'
new = keep + open('../p7/v10_notion.py').read() + '\n' + open('../p7/v11_glass.py').read() + '\n' + open('v15_kids.py').read()
open('render.py', 'w').write(s[:a] + new + "\n" + s[a:])
P
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | tail -6
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=240:-1,tile=8x2" -frames:v 1 pg.png
