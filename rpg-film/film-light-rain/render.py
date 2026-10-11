"""Render the approved storyboard as a stable pixel film with original Mambo audio.

Lighting and pose artwork are generated with built-in image_gen and preserved in
assets/. This renderer composites those animation layers on a fixed pixel canvas;
it never edits the retained review sources or adds a camera pan/zoom.
"""
from __future__ import annotations

import argparse
from collections import deque
from functools import lru_cache
import json
import math
from pathlib import Path
import random
import subprocess
import time
import wave
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).resolve().parent
A = P / 'assets'
WORK = P / '_work'
W, H, SCENE_H, FPS = 480, 270, 208, 24
SCALE = 4
SHOTS = json.loads((P / 'shots.json').read_text())['shots']
CUES = json.loads((P / 'narration-timings.json').read_text())['sentences']
SECONDS = float(SHOTS[-1]['end'])
FRAME_COUNT = round(SECONDS * FPS)
NEAREST = Image.Resampling.NEAREST
FONT_FILE = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
EM_SIZE, CAPTION_WIDTH, CAPTION_STEP = 72, 1800, 78
metrics = ImageFont.truetype(FONT_FILE, 1000).getmetrics()
ASS_SIZE = round(EM_SIZE * sum(metrics) / 1000)
FONT = ImageFont.truetype(FONT_FILE, EM_SIZE)
PUNCT = '，；、！？。......'


