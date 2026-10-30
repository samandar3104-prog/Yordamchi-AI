#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null
for c in "0 330" "330 660" "660 990" "990 1319"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "done|Error" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_330.mp4'\nfile 'r_660.mp4'\nfile 'r_990.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "impact_boom", "gain_db": -16}]
for i, (a, b, lay, pan, z) in enumerate(story.SEG[1:]):
    c.append({"t": a + 0.02, "sfx": ["deep_whoosh", "ui_swipe", "inertia_ramp"][i % 3], "align": "start" if i % 3 == 2 else "hit", "gain_db": -12})
bold = ["ui_pop_2", "button_2", "ui_pop_1"]; n = 0
for lines, t_out in story.CAPTIONS:
    for txt, style, tin in lines:
        if style == "thin": c.append({"t": tin, "sfx": "soft_swoosh", "align": "start", "gain_db": -9})
        else: c.append({"t": tin + 0.02, "sfx": bold[n % 3], "gain_db": -15}); n += 1
ev = [(2.92, "button_2", -16), (3.9, "button_2", -16), (4.9, "digital_glitch", -22),
      (5.78, "ui_chime", -16), (6.95, "cine_strike", -16), (7.05, "sparkle", -12),
      (8.5, "click_ticks", -20), (9.72, "ui_swipe", -18), (10.56, "ui_pop_1", -20), (10.76, "ui_pop_1", -20), (10.96, "ui_pop_1", -20),
      (16.0, "button_3", -20), (16.5, "ui_pop_2", -18), (16.65, "ui_pop_2", -18), (16.8, "ui_pop_2", -18), (17.36, "glass_shine", -16), (18.4, "soft_swoosh", -10),
      (20.6, "soft_swoosh", -10), (21.24, "ui_pop_2", -16), (21.82, "ui_notify", -18), (22.66, "combo", -12),
      (28.7, "gear_click", -18), (31.66, "digital_blip", -14),
      (32.45, "ui_pop_2", -16), (35.0, "impact_boom", -18), (35.02, "sparkle", -12), (35.1, "ui_chime", -14), (35.68, "button_2", -18),
      (38.85, "ui_click", -14), (39.4, "ui_swipe", -16), (39.66, "ui_notify", -14), (41.22, "combo", -12), (38.86, "ui_pop_2", -14), (2.86, "deep_whoosh", -14), (39.76, "ui_chime", -18)]
for j in range(6): ev.append((3.0 + j * 0.28, "soft_swoosh", -16))
for j in range(5): ev.append((23.05 + j * 0.12, "ui_pop_1", -18))
for j in range(3): ev.append((37.66 + j * 0.15, "ui_pop_1", -20))
for tt, s, g in ev: c.append({"t": tt, "sfx": s, "gain_db": g})
for x in c: x["gain_db"] -= 4   # all SFX a bit quieter
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues")
P
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 src.mov)
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
# background music: from 0:50 of the track, ~17 dB under the voice, gentle fades
ffmpeg -v error -y -ss 50 -t $D -i music.mp3 -af "loudnorm=I=-36:TP=-9:LRA=11,afade=t=in:d=0.8,afade=t=out:st=$(python3 -c "print($D-2.2)"):d=2.2" -ar 48000 -ac 2 bgm.wav
ffmpeg -v error -y -i voice.wav -i bgm.wav -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" -map "[a]" -ar 48000 -ac 2 mix.wav
ffmpeg -v error -y -f concat -i rl.txt -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final.mp4 2>&1 | tail -1
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -v error -y -i final.mp4 -vf "fps=0.8,scale=150:-1,tile=9x4" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/notion_qa/motion $R/output
cp final.mp4 $R/output/notion_shablon_reel_motion_9x16.mp4
cp render.py v13_motion.py story.py cues.json build.sh full.sh $R/edits/notion_qa/motion/
cd $R && git add edits && git commit -qm "Notion reel motion-first version: animations full-height, expert full only for hook/CTA, glass card or hidden elsewhere

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
