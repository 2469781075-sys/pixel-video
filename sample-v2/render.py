"""Composite the generated animation layers into a reproducible 24-second film."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math, random, subprocess, wave
import numpy as np
P=Path(__file__).parent
W,H,FPS,SECONDS=640,360,16,24
FONT='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'

def ease(x):
 x=max(0,min(1,x));return x*x*(3-2*x)

def sound():
 sr=24000;tt=np.arange(sr*SECONDS)/sr;rng=np.random.default_rng(21)
 noise=rng.normal(0,1,len(tt))
 rain=np.convolve(noise,np.ones(5)/5,mode='same')*.018
 wind=np.convolve(rng.normal(0,1,len(tt)),np.ones(600)/600,mode='same')*(.3+.65*np.clip((tt-10)/3,0,1))
 music=np.zeros(len(tt))
 for start,freq in [(0,261.63),(3,329.63),(6,392),(9,293.66),(12,349.23),(15,440),(18,329.63),(21,261.63)]:
  dt=np.maximum(tt-start,0);env=np.where(tt>=start,np.exp(-dt/2.4)*(1-np.exp(-dt*15)),0)
  music+=(np.sin(2*np.pi*freq*tt)+.23*np.sin(2*np.pi*freq*2*tt))*.035*env
 fade=np.minimum(1,tt/1.4)*np.minimum(1,(SECONDS-tt)/2.2)
 signal=np.clip((rain+wind+music)*fade,-.9,.9)
 with wave.open(str(P/'ambience.wav'),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((signal*32767).astype('<i2').tobytes())

def load_sprite(path):
 im=Image.open(path).convert('RGBA')
 alpha=np.asarray(im.getchannel('A'))
 xs=np.where((alpha>192).sum(axis=0)>12)[0]
 ys=np.where((alpha>192).sum(axis=1)>12)[0]
 if not len(xs) or not len(ys):raise ValueError('Empty character layer')
 im=im.crop((int(xs[0]),int(ys[0]),int(xs[-1])+1,int(ys[-1])+1))
 return im.resize((131,140),Image.Resampling.NEAREST)

def make_scene(plate,hero,blink,t,particles):
 scene=plate.copy()
 # Small independent breathing motion, anchored at the desk rather than camera.
 rise=round(math.sin(t*1.9)*.65)
 use_blink=((t+.9)%4.6)<.18
 char=blink if use_blink and blink is not None else hero
 scene.paste(char,(204,111+rise),char)
 d=ImageDraw.Draw(scene)
 # Rain over the exterior left panes, avoiding the character and classroom.
 for x,y,s,l in particles:
  yy=round((y+t*s)%211)
  if x<201 and yy<207:
   d.line((x,yy,x-1,yy+l),fill='#d6e1e3',width=1)
 # Fine drifting breeze rather than a flood of opaque lines.
 if t>10:
  for k in range(10):
   x=round((t*16+k*43)%570);y=round(90+k*9+math.sin(t*1.3+k)*8)
   if x<203 or x>336:
    if k%3==0:d.line((x,y,x+6,y-1),fill='#d9e6d1')
    else:d.point((x,y),fill='#e8e7c9')
 # The room gradually cools at the ending, without extinguishing the window.
 night=ease((t-18)/5)
 if night:
  arr=np.asarray(scene).astype(np.float32)
  arr=arr*(1-night*np.array([.47,.38,.22]))+night*np.array([4,5,15])
  scene=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
 # Slow lens movement: classroom -> window child -> wider breath -> return.
 if t<5:
  z=ease(t/5)*.09;cx,cy=320,180
 elif t<10:
  z=.09+ease((t-5)/2)*.31;cx,cy=279,179
 elif t<18:
  z=.40-ease((t-10)/5)*.22;cx,cy=269,177
 else:
  z=.18*(1-ease((t-18)/5));cx,cy=320,180
 cw=round(W*(1-z));ch=round(H*(1-z));left=max(0,min(W-cw,round(cx-cw/2)));top=max(0,min(H-ch,round(cy-ch/2)))
 out=scene.crop((left,top,left+cw,top+ch)).resize((1280,720),Image.Resampling.NEAREST)
 # Typographic overlay is deliberately separate from the pixel illustration.
 layer=Image.new('RGBA',out.size);ld=ImageDraw.Draw(layer)
 ld.rectangle((0,644,1279,719),fill=(43,45,64,224))
 out=Image.alpha_composite(out.convert('RGBA'),layer).convert('RGB');d=ImageDraw.Draw(out)
 font=ImageFont.truetype(FONT,30)
 line=('我经常被安排到最左边靠窗的位置。' if t<6 else
       '那四四方方的格子里，或许住着一个梦想也说不定。' if t<11 else
       '天地之间唤起一片清澈的凉。' if t<18 else
       '我还是跑不出那间教室啊。')
 box=d.textbbox((0,0),line,font=font)
 d.text(((1280-box[2])/2,662),line,font=font,fill='#f7eddb')
 return out

def main():
 plate=Image.open(P/'assets/background.png').convert('RGB').resize((W,H),Image.Resampling.NEAREST)
 hero=load_sprite(P/'assets/hero.png')
 blink_path=P/'assets/hero-blink.png'
 blink=load_sprite(blink_path) if blink_path.exists() else None
 rng=random.Random(23)
 particles=[(rng.randrange(2,201),rng.randrange(210),rng.uniform(24,51),rng.randrange(2,5)) for _ in range(65)]
 sound();shots=[]
 with open(P/'render.log','w') as log:
  p=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','-','-i',str(P/'ambience.wav'),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(P/'window-cute.mp4')],stdin=subprocess.PIPE,stderr=log)
  try:
   for n in range(FPS*SECONDS):
    frame=make_scene(plate,hero,blink,n/FPS,particles)
    p.stdin.write(frame.tobytes())
    if n in [48,128,224,352]:shots.append(frame)
   p.stdin.close()
  except BaseException:
   p.kill();p.wait();raise
  if p.wait():raise RuntimeError('ffmpeg failed; inspect render.log')
 contact=Image.new('RGB',(1280,720))
 for i,s in enumerate(shots):contact.paste(s.resize((640,360),Image.Resampling.NEAREST),((i%2)*640,(i//2)*360))
 contact.save(P/'storyboard.png');shots[2].save(P/'poster.png')
 print('Rendered 24 seconds at 1280x720, 384 frames, with ambient audio.')
if __name__=='__main__':main()
