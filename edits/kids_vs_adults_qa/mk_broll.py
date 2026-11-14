import subprocess, sys
# (t0, t1, clip, clip_start, clip_dur, crop) ; crop "b1" removes the burned-in English words at the bottom
SEGS = [(2.80, 9.00, "b2", 3.5, 6.2, None), (11.40, 20.62, "b1", 0.0, 7.0, "b1"), (24.22, 34.70, "b3", 0.0, 5.2, None),
        (39.80, 50.30, "b1", 7.0, 9.0, "b1"), (50.30, 57.90, "b1", 22.0, 3.4, "b1"), (60.60, 68.90, "b1", 16.0, 6.0, "b1"),
        (68.90, 74.20, "b3", 0.0, 5.2, None)]
TOTAL = 77.22
parts = []; cur = 0.0
def black(d, name):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={d:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", name], check=True)
for j, (t0, t1, clip, cs, cd, crop) in enumerate(SEGS):
    if t0 > cur + 1e-3:
        n = f"seg_{len(parts):02d}.mp4"; black(t0 - cur, n); parts.append(n)
    dur = t1 - t0; speed = cd / dur
    vf = "crop=489:870:115:0," if crop == "b1" else ""
    vf += f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setpts=(PTS-STARTPTS)/{speed:.5f},fps=30"
    n = f"seg_{len(parts):02d}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{cs}", "-t", f"{cd}", "-i", f"broll/{clip}.mp4", "-an", "-vf", vf,
                    "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", n], check=True)
    parts.append(n); cur = t1
if TOTAL > cur: n = f"seg_{len(parts):02d}.mp4"; black(TOTAL - cur, n); parts.append(n)
open("bl.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-i", "bl.txt", "-c", "copy", "broll_track.mp4"], check=True)
print(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "broll_track.mp4"], capture_output=True, text=True).stdout)
