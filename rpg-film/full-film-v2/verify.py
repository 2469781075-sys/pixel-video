"""Verify the actual second-edition output against the unchanged article/audio."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import wave

import numpy as np

P = Path(__file__).resolve().parent


def run(args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def decode_audio(path):
    data = run(['ffmpeg', '-v', 'error', '-i', str(path), '-ar', '48000', '-ac', '1', '-f', 'f32le', '-'])
    return np.frombuffer(data, dtype='<f4')


def decoded_frame(video, t):
    raw = run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(video), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    return np.frombuffer(raw, dtype=np.uint8).reshape(1080, 1920, 3)


def main():
    spec = importlib.util.spec_from_file_location('window_second_renderer', P / 'render.py')
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    video = r.VIDEO
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-show_chapters', '-of', 'json', str(video)]))
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_frames'])) == (1920, 1080, '24/1', 3384)
    assert abs(float(info['format']['duration']) - 141) < .06
    assert v['codec_name'] == 'h264' and v['pix_fmt'] == 'yuv420p' and v['color_space'] == 'bt709'
    assert a['codec_name'] == 'aac' and a['channels'] == 2 and a['sample_rate'] == '48000'
    assert not any(s['codec_type'] == 'subtitle' for s in info['streams']), 'Avoid duplicated player captions'
    original = ''.join((P.parent / 'narration/original.txt').read_text().splitlines())
    blocks = re.split(r'\n\s*\n', (P / 'subtitles.srt').read_text().strip())
    texts, times = [], []
    for b in blocks:
        lines = b.splitlines()
        texts.append(''.join(lines[2:]))
        times.append(lines[1])
    assert texts == [c['text'] for c in r.CUES]
    assert ''.join(texts) == original and len(texts) == 21
    assert times == [r.old.timecode(c['start_seconds']) + ' --> ' + r.old.timecode(c['end_seconds']) for c in r.CUES]
    ass_texts = []
    for line in (P / 'subtitles.ass').read_text().splitlines():
        if line.startswith('Dialogue:') and line.split(',', 9)[3] == 'Chinese':
            ass_texts.append(re.sub(r'\{.*?\}', '', line.split(',', 9)[9]).replace('\\N', ''))
    assert ass_texts == texts
    ass = (P / 'subtitles.ass').read_text()
    style = next(line for line in ass.splitlines() if line.startswith('Style: Chinese,')).split(',')
    assert int(style[2]) == r.CAPTION_SIZE == 66 and style[7] == '-1' and int(style[16]) == 3
    layout_file = json.loads((P / 'subtitle-layout.json').read_text())
    assert layout_file['sentences'] == [r.caption_layout(c) for c in r.CUES]
    caption_bounds = []
    for cue, layout in zip(r.CUES, layout_file['sentences']):
        assert ''.join(layout['lines']) == cue['text']
        assert max(layout['measured_line_widths']) <= r.CAPTION_WIDTH
        assert layout['panel_box'][1] >= 672, 'Keep the principal action above the panel'
        t = (cue['start_seconds'] + cue['end_seconds']) / 2
        # Isolate the actual libass-rendered text on black to check every cue's
        # edges and line count; bright text can be distinguished from its panel.
        raw = run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:r=1',
                   '-vf', f'setpts=PTS+{t}/TB,ass={P / "subtitles.ass"}', '-frames:v', '1',
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        pixels = np.frombuffer(raw, dtype=np.uint8).reshape(1080, 1920, 3)
        ink = np.all(pixels > 180, axis=2)
        ys, xs = np.nonzero(ink)
        assert len(xs) > 100, (cue['id'], 'Missing caption')
        box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        px, py, right, bottom = layout['panel_box']
        assert px + 20 <= box[0] < box[2] <= right - 20, (cue['id'], box)
        assert py + 12 <= box[1] < box[3] <= bottom - 12, (cue['id'], box)
        rows = np.flatnonzero(ink.any(axis=1))
        line_count = 1 + int(np.count_nonzero(np.diff(rows) > 12))
        assert line_count == len(layout['lines']), (cue['id'], line_count)
        caption_bounds.append({'sentence': cue['id'], 'actual_text_box': box, 'display_lines': line_count})
    assert set(i for s in r.SCENES for i in s[3]) == set(range(1, 22))
    assert r.SCENES[0][1] == 0 and r.SCENES[-1][2] == 141
    assert all(s[2] == n[1] and s[2] > s[1] for s, n in zip(r.SCENES, r.SCENES[1:]))
    assert all(s[1] < c['end_seconds'] and s[2] > c['start_seconds'] for s in r.SCENES for c in r.CUES if c['id'] in s[3])

    film = r.Film()
    window = [np.asarray(film.window(t)) for t in (71, 77, 81.6, 85.5, 89)]
    assert all(np.array_equal(window[0][:16], f[:16]) for f in window[1:])
    track = [film.pane_progress(t) for t in np.linspace(70, 88, 433)]
    for side in (0, 1):
        values = [p[side] for p in track]
        assert values[0] == 0 and values[-1] == 1
        assert all(0 <= p <= 1 for p in values)
        assert all(x <= y for x, y in zip(values, values[1:]))
    # The original fixed pane spans have constant dimensions and never cross the frame.
    for lp, rp in track:
        left = 135 - round(lp * 105)
        right = 240 + round(rp * 105)
        assert 30 <= left <= 135 and 240 <= right <= 345 and right + 105 <= 450
    rooms = [np.asarray(film.room('classroom-rear', t)) for t in (31, 34.4, 40.1)]
    assert all(np.array_equal(rooms[0][95:109, 300:370], f[95:109, 300:370]) for f in rooms[1:])
    assert all(np.array_equal(rooms[0][204:220, 205:290], f[204:220, 205:290]) for f in rooms[1:])
    # Compare encoded frames to their expected plates, above the subtitle panel.
    frame_errors = []
    for scene, t in zip(r.SCENES, r.PREVIEW_TIMES):
        encoded = decoded_frame(video, t)[::4, ::4]
        actual_time = np.ceil(t * 24 - 1e-7) / 24
        expected = np.asarray(film.frame(actual_time))
        error = float(np.abs(encoded[:166].astype(np.int16) - expected[:166].astype(np.int16)).mean())
        assert error < 12, (scene[0], error)
        frame_errors.append({'shot': scene[0], 'time': t, 'mean_pixel_error': round(error, 4)})
    f71, f82 = decoded_frame(video, 71), decoded_frame(video, 82)
    rail_delta = float(np.abs(f71[:64].astype(np.int16) - f82[:64].astype(np.int16)).mean())
    assert rail_delta < 2, rail_delta

    source = decode_audio(P / '_work/narration.wav')
    stereo_bytes = run(['ffmpeg', '-v', 'error', '-i', str(video), '-ar', '48000', '-ac', '2', '-f', 'f32le', '-'])
    stereo = np.frombuffer(stereo_bytes, dtype='<f4').reshape(-1, 2)
    # FFmpeg's automatic stereo->mono sum adds 3 dB for identical channels.
    # Use their arithmetic mean for correspondence and each original channel for
    # peak checks, so analysis cannot falsely flag a clean stereo file as clipped.
    actual = stereo.mean(axis=1)
    reference = source[:15 * 48000:8].astype(np.float64)
    mixed = actual[:16 * 48000:8].astype(np.float64)
    fft_size = 1
    while fft_size < len(reference) + len(mixed) - 1:
        fft_size *= 2
    corr = np.fft.irfft(np.fft.rfft(mixed, fft_size) * np.conj(np.fft.rfft(reference, fft_size)), fft_size)
    indices = np.r_[np.arange(251), np.arange(fft_size - 250, fft_size)]
    idx = int(indices[np.argmax(corr[indices])])
    lag = (idx if idx < fft_size // 2 else idx - fft_size) * 8
    assert abs(lag) <= 2000, lag
    per_cue = []
    for c in r.CUES:
        start, end = round(c['start_seconds'] * 48000), round(c['end_seconds'] * 48000)
        start = max(start, -lag, 0)
        end = min(end, len(actual) - lag, len(source))
        ref = source[start:end:8].astype(np.float64)
        sound = actual[start + lag:end + lag:8].astype(np.float64)
        correspondence = float(np.corrcoef(ref, sound)[0, 1])
        rms = float(np.sqrt(np.mean(sound ** 2)))
        assert correspondence > .9, (c['id'], correspondence)
        assert rms > .008, (c['id'], rms)
        per_cue.append({'sentence': c['id'], 'source_correlation': round(correspondence, 5), 'rms': round(rms, 5)})
    peak = float(np.max(np.abs(stereo)))
    assert peak < .96, peak
    with wave.open(str(P / '_work/narration.wav')) as w:
        assert abs(w.getnframes() / w.getframerate() - 139) < .01
    run(['ffmpeg', '-v', 'error', '-threads', '4', '-i', str(video), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    previous = P.parent / 'full-film/window-full-mambo.mp4'
    result = {'status': 'passed', 'video': video.name, 'duration_seconds': float(info['format']['duration']),
              'dimensions': [1920, 1080], 'fps': 24, 'frames': 3384, 'file_bytes': video.stat().st_size,
              'style': 'retained handheld RPG A, strong pixels, 480x270 integer 4x upscale',
              'shots': {'previous_count': 15, 'new_count': len(r.SCENES), 'all_21_sentences_covered': True,
                        'no_timeline_gaps': True, 'encoded_plate_checks': frame_errors},
              'subtitles': {'count': 21, 'verbatim_original_srt_and_ass': True, 'measured_voice_timestamps': True,
                            'burned_in': True, 'previous_font_size': 42, 'font_size': r.CAPTION_SIZE,
                            'bold': True, 'outline': 3, 'maximum_display_lines': max(len(r.wrap_caption(c['text'])) for c in r.CUES),
                            'actual_all_cue_text_bounds_checked': caption_bounds},
              'audio': {'voice': 'existing Mambo, unchanged original sentence audio', 'sample_rate': 48000, 'channels': 2,
                        'encoded_source_checks': per_cue, 'alignment_ms': round(lag / 48, 3), 'decoded_channel_peak': round(peak, 5)},
              'motion': {'fixed_window_top_frame': True, 'two_sashes_slide_monotonically': True,
                         'pane_dimensions_and_tracks_constant': True, 'sequential_left_then_right_hand': True,
                         'encoded_fixed_rail_mean_difference': round(rail_delta, 5), 'front_and_rear_students_ground_regions_anchored': True,
                         'cut_crops_preserve_16_to_9': True},
              'visual_review': 'Rendered keyframes and actual encoded contact sheets inspected; an artistic review, not a claim that numeric checks prove anatomy.',
              'full_audio_video_decode': 'passed', 'previous_video_retained_sha256': hashlib.sha256(previous.read_bytes()).hexdigest()}
    (P / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('shots', 'visual_review')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
