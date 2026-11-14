#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null
for c in "0 580" "580 1160" "1160 1740" "1740 2317"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "done|Traceback" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_580.mp4'\nfile 'r_1160.mp4'\nfile 'r_1740.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "cine_strike", "gain_db": -18}]
tr = ["deep_whoosh", "static_whoosh", "ui_swipe", "inertia_ramp", "soft_swoosh"]
for i, (a, b, lay, pan, z) in enumerate(story.SEG[1:]):
    c.append({"t": a + 0.02, "sfx": tr[i % len(tr)], "align": "start" if tr[i % len(tr)] in ("inertia_ramp", "soft_swoosh") else "hit", "gain_db": -15})
bold = ["ui_pop_2", "button_2", "ui_pop_1"]; nb = 0
for lines, t_out in story.CAPTIONS:
    for txt, style, tin in lines:
        if style == "bold": c.append({"t": tin + 0.02, "sfx": bold[nb % 3], "gain_db": -17}); nb += 1
        elif style == "serif": c.append({"t": tin, "sfx": "soft_swoosh", "align": "start", "gain_db": -13})
        elif style == "caps": c.append({"t": tin, "sfx": "typing", "gain_db": -21})
ev = [(2.82, "glass_shine", -18), (11.42, "low_rise", -20), (13.6, "digital_glitch", -24), (19.04, "basscrack", -22),
      (24.24, "sparkle", -17), (33.72, "combo", -16), (39.82, "click_ticks", -21), (44.3, "ui_texture", -21),
      (48.62, "alienated_warps", -24), (50.32, "riser", -20), (55.98, "ui_chime", -18), (60.62, "ripple_texture", -21),
      (66.72, "ui_pop_1", -19), (69.2, "ui_notify", -18), (73.40, "ui_click", -15), (73.70, "button_3", -17)]
for tt, s, g in ev: c.append({"t": tt, "sfx": s, "gain_db": g})
for x in c: x["gain_db"] -= 3
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues", len(set(x["sfx"] for x in c)), "different sounds")
P
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 src.mov)
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -ss 50 -t $D -i music.mp3 -af "loudnorm=I=-35:TP=-9:LRA=11,afade=t=in:d=1.0,afade=t=out:st=$(python3 -c "print($D-2.5)"):d=2.5" -ar 48000 -ac 2 bgm.wav
ffmpeg -v error -y -i voice.wav -i bgm.wav -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" -map "[a]" -ar 48000 -ac 2 mix.wav
ffmpeg -v error -y -f concat -i rl.txt -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final.mp4 2>&1 | tail -1
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -v error -y -i final.mp4 -vf "fps=0.5,scale=150:-1,tile=13x3" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/kids_vs_adults_qa $R/output
cp final.mp4 $R/output/logoped_bolalar_yonalish_broll_9x16.mp4
cp v15_kids.py v16_broll.py mk_broll.py story.py cues.json build.sh full.sh $R/edits/kids_vs_adults_qa/
cd $R && git add edits && git commit -qm "Logoped long reel v2: B-roll first, expert full / round / rounded card / voice-only, no 50-50 panels

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
