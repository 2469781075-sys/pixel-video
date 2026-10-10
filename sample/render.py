from PIL import Image, ImageDraw, ImageFont
import math, subprocess
from pathlib import Path
P=Path(__file__).parent
W,H=320,180
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',32)
subprocess.run(['ffmpeg','-version'],stdout=subprocess.DEVNULL,check=True)
p=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','12','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'window.mp4')],stdin=subprocess.PIPE,stderr=open(P/'render.log','w'))
shots=[]
for n in range(240):
 t=n/12
 opened=max(0,min(1,(t-9)/3))
 night=max(0,min(1,(t-15)/4))
 def col(a,b): return tuple(int(x*(1-night)+y*night) for x,y in zip(a,b))
 im=Image.new('RGB',(W,H),col((49,61,73),(17,24,44))); d=ImageDraw.Draw(im)
 # classroom architecture and converging floor tracks
 d.rectangle((0,0,319,86),fill=col((83,96,105),(29,39,60)))
 d.rectangle((125,17,270,51),fill=col((36,65,62),(23,39,49)))
 d.rectangle((121,51,274,55),fill=(100,91,76))
 d.rectangle((188,37,209,61),fill=(115,104,89))
 d.rectangle((181,58,218,68),fill=(88,79,71))
 for x in range(-100,500,38): d.line((160+(x-160)*.42,84,x,160),fill=col((69,78,86),(36,44,61)),width=2)
 # left-hand window
 d.rectangle((6,15,82,82),fill=(26,38,49))
 sky=col((119+int(opened*28),151+int(opened*25),164+int(opened*15)),(48,64,102))
 d.rectangle((10,19,78,78),fill=sky)
 for k in range(12):
  x=11+(k*17)%65; y=20+int((k*13+t*24)%55)
  d.line((x,y,x-2,y+4),fill=col((165,195,204),(66,86,125)))
 d.rectangle((10,63,78,78),fill=col((74,115,115),(29,44,70)))
 for k in range(4): d.rectangle((12+k*19,59-k%2*7,20+k*19,76),fill=col((65,92,100),(26,36,58)))
 shift=int(opened*25)
 d.rectangle((9,18,43-shift,79),outline=(135,157,163),width=2)
 d.rectangle((45+shift,18,79,79),outline=(135,157,163),width=2)
 d.line((44,16,44,82),fill=(53,65,78),width=2)
 # desks, pupils; central little groups versus isolated protagonist
 def pupil(x,y,alone=False):
  bob=0 if alone else int(math.sin(t*3+x)*1.5)
  y+=bob
  d.rectangle((x-3,y-9,x+3,y-3),fill=col((178,152,134),(95,96,117)))
  d.rectangle((x-4,y-12,x+3,y-8),fill=(29,33,43))
  d.rectangle((x-5,y-2,x+5,y+9),fill=col((81,112,135) if alone else (105,111,122),(45,54,80)))
  if alone and 8<t<12: d.line((x-5,y+2,x-15,y-int(opened*5)),fill=(157,150,141),width=2)
 for row in range(3):
  y=86+row*25
  for c in range(5):
   x=39+c*58+row*3
   pupil(x,y,alone=c==0 and row==1)
   d.rectangle((x-15,y+7,x+19,y+13),fill=col((135,119,93),(64,64,79)))
   d.line((x-13,y+14,x-13,y+22),fill=(37,41,50),width=2)
   d.line((x+16,y+14,x+16,y+22),fill=(37,41,50),width=2)
   if c>0 and t<9:
    q=int(t*3+c+row)%3
    d.rectangle((x+5,y-21,x+15+q,y-18),fill=(154,164,165))
 # wind traces, flowing into the whole room then vanishing
 if opened:
  for k in range(7):
   x=int((t*34+k*43)%340)-10; y=51+k*12
   d.line([(x,y),(x+9,y-2),(x+20,y-2),(x+29,y-5)],fill=col((140,190,180),(55,80,111)),width=1)
 # light from window
 if night>.2: d.line((10,80,58,145),fill=(88,106,144),width=2)
 d.rectangle((0,158,319,179),fill=(13,20,32))
 out=im.resize((960,540),Image.Resampling.NEAREST)
 od=ImageDraw.Draw(out)
 line=('教室是狭窄逼仄的。' if t<5 else '他们围成了一个个小小世界。' if t<9 else '天地之间唤起一片清澈的凉。' if t<15 else '我还是跑不出那间教室啊。')
 box=od.textbbox((0,0),line,font=font); od.text(((960-box[2])/2,482),line,font=font,fill=(216,227,228))
 p.stdin.write(out.tobytes())
 if n in [24,84,156,222]: shots.append(out.copy())
p.stdin.close()
if p.wait(): raise RuntimeError('ffmpeg failed; see render.log')
contact=Image.new('RGB',(960,1080))
for i,s in enumerate(shots):contact.paste(s.resize((480,270)),((i%2)*480,(i//2)*540))
# compact 2x2 storyboard
contact=Image.new('RGB',(960,540))
for i,s in enumerate(shots): contact.paste(s.resize((480,270)),((i%2)*480,(i//2)*270))
contact.save(P/'storyboard.png')
shots[2].save(P/'poster.png')
print('Rendered 240 frames, 20 seconds: '+str(P/'window.mp4'))
