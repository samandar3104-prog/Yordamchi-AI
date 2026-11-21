#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null 2>&1
for c in "0 378" "378 756" "756 1134" "1134 1509"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "^done|Traceback" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_378.mp4'\nfile 'r_756.mp4'\nfile 'r_1134.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "cine_strike", "gain_db": -20}]
tr = ["soft_swoosh", "ui_swipe", "deep_whoosh", "inertia_ramp"]
for i, (a, b, lay, kind, z) in enumerate(story.SEG[1:]):
    s = tr[i % len(tr)]
    c.append({"t": a + 0.02, "sfx": s, "align": "start" if s in ("soft_swoosh", "inertia_ramp") else "hit", "gain_db": -17})
c += [{"t": 6.62, "sfx": "ui_pop_2", "gain_db": -20}, {"t": 12.42, "sfx": "glass_shine", "gain_db": -20}, {"t": 21.32, "sfx": "basscrack", "gain_db": -23},
      {"t": 24.82, "sfx": "ui_pop_1", "gain_db": -20}, {"t": 28.62, "sfx": "sparkle", "gain_db": -20}, {"t": 35.72, "sfx": "typing", "gain_db": -23},
      {"t": 44.72, "sfx": "ui_chime", "gain_db": -21}, {"t": 49.32, "sfx": "typing", "gain_db": -23}]
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues")
P
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 src.mov)
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -ss 0 -t $D -i music_v3.mp3 -af "loudnorm=I=-33:TP=-9:LRA=11,afade=t=in:d=1.5,afade=t=out:st=$(python3 -c "print($D-2.5)"):d=2.5" -ar 48000 -ac 2 bgm.wav
ffmpeg -v error -y -i voice.wav -i bgm.wav -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]" -map "[a]" -ar 48000 -ac 2 mix.wav
ffmpeg -v error -y -f concat -i rl.txt -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final_hq.mp4 2>&1 | tail -1
ffmpeg -v error -y -i final_hq.mp4 -c:v libx264 -preset slow -crf 22 -maxrate 4M -bufsize 8M -c:a copy -movflags +faststart final.mp4
ls -la final.mp4 | awk '{print $5}'
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -v error -y -i final.mp4 -vf "fps=0.5,scale=150:-1,tile=13x2" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/turmush_qa $R/output
cp final.mp4 $R/output/turmushga_chiqish_v4_9x16.mp4
cp story.py story_broll.py mk_broll.py v18_text.py cues.json build.sh full.sh $R/edits/turmush_qa/ && cp broll2/credits.txt $R/edits/turmush_qa/credits.txt && echo 'Music: "Touching Moments Two - Higher" Kevin MacLeod (incompetech.com), CC BY 4.0' >/dev/null; echo 'Music v3: "Inspired" Kevin MacLeod (incompetech.com), CC BY 4.0' >> $R/edits/turmush_qa/credits.txt
cd $R && git add edits && git commit -qm "Turmushga chiqish reel v4: captions are her exact words (Whisper large-v3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