def ease(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def code(t: float, ass: bool = False) -> str:
    ticks = round(t * (100 if ass else 1000))
    if ass:
        return f'{ticks // 360000}:{ticks // 6000 % 60:02d}:{ticks // 100 % 60:02d}.{ticks % 100:02d}'
    return f'{ticks // 3600000:02d}:{ticks // 60000 % 60:02d}:{ticks // 1000 % 60:02d},{ticks % 1000:03d}'


@lru_cache(maxsize=1024)
def wrap(text: str) -> tuple[str, ...]:
    """Keep every original character, balancing lines and avoiding hanging punctuation."""
    @lru_cache(maxsize=None)
    def width(start: int, end: int) -> float:
        return FONT.getlength(text[start:end])
    for count in range(1, 4):
        target = width(0, len(text)) / count
        states = {(0, 0): (0.0, ())}
        for used in range(count):
            for start in range(len(text)):
                if (used, start) not in states or text[start] in PUNCT:
                    continue
                cost, lines = states[used, start]
                for end in range(start + 1, len(text) + 1):
                    measured = width(start, end)
                    if measured > CAPTION_WIDTH:
                        break
                    if end < len(text) and text[end] in PUNCT:
                        continue
                    penalty = 0 if end == len(text) or text[end - 1] in PUNCT else CAPTION_WIDTH ** 2 * .12
                    score = cost + (measured - target) ** 2 + penalty
                    key = used + 1, end
                    if key not in states or score < states[key][0]:
                        states[key] = score, lines + (text[start:end],)
        if (count, len(text)) in states:
            result = states[count, len(text)][1]
            assert ''.join(result) == text
            return result
    raise ValueError(f'Full sentence cannot fit three large subtitle lines: {text}')


def subtitles() -> None:
    original = ''.join((P / 'original.txt').read_text().splitlines())
    assert ''.join(c['text'] for c in CUES) == original
    srt, events, layouts = [], [], []
    for index, cue in enumerate(CUES):
        lines = wrap(cue['text'])
        srt.append(f"{cue['id']}\n{code(cue['start_seconds'])} --> {code(cue['end_seconds'])}\n{cue['text']}")
        display_end = CUES[index + 1]['start_seconds'] - .04 if index + 1 < len(CUES) else SECONDS - .45
        centers = [952 + (i - (len(lines) - 1) / 2) * CAPTION_STEP for i in range(len(lines))]
        layouts.append({'id':cue['id'], 'text':cue['text'], 'lines':list(lines),
                        'start':cue['start_seconds'], 'end':display_end,
                        'font_em_pixels':EM_SIZE, 'ass_font_size':ASS_SIZE,
                        'widths':[round(FONT.getlength(line), 2) for line in lines],
                        'line_centers':centers, 'panel_box':[0,SCENE_H*SCALE,W*SCALE,H*SCALE]})
        for line, center in zip(lines, centers):
            override = '{\\an5\\pos(960,' + str(round(center)) + ')}'
            events.append(f"Dialogue: 0,{code(cue['start_seconds'],True)},{code(display_end,True)},Caption,,0,0,0,,{override}{line}")
    header = '''[Script Info]
Title: 窗 · 轻颗粒雨天正式动画 · 曼波朗读
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
'''
    header += f'Style: Caption,Noto Sans CJK SC,{ASS_SIZE},&H00FFFFFF,&H00FFFFFF,&H00302010,&H00302010,-1,0,0,0,100,100,0,0,1,2,0,5,48,48,0,1\n'
    header += '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    (P / 'subtitles.srt').write_text('\n\n'.join(srt) + '\n')
    (P / 'subtitles.ass').write_text(header + '\n'.join(events) + '\n')
    (P / 'subtitle-layout.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2)+'\n')
    metadata = ';FFMETADATA1\ntitle=窗 · 轻颗粒雨天版\ncomment=全文逐句原文字幕 · 曼波朗读 · 固定镜头\n'
    for shot in SHOTS:
        metadata += f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(shot['start']*1000)}\nEND={round(shot['end']*1000)}\ntitle={shot['title']}\n"
    (P / 'chapters.ffmeta').write_text(metadata)


class Plate:
    """Fit the complete approved artwork into a fixed viewport, excluding preview captions."""
    def __init__(self, path: Path, art_bottom: int):
        source = Image.open(path).convert('RGB')
        self.source_size = source.size
        self.art_bottom = art_bottom
        art = source.crop((0, 0, source.width, art_bottom))
        self.ratio = min(W / art.width, SCENE_H / art.height)
        self.size = round(art.width * self.ratio), round(art.height * self.ratio)
        self.offset = ((W - self.size[0]) // 2, (SCENE_H - self.size[1]) // 2)
        self.image = Image.new('RGB', (W, SCENE_H), '#17283e')
        self.image.paste(art.resize(self.size, NEAREST), self.offset)

    def xy(self, x: float, y: float) -> tuple[int, int]:
        return round(self.offset[0] + x * self.ratio), round(self.offset[1] + y * self.ratio)

    def box(self, box) -> tuple[int, int, int, int]:
        return (*self.xy(box[0],box[1]), *self.xy(box[2],box[3]))

    def aligned_pose(self, path: Path) -> Image.Image:
        pose = Image.open(path).convert('RGB').resize(self.source_size, NEAREST)
        pose = pose.crop((0,0,self.source_size[0],self.art_bottom)).resize(self.size, NEAREST)
        canvas = Image.new('RGB',(W,SCENE_H),'#17283e')
        canvas.paste(pose,self.offset)
        return canvas


def voice_wave()->Path:
    WORK.mkdir(exist_ok=True)
    target=WORK/'narration.wav'
    if not target.exists():
        with zipfile.ZipFile(P.parent/'narration/mambo/mambo-narration.zip') as archive:
            target.write_bytes(archive.read('narration.wav'))
    with wave.open(str(target)) as audio:
        actual=audio.getnframes()/audio.getframerate()
    assert abs(actual-CUES[-1]['end_seconds'])<.002
    return target


def ambience()->Path:
    """Quiet deterministic rain and a small latch sound, keeping narration dominant."""
    rate=48000;n=round(SECONDS*rate)
    rng=np.random.default_rng(6410)
    timeline=np.arange(n,dtype=np.float32)/rate
    amount=np.full(n,.38,dtype=np.float32)
    amount[(timeline>=26.5)&(timeline<35.37)]=.18
    amount[(timeline>=84.3)&(timeline<95.35)]=.70
    amount[(timeline>=95.35)&(timeline<122.2)]=.16
    amount[timeline>=122.2]=.35
    amount*=np.minimum(1,timeline/1.0)*np.minimum(1,(SECONDS-timeline)/1.2)
    channels=[]
    for channel in range(2):
        noise=rng.normal(0,1,n).astype(np.float32)
        sums=np.concatenate(([0.0],np.cumsum(noise,dtype=np.float64)))
        low=((sums[33:]-sums[:-33])/33).astype(np.float32)
        low=np.pad(low,(16,n-len(low)-16))
        colored=(noise*.23+low*1.4)
        colored/=max(float(np.sqrt(np.mean(colored**2))),1e-6)
        values=colored*.0045*amount
        for at,length,level in [(77.55,.09,.018),(125.18,.08,.012)]:
            count=round(length*rate);tt=np.arange(count)/rate
            click=(np.sin(2*np.pi*1180*tt)+.4*np.sin(2*np.pi*1970*tt))*np.exp(-tt*65)*level
            start=round(at*rate);values[start:start+count]+=click.astype(np.float32)
        channels.append(values)
    stereo=np.column_stack(channels)
    target=WORK/'rain-ambience.wav'
    with wave.open(str(target),'wb') as audio:
        audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(rate)
        audio.writeframes(np.rint(np.clip(stereo,-1,1)*32767).astype('<i2').tobytes())
    return target


def audio_mix()->Path:
    target=WORK/'mix.wav'
    if target.exists():return target
    voice=voice_wave();rain=ambience()
    graph=f'[0:a]apad=whole_dur={SECONDS},aresample=48000,pan=stereo|c0=c0|c1=c0[voice];[voice][1:a]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[out]'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(voice),'-i',str(rain),'-filter_complex',graph,
                    '-map','[out]','-t',str(SECONDS),'-ar','48000','-c:a','pcm_s16le',str(target)],check=True)
    return target


