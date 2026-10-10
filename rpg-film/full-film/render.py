"""Render the full article as a fixed-camera pixel film with the original Mambo audio.

Generated artwork is kept in assets/. This program animates the video layers;
it does not regenerate or overwrite any of the user's retained review images.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
from pathlib import Path
import random
import subprocess
import time
import wave
import zipfile

import numpy as np
from PIL import Image, ImageDraw

P = Path(__file__).resolve().parent
A = P / "assets"
NARRATION = P.parent / "narration"
W, H, FPS, SECONDS = 480, 270, 24, 141
NEAREST = Image.Resampling.NEAREST
SHOTS = json.loads((P / "shots.json").read_text())["shots"]
CUES = json.loads((NARRATION / "mambo/timings.json").read_text())["sentences"]


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def timecode(t: float, ass: bool = False) -> str:
    if ass:
        cs = round(t * 100)
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def wrap_sentence(text: str, limit: float = 38) -> list[str]:
    """Wrap without changing or dropping any character in the original sentence."""
    out = []
    while text:
        width, end = 0.0, 0
        for ch in text:
            step = 0.46 if ord(ch) < 128 else 1.0
            if width + step > limit:
                break
            end += 1
            width += step
        end = max(end, 1)
        if end < len(text):
            candidates = [i + 1 for i, ch in enumerate(text[:end]) if ch in "，；、！？。"]
            if candidates and candidates[-1] >= end - 9:
                end = candidates[-1]
            while end < len(text) and text[end] in "，；、！？。.":
                end += 1
        out.append(text[:end])
        text = text[end:]
    return out


def subtitles() -> None:
    original = "".join((NARRATION / "original.txt").read_text().splitlines())
    if "".join(c["text"] for c in CUES) != original:
        raise ValueError("Narration/subtitles must match the original article verbatim")
    (P / "subtitles.srt").write_text(
        "\n\n".join(
            f'{c["id"]}\n{timecode(c["start_seconds"])} --> {timecode(c["end_seconds"])}\n{c["text"]}'
            for c in CUES
        ) + "\n"
    )
    header = """[Script Info]
Title: 窗 · 完整曼波朗读
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Chinese,Noto Sans CJK SC,42,&H00EDF6FC,&H00EDF6FC,&H00322422,&H00322422,0,0,0,0,100,100,0,0,1,2,0,2,120,120,35,1
Style: Panel,Noto Sans CJK SC,42,&H00372920,&H00372920,&H0092856B,&H00372920,0,0,0,0,100,100,0,0,1,1,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in CUES:
        lines = wrap_sentence(c["text"])
        assert "".join(lines) == c["text"]
        panel_h = 44 + len(lines) * 59
        y = 1060 - panel_h
        start, end = timecode(c["start_seconds"], True), timecode(c["end_seconds"], True)
        panel = f"{{\\an7\\pos(80,{y})\\p1\\1a&H25&\\3a&H45&}}m 0 0 l 1760 0 1760 {panel_h} 0 {panel_h}{{\\p0}}"
        caption = "{\\an2\\pos(960,1038)\\fad(50,50)}" + "\\N".join(lines)
        events.append(f"Dialogue: 0,{start},{end},Panel,,0,0,0,,{panel}")
        events.append(f"Dialogue: 1,{start},{end},Chinese,,0,0,0,,{caption}")
    (P / "subtitles.ass").write_text(header + "\n".join(events) + "\n")
    chapters = [(0, 26.5, "教室"), (26.5, 44.71, "小小世界"), (44.71, 66.94, "窗边"),
                (66.94, 95.35, "开窗"), (95.35, 122.2, "风与想象"), (122.2, 141, "夜色")]
    metadata = ";FFMETADATA1\ntitle=窗 · 强化像素完整动画\ncomment=用户原文逐句字幕 · 曼波朗读\n"
    for start, end, title in chapters:
        metadata += f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start * 1000)}\nEND={round(end * 1000)}\ntitle={title}\n"
    (P / "chapters.ffmeta").write_text(metadata)


