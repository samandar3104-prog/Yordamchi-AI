#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null
for c in "0 367" "367 734" "734 1101" "1101 1468"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "done|Error" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_367.mp4'\nfile 'r_734.mp4'\nfile 'r_1101.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "impact_boom", "gain_db": -14}, {"t": 2.9, "sfx": "cine_strike", "gain_db": -16}]
for i, (a, b, lay, pan, z) in enumerate(story.SEG[1:]):
    c.append({"t": a + 0.02, "sfx": ["deep_whoosh", "ui_swipe", "inertia_ramp"][i % 3], "align": "start" if i % 3 == 2 else "hit", "gain_db": -12})
bold = ["ui_pop_2", "button_2", "ui_pop_1"]; n = 0
for lines, t_out in story.CAPTIONS:
    for txt, style, tin in lines:
        if style == "thin": c.append({"t": tin, "sfx": "soft_swoosh", "align": "start", "gain_db": -8})
        else: c.append({"t": tin + 0.02, "sfx": bold[n % 3], "gain_db": -14}); n += 1
ev = [(2.55, "glass_shine", -16), (3.1, "ui_swipe", -18), (4.5, "ui_swipe", -18), (5.9, "ui_swipe", -18),
      (4.2, "digital_blip", -14), (5.55, "ui_pop_1", -14),
      (7.3, "ui_pop_2", -16), (8.85, "ui_chime", -14), (10.2, "low_rise", -16), (11.8, "ui_pop_1", -16),
      (15.25, "ui_swipe", -16), (15.5, "sparkle", -12), (15.55, "ui_chime", -14),
      (18.0, "button_3", -16), (18.42, "button_3", -16), (18.84, "button_3", -16), (19.26, "button_3", -16), (19.68, "button_3", -16),
      (20.12, "combo", -12), (20.2, "sparkle", -12),
      (22.06, "ui_pop_1", -18), (22.36, "ui_pop_1", -18), (22.66, "ui_pop_1", -18), (22.96, "ui_pop_2", -18), (24.04, "ui_pop_2", -18),
      (24.65, "digital_glitch", -20), (25.65, "ui_chime", -14), (25.75, "sparkle", -14),
      (28.45, "glass_shine", -16), (30.42, "ui_pop_2", -14),
      (39.8, "ui_pop_1", -14), (39.95, "digital_blip", -16), (40.4, "ui_chime", -14), (40.95, "sparkle", -12),
      (44.75, "ui_click", -12), (45.05, "ui_notify", -14)]
for j in range(8): ev.append((32.5 + j * 0.5, "click_ticks", -24))
for tt, s, g in ev: c.append({"t": tt, "sfx": s, "gain_db": g})
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues")
P
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -f concat -i rl.txt -i voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final.mp4 2>&1 | tail -1
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -v error -y -i final.mp4 -vf "fps=0.8,scale=150:-1,tile=10x4" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/rl_swap_qa/av $R/output
cp final.mp4 $R/output/rl_almashtirish_reel_v3_9x16.mp4
cp render.py v9_cast.py seg2.py seg3.py story.py cues.json build.sh full.sh $R/edits/rl_swap_qa/ && cp av/girl_cut.png av/mom3_cut.png av/logo_cut.png $R/edits/rl_swap_qa/av/
cd $R && git add edits && git commit -qm "R/L swap reel v3: captions never cross a full/split layout change (no text over the face)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
