# Mix voice + ducked music + SFX events from events5.json onto the silent render.
import json, subprocess, sys
video, music, out = sys.argv[1], sys.argv[2], sys.argv[3]
sfxdir = sys.argv[4] if len(sys.argv) > 4 else "."
j = json.load(open("events5.json")); ev, dur, off = j["events"], j["dur"], j["off"]
base = {"boom": 0.55, "swish": 0.35, "whoosh": 0.35, "glitch": 0.25, "click": 0.3, "ticks": 0.3, "swell": 0.35,
        "sparkle": 0.22, "pop": 0.25, "heart": 0.6, "ding": 0.3, "riser": 0.3}
ms = int(off * 1000)
SPEED = float(__import__("os").environ.get("SPEED", "1.1"))
args = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", "vo.mp3", "-i", music, "-i", music]
# music: first 30s, then crossfade into the section that ends on the track's natural ending at video end
mlen = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", music]))
bstart = max(0.0, 30 + min(mlen, 39.5) - 2 - dur)  # keep the track at full level until the video ends
fl = [f"[1:a]atempo={SPEED},adelay={ms}|{ms},aformat=channel_layouts=stereo,volume=1.7,apad,asplit=2[v][sc]",
      f"[2:a]atrim=0:30[ma];[3:a]atrim=start={bstart:.2f},asetpts=PTS-STARTPTS[mb];[ma][mb]acrossfade=d=2,aformat=channel_layouts=stereo,volume=0.7,afade=t=in:d=0.8,afade=t=out:st={dur-1.2:.2f}:d=1.2[m0]",
      "[m0][sc]sidechaincompress=threshold=0.025:ratio=5:attack=30:release=450[m]"]
labs = ["[v]", "[m]"]
for i, (n, t, g) in enumerate(ev):
    args += ["-i", f"{sfxdir}/{n}.wav"]; k = 4 + i; d = int(t * 1000)
    fl.append(f"[{k}:a]volume={base[n]*g:.3f},adelay={d}|{d}[s{i}]"); labs.append(f"[s{i}]")
fl.append("".join(labs) + f"amix=inputs={len(labs)}:normalize=0:duration=first,atrim=0:{dur:.2f},alimiter=limit=0.95[a]")
args += ["-filter_complex", ";".join(fl), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
subprocess.run(args, check=True); print("mixed", len(ev), "sfx")
