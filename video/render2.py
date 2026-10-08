# v2: floating parallax sprites, camera punch-ins, circular wipe transitions,
# bouncy word pops, confetti bursts. Writes silent video + sfx event list.
import sys, json, math, subprocess, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H,FPS=1080,1920,30
timings=json.load(open(sys.argv[1])); dur=float(sys.argv[2]); out=sys.argv[3]
FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PAL=[((20,36,84),(60,90,190)),((70,26,96),(190,70,140)),((10,70,84),(30,160,140)),((120,52,16),(235,150,60)),((24,60,140),(90,170,235))]
ACC=[(255,214,90),(255,140,175),(120,235,205),(255,225,140),(255,235,120)]
COLS=[(255,140,175),(120,235,205),(255,214,90),(140,185,255),(200,160,255)]
scenes=[
 {"title":"DIQQAT!","lines":["Autizmni 100% davolaydigan","dori topildi?","Hozircha ishonmay turing!"],"hl":["100%","ishonmay"],"icon":"pill"},
 {"title":"AUTIZM — KASALLIK EMAS","lines":["U gripp yoki","shamollashga o'xshamaydi.","Dori ichib o'tkazib","bo'lmaydi."],"hl":["EMAS","o'xshamaydi."],"icon":"nopill"},
 {"title":"MIYANING BOSHQACHA ISHLASHI","lines":["Bola dunyoni boshqacha","ko'radi, eshitadi,","his qiladi.","Har bir bola — o'ziga xos."],"hl":["ko'radi,","eshitadi,","his","o'ziga","xos."],"icon":"brain"},
 {"title":"QABUL QILING VA O'RGATING","lines":["Gapirishni","Muloqot qilishni","O'zini boshqarishni"],"hl":["Gapirishni","Muloqot","boshqarishni"],"icon":"puzzle"},
 {"title":"BIZ YORDAM BERAMIZ","lines":["Farzandingiz tashxisli bo'lsa,","markazimizga keling!","Qo'ldan kelgancha","yordam beramiz."],"hl":["markazimizga","keling!","yordam"],"icon":"heart"},
]
def ease(t): t=max(0.,min(1.,t)); return 1-(1-t)**3
def eio(t): t=max(0.,min(1.,t)); return t*t*(3-2*t)
def back(t,c=2.2):
    t=max(0.,min(1.,t)); return 1+(c+1)*(t-1)**3+c*(t-1)**2
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(len(a)))
# ---------- sprites ----------
def spr_puzzle(s,col):
    im=Image.new("RGBA",(s*3,s*3)); d=ImageDraw.Draw(im); c=s*1.5; h=s/2; k=s*0.2
    d.rounded_rectangle([c-h,c-h,c+h,c+h],radius=int(s*0.1),fill=col)
    d.ellipse([c+h-k*0.5,c-k,c+h+k*1.5,c+k],fill=col); d.ellipse([c-k,c-h-k*1.5,c+k,c-h+k*0.5],fill=col)
    return im
def spr_heart(s,col):
    im=Image.new("RGBA",(s*3,s*3)); d=ImageDraw.Draw(im); cx=cy=s*1.5; r=s*0.3
    d.ellipse([cx-2*r,cy-r*1.6,cx,cy+r*0.4],fill=col); d.ellipse([cx,cy-r*1.6,cx+2*r,cy+r*0.4],fill=col)
    d.polygon([(cx-2*r+2,cy-r*0.4),(cx+2*r-2,cy-r*0.4),(cx,cy+s*0.75)],fill=col); return im
def spr_star(s,col):
    im=Image.new("RGBA",(s*3,s*3)); d=ImageDraw.Draw(im); c=s*1.5
    pts=[(c+math.cos(math.pi/2+i*math.pi/5)*(s*0.6 if i%2==0 else s*0.25), c-math.sin(math.pi/2+i*math.pi/5)*(s*0.6 if i%2==0 else s*0.25)) for i in range(10)]
    d.polygon(pts,fill=col); return im