def narration_wave() -> Path:
    work = P / "_work"
    work.mkdir(exist_ok=True)
    target = work / "narration.wav"
    if not target.exists():
        with zipfile.ZipFile(NARRATION / "mambo/mambo-narration.zip") as z:
            target.write_bytes(z.read("narration.wav"))
    with wave.open(str(target)) as audio:
        duration = audio.getnframes() / audio.getframerate()
    if abs(duration - 139.0) > 0.01:
        raise ValueError(f"Unexpected full narration length: {duration}")
    return target


def sprite_cells(name: str, height: int) -> list[Image.Image]:
    """Extract the two transparent sprites using their main connected silhouettes."""
    sheet = Image.open(A / name).convert("RGBA")
    sprites = []
    for i in range(2):
        cell = sheet.crop((round(sheet.width * i / 2), 0, round(sheet.width * (i + 1) / 2), sheet.height))
        alpha = cell.getchannel("A")
        size = (max(1, cell.width // 6), max(1, cell.height // 6))
        occupied = np.asarray(alpha.resize(size, NEAREST)) > 150
        seen = np.zeros(occupied.shape, dtype=bool)
        largest: list[tuple[int, int]] = []
        for sy, sx in np.argwhere(occupied):
            if seen[sy, sx]:
                continue
            queue = deque([(int(sy), int(sx))])
            seen[sy, sx] = True
            component = []
            while queue:
                y, x = queue.popleft()
                component.append((y, x))
                for yy, xx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= yy < size[1] and 0 <= xx < size[0] and occupied[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        queue.append((yy, xx))
            if len(component) > len(largest):
                largest = component
        if not largest:
            raise ValueError(f"No transparent sprite in {name}, cell {i}")
        yy, xx = zip(*largest)
        xscale, yscale = cell.width / size[0], cell.height / size[1]
        box = (max(0, math.floor((min(xx)-1) * xscale)), max(0, math.floor((min(yy)-1) * yscale)),
               min(cell.width, math.ceil((max(xx)+2) * xscale)), min(cell.height, math.ceil((max(yy)+2) * yscale)))
        cell = cell.crop(box)
        cell = cell.resize((round(cell.width * height / cell.height), height), NEAREST)
        cell.putalpha(cell.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        sprites.append(cell)
    return sprites


class Film:
    def __init__(self):
        self.plates = {p.stem: Image.open(p).convert("RGB").resize((W, H), NEAREST)
                       for p in A.glob("*.png") if p.stem not in {"hands", "knight-poses"}}
        for shot in SHOTS:
            if Path(shot["asset"]).stem not in self.plates:
                raise ValueError(f"Missing plate: {shot['asset']}")
        if "hero-blink" not in self.plates:
            raise ValueError("The hero eyelid animation asset is required")
        self.hands = sprite_cells("hands.png", 99)
        self.knight = sprite_cells("knight-poses.png", 88)
        rng = random.Random(20261010)
        self.rain = [(rng.randrange(W), rng.randrange(H), rng.uniform(13, 28), rng.randrange(2, 5)) for _ in range(105)]
        self.ripples = [(rng.randrange(140, 465), rng.randrange(135, 265), rng.randrange(3, 12), rng.random()*6) for _ in range(75)]
        self.leaves = [(rng.randrange(W), rng.randrange(60, 208), rng.uniform(6, 12), rng.random()*6) for _ in range(9)]
        self.window_masks = {}
        for name in ("classroom-wide", "classroom-night", "classmates", "hero-close"):
            mask = Image.new("L", (W, H))
            d = ImageDraw.Draw(mask)
            if name in {"classroom-wide", "classroom-night"}:
                d.polygon([(0, 90), (81, 11), (81, 71), (0, 188)], fill=255)
            elif name == "classmates":
                d.polygon([(0, 35), (77, 0), (77, 62), (0, 133)], fill=255)
            else:
                d.polygon([(0, 0), (159, 0), (159, 88), (0, 181)], fill=255)
            # Keep added drops off warm opaque walls/sills and the black frame.
            rgb = np.asarray(self.plates[name]).astype(np.int16)
            valid = (rgb[..., 2] > rgb[..., 0] * .90) & (rgb.max(axis=2) > 80)
            self.window_masks[name] = np.asarray(mask) * valid.astype(np.uint8)
        river = np.asarray(self.plates["river"]).astype(np.int16)
        region = Image.new("L", (W, H))
        ImageDraw.Draw(region).polygon([(207, 128), (260, 127), (350, 153), (296, 172),
                                       (386, 207), (480, 230), (480, 270), (239, 270),
                                       (218, 233), (159, 219), (142, 178), (270, 159)], fill=255)
        self.water_mask = np.asarray(region) * ((river[..., 2] > river[..., 0]*1.05) &
                                              (river[..., 2] > river[..., 1]*.80)).astype(np.uint8)

    def rain_layer(self, im: Image.Image, t: float, mask: np.ndarray | None = None, strength: int = 95):
        layer = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(layer)
        for x, start, speed, length in self.rain:
            y = round((start + t * speed) % H)
            d.line((x, y, x-1, y+length), fill=(204, 226, 240, strength), width=1)
        if mask is not None:
            alpha = np.asarray(layer.getchannel("A")).astype(np.uint16)
            layer.putalpha(Image.fromarray((alpha * mask // 255).astype(np.uint8)))
        im.paste(layer, (0, 0), layer)

    def breeze(self, im: Image.Image, t: float, intensity: float = 1):
        layer = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(layer)
        for k, (start, y, speed, phase) in enumerate(self.leaves):
            x = round((start + (t-80)*speed) % (W+24)) - 12
            yy = round(y + math.sin(t*.5+phase)*4)
            color = (211, 235, 216, round(90*intensity))
            if k % 3 == 0:
                d.line((x, yy, x+4, yy-1), fill=color)
                d.point((x+2, yy-2), fill=color)
            else:
                d.point((x, yy), fill=color)
        im.paste(layer, (0, 0), layer)

    @staticmethod
    def bubble(im: Image.Image, x: int, y: int, t: float, phase: float = 0):
        local = (t + phase) % 6.8
        if local > 3.2:
            return
        d = ImageDraw.Draw(im)
        d.rectangle((x, y, x+15, y+7), fill="#f4ecd4", outline="#666678")
        d.polygon([(x+4, y+7), (x+5, y+10), (x+8, y+7)], fill="#f4ecd4")
        for j in range(1 + int(local * 2) % 3):
            d.point((x+4+j*3, y+4), fill="#63607a")

    def classroom(self, name: str, t: float) -> Image.Image:
        im = self.plates[name].copy()
        self.rain_layer(im, t, self.window_masks[name], 70 if "night" in name else 105)
        d = ImageDraw.Draw(im)
        # Small alternating page highlights; bodies, chairs and contact shadows stay anchored.
        if name == "classroom-wide":
            books = [(341, 194), (397, 153)]
        elif name == "classmates":
            books = [(390, 257), (447, 194)]
        else:
            books = []
        for k, (x, y) in enumerate(books):
            if (t+k*1.8) % 7.2 < .32:
                d.line((x-2, y, x+2, y-2), fill="#f0e7c5")
                d.line((x+2, y-2, x+3, y), fill="#bcb49c")
        if name == "classmates":
            self.bubble(im, 372, 41, t, .5)
            self.bubble(im, 235, 147, t, 3.5)
        if name == "classroom-wide" and 3 < t < 27:
            self.bubble(im, 331, 47, t, 1.1)
        if "night" in name:
            self.breeze(im, t, .30)
            # A few drifting reflections in the window's light, not a moving light beam.
            if int(t*2) % 4 == 0:
                d.point((94, 109), fill="#b8c7de")
        return im

    def hero(self, t: float) -> Image.Image:
        im = self.plates["hero-close"].copy()
        self.rain_layer(im, t, self.window_masks["hero-close"], 70)
        if (t+1.05) % 4.9 < .14:
            box = (176, 82, 190, 99)
            im.paste(self.plates["hero-blink"].crop(box), box[:2])
        return im

    @staticmethod
    def opening_progress(t: float) -> float:
        first = .22 * ease((t-73.0)/1.7)
        return max(first, .22 + .78*ease((t-79.0)/5.4)) if t >= 79 else first

    def window(self, t: float, open_shot: bool = False, dream: bool = False) -> Image.Image:
        im = self.plates["courtyard"].copy()
        self.rain_layer(im, t, None, 65)
        p = 0.0 if dream else (1.0 if open_shot else self.opening_progress(t))
        # Four panes on two tracks: outer panes fixed, the two inner panes overlap them.
        # All pane sizes are constant. Opening creates a real central aperture.
        pane_w, x0, top, bottom = 105, 30, 23, 217
        left_x, right_x = x0 + pane_w - round(p*pane_w), x0 + 2*pane_w + round(p*pane_w)
        assert x0 <= left_x <= x0+pane_w and x0+2*pane_w <= right_x <= x0+3*pane_w
        glass = Image.new("RGBA", (W, H))
        gd = ImageDraw.Draw(glass)
        for k, x in enumerate((x0, x0+3*pane_w, left_x, right_x)):
            gd.rectangle((x+3, top+2, x+pane_w-3, bottom-2), fill=(171, 200, 220, 27))
            # Straight, equal metal rails and stiles with two-tone pixel highlights.
            gd.rectangle((x, top, x+pane_w, bottom), outline=(42, 58, 75, 255), width=3)
            gd.line((x+1, top+2, x+1, bottom-2), fill=(184, 205, 214, 255), width=1)
            gd.line((x+pane_w-1, top+2, x+pane_w-1, bottom-2), fill=(207, 218, 219, 255), width=1)
            gd.line((x+2, top+2, x+pane_w-2, top+2), fill=(219, 229, 219, 255))
            for dot in range(9):
                dx = x+8+((dot*37+k*13) % 85)
                dy = top+14+((dot*29+k*17) % 168)
                gd.point((dx, dy), fill=(222, 232, 235, 115))
        for x in (left_x+pane_w-7, right_x+4):
            gd.rectangle((x, 113, x+3, 133), fill=(44, 59, 70, 255))
            gd.line((x+1, 115, x+1, 130), fill=(190, 203, 209, 255))
        im.paste(glass, (0, 0), glass)
        d = ImageDraw.Draw(im)
        # Opaque lower wall and rigid outer frame keep the viewer inside the classroom.
        d.rectangle((0, 0, W, 16), fill="#d9c6aa")
        d.rectangle((0, 0, 24, H), fill="#cbbbab")
        d.rectangle((456, 0, W, H), fill="#bbaea2")
        d.rectangle((0, 229, W, H), fill="#bdb39f")
        d.rectangle((22, 16, 457, 224), outline="#27394c", width=4)
        d.line((28, 20, 451, 20), fill="#e4e4cf", width=2)
        d.line((27, 222, 452, 222), fill="#728d9c", width=2)
        d.line((27, 225, 452, 225), fill="#e6d1ac", width=2)
        d.polygon([(18, 228), (459, 228), (476, 244), (3, 244)], fill="#c69b65")
        d.line((18, 229, 459, 229), fill="#f0d29b", width=2)
        d.line((3, 244, 476, 244), fill="#826950", width=2)
        for y in (234, 239):
            d.line((30, y, 449, y), fill="#b08457")
        if p > .55:
            self.breeze(im, t, .75*p)
            d = ImageDraw.Draw(im)
            for i in range(5):
                if math.sin(t*1.5+i*2) > .25:
                    x = 144+i*37
                    d.line((x, 233+i%2, x+7, 233+i%2), fill="#cde0de")
        if not open_shot and not dream and 69.5 < t < 88.8:
            reach = ease((t-69.5)/3.0)
            lower = ease((t-85.8)/3.0)
            grip_y = round(115 + (1-reach)*145 + lower*155)
            left, right = self.hands
            lx = left_x+pane_w-5-round(left.width*.80)
            rx = right_x+5-round(right.width*.20)
            # Continue the sleeves below the sprite sheet's crop, off-screen toward
            # the viewer's shoulders. A lifted hand must not end in a floating cuff.
            base_y = grip_y-11+round(left.height*.90)
            if base_y < H:
                d = ImageDraw.Draw(im)
                lpoly = [(lx+2, base_y-5), (lx+round(left.width*.59), base_y-5),
                         (lx+round(left.width*.36), H+6), (lx-43, H+6)]
                rpoly = [(rx+round(right.width*.41), base_y-5), (rx+right.width-2, base_y-5),
                         (rx+right.width+43, H+6), (rx+round(right.width*.64), H+6)]
                d.polygon(lpoly, fill="#f4e7bf", outline="#29354e", width=2)
                d.polygon(rpoly, fill="#f4e7bf", outline="#29354e", width=2)
                d.polygon([(lx+round(left.width*.47), base_y), (lx+round(left.width*.58), base_y),
                           (lx+round(left.width*.36), H+6), (lx+round(left.width*.19), H+6)], fill="#b7adc0")
                d.polygon([(rx+round(right.width*.42), base_y), (rx+round(right.width*.54), base_y),
                           (rx+round(right.width*.81), H+6), (rx+round(right.width*.64), H+6)], fill="#b7adc0")
            # The two hands are independent rigid sprites following the sliding stiles.
            im.paste(left, (lx, grip_y-11), left)
            im.paste(right, (rx, grip_y-11), right)
        if open_shot:
            # A fixed cut to a wider view, never a continuous zoom or handheld shake.
            im = im.crop((24, 16, 457, 260)).resize((W, H), NEAREST)
        return im

    def river(self, t: float) -> Image.Image:
        im = self.plates["river"].copy()
        layer = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(layer)
        for x, y, width, phase in self.ripples:
            strength = round(60+50*math.sin(t*.9+phase))
            if strength < 45:
                continue
            xx = x+round(math.sin(t*.6+phase)*3)
            d.line((xx, y, xx+width, y), fill=(189, 219, 235, strength))
        alpha = np.asarray(layer.getchannel("A")).astype(np.uint16)
        layer.putalpha(Image.fromarray((alpha*self.water_mask//255).astype(np.uint8)))
        im.paste(layer, (0, 0), layer)
        self.breeze(im, t, .60)
        return im

    def social(self, t: float) -> Image.Image:
        im = self.plates["social-dream"].copy()
        self.bubble(im, 212, 81, t, 2.3)
        self.bubble(im, 302, 88, t, 5.4)
        self.breeze(im, t, .24)
        return im

    def knight_scene(self, t: float) -> Image.Image:
        im = self.plates["knight-courtyard"].copy()
        local = max(0, t-115.37)
        progress = ease(local/5.2)
        x, foot = round(131+82*progress), round(227-26*progress)
        moving = local < 5.2
        sprite = self.knight[int(local*4) % 2 if moving else 0]
        d = ImageDraw.Draw(im)
        d.ellipse((x-12, foot-4, x+12, foot+2), fill="#77778a")
        im.paste(sprite, (x-sprite.width//2, foot-sprite.height), sprite)
        # Small fountain droplets are confined to the fountain, with the scenery fixed.
        for i in range(5):
            yy = 143+round((t*14+i*7) % 41)
            d = ImageDraw.Draw(im)
            d.point((347+i%3, yy), fill="#c3edf0")
        return im

    def raw_shot(self, shot: dict, t: float) -> Image.Image:
        sid = shot["id"]
        if sid in {"classroom", "platform", "rear"}:
            im = self.classroom("classroom-wide", t)
            if sid == "platform":
                return im.crop((67, 7, 427, 210)).resize((W, H), NEAREST)
            if sid == "rear":
                return im.crop((60, 93, 375, 270)).resize((W, H), NEAREST)
            return im
        if sid in {"classmates", "glances"}:
            return self.classroom("classmates", t)
        if sid in {"hero", "hesitation"}:
            return self.hero(t)
        if sid == "window-dream":
            return self.window(t, dream=True)
        if sid == "opening":
            return self.window(t)
        if sid == "after-opening":
            return self.window(t, open_shot=True)
        if sid == "river":
            return self.river(t)
        if sid == "social-dream":
            return self.social(t)
        if sid == "knight-dream":
            return self.knight_scene(t)
        im = self.classroom("classroom-night", t)
        if sid == "return":
            return im.crop((40, 52, 308, 203)).resize((W, H), NEAREST)
        return im

    def frame(self, t: float) -> Image.Image:
        index = next(i for i, s in enumerate(SHOTS) if s["start"] <= t < s["end"])
        shot = SHOTS[index]
        im = self.raw_shot(shot, t)
        if index and shot["id"] in {"river", "social-dream", "knight-dream", "return"} and t < shot["start"]+.28:
            old = self.raw_shot(SHOTS[index-1], shot["start"]-.02)
            im = Image.blend(old, im, ease((t-shot["start"])/.28))
        if t < .4:
            im = Image.blend(Image.new("RGB", (W, H), "#141a2c"), im, ease(t/.4))
        if t > 139.3:
            im = Image.blend(im, Image.new("RGB", (W, H), "#101424"), ease((t-139.3)/1.7))
        return im


def ambience() -> None:
    rate, n = 48000, 48000*SECONDS
    rng = np.random.default_rng(1842)
    noise = rng.normal(0, 1, n).astype(np.float32)
    c = np.concatenate(([0.0], np.cumsum(noise, dtype=np.float64)))
    rain = ((c[5:]-c[:-5])/5).astype(np.float32)
    rain = np.pad(rain, (0, n-len(rain))) * .0034
    c = np.concatenate(([0.0], np.cumsum(rng.normal(0, 1, n), dtype=np.float64)))
    wind = ((c[161:]-c[:-161])/161).astype(np.float32)
    wind = np.pad(wind, (0, n-len(wind)))
    tt = np.arange(n, dtype=np.float32)/rate
    wind *= (.018 + .047*np.clip((tt-79)/6, 0, 1))
    music = np.zeros(n, dtype=np.float32)
    frequencies = [220.0, 261.626, 329.628, 293.665, 196.0, 246.942, 293.665, 220.0]
    for k, start in enumerate(np.arange(0, SECONDS, 3.4)):
        a, b = round(start*rate), min(n, round((start+5)*rate))
        dt = np.arange(b-a, dtype=np.float32)/rate
        f = frequencies[k % len(frequencies)]
        envelope = np.exp(-dt/1.8)*(1-np.exp(-dt*18))
        tone = np.sin(2*np.pi*f*dt)+.13*np.sin(2*np.pi*f*2*dt)
        volume = .009 if start < 66.94 else (.0055 if start < 122.2 else .0045)
        music[a:b] += tone*envelope*volume
    sound = rain+wind+music
    # Quiet latch/track foley follows the first-person action instead of invented dialogue.
    for moment, length, gain, freq in [(72.3, .10, .030, 850), (73.3, 1.3, .008, 170),
                                       (79.1, 5.1, .006, 180), (84.4, .08, .018, 540)]:
        a, b = round(moment*rate), round((moment+length)*rate)
        dt = np.arange(b-a)/rate
        envelope = np.minimum(1, dt/.025)*np.minimum(1, (length-dt)/.045)
        sound[a:b] += (np.sin(2*np.pi*freq*dt)*.3+noise[a:b]*.25)*gain*envelope
    fade = np.minimum(1, tt/.8)*np.minimum(1, (SECONDS-tt)/1.5)
    left, right = (sound+rain*.10)*fade, (sound-rain*.08)*fade
    samples = np.stack([left, right], axis=1)
    with wave.open(str(P / "ambience.wav"), "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((np.clip(samples, -.95, .95)*32767).astype("<i2").tobytes())


PREVIEW_TIMES = [5, 11, 22, 40, 49, 64, 71, 77, 82, 88, 93, 101, 110, 119, 126, 137]


def previews(film: Film) -> None:
    folder = P / "previews"
    folder.mkdir(exist_ok=True)
    for t in PREVIEW_TIMES:
        film.frame(t).resize((1920, 1080), NEAREST).save(folder / f"{t:03d}.png")
    film.frame(49).resize((1920, 1080), NEAREST).save(P / "poster.png")
    sheet = Image.new("RGB", (1920, 1080), "#111827")
    for i, t in enumerate([5, 40, 49, 71, 82, 93, 101, 119, 137]):
        sheet.paste(film.frame(t).resize((640, 360), NEAREST), ((i%3)*640, (i//3)*360))
    sheet.save(P / "storyboard.png")


def encoded_previews() -> None:
    """Save representative frames from the actual encoded film, including captions."""
    for t in PREVIEW_TIMES:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t),
                        "-i", str(P / "window-full-mambo.mp4"), "-frames:v", "1",
                        str(P / "previews" / f"{t:03d}.png")], check=True)
    with Image.open(P / "previews/049.png") as poster:
        poster.save(P / "poster.png")
    sheet = Image.new("RGB", (1920, 1080))
    for i, t in enumerate([5, 40, 49, 71, 82, 93, 101, 119, 137]):
        with Image.open(P / "previews" / f"{t:03d}.png") as frame:
            sheet.paste(frame.resize((640, 360), NEAREST), ((i%3)*640, (i//3)*360))
    sheet.save(P / "storyboard.png")


def render(film: Film) -> None:
    voice = narration_wave()
    ambience()
    pwork = P / "_work"
    pwork.mkdir(exist_ok=True)
    mix = pwork / "mixed.wav"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(voice), "-i", str(P/"ambience.wav"),
        "-filter_complex", "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-17:TP=-2:LRA=9,apad=whole_dur=141[v];[v][1:a]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.94:level=0,afade=t=out:st=139.3:d=1.7[m]",
        "-map", "[m]", "-ar", "48000", "-t", "141", str(mix)
    ], check=True)
    target = P / "window-full-mambo.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-y", "-nostats", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", str(mix), "-i", str(P/"chapters.ffmeta"),
        "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "2", "-map_chapters", "2",
        "-vf", f"scale=1920:1080:flags=neighbor,ass={P/'subtitles.ass'}",
        "-c:v", "libx264", "-threads", "4", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-metadata:s:a:0", "title=曼波朗读 · 全文",
        "-t", str(SECONDS), "-movflags", "+faststart", str(target)
    ]
    start = time.monotonic()
    with open(P / "render.log", "w") as log:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for i in range(FPS*SECONDS):
                proc.stdin.write(film.frame(i/FPS).tobytes())
                if i % (FPS*10) == 0:
                    print(f"Rendering {i/FPS:.0f}/{SECONDS}s; elapsed {time.monotonic()-start:.1f}s", flush=True)
            proc.stdin.close()
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        if proc.wait() != 0:
            raise RuntimeError("FFmpeg failed; see render.log")
    print(f"Rendered {target.name}: {SECONDS}s, {FPS*SECONDS} frames, elapsed {time.monotonic()-start:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    subtitles()
    film = Film()
    previews(film)
    if not args.preview_only:
        render(film)
        encoded_previews()


if __name__ == "__main__":
    main()
