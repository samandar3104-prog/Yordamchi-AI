#!/bin/bash
cd "$(dirname "$0")"
python3 - <<'P'
s = open('../p6/render.py').read()
s = s.replace("N = 1468", "N = 3656", 1)
s = s.replace("if 0.84 <= t < 1.04:", "if False:", 1)
a = s.rindex('def decode(')
keep = '\n_ORIG = dict(anim_line=anim_line, draw_captions=draw_captions, expert_crop=expert_crop, scene=scene, render=render, TERRA=TERRA, STY=dict(STY))\n'
new = keep + '\n'.join(open(f).read() for f in ('../p7/v10_notion.py', '../p7/v11_glass.py', '../p10/v15_kids.py', 'v17_cartoon.py'))
open('render.py', 'w').write(s[:a] + new + "\n" + s[a:])
P
rm -f pv_*
python3 render.py src.mov pv preview "$1" 2>&1 | grep -v "Broken pipe\|Error muxing\|Error writing\|Error closing\|Error submitting" | tail -6
ffmpeg -v error -y -pattern_type glob -i 'pv_*.png' -vf "scale=200:-1,tile=9x2" -frames:v 1 pg.png
