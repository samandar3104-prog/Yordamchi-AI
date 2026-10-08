# Mix: voice (delayed 0.4s) + music ducked under voice (sidechain) + timed SFX.
import json, subprocess, sys
video, music, out = sys.argv[1], sys.argv[2], sys.argv[3]
ev=json.load(open("events.json"))
vol={"whoosh":0.35,"pop":0.25,"sparkle":0.22,"heart":0.6,"ding":0.3,"riser":0.25}
args=["ffmpeg","-y","-loglevel","error","-i",video,"-i","vo.mp3","-i",music]
fl=["[1:a]adelay=400|400,aformat=channel_layouts=stereo,volume=1.6,apad,asplit=2[v][sc]",
    "[2:a]aformat=channel_layouts=stereo,volume=0.55,afade=t=in:d=1.5,afade=t=out:st=40.3:d=2[m0]",
    "[m0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[m]"]
labs=["[v]","[m]"]
for i,(n,t) in enumerate(ev):
    args+=["-i",f"sfx/{n}.wav"]; k=3+i; ms=int(t*1000)
    fl.append(f"[{k}:a]volume={vol[n]},adelay={ms}|{ms}[s{i}]"); labs.append(f"[s{i}]")
fl.append("".join(labs)+f"amix=inputs={len(labs)}:normalize=0:duration=first,alimiter=limit=0.95[a]")
args+=["-filter_complex",";".join(fl),"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out]
subprocess.run(args,check=True); print("mixed")
