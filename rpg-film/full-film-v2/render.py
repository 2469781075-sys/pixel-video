"""Second complete edition of 窗: richer sentence-led cuts and anchored pixel motion.

Original retained art and sprite loaders are reused from full-film/render.py.
All new outputs live here; the first edition is never overwritten.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import time
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).resolve().parent
BASE = P.parent / 'full-film'
spec = importlib.util.spec_from_file_location('window_original_renderer', BASE / 'render.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
old.P = P  # Helpers write to the new version; its source artwork stays in BASE/assets.
W, H, FPS, SECONDS = 480, 270, 24, 141
NEAREST = Image.Resampling.NEAREST
CUES = old.CUES
VIDEO = P / 'window-full-mambo-v2.mp4'
CAPTION_SIZE = 66
CAPTION_WIDTH = 1640


def caption_font() -> ImageFont.FreeTypeFont:
    """Measure the em width at libass's ascender/descender-normalized font size."""
    font_path = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    metrics = ImageFont.truetype(str(font_path), 1000).getmetrics()
    em_size = math.ceil(CAPTION_SIZE * 1000 / sum(metrics))
    return ImageFont.truetype(str(font_path), em_size)


def wrap_caption(text: str) -> list[str]:
    """Balance full-sentence lines at punctuation, with measured width limits."""
    font = caption_font()
    # Clause endings are preferable to splitting a word or leaving a short tail.
    # Fall back to character boundaries only if a single clause is too wide.
    candidates = [0] + [m.end() for m in re.finditer(r'[，；、！？。]+|\.{2,}', text)]
    if candidates[-1] != len(text):
        candidates.append(len(text))
    for start, end in zip(candidates, candidates[1:]):
        if font.getlength(text[start:end]) > CAPTION_WIDTH:
            candidates.extend(range(start + 1, end))
    candidates = sorted(set(candidates))
    for count in range(1, len(text) + 1):
        target = font.getlength(text) / count
        states = {(0, 0): (0., [])}
        for used in range(count):
            for start in candidates:
                if (used, start) not in states:
                    continue
                cost, lines = states[used, start]
                for end in candidates:
                    if end <= start or text[end - 1] in '，；、！？。.' and end < len(text) and text[end] in '，；、！？。.':
                        continue
                    if text[start] in '，；、！？。.':
                        continue
                    width = font.getlength(text[start:end])
                    if width > CAPTION_WIDTH:
                        break
                    penalty = 0 if end == len(text) or text[end - 1] in '，；、！？。.' else CAPTION_WIDTH ** 2
                    score = cost + (width - target) ** 2 + penalty
                    key = (used + 1, end)
                    if key not in states or score < states[key][0]:
                        states[key] = (score, lines + [text[start:end]])
        if (count, len(text)) in states:
            result = states[count, len(text)][1]
            assert ''.join(result) == text
            return result
    raise ValueError('No caption layout fits')


def caption_layout(cue: dict) -> dict:
    lines = wrap_caption(cue['text'])
    height = 44 + len(lines) * CAPTION_SIZE
    return {'sentence': cue['id'], 'font_size': CAPTION_SIZE, 'lines': lines,
            'measured_line_widths': [round(caption_font().getlength(line), 2) for line in lines],
            'panel_box': [80, 1060 - height, 1840, 1060], 'text_anchor': [960, 1038]}


