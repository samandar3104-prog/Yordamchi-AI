# Synthesize original SFX (whoosh, pop, sparkle, heartbeat, ding) as 44.1k wavs.
import numpy as np, wave
SR=44100
def save(n,x):
    x=x/ (np.abs(x).max()+1e-9)*0.9
    d=np.int16(np.column_stack([x,x])*32767)
    w=wave.open(n,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
t=lambda s: np.arange(int(SR*s))/SR
rng=np.random.default_rng(1)
# whoosh: filtered noise sweep
T=t(0.7); n=rng.standard_normal(len(T)); env=np.sin(np.pi*T/0.7)**2
f=np.linspace(300,4000,len(T)); y=np.zeros_like(n); a=0
for i in range(len(n)):
    c=np.exp(-2*np.pi*f[i]/SR); a=(1-c)*n[i]+c*a; y[i]=a
y=y-np.convolve(y,np.ones(40)/40,"same")*0.6
save("whoosh.wav",y*env)
# pop: pitch drop sine
T=t(0.18); save("pop.wav",np.sin(2*np.pi*np.cumsum(np.linspace(900,250,len(T)))/SR)*np.exp(-T*28))
# sparkle: ascending bell partials
T=t(1.2); y=np.zeros_like(T)
for k,fr in enumerate([1568,2093,2637,3136,4186]):
    st=int(k*0.07*SR); tt=T[:len(T)-st]
    y[st:]+=np.sin(2*np.pi*fr*tt)*np.exp(-tt*5)*(0.8**k)+0.3*np.sin(2*np.pi*fr*2.01*tt)*np.exp(-tt*9)
save("sparkle.wav",y)
# heartbeat: two low thumps
T=t(0.7); y=np.zeros_like(T)
for st in (0,0.22):
    s=int(st*SR); tt=T[:len(T)-s]; y[s:]+=np.sin(2*np.pi*np.cumsum(np.linspace(90,45,len(tt)))/SR)*np.exp(-tt*14)
save("heart.wav",y)
# ding (soft marimba)
T=t(0.8); save("ding.wav",np.sin(2*np.pi*880*T)*np.exp(-T*7)+0.4*np.sin(2*np.pi*3520*T)*np.exp(-T*20))
# riser for final
T=t(1.5); n=rng.standard_normal(len(T)); env=(T/1.5)**2
save("riser.wav",(n*0.3+np.sin(2*np.pi*np.cumsum(np.linspace(200,1200,len(T)))/SR))*env)
print("ok")
