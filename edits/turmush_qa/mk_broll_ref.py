import subprocess, sys
sys.path.insert(0, '.')
import story_ref as S
TOTAL = 50.30
parts = []; cur = 0.0
def black(d, n):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={d:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", n], check=True)
for t0, t1, clip, cs, crop in S.BROLL:
    if t0 > cur + 1e-3:
        n = f"seg_{len(parts):02d}.mp4"; black(t0 - cur, n); parts.append(n)
    dur = t1 - t0
    vf = ("crop=720:1280:200:420,scale=1080:1920," if crop == "rings" else "") + "fps=30"
    n = f"seg_{len(parts):02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{cs}", "-i", f"broll2/{clip}.mp4", "-an", "-vf", vf,
                    "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", n], check=True)
    parts.append(n); cur = t1
if TOTAL > cur: n = f"seg_{len(parts):02d}.mp4"; black(TOTAL - cur, n); parts.append(n)
open("bl.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-i", "bl.txt", "-c", "copy", "broll_track.mp4"], check=True)
print("track ok")
