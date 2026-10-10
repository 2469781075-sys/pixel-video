"""Render the first 30 seconds of Window: fixed RPG map, independent animated actors."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math, random, subprocess, wave, json
import numpy as np
P=Path(__file__).resolve().parent
W,H,SCALE,FPS,DURATION=640,360,3,24,30
CUES=[
 (0,3,'不知道大家的中学生活是怎么样的？'),
 (3,7,'教室是狭窄逼仄的。'),
 (7,11,'几路层层格格的铁轨，规矩地张满地板。'),
 (11,15,'他们围成了一个个小小世界。'),
 (15,19,'讲述着我听不懂的历史。'),
 (19,23,'我经常被安排到最左边靠窗的位置。'),
 (23,27,'那四四方方的格子里，或许住着一个梦想也说不定。'),
 (27,30,'只是，我能经受灼热目光的冒险吗？')]

def ease(v):
 v=max(0,min(1,v));return v*v*(3-2*v)

def sprite_cells(path,cols,rows,heights):
 im=Image.open(path).convert('RGBA');out=[]
 for row in range(rows):
  for col in range(cols):
   cell=im.crop((round(im.width*col/cols),round(im.height*row/rows),round(im.width*(col+1)/cols),round(im.height*(row+1)/rows)))
   a=np.asarray(cell.getchannel('A'))
   xx=np.where((a>190).sum(axis=0)>5)[0];yy=np.where((a>190).sum(axis=1)>5)[0]
   if not len(xx) or not len(yy):raise RuntimeError('Empty atlas cell: '+str((col,row)))
   cell=cell.crop((int(xx[0]),int(yy[0]),int(xx[-1])+1,int(yy[-1])+1))
   target_h=heights[len(out)]
   out.append(cell.resize((round(cell.width*target_h/cell.height),target_h),Image.Resampling.NEAREST))
 return out

class Film:
 def __init__(self):
  self.background=Image.open(P/'assets/background.png').convert('RGB').resize((W,H),Image.Resampling.NEAREST)
  self.npcs=sprite_cells(P/'assets/students.png',4,2,[32]*8)
  self.hero=sprite_cells(P/'assets/hero-poses.png',4,1,[32,32,52,52])
  self.font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',38)
  self.small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22)
  # One actor per occupied seat; keep hero and adjacent seat separate.
  self.cast=[]
  xs=[128,209,285,366,444,524];ys=[125,166,208,249]
  for r,y in enumerate(ys):
   for c,x in enumerate(xs):
    if (r,c) in [(0,0),(1,0),(1,1)]:continue
    kind=(r*3+c)%4
    if (r,c)==(0,5):kind=4
    if (r,c)==(1,3):kind=4
    if (r,c)==(2,4):kind=4
    if (r,c) in [(1,2),(2,2),(3,5)]:kind=6
    self.cast.append({'x':x,'y':y,'kind':kind,'phase':r*1.7+c*.8,'seat':[r,c]})
  self.cast.extend([
   {'x':552,'y':125,'kind':5,'phase':1.5,'seat':None},
   {'x':391,'y':167,'kind':5,'phase':3.2,'seat':None},
   {'x':473,'y':209,'kind':5,'phase':4.1,'seat':None},
   {'x':311,'y':249,'kind':5,'phase':5.2,'seat':None},
  ])
  assert len(self.cast)+1==26
  rng=random.Random(57)
  self.rain=[]
  # Five identical flat window apertures, independent of floor perspective.
  for i,(y0,y1) in enumerate([(18,67),(78,123),(135,182),(195,241),(253,296)]):
   for k in range(9):self.rain.append((rng.randrange(41,77),rng.uniform(y0,y1),rng.uniform(17,27),y0,y1))

 def put(self,im,sprite,x,y):
  im.paste(sprite,(round(x-sprite.width/2),round(y)),sprite)

 def actor(self,im,a,t):
  kind=a['kind'];phase=a['phase'];sprite=self.npcs[kind];x,y=a['x'],a['y']
  # Separate head movement from the anchored arms/body.
  turn=kind in [0,2] and 7<t<18 and 3<((t+phase)%9)<5.5
  moving=(kind in [4,5,6,7] or turn) and t>7
  nod=(1 if math.sin(t*1.7+phase)>.83 else 0) if moving else 0
  if nod or turn:
   head_source=self.npcs[4 if kind==0 else 5] if turn else sprite
   head=head_source.crop((0,0,head_source.width,20));body=sprite.crop((0,20,sprite.width,sprite.height))
   self.put(im,body,x,y+20);self.put(im,head,x,y+nod)
  else:self.put(im,sprite,x,y)
  d=ImageDraw.Draw(im)
  # Tiny hands and page motion give the crowd distinct activities.
  if kind==6:
   by=y+28;d.polygon([(x-8,by),(x,by-1),(x+8,by),(x+8,by+4),(x-8,by+4)],fill='#f5e8c8');d.line((x,by,x,by+4),fill='#b29a7d')
   if (t+phase)%6<.35:d.line((x,by-1,x+5,by-3),fill='#fff1d7')
  if kind in [4,5] and 8<t<19 and (t+phase)%4<2.8:
   bx=x+(8 if kind==4 else -16);by=y-8
   d.rectangle((bx,by,bx+13,by+5),fill='#f8e9c9');d.polygon([(bx+3,by+5),(bx+5,by+8),(bx+7,by+5)],fill='#f8e9c9')
   count=1+int((t*2+phase)%3)
   for j in range(count):d.point((bx+3+j*3,by+2),fill='#a5877c')

 def frame(self,t,caption=True):
  im=self.background.copy();d=ImageDraw.Draw(im)
  # Rain is clipped inside straight panes: window frame pixels never move.
  for x,start,speed,y0,y1 in self.rain:
   y=y0+round((start-y0+t*speed)%(y1-y0-4))
   d.line((x,y,x,y+3),fill='#c0d6e3')
  # Readable notebooks; local page flips do not disturb the fixed tile map.
  for a in self.cast:
   if a['seat'] is not None and a['kind']<4:
    x,y=a['x'],a['y']+13
    d.rectangle((x-7,y-3,x+7,y+2),fill='#e8d8b6');d.line((x,y-3,x,y+2),fill='#b39877')
  for a in sorted(self.cast,key=lambda a:a['y']):self.actor(im,a,t)
  # A shy hero reads, looks toward the window, stands and hesitates at its latch.
  hx,hy=128,151
  if t<8:
   sprite=self.hero[0]
  elif t<11:
   sprite=self.hero[1]
  elif t<18:
   sprite=self.hero[0]
  elif t<23.5:
   sprite=self.hero[1]
  elif t<27:
   sprite=self.hero[2];hx=128-16*ease((t-24)/2.5);hy=133
   # Two walking foot phases; upper body remains anchored.
   if 24<t<26.5 and int(t*4)%2:
    leg=sprite.crop((0,37,sprite.width,52));body=sprite.crop((0,0,sprite.width,37))
    self.put(im,body,hx,hy);self.put(im,leg,hx+1,hy+37);sprite=None
  else:
   sprite=self.hero[3];hx=112;hy=133
  if sprite is not None:self.put(im,sprite,hx,hy)
  # Hero book on the near desk; subtle tilt at the start of the hesitant movement.
  d=ImageDraw.Draw(im);d.rectangle((119,176,136,181),fill='#f6e9ce');d.line((127,176,127,181),fill='#b4a086')
  if t<23.5:
   dy=0 # No floating marker bounce, in keeping with the stable-camera direction.
   d.polygon([(128,141+dy),(131,144+dy),(128,147+dy),(125,144+dy)],fill='#edf4e8');d.point((128,144),fill='#85cbd3')
  # A very small latch highlight is the visual handoff to the next third.
  if t>27:
   d.rectangle((78,161,80,164),fill='#ddc99d')
  out=im.resize((W*SCALE,H*SCALE),Image.Resampling.NEAREST)
  if caption:
   layer=Image.new('RGBA',out.size);ld=ImageDraw.Draw(layer)
   ld.rectangle((105,972,1815,1060),fill=(29,34,52,234));ld.rectangle((105,972,1815,1060),outline=(137,144,153,180),width=2)
   out=Image.alpha_composite(out.convert('RGBA'),layer).convert('RGB');od=ImageDraw.Draw(out)
   text=next((s for start,end,s in CUES if start<=t<end),'')
   box=od.textbbox((0,0),text,font=self.font);od.text(((W*SCALE-box[2])/2,990),text,font=self.font,fill='#f8eed5')
  return out

def soundtrack():
 sr=48000;tt=np.arange(sr*DURATION)/sr;rng=np.random.default_rng(38)
 noise=rng.normal(0,1,len(tt));rain=np.convolve(noise,np.ones(5)/5,mode='same')*.025
 # An original soft game-like score with no third-party recordings.
 music=np.zeros(len(tt))
 for start,freq in [(0,261.63),(2.5,329.63),(5,392),(7.5,293.66),(10,349.23),(12.5,440),(15,329.63),(17.5,293.66),(20,261.63),(23,329.63),(26,293.66)]:
  dt=np.maximum(tt-start,0);env=np.where(tt>=start,np.exp(-dt/3.2)*(1-np.exp(-dt*20)),0)
  music+=(np.sin(2*np.pi*freq*tt)+.22*np.sin(2*np.pi*freq*2*tt)+.08*np.sin(2*np.pi*freq*3*tt))*.045*env
 # Soft nonverbal chatter: changes in attention are audible without invented dialogue.
 chatter=np.zeros(len(tt))
 for k in range(8):
  freq=145+k*16;env=np.maximum(0,np.sin(tt*(1.7+k*.1)+k))**5
  chatter+=(np.sin(2*np.pi*freq*tt)+.25*np.sin(2*np.pi*freq*2.03*tt))*env*.003
 attention=1-.7*np.clip((tt-18)/6,0,1)
 base=rain+music+chatter*attention
 for when in [6.3,13.4,18.6]:
  dt=tt-when;base+=rng.normal(0,1,len(tt))*.009*np.where((dt>=0)&(dt<.18),np.exp(-np.maximum(dt,0)*18),0)
 for when in [24.3,25.1,25.9]:
  dt=tt-when;base+=np.sin(2*np.pi*95*tt)*.04*np.where((dt>=0)&(dt<.12),np.exp(-np.maximum(dt,0)*35),0)
 fade=np.minimum(1,tt/.5)
 left=(base+rain*.15)*fade;right=(base-rain*.1)*fade
 stereo=np.stack([left,right],axis=1)
 with wave.open(str(P/'soundtrack.wav'),'wb') as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(stereo,-.95,.95)*32767).astype('<i2').tobytes())

def timecode(s):
 ms=round(s*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def main():
 film=Film();soundtrack()
 (P/'subtitles.srt').write_text('\n\n'.join(f'{i+1}\n{timecode(a)} --> {timecode(b)}\n{s}' for i,(a,b,s) in enumerate(CUES))+'\n')
 (P/'cast.json').write_text(json.dumps({'student_count':len(film.cast)+1,'camera':'fixed','duration_seconds':DURATION,'fps':FPS,'npcs':film.cast},ensure_ascii=False,indent=2)+'\n')
 shots=[]
 with open(P/'render.log','w') as log:
  p=subprocess.Popen(['ffmpeg','-y','-nostats','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(FPS),'-i','-','-i',str(P/'soundtrack.wav'),'-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-18:TP=-2:LRA=8','-t',str(DURATION),'-movflags','+faststart',str(P/'window-part-01.mp4')],stdin=subprocess.PIPE,stderr=log)
  try:
   for n in range(FPS*DURATION):
    t=n/FPS;frame=film.frame(t);p.stdin.write(frame.tobytes())
    if n in [5*FPS,14*FPS,29*FPS]:shots.append(frame)
   p.stdin.close()
  except BaseException:
   p.kill();p.wait();raise
  if p.wait():raise RuntimeError('FFmpeg failed; inspect render.log')
 for name,shot in zip(['01-classroom.png','02-little-worlds.png','03-window.png'],shots):shot.save(P/name)
 shots[0].save(P/'poster.png')
 sheet=Image.new('RGB',(1920,360))
 for i,shot in enumerate(shots):sheet.paste(shot.resize((640,360),Image.Resampling.NEAREST),(i*640,0))
 sheet.save(P/'storyboard.png')
 print(f'Rendered {DURATION} seconds, {FPS*DURATION} frames, {len(film.cast)+1} students, 1080p stereo.')
if __name__=='__main__':main()
