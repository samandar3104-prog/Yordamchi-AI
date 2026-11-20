#!/usr/bin/env python3
"""Download stock B-roll clips (Pexels, found via the vidIQ find_broll tool) and normalise them for 9:16 reels.

Usage:  python3 tools/broll_fetch.py OUT_DIR "name|mp4_url|photographer|source_page" [...]
Each clip is saved as OUT_DIR/<name>.mp4: 1080x1920, 30 fps, no audio, centre-cropped.
A credits.txt with photographer + source link is written next to the clips (Pexels asks for attribution).
"""
import os, subprocess, sys

def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    credits = []
    for spec in sys.argv[2:]:
        name, url, who, page = (spec.split("|") + ["", "", ""])[:4]
        raw = os.path.join(out, name + "_raw.mp4")
        subprocess.run(["curl", "-sS", "-L", "--fail", "-o", raw, url], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-an", "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", os.path.join(out, name + ".mp4")], check=True)
        os.remove(raw)
        credits.append(f"{name}: {who} — {page}")
        print("ok", name)
    with open(os.path.join(out, "credits.txt"), "a") as f:
        f.write("\n".join(credits) + "\n")

if __name__ == "__main__":
    main()