def subtitles() -> None:
    # Preserve the original cue times, SRT and chapters; replace only this edition's
    # display typography. The first edition's renderer and files stay untouched.
    old.subtitles()
    original_ass = (P / 'subtitles.ass').read_text()
    header = original_ass.split('Dialogue:', 1)[0]
    header = header.replace('Chinese,Noto Sans CJK SC,42,', f'Chinese,Noto Sans CJK SC,{CAPTION_SIZE},')
    header = header.replace('&H00322422,&H00322422,0,0,0,0,100,100,0,0,1,2,0,2',
                            '&H00322422,&H00322422,-1,0,0,0,100,100,0,0,1,3,0,2')
    events, layouts = [], []
    for cue in CUES:
        layout = caption_layout(cue)
        layouts.append(layout)
        x, y, _, bottom = layout['panel_box']
        height = bottom - y
        start, end = old.timecode(cue['start_seconds'], True), old.timecode(cue['end_seconds'], True)
        panel = f"{{\\an7\\pos({x},{y})\\p1\\1a&H25&\\3a&H45&}}m 0 0 l 1760 0 1760 {height} 0 {height}{{\\p0}}"
        caption = '{\\an2\\pos(960,1038)\\fad(50,50)}' + '\\N'.join(layout['lines'])
        events.append(f'Dialogue: 0,{start},{end},Panel,,0,0,0,,{panel}')
        events.append(f'Dialogue: 1,{start},{end},Chinese,,0,0,0,,{caption}')
    (P / 'subtitles.ass').write_text(header + '\n'.join(events) + '\n')
    (P / 'subtitle-layout.json').write_text(json.dumps({'previous_font_size': 42, 'font_size': CAPTION_SIZE,
        'font': 'Noto Sans CJK SC Bold', 'outline': 3, 'maximum_text_width': CAPTION_WIDTH,
        'complete_sentence_per_cue': True, 'sentences': layouts}, ensure_ascii=False, indent=2) + '\n')

# Each entry is a fixed camera cut. Long original sentences keep their single cue
# while their visual clauses can advance through several compositions.
SCENES = [
    ('establish', 0, 3.11, [1], '21 classmates, paired desks, rear aisle'),
    ('narrow', 3.11, 6.26, [2], 'protagonist and present deskmate in their seats'),
    ('rows', 6.26, 10.75, [3], 'ordered paired desk rows'),
    ('platform', 10.75, 16.83, [3], 'one-step podium and elevated teacher desk'),
    ('rear', 16.83, 21.4, [4], 'real empty rear aisle'),
    ('enclosure', 21.4, 26.5, [4], 'tight desk/chair spacing, anchored bodies'),
    ('river-boundary', 26.5, 30.7, [5], 'river and its visible banks, literary image'),
    ('friends', 30.7, 35.37, [5], 'back to classmates in the same classroom'),
    ('friend-pair', 35.37, 39.9, [6], 'quiet book sharing, eyelids and lips'),
    ('little-worlds', 39.9, 42.3, [7], 'separate conversational groups'),
    ('front-group', 42.3, 44.71, [7], 'three grounded friends by the podium'),
    ('window-seat', 44.71, 47.98, [8], 'left-window seat with present deskmate'),
    ('crowded-thought', 47.98, 53.07, [9], 'fixed closer protagonist composition'),
    ('window-dream', 53.07, 57.88, [10], 'closed sliding window, courtyard beyond'),
    ('glances', 57.88, 61.11, [11], 'a fixed cut to classmates, no invented speech'),
    ('hesitation', 61.11, 66.94, [12], 'silent protagonist with restrained blinking'),
    ('empty-seat', 66.94, 70.3, [13], 'deskmate absent, his chair and bag retained'),
    ('reach', 70.3, 75.05, [13], 'first person, sleeves continuously reach into frame'),
    ('latch', 75.05, 78.65, [14], 'first-person detail of fingers at the window latch'),
    ('slide', 78.65, 84.55, [14], 'two rigid panes move horizontally on two tracks'),
    ('first-air', 84.55, 87.65, [14], 'hands lower, clear aperture, air and wet glints'),
    ('cool-room', 87.65, 90.94, [14], 'cut back to the same class in cool rain light'),
    ('open-yard', 90.94, 93.2, [15], 'new open-window composition with wet courtyard'),
    ('room-embrace', 93.2, 95.35, [15], 'cool window seat and surrounding classmates'),
    ('breeze', 95.35, 98.4, [16], 'window air and courtyard leaves'),
    ('river-dusk', 98.4, 102.4, [16], 'flowing water reflections toward dusk'),
    ('river-detail', 102.4, 105.3, [16], 'separate fixed detail of the water current'),
    ('social', 105.3, 110.0, [17], 'imagined relaxed school conversation'),
    ('confidence', 110.0, 115.37, [17], 'same original protagonist in a closer dream cut'),
    ('knight', 115.37, 119.7, [18], 'original knight character walks with a foot anchor'),
    ('knight-pause', 119.7, 122.2, [18], 'pause by the school-as-court, fountain droplets'),
    ('return-seat', 122.2, 126.1, [19], 'return to the real desk in evening'),
    ('return-wide', 126.1, 129.71, [19], 'classroom enclosure remains'),
    ('symptom', 129.71, 134.52, [20], 'the open window still breathes in the dark'),
    ('night-light', 134.52, 141, [21], 'one remaining window light, two-second ending'),
]


