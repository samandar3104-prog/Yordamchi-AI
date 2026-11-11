#!/bin/bash
cd "$(dirname "$0")"
bash build.sh 5.0 >/dev/null
for c in "0 380" "380 760" "760 1140" "1140 1518"; do set -- $c; python3 render.py src.mov r_$1 $1 $2 > lr_$1.txt 2>&1 & done
wait; grep -hE "done|Error" lr_*.txt
printf "file 'r_0.mp4'\nfile 'r_380.mp4'\nfile 'r_760.mp4'\nfile 'r_1140.mp4'\n" > rl.txt
python3 -I - <<'P'
import json, sys
sys.path.insert(0, '.')
import story
c = [{"t": 0.02, "sfx": "impact_boom", "gain_db": -18}]
for a, b, lay, kind, z in story.SEG[1:]:
    c.append({"t": a + 0.02, "sfx": "ui_swipe", "gain_db": -18})
n = 0
for lines, t_out in story.CAPTIONS:            # only the keyword (bold) lines get a sound, and only every other one
    for txt, style, tin in lines:
        if style == "bold":
            if n % 2 == 0: c.append({"t": tin + 0.02, "sfx": "ui_pop_2", "gain_db": -18})
            n += 1
ev = [(9.24, "ui_click", -16), (12.95, "ui_click", -16), (16.42, "ui_click", -16), (17.42, "ui_chime", -17),
      (28.0, "ui_click", -16), (30.84, "ui_click", -16), (31.32, "ui_notify", -17), (37.4, "sparkle", -18),
      (39.45, "ui_click", -16), (44.1, "ui_chime", -17), (47.02, "ui_pop_1", -17), (49.04, "ui_pop_1", -17)]
for tt, s, g in ev: c.append({"t": tt, "sfx": s, "gain_db": g})
for x in c: x["gain_db"] -= 3
c.sort(key=lambda x: x["t"])
json.dump(c, open('cues.json', 'w'), indent=1)
print(len(c), "cues")
P
ffmpeg -v error -y -i src.mov -vn -af "highpass=f=80,loudnorm=I=-15:TP=-1.5:LRA=9" -ar 48000 -ac 2 voice.wav
ffmpeg -v error -y -f concat -i rl.txt -i voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart base.mp4
python3 /home/user/Yordamchi-AI/sfx/apply_sfx.py base.mp4 cues.json final.mp4 2>&1 | tail -1
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
ffmpeg -v error -y -i final.mp4 -vf "fps=0.8,scale=150:-1,tile=9x5" -frames:v 1 gfinal.png
R=/home/user/Yordamchi-AI
mkdir -p $R/edits/vpn_music_qa/av $R/output
cp final.mp4 $R/output/instagram_musiqa_vpn_reel_9x16.mp4
cp render.py v14_vpn.py story.py cues.json build.sh full.sh $R/edits/vpn_music_qa/ && cp av/app.jpg $R/edits/vpn_music_qa/av/ && cp -r av/svg $R/edits/vpn_music_qa/av/
cd $R && git add edits && git commit -qm "Instagram music via VPN reel: full / 50-50 / round expert frames, phone UI scenes (store, VPN, music picker, publish, edit), sparse SFX

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UonvvDdpC4BVYpgLmBEMkX" && git push -q origin claude/brave-euler-2p9lcf 2>&1 | tail -1
echo saved