def render_commands(start:float,end:float,name:str)->tuple[list[str],list[str]]:
    stage=WORK/(Path(name).stem+'-picture.mp4')
    vf=f'scale=1920:1080:flags=neighbor,setsar=1,setpts=PTS+{start}/TB,ass=subtitles.ass,setpts=PTS-{start}/TB'
    picture=['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
             '-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-vf',vf,
             '-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',
             '-threads','4','-movflags','+faststart',str(stage)]
    output=P/name if start==0 and end==SECONDS else WORK/name
    mux=['ffmpeg','-v','error','-y','-i',str(stage),'-ss',str(start),'-i',str(WORK/'mix.wav')]
    if start==0 and end==SECONDS:mux+=['-i',str(P/'chapters.ffmeta')]
    mux+=['-map','0:v:0','-map','1:a:0']
    if start==0 and end==SECONDS:mux+=['-map_metadata','2']
    mux+=['-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',str(end-start),
          '-movflags','+faststart',str(output)]
    return picture,mux


def render(film:Film,start:float,end:float,name:str)->Path:
    audio_mix()
    commands=render_commands(start,end,name)
    count=round((end-start)*FPS)
    log=WORK/(Path(name).stem+'-encode.log')
    begun=time.monotonic()
    with log.open('w') as errors:
        process=subprocess.Popen(commands[0],cwd=P,stdin=subprocess.PIPE,stderr=errors)
        try:
            for index in range(count):
                frame=film.frame(start+index/FPS)
                process.stdin.write(frame.tobytes())
                if index and index%(FPS*12)==0:
                    print(f'Render {index/count:.0%}: {start+index/FPS:.1f}s / {end:.1f}s',flush=True)
            process.stdin.close()
        except BaseException:
            process.kill();process.wait();raise
        code_value=process.wait()
    if code_value:
        raise RuntimeError(f'Picture encoding failed ({code_value}): {log.read_text()}')
    subprocess.run(commands[1],cwd=P,check=True)
    result=P/name if start==0 and end==SECONDS else WORK/name
    print(json.dumps({'output':str(result),'duration':count/FPS,'frames':count,
                      'render_seconds':round(time.monotonic()-begun,2),'bytes':result.stat().st_size}),flush=True)
    return result


def extract_frame(video:Path,t:float,path:Path):
    path.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1',str(path)],check=True)


