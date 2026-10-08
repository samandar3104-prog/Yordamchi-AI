# Extra cinematic SFX: boom, swish, glitch, click, ticks, swell.
import numpy as np, wave
SR=44100; rng=np.random.default_rng(5)
def save(n,x,g=0.9):
    x=x/(np.abs(x).max()+1e-9)*g; d=np.int16(np.column_stack([x,x])*32767)
    w=wave.open(n,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
T=lambda s: np.arange(int(SR*s))/SR
def lp(x,a):
    y=np.zeros_like(x); s=0
    for i,v in enumerate(x): s=s+a*(v-s); y[i]=s
    return y
# boom: sub drop + noise thump + tail
t=T(1.6); sub=np.sin(2*np.pi*np.cumsum(55*np.exp(-t*1.5)+30)/SR)*np.exp(-t*2.2)
th=lp(rng.standard_normal(len(t)),0.05)*np.exp(-t*12)*3
save("boom.wav",sub+th)
# swish: short bandpassed noise sweep
t=T(0.35); n=rng.standard_normal(len(t)); env=np.sin(np.pi*(t/0.35)**0.6)**2
a=np.linspace(0.02,0.35,len(t)); y=np.zeros_like(n); s=0
for i in range(len(n)): s=s+a[i]*(n[i]-s); y[i]=s
save("swish.wav",(y-lp(y,0.01))*env,0.8)
# glitch: stuttered digital bursts
t=T(0.45); y=np.zeros_like(t)
for k in range(7):
    st=int(k*0.06*SR); ln=int(rng.uniform(0.02,0.05)*SR); f=rng.uniform(200,2500)
    tt=np.arange(ln)/SR; y[st:st+ln]+=np.sign(np.sin(2*np.pi*f*tt))*0.5+rng.standard_normal(ln)*0.3
save("glitch.wav",y,0.6)
# click
t=T(0.05); save("click.wav",np.sin(2*np.pi*2400*t)*np.exp(-t*120)+rng.standard_normal(len(t))*np.exp(-t*300)*0.3,0.7)
# ticks: accelerating counter clicks (1.2s)
t=T(1.3); y=np.zeros_like(t); pos=0.0; gap=0.11
while pos<1.2:
    s=int(pos*SR); ln=int(0.02*SR); tt=np.arange(ln)/SR
    y[s:s+ln]+=np.sin(2*np.pi*3000*tt)*np.exp(-tt*250); pos+=gap; gap=max(0.035,gap*0.88)
save("ticks.wav",y,0.6)
# swell: reverse reverb-like rise into hit (0.9s)
t=T(0.9); n=lp(rng.standard_normal(len(t)),0.2); save("swell.wav",n*(t/0.9)**3,0.7)
print("ok")