def fixed_crop(im: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H
    assert (x1 - x0) * 9 == (y1 - y0) * 16, 'A cut must not stretch character anatomy'
    return im.crop(box).resize((W, H), NEAREST)


class Film(old.Film):
    def __init__(self):
        super().__init__()
        for name in ('hero-with-mate', 'mate-turn', 'classroom-rear', 'classroom-cool'):
            self.plates[name] = Image.open(P / 'assets' / (name + '.png')).convert('RGB').resize((W, H), NEAREST)
        self.window_masks['hero-with-mate'] = self.window_masks['hero-close']
        for name in ('classroom-rear', 'classroom-cool'):
            mask = Image.new('L', (W, H))
            ImageDraw.Draw(mask).polygon([(0, 58), (106, 1), (106, 70), (0, 187)], fill=255)
            rgb = np.asarray(self.plates[name]).astype(np.int16)
            valid = (rgb[..., 2] > rgb[..., 0] * .96) & (rgb.max(axis=2) > 80)
            self.window_masks[name] = np.asarray(mask) * valid.astype(np.uint8)

    @staticmethod
    def opening_progress(t: float) -> float:
        return old.ease((t - 78.65) / 5.9)

    def micro_faces(self, im: Image.Image, t: float, close: bool = False):
        # Only eyes/lips move; necks, shoulders, hips, chairs and feet never drift.
        faces = [(346, 66, .0), (377, 69, 1.6), (408, 74, 3.3)] if close else [(337, 76, .0), (363, 70, 1.6), (394, 75, 3.3)]
        d = ImageDraw.Draw(im)
        for x, y, phase in faces:
            if (t + phase) % 5.3 < .12:
                d.line((x - 2, y, x + 1, y), fill='#725339')
            if (t + phase) % 6.8 < 2.6 and int(t * 3 + phase) % 3 == 0:
                d.line((x, y + 5, x + 1, y + 5), fill='#ad7061')

    def room(self, name: str, t: float) -> Image.Image:
        if name in ('classroom-wide', 'classmates', 'classroom-night'):
            im = super().classroom(name, t)
            if name == 'classmates':
                self.micro_faces(im, t, close=True)
            return im
        im = self.plates[name].copy()
        self.rain_layer(im, t, self.window_masks[name], 48)
        if name == 'classroom-rear':
            self.bubble(im, 330, 44, t, 1.1)
            self.bubble(im, 230, 131, t, 3.8)
            # A notebook's small sheet corner, without moving the student's arms.
            if (t + .7) % 6.1 < .35:
                d = ImageDraw.Draw(im)
                d.polygon([(141, 106), (145, 102), (145, 107)], fill='#e6ddbd')
        else:
            self.breeze(im, t, .30)
            layer = Image.new('RGBA', (W, H))
            d = ImageDraw.Draw(layer)
            for k in range(12):
                x, y = 38 + k * 4, 208 - k * 7
                alpha = int(30 + 18 * math.sin(t * .8 + k * .8))
                d.line((x, y, x + 4, y - 1), fill=(170, 214, 223, alpha))
            im.paste(layer, (0, 0), layer)
        return im

    def hero_present(self, t: float) -> Image.Image:
        im = self.plates['hero-with-mate'].copy()
        # This is a generated second key pose. Only the head rectangle is animated;
        # its chair, torso, arms, feet and all surrounding artwork remain anchored.
        if any(a <= t < b for a, b in ((3.8, 5.3), (46.0, 47.4), (49.0, 50.9), (63.2, 64.6))):
            box = (264, 53, 345, 118)
            im.paste(self.plates['mate-turn'].crop(box), box[:2])
        self.rain_layer(im, t, self.window_masks['hero-with-mate'], 60)
        if (t + 1.05) % 4.9 < .14:
            box = (176, 82, 190, 99)
            im.paste(self.plates['hero-blink'].crop(box), box[:2])
        d = ImageDraw.Draw(im)
        if (t + .4) % 5.8 < .4:
            d.polygon([(308, 160), (314, 154), (314, 161)], fill='#f7e9c6')
        return im

    def window(self, t: float, open_shot: bool = False, dream: bool = False) -> Image.Image:
        im = self.plates['courtyard'].copy()
        self.rain_layer(im, t, None, 60)
        lp, rp = self.pane_progress(t)
        if dream:
            lp, rp = 0., 0.
        if open_shot:
            lp, rp = 1., 1.
        pw, x0, top, bottom = 105, 30, 23, 217
        left_x = x0 + pw - round(lp * pw)
        right_x = x0 + 2 * pw + round(rp * pw)
        glass = Image.new('RGBA', (W, H))
        gd = ImageDraw.Draw(glass)
        for k, x in enumerate((x0, x0 + 3 * pw, left_x, right_x)):
            gd.rectangle((x + 3, top + 2, x + pw - 3, bottom - 2), fill=(171, 200, 220, 27))
            gd.rectangle((x, top, x + pw, bottom), outline=(42, 58, 75, 255), width=3)
            gd.line((x + 1, top + 2, x + 1, bottom - 2), fill=(184, 205, 214, 255))
            gd.line((x + pw - 1, top + 2, x + pw - 1, bottom - 2), fill=(207, 218, 219, 255))
            gd.line((x + 2, top + 2, x + pw - 2, top + 2), fill=(219, 229, 219, 255))
            for dot in range(9):
                gd.point((x + 8 + (dot * 37 + k * 13) % 85, top + 14 + (dot * 29 + k * 17) % 168), fill=(222, 232, 235, 100))
        for x in (left_x + pw - 7, right_x + 4):
            gd.rectangle((x, 113, x + 3, 133), fill=(44, 59, 70, 255))
            gd.line((x + 1, 115, x + 1, 130), fill=(190, 203, 209, 255))
        im.paste(glass, (0, 0), glass)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 16), fill='#d9c6aa')
        d.rectangle((0, 0, 24, H), fill='#cbbbab')
        d.rectangle((456, 0, W, H), fill='#bbaea2')
        d.rectangle((0, 229, W, H), fill='#bdb39f')
        d.rectangle((22, 16, 457, 224), outline='#27394c', width=4)
        d.line((28, 20, 451, 20), fill='#e4e4cf', width=2)
        d.line((27, 222, 452, 222), fill='#728d9c', width=2)
        d.line((27, 225, 452, 225), fill='#e6d1ac', width=2)
        d.polygon([(18, 228), (459, 228), (476, 244), (3, 244)], fill='#c69b65')
        d.line((18, 229, 459, 229), fill='#f0d29b', width=2)
        d.line((3, 244, 476, 244), fill='#826950', width=2)
        for y in (234, 239):
            d.line((30, y, 449, y), fill='#b08457')
        if not dream and lp + rp > .6:
            self.breeze(im, t, .60)
        if not dream and not open_shot and 70.3 < t < 88:
            left, right = self.hands
            # One hand reaches the latch first. The other reaches its own sash only
            # after the left has made enough room; the two silhouettes never clasp.
            for hand, side, x, reach_start, reach_dur, release_start in (
                (left, 0, left_x + pw - 5, 70.3, 3.0, 84.7),
                (right, 1, right_x + 5, 79.2, 1.0, 85.4),
            ):
                if t < reach_start:
                    continue
                reach = old.ease((t - reach_start) / reach_dur)
                lower = old.ease((t - release_start) / 2.0)
                grip_y = round(115 + (1 - reach) * 145 + lower * 155)
                hx = x - round(hand.width * (.80 if side == 0 else .20))
                base_y = grip_y - 11 + round(hand.height * .90)
                if base_y < H:
                    d = ImageDraw.Draw(im)
                    if side == 0:
                        poly = [(hx + 2, base_y - 5), (hx + round(hand.width * .59), base_y - 5), (hx + round(hand.width * .36), H + 6), (hx - 43, H + 6)]
                        shade = [(hx + round(hand.width * .47), base_y), (hx + round(hand.width * .58), base_y), (hx + round(hand.width * .36), H + 6), (hx + round(hand.width * .19), H + 6)]
                    else:
                        poly = [(hx + round(hand.width * .41), base_y - 5), (hx + hand.width - 2, base_y - 5), (hx + hand.width + 43, H + 6), (hx + round(hand.width * .64), H + 6)]
                        shade = [(hx + round(hand.width * .42), base_y), (hx + round(hand.width * .54), base_y), (hx + round(hand.width * .81), H + 6), (hx + round(hand.width * .64), H + 6)]
                    d.polygon(poly, fill='#f4e7bf', outline='#29354e', width=2)
                    d.polygon(shade, fill='#b7adc0')
                    # Creases continue the sprite's pixel shading down the sleeve.
                    sleeve_mask = Image.new('L', (W, H))
                    ImageDraw.Draw(sleeve_mask).polygon(poly, fill=255)
                    folds = Image.new('RGBA', (W, H))
                    fd = ImageDraw.Draw(folds)
                    for j in range(4):
                        fy = base_y + 14 + j * 19
                        fx = hx + 7 - j * 7 if side == 0 else hx + hand.width - 13 + j * 7
                        fd.line((fx - 8, fy + 3, fx + 5, fy), fill=(207, 191, 164, 210), width=2)
                        fd.line((fx - 7, fy + 6, fx + 3, fy + 4), fill=(255, 244, 205, 210), width=1)
                    a = np.asarray(folds.getchannel('A')).astype(np.uint16)
                    folds.putalpha(Image.fromarray((a * np.asarray(sleeve_mask) // 255).astype(np.uint8)))
                    im.paste(folds, (0, 0), folds)
                im.paste(hand, (hx, grip_y - 11), hand)
            if 75.5 < t < 78.65:
                d = ImageDraw.Draw(im)
                if t < 76.4:
                    d.rectangle((239, 120, 241, 127), fill='#cfdee1', outline='#334559')
                else:
                    d.rectangle((233, 123, 240, 125), fill='#cfdee1', outline='#334559')
        if open_shot:
            # An independent composition with exactly 16:9 framing.
            im = fixed_crop(im, (24, 14, 456, 257))
        return im

    @staticmethod
    def pane_progress(t: float) -> tuple[float, float]:
        return old.ease((t - 78.65) / 4.2), old.ease((t - 80.2) / 4.35)

    def raw(self, sid: str, t: float) -> Image.Image:
        if sid in ('establish', 'rows', 'platform', 'rear', 'enclosure'):
            im = self.room('classroom-rear', t)
            if sid == 'rows':
                return fixed_crop(im, (48, 45, 432, 261))
            if sid == 'platform':
                return fixed_crop(im, (128, 0, 384, 144))
            if sid == 'enclosure':
                return fixed_crop(im, (64, 85, 384, 265))
            return im
        if sid in ('narrow', 'window-seat', 'crowded-thought', 'hesitation'):
            im = self.hero_present(t)
            if sid == 'crowded-thought':
                return fixed_crop(im, (56, 35, 440, 251))
            return im
        if sid == 'empty-seat':
            return self.hero(t)
        if sid in ('friends', 'friend-pair', 'little-worlds', 'front-group', 'glances'):
            im = self.room('classroom-rear', t)
            if sid == 'friend-pair':
                return fixed_crop(im, (176, 106, 432, 250))
            if sid in ('front-group', 'glances'):
                return fixed_crop(im, (248, 15, 472, 141))
            if sid == 'little-worlds':
                self.bubble(im, 368, 159, t, 4.1)
            return im
        if sid == 'window-dream':
            return self.window(t, dream=True)
        if sid in ('reach', 'latch', 'slide', 'first-air'):
            im = self.window(t)
            if sid == 'latch':
                return fixed_crop(im, (80, 60, 400, 240))
            return im
        if sid in ('cool-room', 'room-embrace'):
            im = self.room('classroom-cool', t)
            if sid == 'room-embrace':
                return fixed_crop(im, (48, 74, 304, 218))
            return im
        if sid in ('open-yard', 'breeze'):
            im = self.window(t, open_shot=True)
            if sid == 'breeze':
                self.breeze(im, t, .70)
            return im
        if sid in ('river-boundary', 'river-dusk', 'river-detail'):
            im = self.river(t)
            if sid == 'river-boundary':
                # The same motif first appears in clearer daylight, then in dusk.
                return Image.blend(im, Image.new('RGB', (W, H), '#d1ebdb'), .11)
            if sid == 'river-detail':
                return fixed_crop(im, (144, 117, 400, 261))
            return im
        if sid in ('social', 'confidence'):
            im = self.social(t)
            if sid == 'confidence':
                return fixed_crop(im, (80, 43, 464, 259))
            return im
        if sid in ('knight', 'knight-pause'):
            im = self.knight_scene(t)
            if sid == 'knight-pause':
                return fixed_crop(im, (96, 70, 352, 214))
            return im
        if sid == 'symptom':
            im = self.window(t, open_shot=True)
            return Image.blend(im, Image.new('RGB', (W, H), '#12213e'), .62)
        im = self.room('classroom-night', t)
        if sid == 'return-seat':
            return fixed_crop(im, (40, 52, 296, 196))
        return im

    def frame(self, t: float) -> Image.Image:
        i = next(i for i, s in enumerate(SCENES) if s[1] <= t < s[2])
        sid, start, end, _, _ = SCENES[i]
        im = self.raw(sid, t)
        # Short dissolves only at emotional transitions; each source camera is fixed.
        if i and sid in ('river-boundary', 'river-dusk', 'social', 'knight', 'return-seat', 'symptom') and t < start + .25:
            previous = self.raw(SCENES[i - 1][0], start - .02)
            im = Image.blend(previous, im, old.ease((t - start) / .25))
        if t < .4:
            im = Image.blend(Image.new('RGB', (W, H), '#141a2c'), im, old.ease(t / .4))
        if t > 139.5:
            im = Image.blend(im, Image.new('RGB', (W, H), '#101424'), old.ease((t - 139.5) / 1.5))
        return im


def ambience() -> None:
    rate, n = 48000, 48000 * SECONDS
    rng = np.random.default_rng(1842)
    noise = rng.normal(0, 1, n).astype(np.float32)
    c = np.concatenate(([0.0], np.cumsum(noise, dtype=np.float64)))
    rain = np.pad(((c[5:] - c[:-5]) / 5).astype(np.float32), (0, 4)) * .0030
    c = np.concatenate(([0.0], np.cumsum(rng.normal(0, 1, n), dtype=np.float64)))
    wind = np.pad(((c[161:] - c[:-161]) / 161).astype(np.float32), (0, 160))
    tt = np.arange(n, dtype=np.float32) / rate
    wind *= (.012 + .048 * np.clip((tt - 78.65) / 5.9, 0, 1))
    sound = rain + wind
    frequencies = [220., 261.626, 329.628, 293.665, 196., 246.942, 293.665, 220.]
    for k, start in enumerate(np.arange(0, SECONDS, 3.4)):
        a, b = round(start * rate), min(n, round((start + 5) * rate))
        dt = np.arange(b - a, dtype=np.float32) / rate
        env = np.exp(-dt / 1.8) * (1 - np.exp(-dt * 18))
        f = frequencies[k % len(frequencies)]
        sound[a:b] += (np.sin(2 * np.pi * f * dt) + .13 * np.sin(4 * np.pi * f * dt)) * env * .005
    for moment, length, gain, freq in [(76.4, .10, .025, 850), (78.65, 5.9, .006, 180), (84.55, .08, .016, 540)]:
        a, b = round(moment * rate), round((moment + length) * rate)
        dt = np.arange(b - a) / rate
        env = np.minimum(1, dt / .025) * np.minimum(1, (length - dt) / .045)
        sound[a:b] += (np.sin(2 * np.pi * freq * dt) * .3 + noise[a:b] * .25) * gain * env
    fade = np.minimum(1, tt / .8) * np.minimum(1, (SECONDS - tt) / 1.5)
    stereo = np.stack([(sound + rain * .08) * fade, (sound - rain * .08) * fade], axis=1)
    with wave.open(str(P / 'ambience.wav'), 'wb') as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes((np.clip(stereo, -.95, .95) * 32767).astype('<i2').tobytes())


PREVIEW_TIMES = [round((s[1] + min(s[2], 139.0)) / 2, 3) for s in SCENES]


def previews(film: Film, encoded: bool = False):
    folder = P / 'previews'
    folder.mkdir(exist_ok=True)
    for i, t in enumerate(PREVIEW_TIMES):
        target = folder / f'{i + 1:02d}-{SCENES[i][0]}.png'
        if encoded:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(VIDEO), '-frames:v', '1', str(target)], check=True)
        else:
            film.frame(t).resize((1920, 1080), NEAREST).save(target)
    # Separate geometry review includes closed, grasp, half-open, fully open, hands down.
    if not encoded:
        for t in (69, 74, 76, 81.6, 84.6, 89):
            film.window(t).resize((1920, 1080), NEAREST).save(folder / f'window-{t}.png')
    sheet = Image.new('RGB', (1920, 3 * 216), '#141b2a')
    for cell, i in enumerate((0, 2, 3, 4, 7, 8, 11, 16, 18, 19, 21, 24, 25, 29, 34)):
        source = folder / f'{i + 1:02d}-{SCENES[i][0]}.png'
        with Image.open(source) as im:
            sheet.paste(im.resize((384, 216), NEAREST), ((cell % 5) * 384, (cell // 5) * 216))
    # 5 columns x3 rows, with no unused rows.
    sheet.crop((0, 0, 1920, 648)).save(P / 'storyboard.png')
    with Image.open(folder / '20-slide.png') as im:
        im.save(P / 'poster.png')


def render(film: Film):
    voice = old.narration_wave()
    ambience()
    work = P / '_work'
    mix = work / 'mixed.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(voice), '-i', str(P / 'ambience.wav'), '-filter_complex',
                    '[0:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-17:TP=-2:LRA=9,apad=whole_dur=141[v];[v][1:a]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.94:level=0,afade=t=out:st=139.5:d=1.5[m]',
                    '-map', '[m]', '-ar', '48000', '-t', '141', str(mix)], check=True)
    command = ['ffmpeg', '-hide_banner', '-y', '-nostats', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '480x270', '-r', '24', '-i', '-',
               '-i', str(mix), '-i', str(P / 'chapters.ffmeta'), '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '2', '-map_chapters', '2',
               '-vf', f"scale=1920:1080:flags=neighbor,ass={P / 'subtitles.ass'}", '-c:v', 'libx264', '-threads', '4', '-preset', 'medium', '-crf', '18',
               '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-metadata', 'title=窗 · 丰富分镜第二版', '-metadata:s:a:0', 'title=曼波朗读 · 全文',
               '-t', '141', '-movflags', '+faststart', str(VIDEO)]
    (work / 'render-command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2) + '\n')
    started = time.monotonic()
    with open(P / 'render.log', 'w') as log:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for i in range(FPS * SECONDS):
                proc.stdin.write(film.frame(i / FPS).tobytes())
                if i % (FPS * 10) == 0:
                    print(f'Rendering {i / FPS:.0f}/{SECONDS}s; elapsed {time.monotonic() - started:.1f}s', flush=True)
            proc.stdin.close()
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        if proc.wait() != 0:
            raise RuntimeError('FFmpeg failed; inspect full-film-v2/render.log')
    print(f'Render complete: {VIDEO.name}, {time.monotonic() - started:.1f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    assert SCENES[0][1] == 0 and SCENES[-1][2] == SECONDS
    assert all(a[2] == b[1] for a, b in zip(SCENES, SCENES[1:]))
    subtitles()
    shots = [{'id': s[0], 'start': s[1], 'end': s[2], 'sentences': s[3], 'action': s[4], 'camera': 'fixed'} for s in SCENES]
    (P / 'shots.json').write_text(json.dumps({'title': '窗 · 第二版', 'style': '强化像素 · 掌机 RPG A', 'logical_dimensions': [W, H], 'dimensions': [1920, 1080], 'fps': FPS, 'duration_seconds': SECONDS, 'voice': '曼波朗读', 'shots': shots}, ensure_ascii=False, indent=2) + '\n')
    film = Film()
    previews(film)
    if not args.preview_only:
        render(film)
        previews(film, encoded=True)


if __name__ == '__main__':
    main()