def previews(video:Path)->None:
    folder=P/'previews';folder.mkdir(exist_ok=True)
    records=[]
    for shot in SHOTS:
        at=min(shot['end']-.6,shot['start']+max(1.0,(shot['end']-shot['start'])*.45))
        file=f"{shot['number']:02d}-{Path(shot['asset']).stem.split('-',1)[1]}.png"
        extract_frame(video,at,folder/file)
        records.append({'shot':shot['number'],'time':at,'file':'previews/'+file})
    for at in (75.8,77.8,80.6,83.0,84.5,86.2,124.0,126.2):
        file=f'key-{at:.1f}.png';extract_frame(video,at,folder/file)
        records.append({'time':at,'file':'previews/'+file})
    (P/'preview-times.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    extract_frame(video,46.2,P/'poster.png')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--sample',help='START:END in full-article seconds')
    parser.add_argument('--previews-only',action='store_true')
    args=parser.parse_args()
    WORK.mkdir(exist_ok=True);subtitles()
    name='window-light-rain-mambo.mp4'
    if args.dry_run:
        plan={'native_canvas':[W,H],'scene_height':SCENE_H,'output':[1920,1080],
              'fps':FPS,'seconds':SECONDS,'frames':FRAME_COUNT,'shots':len(SHOTS),
              'sentences':len(CUES),'voice':'Retained original Mambo recording at 1.0x speed',
              'camera':'Fixed throughout each shot','grain':'Static light material grain; never random per frame',
              'caption_em_pixels':EM_SIZE,'ass_font_size':ASS_SIZE,
              'max_caption_lines':max(len(wrap(c['text'])) for c in CUES),
              'commands':render_commands(0,SECONDS,name)}
        (P/'render-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(plan,ensure_ascii=False));return
    if args.previews_only:previews(P/name);return
    film=Film()
    if args.sample:
        start,end=map(float,args.sample.split(':'))
        assert 0<=start<end<=SECONDS
        render(film,start,end,f'sample-{start:.2f}-{end:.2f}.mp4')
    else:
        result=render(film,0,SECONDS,name);previews(result)


def sprite_cells(path: Path, height: int) -> list[Image.Image]:
    """Separate the two generated transparent cells, preserving a constant sprite canvas."""
    sheet = Image.open(path).convert('RGBA')
    if np.asarray(sheet.getchannel('A')).min() >= 128:
        raise ValueError(f'Transparent sprite sheet has no transparent background: {path}')
    cells = []
    for index in range(2):
        cell = sheet.crop((sheet.width*index//2,0,sheet.width*(index+1)//2,sheet.height))
        occupied = np.asarray(cell.getchannel('A').resize((max(1,cell.width//4),max(1,cell.height//4)),NEAREST)) >= 200
        seen = np.zeros(occupied.shape,dtype=bool)
        largest = []
        for sy, sx in np.argwhere(occupied):
            if seen[sy,sx]:
                continue
            queue = deque([(int(sy),int(sx))]); seen[sy,sx] = True
            component = []
            while queue:
                y,x = queue.popleft(); component.append((y,x))
                for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                    if 0 <= yy < occupied.shape[0] and 0 <= xx < occupied.shape[1] and occupied[yy,xx] and not seen[yy,xx]:
                        seen[yy,xx] = True; queue.append((yy,xx))
            if len(component)>len(largest): largest = component
        if not largest: raise ValueError(f'Missing sprite cell {index}: {path}')
        yy,xx = zip(*largest)
        sx,sy = cell.width/occupied.shape[1],cell.height/occupied.shape[0]
        bounds = (max(0,math.floor((min(xx)-1)*sx)),max(0,math.floor((min(yy)-1)*sy)),
                  min(cell.width,math.ceil((max(xx)+2)*sx)),min(cell.height,math.ceil((max(yy)+2)*sy)))
        cell = cell.crop(bounds)
        cell = cell.resize((round(cell.width*height/cell.height),height),NEAREST)
        cell.putalpha(cell.getchannel('A').point(lambda value:255 if value>=200 else 0))
        cells.append(cell)
    return cells


# Source-image coordinates. Masks keep weather outside, with students occluding it.
GLASS = {
    1:[[(1248,0),(1672,0),(1672,585),(1412,367),(1302,252),(1248,198)]],
    2:[[(0,0),(708,0),(655,235),(352,323),(0,301)]],
    3:[[(0,0),(373,0),(50,620),(0,650)]],
    5:[[(1378,0),(1672,0),(1672,437),(1486,297),(1390,222)]],
    6:[[(1127,0),(1672,0),(1672,567),(1265,430),(1110,319)]],
    7:[[(0,0),(105,0),(105,608),(0,608)],[(337,0),(1390,0),(1390,628),(337,628)],[(1585,0),(1672,0),(1672,608),(1585,608)]],
    8:[[(1125,0),(1672,0),(1672,505),(1220,390),(1125,309)]],
    9:[[(0,0),(760,0),(714,340),(319,450),(0,444)]],
    11:[[(0,0),(760,0),(714,340),(319,450),(0,444)]],
    15:[[(942,0),(1672,0),(1672,521),(1150,356),(1056,243),(954,172)]],
    16:[[(1130,0),(1672,0),(1672,485),(1300,432),(1130,402)]]
}
OCCLUDERS = {1:[(1170,110,1310,273)],2:[(279,70,747,370)],
             5:[(1250,120,1398,283)],6:[(803,130,1141,477)],
             8:[(747,81,1118,609)],9:[(177,181,751,493)],
             11:[(395,176,779,495)],15:[(745,113,1125,505)]}
EYES = {5:(849,290,938,329),6:(953,231,1070,288),
        8:(862,300,1055,369),16:(872,242,986,316)}
MOUTHS = [(336,328,373,352),(453,322,497,352),
          (881,329,916,352),(1024,328,1061,354)]
PAGE_ANCHORS = {1:[(155,548),(786,552)],3:[(1390,601)],
                5:[(387,448)],6:[(1003,476)],8:[(955,634)],
                11:[(788,460),(968,470)],16:[(1030,646)]}


class Film:
    def __init__(self):
        self.plates = {s['number']:Plate(P/s['asset'],s['art_bottom']) for s in SHOTS}
        self.poses = {}
        for name,n in [('05-talk-pose',5),('06-hero-blink',6),('08-quiet-blink',8),
                       ('09-empty-aisle-rest',9),('09-mid-reach',9),('10-window-clean',10),
                       ('14-scroll-lowered',14),('15-book-open',15),('16-hero-blink',16)]:
            path = A/'animation'/f'{name}.png'
            if not path.exists(): raise FileNotFoundError(path)
            self.poses[name] = self.plates[n].aligned_pose(path)
        self.hands = sprite_cells(A/'animation/10-hands-sheet.png',135)
        self.walk = sprite_cells(A/'animation/09-mate-walk-sheet.png',140)
        rng = random.Random(20261011)
        self.drops = [(rng.randrange(W),rng.randrange(SCENE_H),rng.uniform(22,43),rng.randrange(2,5)) for _ in range(130)]
        self.trails = [(rng.randrange(W),rng.randrange(SCENE_H),rng.uniform(2,5),rng.random()*8) for _ in range(24)]
        self.waves = [(rng.randrange(W),rng.randrange(SCENE_H),rng.randrange(3,10),rng.random()*8) for _ in range(42)]
        self.glass_masks, self.allowed, self.water_masks = {}, {}, {}
        for n,plate in self.plates.items():
            self.allowed[n] = Image.new('L',(W,SCENE_H))
            mask = Image.new('L',(W,SCENE_H)); d=ImageDraw.Draw(mask)
            for polygon in GLASS.get(n,[]): d.polygon([plate.xy(*p) for p in polygon],fill=255)
            for box in OCCLUDERS.get(n,[]): d.rectangle(plate.box(box),fill=0)
            self.glass_masks[n]=mask
            self.allow_mask(n,mask)
            for x,y in PAGE_ANCHORS.get(n,[]):
                cx,cy=plate.xy(x,y); self.allow_box(n,(cx-5,cy-6,cx+6,cy+3))
        for n,box in EYES.items(): self.allow_box(n,self.plates[n].box(box))
        for box in MOUTHS:self.allow_box(5,self.plates[5].box(box))
        self.arm_mask=Image.new('L',(W,SCENE_H)); d=ImageDraw.Draw(self.arm_mask)
        d.polygon([self.plates[9].xy(x,y) for x,y in [(175,220),(330,220),(444,330),(539,355),(570,491),(380,495),(277,455),(175,447)]],fill=255)
        d.rectangle(self.plates[9].box((427,174,683,355)),fill=0)
        self.allow_mask(9,self.arm_mask)
        self.allow_box(9,(315,14,399,188))
        self.allow_box(10,(47,3,434,208))
        self.scroll_box=self.plates[14].box((642,320,914,489));self.allow_box(14,self.scroll_box)
        self.book_box=self.plates[15].box((751,423,1138,562));self.allow_box(15,self.book_box)
        for n in (4,12):
            plate=self.plates[n]
            arr=np.asarray(plate.image).astype(np.int16)
            region=Image.new('L',(W,SCENE_H));d=ImageDraw.Draw(region)
            if n==4:
                polygon=[(445,340),(1050,299),(1350,355),(1150,503),(1460,740),(230,740),(425,550),(390,443)]
            else:
                polygon=[(748,395),(1240,405),(1672,475),(1672,750),(174,750),(279,630),(786,490)]
            d.polygon([plate.xy(*p) for p in polygon],fill=255)
            d.rectangle(plate.box((665,111,876,611) if n==4 else (334,90,518,582)),fill=0)
            color=(arr[:,:,2]>arr[:,:,0]*1.10)&(arr[:,:,2]>arr[:,:,1]*.89)
            mask=Image.fromarray((np.asarray(region)*color.astype(np.uint8)).astype(np.uint8))
            self.water_masks[n]=mask;self.allow_mask(n,mask)
        self.wind_masks={}
        for n,rows in {11:(136,166,187),12:(95,139,175),13:(88,151,194)}.items():
            mask=Image.new('L',(W,SCENE_H));d=ImageDraw.Draw(mask)
            for row in rows:d.rectangle((150 if n==12 else 0,row-4,W-1,row+4),fill=255)
            self.wind_masks[n]=mask;self.allow_mask(n,mask)

    def allow_mask(self,n:int,mask:Image.Image):
        self.allowed[n]=Image.fromarray(np.maximum(np.asarray(self.allowed[n]),np.asarray(mask)))

    def allow_box(self,n:int,box):
        ImageDraw.Draw(self.allowed[n]).rectangle(box,fill=255)

    def masked_layer(self,im:Image.Image,layer:Image.Image,mask:Image.Image):
        alpha=np.asarray(layer.getchannel('A')).astype(np.uint16)
        layer.putalpha(Image.fromarray((alpha*np.asarray(mask)//255).astype(np.uint8)))
        im.paste(layer,(0,0),layer)

    def rain(self,im:Image.Image,t:float,mask:Image.Image,strength:int=85):
        layer=Image.new('RGBA',(W,SCENE_H));d=ImageDraw.Draw(layer)
        for x,start,speed,length in self.drops:
            y=round((start+t*speed)%SCENE_H)
            d.line((x,y,x-1,y+length),fill=(203,226,243,strength))
        for x,start,speed,phase in self.trails:
            y=round((start+t*speed+phase)%SCENE_H)
            d.line((x,y,x,y+2),fill=(208,229,247,strength//2))
            d.point((x,y+3),fill=(208,229,247,strength))
        self.masked_layer(im,layer,mask)

    def patch(self,im:Image.Image,n:int,name:str,box):
        target=self.plates[n].box(box)
        im.paste(self.poses[name].crop(target),target[:2])

    def page_motion(self,im:Image.Image,n:int,t:float):
        d=ImageDraw.Draw(im)
        for index,(sx,sy) in enumerate(PAGE_ANCHORS.get(n,[])):
            phase=(t+index*2.6)%6.8
            if phase>1.15:continue
            x,y=self.plates[n].xy(sx,sy)
            lift=round(3*math.sin(phase/1.15*math.pi))
            if lift:
                d.polygon([(x-3,y),(x+4,y),(x+3,y-lift),(x-2,y-lift)],fill='#d8e2f1')
                d.line((x-2,y-lift,x+3,y-lift),fill='#acbed9')

    def water(self,im:Image.Image,n:int,t:float):
        layer=Image.new('RGBA',(W,SCENE_H));d=ImageDraw.Draw(layer)
        for x,y,width,phase in self.waves:
            pulse=math.sin(t*.8+phase)
            if pulse<0:continue
            xx=x+round(4*math.sin(t*.35+phase))
            d.line((xx,y,xx+width,y),fill=(183,216,240,round(24+40*pulse)))
        self.masked_layer(im,layer,self.water_masks[n])

    def breeze(self,im:Image.Image,n:int,t:float):
        layer=Image.new('RGBA',(W,SCENE_H));d=ImageDraw.Draw(layer)
        rows={11:(136,166,187),12:(95,139,175),13:(88,151,194)}[n]
        minimum=150 if n==12 else 0
        for index,row in enumerate(rows):
            x=round(minimum+(t*12+index*137)%(W-minimum))
            y=row+round(2*math.sin(t*.55+index*2))
            d.polygon([(x,y),(x+3,y-1),(x+2,y+1),(x-1,y+2)],fill=(116,157,79,120))
            d.line((x,y+1,x+2,y),fill=(171,189,122,100))
        self.masked_layer(im,layer,self.wind_masks[n])

    @staticmethod
    def window_state(t:float)->dict:
        left=ease((t-78.8)/4.5)
        right=ease((t-79.7)/4.6)
        reach=ease((t-75.35)/1.85)
        lower=ease((t-84.7)/1.30)
        return {'left':left,'right':right,'left_x':134-round(83*left),
                'right_x':239+round(83*right),'pane_width':105,
                'top':5,'bottom':166,'reach':reach,'lower':lower}

    def window(self,t:float)->Image.Image:
        im=self.poses['10-window-clean'].copy()
        mask=Image.new('L',(W,SCENE_H));d=ImageDraw.Draw(mask)
        for box in [(53,5,143,153),(161,5,321,161),(337,5,428,153)]:d.rectangle(box,fill=255)
        self.rain(im,t,mask,67)
        state=self.window_state(t)
        pw,top,bottom=state['pane_width'],state['top'],state['bottom']
        glass=Image.new('RGBA',(W,SCENE_H));gd=ImageDraw.Draw(glass)
        for index,x in enumerate((state['left_x'],state['right_x'])):
            gd.rectangle((x+4,top+4,x+pw-4,bottom-4),fill=(108,137,173,35))
            gd.rectangle((x,top,x+pw,bottom),outline=(34,51,74,255),width=4)
            gd.line((x+1,top+3,x+1,bottom-3),fill=(112,145,179,255))
            gd.line((x+pw-1,top+3,x+pw-1,bottom-3),fill=(142,173,202,255))
            gd.line((x+3,top+2,x+pw-3,top+2),fill=(139,166,193,255))
            gd.line((x+3,bottom-2,x+pw-3,bottom-2),fill=(101,130,164,255))
            handle=x+pw-4 if index==0 else x+5
            gd.rectangle((handle-2,77,handle+2,108),fill=(26,42,60,255))
            gd.line((handle-1,79,handle-1,106),fill=(169,189,206,255))
            for drop in range(14):
                dx=x+9+(drop*17+index*7)%(pw-18)
                dy=top+9+round((drop*21+t*(2+drop%3))%(bottom-top-20))
                gd.line((dx,dy,dx,dy+2),fill=(194,222,243,118))
        im.paste(glass,(0,0),glass)
        # Generated forearms continue off-screen; palms track their own sash handle.
        for index,sprite in enumerate(self.hands):
            arr=np.asarray(sprite)
            skin=(arr[:,:,0]>arr[:,:,1]*1.1)&(arr[:,:,0]>arr[:,:,2]*1.2)&(arr[:,:,3]>200)
            yy,xx=np.where(skin)
            if not len(xx):raise ValueError('Hand sprite skin/grip anchor not found')
            grip_x=int(xx.max()-4 if index==0 else xx.min()+4)
            grip_y=int(yy.min()+9)
            handle=state['left_x']+pw-4 if index==0 else state['right_x']+5
            y=round(91+(1-state['reach'])*160+state['lower']*170)-grip_y
            x=handle-grip_x
            im.paste(sprite,(x,y),sprite)
        return im

    def departure(self,t:float)->Image.Image:
        im=self.poses['09-empty-aisle-rest'].copy()
        local=t-66.94
        if local>=2.35:
            pose=self.plates[9].image if local>=2.62 else self.poses['09-mid-reach']
            im.paste(pose,(0,0),self.arm_mask)
        progress=ease(max(0,local)/7.5)
        sprite=self.walk[int(max(0,local)*3.0)%2]
        height=round(140-15*progress)
        sprite=sprite.resize((round(sprite.width*height/sprite.height),height),NEAREST)
        center=round(363-9*progress);foot=round(184-25*progress)
        ImageDraw.Draw(im).ellipse((center-9,foot-2,center+8,foot+1),fill='#465671')
        im.paste(sprite,(center-sprite.width//2,foot-sprite.height),sprite)
        return im

    def raw(self,shot:dict,t:float)->Image.Image:
        n=shot['number'];local=t-shot['start']
        if n==10:return self.window(t)
        im=self.departure(t) if n==9 else self.plates[n].image.copy()
        if n in self.glass_masks:self.rain(im,t,self.glass_masks[n],58 if n in (15,16) else 82)
        if n==5:
            for index,box in enumerate(MOUTHS):
                if (local+index*.22)%.95<.42:self.patch(im,5,'05-talk-pose',box)
            if (local+1.1)%4.8<.125:self.patch(im,5,'05-talk-pose',EYES[5])
        if n in (6,8,16):
            name={6:'06-hero-blink',8:'08-quiet-blink',16:'16-hero-blink'}[n]
            if (local+1.7)%4.9<(.23 if n==8 else .125):self.patch(im,n,name,EYES[n])
        if n==14 and local<1.2:
            im.paste(self.poses['14-scroll-lowered'].crop(self.scroll_box),self.scroll_box[:2])
        if n==15 and local<3.0:
            im.paste(self.poses['15-book-open'].crop(self.book_box),self.book_box[:2])
        self.page_motion(im,n,t)
        if n in self.water_masks:self.water(im,n,t)
        if n in self.wind_masks:self.breeze(im,n,t)
        return im

    def frame(self,t:float,fade:bool=True)->Image.Image:
        t=min(max(t,0),SECONDS-1/FPS)
        shot=next(s for s in SHOTS if s['start']<=t<s['end'])
        scene=self.raw(shot,t)
        if fade and t<.28:scene=Image.blend(Image.new('RGB',scene.size,'#14233a'),scene,ease(t/.28))
        if fade and t>SECONDS-1.1:scene=Image.blend(scene,Image.new('RGB',scene.size,'#14233a'),ease((t-(SECONDS-1.1))/1.1))
        canvas=Image.new('RGB',(W,H),'#09203f');canvas.paste(scene,(0,0))
        d=ImageDraw.Draw(canvas)
        d.line((0,SCENE_H,W-1,SCENE_H),fill='#6580ab',width=1)
        d.rectangle((3,SCENE_H+3,W-4,H-4),outline='#4d6b97',width=1)
        for x,sign in ((3,1),(W-4,-1)):
            for y,sy in ((SCENE_H+3,1),(H-4,-1)):
                d.line((x,y,x+sign*4,y),fill='#8aa6cb')
                d.line((x,y,x,y+sy*3),fill='#8aa6cb')
        return canvas


if __name__=='__main__':main()
