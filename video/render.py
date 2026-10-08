# Renders a 1080x1920 motion video: animated pastel blobs, puzzle-piece / heart motifs,
# word-by-word kinetic captions synced to scene timings. Frames piped to ffmpeg.
import sys, json, math, subprocess, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H,FPS=1080,1920,30
audio=sys.argv[1]; timings=json.loads(open(sys.argv[2]).read()); out=sys.argv[3]
dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",audio]))+1.2
FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PAL=[((24,48,94),(46,110,170)),((88,40,110),(170,80,140)),((20,90,100),(40,160,150)),((110,60,20),(220,140,60)),((30,70,140),(80,160,220))]
ACC=[(255,210,90),(255,140,170),(120,230,200),(255,200,120),(255,230,120)]
scenes=[
 {"title":"DIQQAT!","lines":["Autizmni 100% davolaydigan","dori topildi?","Hozircha ishonmay turing!"],"hl":["100%","ishonmay"],"icon":"pill"},
 {"title":"AUTIZM — KASALLIK EMAS","lines":["U gripp yoki","shamollashga o'xshamaydi.","Dori ichib o'tkazib","bo'lmaydi."],"hl":["emas","o'xshamaydi."],"icon":"nopill"},
 {"title":"MIYANING BOSHQACHA ISHLASHI","lines":["Bola dunyoni boshqacha","ko'radi, eshitadi,","his qiladi.","Har bir bola — o'ziga xos."],"hl":["ko'radi,","eshitadi,","his","o'ziga","xos."],"icon":"brain"},
 {"title":"QABUL QILING VA O'RGATING","lines":["Gapirishni","Muloqot qilishni","O'zini boshqarishni"],"hl":["Gapirishni","Muloqot","boshqarishni"],"icon":"puzzle"},
 {"title":"BIZ YORDAM BERAMIZ","lines":["Farzandingiz tashxisli bo'lsa,","markazimizga keling!","Qo'ldan kelgancha","yordam beramiz."],"hl":["markazimizga","keling!","yordam"],"icon":"heart"},
]
fT=ImageFont.truetype(FB,62); fL=ImageFont.truetype(FB,74); fS=ImageFont.truetype(FR,40)
def ease(t): t=max(0,min(1,t)); return 1-(1-t)**3
def back(t):
    t=max(0,min(1,t)); c=1.70158; return 1+(c+1)*(t-1)**3+c*(t-1)**2
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
random.seed(3)
blobs=[(random.random(),random.random(),random.uniform(160,320),random.uniform(0.2,0.5),random.random()*6.28) for _ in range(9)]
bubbles=[(random.random(),random.random(),random.uniform(6,18),random.uniform(30,80)) for _ in range(40)]
def bg(t,si,blend):
    a=PAL[si]; b=PAL[min(si+1,4)]
    c1=lerp(a[0],b[0],blend); c2=lerp(a[1],b[1],blend)
    img=Image.new("RGB",(W,H)); d=ImageDraw.Draw(img)
    for y in range(0,H,8): d.rectangle([0,y,W,y+8],fill=lerp(c1,c2,y/H))
    ov=Image.new("RGBA",(W//4,H//4),(0,0,0,0)); od=ImageDraw.Draw(ov)
    for (x,y,r,s,p) in blobs:
        cx=(x*W+math.sin(t*s+p)*120)/4; cy=(y*H+math.cos(t*s*0.8+p)*160)/4; rr=r/4
        od.ellipse([cx-rr,cy-rr,cx+rr,cy+rr],fill=(255,255,255,28))
    ov=ov.filter(ImageFilter.GaussianBlur(18)).resize((W,H))
    img.paste(ov,(0,0),ov); d=ImageDraw.Draw(img,"RGBA")
    for (x,y,r,sp) in bubbles:
        yy=(y*H - t*sp)%H; xx=x*W+math.sin(t+y*10)*20
        d.ellipse([xx-r,yy-r,xx+r,yy+r],outline=(255,255,255,70),width=2)
    return img
def puzzle(d,cx,cy,s,col,rot=0):
    pts=[]
    d.rounded_rectangle([cx-s,cy-s,cx+s,cy+s],radius=int(s*0.2),fill=col)
    k=s*0.38
    d.ellipse([cx+s-k*0.4,cy-k,cx+s+k*1.6,cy+k],fill=col)
    d.ellipse([cx-k,cy-s-k*1.6,cx+k,cy-s+k*0.4],fill=col)
def heart(d,cx,cy,s,col):
    r=s*0.55
    d.ellipse([cx-2*r,cy-r*1.4,cx,cy+r*0.6],fill=col); d.ellipse([cx,cy-r*1.4,cx+2*r,cy+r*0.6],fill=col)
    d.polygon([(cx-2*r+4,cy-r*0.1),(cx+2*r-4,cy-r*0.1),(cx,cy+s*1.5)],fill=col)
def icon(img,kind,t,lt,acc):
    d=ImageDraw.Draw(img,"RGBA"); cx,cy=W//2,560
    sc=back(lt/0.7); pulse=1+0.04*math.sin(t*3)
    s=int(150*sc*pulse)
    if s<=2: return
    d.ellipse([cx-s*1.5,cy-s*1.5,cx+s*1.5,cy+s*1.5],fill=(255,255,255,40))
    if kind in("pill","nopill"):
        a=math.radians(-35+6*math.sin(t*2)); L=s*1.1; w=s*0.45
        dx,dy=math.cos(a)*L/2,math.sin(a)*L/2
        d.line([(cx-dx,cy-dy),(cx,cy)],fill=(255,255,255,255),width=int(w)); d.line([(cx,cy),(cx+dx,cy+dy)],fill=acc+(255,),width=int(w))
        for (px,py) in [(cx-dx,cy-dy),(cx+dx,cy+dy)]:
            d.ellipse([px-w/2,py-w/2,px+w/2,py+w/2],fill=(255,255,255,255) if px<cx else acc+(255,))
        if kind=="pill":
            q=ease((lt-0.8)/0.4)
            if q>0:
                d.ellipse([cx+s*0.6,cy-s*1.3,cx+s*1.4,cy-s*0.5],fill=(230,60,80,int(255*q)))
                f=ImageFont.truetype(FB,int(s*0.6)); d.text((cx+s,cy-s*0.9),"?",font=f,fill=(255,255,255,int(255*q)),anchor="mm")
        else:
            q=ease((lt-0.6)/0.5)
            if q>0:
                r=s*1.25; d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(235,70,80,255),width=22)
                e=q; d.line([(cx-r*0.7,cy-r*0.7),(cx-r*0.7+1.4*r*0.7*e,cy-r*0.7+1.4*r*0.7*e)],fill=(235,70,80,255),width=22)
    elif kind=="brain":
        cols=[(255,140,170),(120,230,200),(255,210,90),(130,180,255)]
        for i in range(4):
            a=t*0.8+i*math.pi/2; rr=s*0.55
            px,py=cx+math.cos(a)*rr,cy+math.sin(a)*rr; q=s*0.55
            d.ellipse([px-q,py-q,px+q,py+q],fill=cols[i]+(220,))
        d.ellipse([cx-s*0.35,cy-s*0.35,cx+s*0.35,cy+s*0.35],fill=(255,255,255,255))
    elif kind=="puzzle":
        cols=[(255,140,170),(120,230,200),(255,210,90),(130,180,255)]
        off=(1-ease((lt-0.2)/0.9))*260
        for i,(ox,oy) in enumerate([(-1,-1),(1,-1),(-1,1),(1,1)]):
            puzzle(d,cx+ox*(s*0.55+off),cy+oy*(s*0.55+off),int(s*0.48),cols[i]+(255,))
    elif kind=="heart":
        b=1+0.08*abs(math.sin(t*2.6))
        heart(d,cx,cy-20,int(s*b),(240,80,110,255))
        puzzle(d,cx,cy-30,int(s*0.28*b),(255,255,255,235))
def draw_text(img,sc,lt,sdur,acc,fade):
    d=ImageDraw.Draw(img,"RGBA")
    # title pill
    q=ease(lt/0.5); a=int(255*q*fade)
    tw=d.textlength(sc["title"],font=fT)
    if tw>W-120: f=ImageFont.truetype(FB,int(62*(W-140)/tw)); tw=d.textlength(sc["title"],font=f)
    else: f=fT
    y0=860+int((1-q)*40)
    d.rounded_rectangle([W/2-tw/2-40,y0-50,W/2+tw/2+40,y0+50],radius=50,fill=acc+(a,))
    d.text((W/2,y0),sc["title"],font=f,fill=(30,30,50,a),anchor="mm")
    words=[(li,w) for li,l in enumerate(sc["lines"]) for w in l.split()]
    span=max(0.6,sdur*0.62-0.6); per=span/len(words)
    y=1020; idx=0
    for li,l in enumerate(sc["lines"]):
        ws=l.split(); f=fL
        lw=d.textlength(l,font=f)
        if lw>W-100: f=ImageFont.truetype(FB,int(74*(W-100)/lw)); lw=d.textlength(l,font=f)
        x=W/2-lw/2; sp=d.textlength(" ",font=f)
        for w in ws:
            st=0.6+idx*per; p=ease((lt-st)/0.35); idx+=1
            ww=d.textlength(w,font=f)
            if p>0:
                al=int(255*p*fade); col=acc if any(w.startswith(h.rstrip(".,!")) for h in sc["hl"]) else (255,255,255)
                yy=y+int((1-p)*50)
                d.text((x+3,yy+4),w,font=f,fill=(0,0,0,int(al*0.35)))
                d.text((x,yy),w,font=f,fill=col+(al,))
            x+=ww+sp
        y+=f.size+30
    # footer
    d.text((W/2,H-130),"2-aprel — Butunjahon autizm haqida xabardorlik kuni" if False else "Har bir bola alohida e'tiborga loyiq",font=fS,fill=(255,255,255,170),anchor="mm")
proc=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",audio,
 "-filter_complex","[1:a]adelay=400|400,apad[a]","-map","0:v","-map","[a]","-shortest","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",out],stdin=subprocess.PIPE)
starts=[s+0.4 for s in timings]+[dur+10]; starts[0]=0
N=int(dur*FPS)
for fi in range(N):
    t=fi/FPS; si=max(i for i in range(5) if starts[i]<=t)
    sdur=starts[si+1]-starts[si] if si<4 else dur-starts[si]
    lt=t-starts[si]; blend=ease((lt-(sdur-0.6))/0.6) if si<4 else 0
    img=bg(t,si,blend); acc=ACC[si]
    fade=1-ease((lt-(sdur-0.45))/0.4) if si<4 else 1-ease((t-(dur-0.5))/0.5)
    ic=img.copy(); icon(ic,scenes[si]["icon"],t,lt,acc)
    img=Image.blend(img,ic,max(0,fade))
    draw_text(img,scenes[si],lt,sdur,acc,max(0,fade))
    proc.stdin.write(img.tobytes())
proc.stdin.close(); proc.wait(); print("done",N)
