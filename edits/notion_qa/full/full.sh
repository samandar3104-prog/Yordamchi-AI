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
    c.append({"t": a + 0.02, "sfx": "ui_swipe", "gain_db": -16})
bold = ["ui_pop_2", "button_2", "ui_pop_1"]; n = 0
for lines, t_out in story.CAPTIONS:
    for txt, style, tin in lines:
        if style == "thin": c.append({"t": tin, "sfx": "soft_swoosh", "align": "start", "gain_db": -9})
        else: c.append({"t": tin + 0.02, "sfx": bold[n % 3], "gain_db": -15}); n += 1
ev = [(41.22, "combo", -12)]
import re
for line in open('v12_full.py').read().split("SIDE = [")[1].split("]\n")[0].split("\n"):
    for m in re.finditer(r"\((\d+\.\d+), (\d+\.\d+), \"(L|R)\"", line):
        ev.append((float(m.group(1)) + 0.02, "ui_pop_2", -17))
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
mkdir -p $R/edits/notion_qa/full $R/output
cp final.mp4 $R/output/notion_shablon_reel_full_9x16.mp4
cp render.py v12_full.py story.py cues.json build.sh full.sh $R/edits/notion_qa/full/
cd $R && git add edits && git commit -qm "Notion reel full-screen version: no 50/50, chin-anchored zoom cuts, glass icons beside the head, same captions/music/SFX

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