def spr_circle(s,col):
    im=Image.new("RGBA",(s*3,s*3)); d=ImageDraw.Draw(im); c=s*1.5
    d.ellipse([c-s*0.45,c-s*0.45,c+s*0.45,c+s*0.45],outline=col,width=max(3,s//10)); return im
random.seed(7)
floaters=[]
for i in range(26):
    depth=random.uniform(0.35,1.0); s=int(40+70*depth)
    kind=random.choice([spr_puzzle,spr_puzzle,spr_heart,spr_star,spr_circle])
    col=random.choice(COLS)+(int(110+120*depth),)
    im=kind(s,col)
    if depth<0.55: im=im.filter(ImageFilter.GaussianBlur(3))
    floaters.append(dict(im=im,x=random.uniform(0,W),y=random.uniform(0,H),sp=20+60*depth,ph=random.uniform(0,6.3),rs=random.uniform(-40,40),amp=random.uniform(20,60),depth=depth))
floaters.sort(key=lambda f:f["depth"])
twinkles=[(random.uniform(0,W),random.uniform(0,H),random.uniform(0,6.3),random.uniform(1.5,4)) for _ in range(50)]
def gradient(c1,c2):
    g=Image.new("RGB",(1,256))
    for y in range(256): g.putpixel((0,y),lerp(c1,c2,y/255))
    return g.resize((W,H))
GRADS=[gradient(*p) for p in PAL]
GLOW=Image.new("L",(400,400)); ImageDraw.Draw(GLOW).ellipse([60,60,340,340],fill=255); GLOW=GLOW.filter(ImageFilter.GaussianBlur(60))
def background(si,t):
    img=GRADS[si].copy()
    # moving soft light blobs
    for k in range(3):
        cx=W/2+math.sin(t*0.4+k*2.1)*380; cy=H*(0.25+0.3*k)+math.cos(t*0.33+k)*200
        lay=Image.new("RGB",(400,400),(255,255,255))
        img.paste(lay,(int(cx-200),int(cy-200)),GLOW.point(lambda v:int(v*0.22)))
    return img
def draw_floaters(img,t,front):
    for f in floaters:
        if front: return
        y=(f["y"]-t*f["sp"])%(H+300)-150; x=f["x"]+math.sin(t*0.8+f["ph"])*f["amp"]
        r=f["im"].rotate(f["rs"]*t+math.sin(t+f["ph"])*15,resample=Image.BICUBIC)
        img.paste(r,(int(x-r.width/2),int(y-r.height/2)),r)
def draw_twinkles(d,t):
    for (x,y,p,s) in twinkles:
        a=max(0,math.sin(t*s+p)); 
        if a<0.2: continue
        r=2+4*a; al=int(220*a)
        d.line([(x-r*2,y),(x+r*2,y)],fill=(255,255,255,al),width=2); d.line([(x,y-r*2),(x,y+r*2)],fill=(255,255,255,al),width=2)
# ---------- icons ----------
def icon(img,kind,t,lt,acc,events,si):
    lay=Image.new("RGBA",(700,700)); d=ImageDraw.Draw(lay); cx=cy=350
    sc=back(lt/0.6,2.6); s=int(150*sc)
    if s<=2: return
    d.ellipse([cx-s*1.55,cy-s*1.55,cx+s*1.55,cy+s*1.55],fill=(255,255,255,45))
    d.ellipse([cx-s*1.3,cy-s*1.3,cx+s*1.3,cy+s*1.3],fill=(255,255,255,35))
    if kind in("pill","nopill"):
        a=math.radians(-35+8*math.sin(t*2.2)); L=s*1.15; w=s*0.48
        dx,dy=math.cos(a)*L/2,math.sin(a)*L/2
        d.line([(cx-dx,cy-dy),(cx,cy)],fill=(255,255,255,255),width=int(w)); d.line([(cx,cy),(cx+dx,cy+dy)],fill=acc+(255,),width=int(w))
        d.ellipse([cx-dx-w/2,cy-dy-w/2,cx-dx+w/2,cy-dy+w/2],fill=(255,255,255,255)); d.ellipse([cx+dx-w/2,cy+dy-w/2,cx+dx+w/2,cy+dy+w/2],fill=acc+(255,))
        if kind=="pill":
            q=back((lt-0.9)/0.4)
            if q>0.01:
                rr=s*0.45*q; px,py=cx+s,cy-s*0.9
                d.ellipse([px-rr,py-rr,px+rr,py+rr],fill=(235,60,85,255))
                f=ImageFont.truetype(FB,max(8,int(s*0.6*q))); d.text((px,py),"?",font=f,fill="white",anchor="mm")
        else:
            q=ease((lt-0.7)/0.5)
            if q>0:
                r=s*1.3; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(235,70,85,int(255*min(1,q*3))),width=24)
                e=r*0.7; d.line([(cx-e,cy-e),(cx-e+2*e*q,cy-e+2*e*q)],fill=(235,70,85,255),width=24)
    elif kind=="brain":
        for i in range(4):
            a=t*1.1+i*math.pi/2; rr=s*0.6*(1+0.08*math.sin(t*3+i))
            px,py=cx+math.cos(a)*rr,cy+math.sin(a)*rr; q=s*0.55
            d.ellipse([px-q,py-q,px+q,py+q],fill=COLS[i]+(225,))
        q=s*0.35*(1+0.1*math.sin(t*4)); d.ellipse([cx-q,cy-q,cx+q,cy+q],fill=(255,255,255,255))
    elif kind=="puzzle":
        off=(1-ease((lt-0.2)/1.0))*300
        for i,(ox,oy) in enumerate([(-1,-1),(1,-1),(-1,1),(1,1)]):
            p=spr_puzzle(int(s*0.95),COLS[i]+(255,)).rotate((1-ease((lt-0.2)/1.0))*90*ox,resample=Image.BICUBIC)
            px=cx+ox*(s*0.5+off); py=cy+oy*(s*0.5+off)
            lay.paste(p,(int(px-p.width/2),int(py-p.height/2)),p)
    elif kind=="heart":
        b=1+0.1*max(0,math.sin(t*2*math.pi*1.1))**8
        h=spr_heart(int(s*1.9*b),(240,75,110,255)); lay.paste(h,(int(cx-h.width/2),int(cy-h.height/2-10)),h)
        p=spr_puzzle(int(s*0.55*b),(255,255,255,240)); lay.paste(p,(int(cx-p.width/2),int(cy-p.height/2-25)),p)
    bob=math.sin(t*1.6)*18; rot=math.sin(t*1.1)*4
    lay=lay.rotate(rot,resample=Image.BICUBIC)
    img.paste(lay,(int(W/2-350),int(560-350+bob)),lay)
# ---------- confetti ----------
bursts=[]
def burst(t0,cx,cy,n=36):
    rnd=random.Random(int(t0*100))
    bursts.append([(t0,cx,cy,rnd.uniform(0,6.28),rnd.uniform(500,1100),rnd.choice(COLS),rnd.uniform(8,16),rnd.uniform(-8,8)) for _ in range(n)])
def draw_confetti(d,t):
    for b in bursts:
        for (t0,cx,cy,a,v,c,s,sp) in b:
            dt=t-t0
            if dt<0 or dt>1.8: continue
            x=cx+math.cos(a)*v*dt*0.9; y=cy+math.sin(a)*v*dt*0.9+500*dt*dt
            al=int(255*(1-dt/1.8)); r=s*(1-dt/2.2)
            ang=sp*dt; dx,dy=math.cos(ang)*r,math.sin(ang)*r*0.5
            d.polygon([(x-dx,y-dy),(x+dy,y-dx),(x+dx,y+dy),(x-dy,y+dx)],fill=c+(al,))
# ---------- text ----------
FONTC={}
def font(sz):
    if sz not in FONTC: FONTC[sz]=ImageFont.truetype(FB,sz)
    return FONTC[sz]
WORDC={}
def word_img(w,sz,col):
    k=(w,sz,col)
    if k not in WORDC:
        f=font(sz); bb=f.getbbox(w); ww,hh=bb[2]+20,sz+40
        im=Image.new("RGBA",(ww,hh)); d=ImageDraw.Draw(im)
        (d.text((10+3,10+5),w,font=f,fill=(0,0,0,90)) if col==(255,255,255) else None); d.text((10,10),w,font=f,fill=col+(255,))
        WORDC[k]=im
    return WORDC[k]
def draw_text(img,sc,lt,sdur,acc,fade,events,t,si):
    d=ImageDraw.Draw(img,"RGBA")
    q=back(lt/0.55,1.8); f=font(60); tw=d.textlength(sc["title"],font=f)
    if tw>W-150: f=font(int(60*(W-150)/tw)); tw=d.textlength(sc["title"],font=f)
    pw=(tw/2+40)*min(1,max(0,q)); y0=880
    if pw>5:
        d.rounded_rectangle([W/2-pw,y0-48,W/2+pw,y0+48],radius=48,fill=acc+(int(255*fade),))
        if q>0.7: d.text((W/2,y0),sc["title"],font=f,fill=(30,25,50,int(255*fade*min(1,(q-0.7)/0.3))),anchor="mm")
    words=[w for l in sc["lines"] for w in l.split()]
    span=max(0.6,sdur*0.62-0.7); per=span/len(words); y=1020; idx=0
    for li,l in enumerate(sc["lines"]):
        sz=76; lw=d.textlength(l,font=font(sz))
        if lw>W-110: sz=int(76*(W-110)/lw); lw=d.textlength(l,font=font(sz))
        x=W/2-lw/2; sp=d.textlength(" ",font=font(sz))
        for w in l.split():
            st=0.7+idx*per; p=(lt-st)/0.3; idx+=1
            ww=d.textlength(w,font=font(sz))
            hl=any(w.strip(".,!?").lower()==h.strip(".,!?").lower() for h in sc["hl"])
            if p>0:
                s=back(p,3.0) if p<1 else 1
                if hl and p>=1: s=1+0.04*math.sin((lt-st)*6)
                im=word_img(w,sz,(35,28,60) if hl else (255,255,255))
                if hl:
                    bw=(ww/2+12)*min(1,max(0,back(p,2.0)))
                    if bw>2: d.rounded_rectangle([x+ww/2-bw,y-4,x+ww/2+bw,y+sz+14],radius=16,fill=acc+(int(255*fade),))
                if abs(s-1)>0.01 and s>0.02: im=im.resize((max(1,int(im.width*s)),max(1,int(im.height*s))),Image.BICUBIC)
                if fade<1: im=im.copy(); im.putalpha(im.getchannel("A").point(lambda v:int(v*fade)))
                yy=y+(1-min(1,p))*30
                img.paste(im,(int(x+ww/2-im.width/2),int(yy+(sz+40)/2-10-im.height/2)),im)
            x+=ww+sp
        y+=sz+34
# ---------- main ----------
events=[]
starts=list(timings)+[dur+10]
for i,s in enumerate(timings):
    events.append(("whoosh",max(0,s-0.25)) if i>0 else ("sparkle",0.2))
    events.append(("pop",s+0.35)); events.append(("sparkle" if i in(2,3) else "pop",s+0.95))
    burst(s+0.45,W/2,560)
events.append(("riser",timings[4]-1.4)); events.append(("heart",timings[4]+1.0)); events.append(("heart",timings[4]+2.0)); events.append(("ding",dur-1.6))
proc=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
 "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",out],stdin=subprocess.PIPE)
