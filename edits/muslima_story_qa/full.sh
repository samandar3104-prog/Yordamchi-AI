#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null 2>&1
for c in "0 914" "914 1828" "1828 2742" "2742 3656"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "^done|Traceback" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_914.mp4'\nfile 'r_1828.mp4'\nfile 'r_2742.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "cine_strike", "gain_db": -19}]
tr = ["deep_whoosh", "ui_swipe", "static_whoosh", "inertia_ramp", "soft_swoosh"]
for i, (a, b, nm) in enumerate(story.SCENES[1:]):
    s = tr[i % len(tr)]
    c.append({"t": a + 0.02, "sfx": s, "align": "start" if s in ("inertia_ramp", "soft_swoosh") else "hit", "gain_db": -16})
c += [{"t": 49.62, "sfx": "riser", "gain_db": -20}, {"t": 66.32, "sfx": "deep_whoosh", "gain_db": -16}, {"t": 96.02, "sfx": "riser", "gain_db": -20}]
bold = ["ui_pop_2", "button_2", "ui_pop_1"]; nb = 0
for lines, t_out in story.CAPTIONS:
    for txt, style, tin in lines:
        if style == "bold":
            if nb % 2 == 0: c.append({"t": tin + 0.02, "sfx": bold[(nb // 2) % 3], "gain_db": -19})
            nb += 1
        elif style == "caps": c.append({"t": tin, "sfx": "typing", "gain_db": -22})
ev = [(0.62, "glass_shine", -19), (8.42, "combo", -17), (8.5, "sparkle", -17),
      (11.12, "button_1", -19), (11.92, "button_3", -19), (12.62, "button_1", -19), (13.22, "basscrack", -22),
      (16.12, "ui_tap_tail", -19), (17.22, "ui_tap_tail", -19), (18.52, "ui_tap_tail", -19), (17.9, "ui_chime", -21),
      (22.32, "ui_pop_1", -19), (24.12, "ripple_texture", -21),
      (27.42, "low_rise", -20), (31.92, "glass_shine", -19), (32.92, "ui_pop_2", -20),
      (38.0, "click_ticks", -22), (40.42, "ui_pop_1", -19), (43.62, "impact_boom", -21), (44.82, "riser", -21),
      (69.72, "glass_shine", -19), (72.92, "click_ticks", -22), (74.92, "sparkle", -17), (75.0, "ui_chime", -20),
      (78.42, "ui_notify", -18), (88.42, "ui_pop_2", -19), (91.22, "sparkle", -19), (94.82, "combo", -18)]
for tt, s, g in ev: c.append({"t": tt, "sfx": s, "gain_db": g})
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues", len(set(x["sfx"] for x in c)), "different sounds")
P
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 src.mov)
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -ss 50 -t $D -i music.mp3 -af "loudnorm=I=-36:TP=-9:LRA=11,afade=t=in:d=1.0,afade=t=out:st=$(python3 -c "print($D-3)"):d=3" -ar 48000 -ac 2 bgm.wav
ffmpeg -v error -y -i voice.wav -i bgm.wav -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" -map "[a]" -ar 48000 -ac 2 mix.wav
ffmpeg -v error -y -f concat -i rl.txt -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final_hq.mp4 2>&1 | tail -1
# deliverable under 30 MB-ish for easy sharing: re-encode video at a sane bitrate
ffmpeg -v error -y -i final_hq.mp4 -c:v libx264 -preset slow -crf 23 -maxrate 3M -bufsize 6M -c:a copy -movflags +faststart final.mp4
ls -la final.mp4 final_hq.mp4 | awk '{print $5, $9}'
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -v error -y -i final.mp4 -vf "fps=0.33,scale=150:-1,tile=14x3" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/muslima_story_qa $R/output
cp final.mp4 $R/output/muslima_usman_hikoya_multfilm_9x16.mp4
cp v17_cartoon.py story.py cues.json build.sh full.sh $R/edits/muslima_story_qa/
cd $R && git add edits && git commit -qm "Muslima Usman story reel: cartoon scenes with reference puppets and Fluent 3D props, expert only mid and end, 5 parts joined

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
