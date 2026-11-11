#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null
for c in "0 243" "243 486" "486 729" "729 972"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "done|Traceback" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_243.mp4'\nfile 'r_486.mp4'\nfile 'r_729.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "impact_boom", "gain_db": -20}]
for a, b, lay, pan, z in story.SEG[1::2]:              # every other cut: a soft swish
    c.append({"t": a + 0.02, "sfx": "soft_swoosh", "align": "start", "gain_db": -14})
n = 0
for lines, t_out in story.CAPTIONS:                    # every other keyword line: a soft pop
    for txt, style, tin in lines:
        if style == "bold":
            if n % 2 == 0: c.append({"t": tin + 0.02, "sfx": "ui_pop_2", "gain_db": -19})
            n += 1
c += [{"t": 12.04, "sfx": "ui_chime", "gain_db": -19}, {"t": 30.60, "sfx": "ui_notify", "gain_db": -18}]
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues")
P
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -f concat -i rl.txt -i voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final.mp4 2>&1 | tail -1
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/seminar_qa $R/output
cp final.mp4 $R/output/logo_centre_seminar_reel_9x16.mp4
cp story.py cues.json build.sh full.sh $R/edits/seminar_qa/
cd $R && git add edits && git commit -qm "Logo Centre seminar reel: simple full-screen edit, subtitles, soft zoom cuts, sparse SFX

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