def scene_frame(si,t):
    lt=t-starts[si]; sdur=starts[si+1]-starts[si] if si<4 else dur-starts[si]
    img=background(si,t).convert("RGBA"); acc=ACC[si]
    draw_floaters(img,t,False)
    d=ImageDraw.Draw(img,"RGBA"); draw_twinkles(d,t)
    fade=1.0 if si<4 else 1-ease((t-(dur-0.6))/0.6)
    icon(img,scenes[si]["icon"],t,lt,acc,events,si)
    draw_confetti(ImageDraw.Draw(img,"RGBA"),t)
    draw_text(img,scenes[si],lt,sdur,acc,fade,events,t,si)
    draw_floaters(img,t,True)
    d=ImageDraw.Draw(img,"RGBA")
    d.text((W/2,H-150),"Har bir bola alohida e'tiborga loyiq",font=ImageFont.truetype(FR,40),fill=(255,255,255,int(180*fade)),anchor="mm")
    # progress bar
    d.rounded_rectangle([80,90,W-80,100],radius=5,fill=(255,255,255,60))
    d.rounded_rectangle([80,90,80+(W-160)*min(1,t/dur),100],radius=5,fill=acc+(230,))
    # camera: punch-in at scene start + slow drift zoom
    z=1.0+0.05*(1-ease(lt/0.7))+0.015*math.sin(t*0.5)
    if z>1.001:
        cw,ch=W/z,H/z; ox=max(0,min(W-cw,(W-cw)/2+math.sin(t*0.7)*6)); oy=(H-ch)/2
        img=img.resize((W,H),Image.BICUBIC,box=(ox,oy,ox+cw,oy+ch))
    return img.convert("RGB")
N=int(dur*FPS)
for fi in range(N):
    t=fi/FPS; si=max(i for i in range(5) if starts[i]<=t)
    img=scene_frame(si,t)
    # circular wipe into next scene over last 0.5s
    if si<4:
        tr=(t-(starts[si+1]-0.5))/0.5
        if tr>0:
            nxt=scene_frame(si+1,starts[si+1]+0.0001)
            m=Image.new("L",(W,H)); r=eio(tr)*1150
            ImageDraw.Draw(m).ellipse([W/2-r,960-r,W/2+r,960+r],fill=255)
            img.paste(nxt,(0,0),m)
    if t<0.4: img=Image.blend(Image.new("RGB",(W,H)),img,t/0.4)
    proc.stdin.write(img.tobytes())
proc.stdin.close(); proc.wait()
json.dump(events,open("events.json","w")); print("frames",N)
