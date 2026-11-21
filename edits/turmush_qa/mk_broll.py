import subprocess
# (t0, t1, clip, clip_start, clip_dur, crop)
SEGS = [(5.60, 11.30, "think", 0.0, 9.0, None),
        (11.30, 14.90, "dua", 0.0, 6.0, None), (14.90, 17.95, "rings", 7.5, 5.0, "rings"),
        (17.95, 24.10, "frustrated", 0.0, 10.5, None),
        (27.10, 31.00, "study", 0.0, 7.0, None), (31.00, 35.60, "read", 2.0, 8.0, None),
        (37.20, 44.10, "smile", 0.0, 10.0, None)]
TOTAL = 50.30
parts = []; cur = 0.0
def black(d, n):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={d:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", n], check=True)
for t0, t1, clip, cs, cd, crop in SEGS:
    if t0 > cur + 1e-3:
        n = f"seg_{len(parts):02d}.mp4"; black(t0 - cur, n); parts.append(n)
    dur = t1 - t0; speed = cd / dur
    vf = "crop=619:1100:300:780,scale=1080:1920," if crop == "rings" else ""
    vf += f"setpts=(PTS-STARTPTS)/{speed:.5f},fps=30"
    n = f"seg_{len(parts):02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{cs}", "-t", f"{cd}", "-i", f"broll2/{clip}.mp4", "-an", "-vf", vf,
                    "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", n], check=True)
    parts.append(n); cur = t1
if TOTAL > cur: n = f"seg_{len(parts):02d}.mp4"; black(TOTAL - cur, n); parts.append(n)
open("bl.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-i", "bl.txt", "-c", "copy", "broll_track.mp4"], check=True)
