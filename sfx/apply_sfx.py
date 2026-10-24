#!/usr/bin/env python3
"""Videoga SFX qo'shish.

  python3 sfx/apply_sfx.py input.mp4 cues.json output.mp4
  python3 sfx/apply_sfx.py input.mp4 --suggest        # sahna kesimlarini topib, cue taklif qiladi

cues.json misoli:
  [
    {"t": 0.0, "sfx": "cyber_shift"},
    {"t": 1.5, "sfx": "cine_strike", "gain_db": -3},
    {"t": 4.2, "sfx": "soft_swoosh", "align": "start"}
  ]

"t"      — video vaqti (soniya). Default "align": "hit" — SFX ning eng kuchli nuqtasi shu vaqtga tushadi.
"gain_db"— SFX balandligi (default 0).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = json.load(open(os.path.join(HERE, "library.json")))["sfx"]


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    return bool(out.strip())


def suggest(video, threshold=0.3):
    res = subprocess.run(
        ["ffmpeg", "-i", video, "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    times = [float(m) for m in re.findall(r"pts_time:([\d.]+)", res.stderr)]
    rotation = ["cine_strike", "cyber_shift", "basscrack", "soft_swoosh", "impact_boom", "noise_burst"]
    cues = [{"t": round(t, 2), "sfx": rotation[i % len(rotation)]} for i, t in enumerate(times)]
    print(json.dumps(cues, indent=2))


def apply(video, cues_path, output):
    cues = json.load(open(cues_path))
    inputs = ["-i", video]
    filters, labels = [], []
    for i, c in enumerate(cues):
        s = LIB[c["sfx"]]
        inputs += ["-i", os.path.join(HERE, s["file"])]
        offset = c["t"] - (s["hit"] if c.get("align", "hit") == "hit" else 0)
        trim = max(0.0, -offset)
        delay_ms = int(max(0.0, offset) * 1000)
        filters.append(
            f"[{i + 1}:a]atrim=start={trim},asetpts=PTS-STARTPTS,volume={c.get('gain_db', 0)}dB,"
            f"adelay={delay_ms}|{delay_ms}[s{i}]")
        labels.append(f"[s{i}]")
    if has_audio(video):
        filters.append("[0:a]anull[orig]")
        labels.insert(0, "[orig]")
    # apad + -shortest: audio video uzunligiga teng bo'ladi (ovozsiz video bo'lsa ham)
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
                   f"alimiter=limit=0.95,apad[aout]")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output]
    subprocess.run(cmd, check=True)
    print(f"Tayyor: {output}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2] == "--suggest":
        suggest(sys.argv[1])
    elif len(sys.argv) == 4:
        apply(*sys.argv[1:])
    else:
        print(__doc__)
        sys.exit(1)
